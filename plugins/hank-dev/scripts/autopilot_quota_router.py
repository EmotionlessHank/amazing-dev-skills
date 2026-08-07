#!/usr/bin/env python3
"""Autopilot 配额感知路由的默认拒绝纯函数与唯一调度入口。"""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
import posixpath
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable, Iterable, Mapping, Sequence


ALLOW = "ALLOW"
AWAITING_APPROVAL = "AWAITING_APPROVAL"
PARTIAL_BLOCKED = "PARTIAL_BLOCKED"

DAILY_TARGET_PERCENT = 25.0
PER_WORKER_RESERVE_PERCENT = 5.0
DEFAULT_MAX_PARALLEL_WORKERS = 3
DEFAULT_SNAPSHOT_MAX_AGE_SECONDS = 900
VALID_EFFORTS = {"high", "xhigh", "max"}

Decision = dict[str, Any]
Launcher = Callable[[Mapping[str, Any], Decision], Any]

__all__ = [
    "ALLOW",
    "AWAITING_APPROVAL",
    "PARTIAL_BLOCKED",
    "decide_batch_route",
    "dispatch_wave",
    "plan_execution_waves",
]


def _decision(
    status: str,
    reason_code: str,
    batch_id: str,
    *,
    selected_tier: str | None = None,
    selected_model: str | None = None,
    reasoning_effort: str | None = None,
    daily_headroom_percent: float | None = None,
    reserved_percent: float | None = None,
) -> Decision:
    return {
        "status": status,
        "reason_code": reason_code,
        "batch_id": batch_id,
        "selected_tier": selected_tier,
        "selected_model": selected_model,
        "reasoning_effort": reasoning_effort,
        "daily_headroom_percent": daily_headroom_percent,
        "reserved_percent": reserved_percent,
    }


def _as_percent(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if 0.0 <= number <= 100.0 else None


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _snapshot_error(usage: Any, runtime: Any) -> str | None:
    if not isinstance(usage, Mapping):
        return "USAGE_SNAPSHOT_REQUIRED"
    if not isinstance(runtime, Mapping):
        return "TRUSTED_RUNTIME_REQUIRED"

    period_id = usage.get("period_id")
    if not isinstance(period_id, str) or not period_id:
        return "USAGE_PERIOD_REQUIRED"
    current_period_id = runtime.get("current_period_id")
    if not isinstance(current_period_id, str) or not current_period_id:
        return "CURRENT_PERIOD_REQUIRED"
    if period_id != current_period_id:
        return "USAGE_PERIOD_MISMATCH"

    captured_at = _parse_timestamp(usage.get("captured_at"))
    evaluated_at = _parse_timestamp(runtime.get("now"))
    max_age_seconds = runtime.get("snapshot_max_age_seconds")
    if (
        captured_at is None
        or evaluated_at is None
        or isinstance(max_age_seconds, bool)
        or not isinstance(max_age_seconds, (int, float))
        or max_age_seconds <= 0
    ):
        return "USAGE_FRESHNESS_REQUIRED"

    age_seconds = (evaluated_at - captured_at).total_seconds()
    if age_seconds < 0 or age_seconds > float(max_age_seconds):
        return "USAGE_SNAPSHOT_STALE"

    if _as_percent(usage.get("weekly_remaining_percent")) is None:
        return "WEEKLY_REMAINING_INVALID"
    if _as_percent(usage.get("today_used_percent")) is None:
        return "TODAY_USED_INVALID"
    return None


def _catalog_entry(
    model_catalog: Any, tier: str
) -> tuple[str, set[str]] | None:
    if not isinstance(model_catalog, Mapping):
        return None
    entry = model_catalog.get(tier)
    if not isinstance(entry, Mapping) or entry.get("available") is not True:
        return None

    model = entry.get("model")
    efforts = entry.get("reasoning_efforts")
    if not isinstance(model, str) or not model:
        return None
    if not isinstance(efforts, Sequence) or isinstance(efforts, (str, bytes)):
        return None
    normalized_efforts = {
        effort for effort in efforts if isinstance(effort, str) and effort in VALID_EFFORTS
    }
    return (model, normalized_efforts)


def _authorization_error(
    authorization: Any,
    *,
    request: Mapping[str, Any],
    batch_id: str,
    tier: str,
    period_id: str,
    requires_effort_raise: bool,
) -> str | None:
    if not isinstance(authorization, Mapping) or authorization.get("approved") is not True:
        return "MODEL_APPROVAL_REQUIRED"
    if authorization.get("run_id") != request.get("run_id"):
        return "MODEL_APPROVAL_RUN_MISMATCH"
    if authorization.get("period_id") != period_id:
        return "MODEL_APPROVAL_PERIOD_MISMATCH"
    if authorization.get("model_tier") != tier:
        return "MODEL_APPROVAL_TIER_MISMATCH"

    batch_ids = authorization.get("batch_ids")
    if not isinstance(batch_ids, Sequence) or isinstance(batch_ids, (str, bytes)):
        return "MODEL_APPROVAL_SCOPE_MISSING"
    if batch_id not in batch_ids:
        return "MODEL_APPROVAL_BATCH_MISMATCH"

    authorization_text = authorization.get("authorization_text")
    if not isinstance(authorization_text, str) or not authorization_text.strip():
        return "MODEL_APPROVAL_TEXT_REQUIRED"

    runtime = request.get("runtime")
    evaluated_at = _parse_timestamp(runtime.get("now")) if isinstance(runtime, Mapping) else None
    valid_until = _parse_timestamp(authorization.get("valid_until"))
    if evaluated_at is None or valid_until is None or evaluated_at > valid_until:
        return "MODEL_APPROVAL_EXPIRED"

    if requires_effort_raise:
        raised_batch_ids = authorization.get("high_to_xhigh_batch_ids")
        if (
            not isinstance(raised_batch_ids, Sequence)
            or isinstance(raised_batch_ids, (str, bytes))
            or batch_id not in raised_batch_ids
        ):
            return "EFFORT_RAISE_APPROVAL_REQUIRED"
    return None


def decide_batch_route(request: Mapping[str, Any]) -> Decision:
    """根据单个 Batch 和当前波次输入返回默认拒绝的纯路由决策。"""

    if not isinstance(request, Mapping):
        return _decision(AWAITING_APPROVAL, "ROUTE_REQUEST_REQUIRED", "")

    run_id = request.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        return _decision(AWAITING_APPROVAL, "RUN_ID_REQUIRED", "")

    batch = request.get("batch")
    if not isinstance(batch, Mapping):
        return _decision(PARTIAL_BLOCKED, "BATCH_METADATA_REQUIRED", "")

    batch_id = batch.get("id")
    if not isinstance(batch_id, str) or not batch_id:
        return _decision(PARTIAL_BLOCKED, "BATCH_ID_REQUIRED", "")

    effort = batch.get("reasoning_effort")
    effort_basis = batch.get("effort_basis")
    spark_eligible = batch.get("spark_eligible")
    spark_reasons = batch.get("spark_ineligibility_reasons")
    if effort not in VALID_EFFORTS:
        return _decision(PARTIAL_BLOCKED, "BATCH_EFFORT_INVALID", batch_id)
    if not isinstance(effort_basis, str) or not effort_basis.strip():
        return _decision(PARTIAL_BLOCKED, "EFFORT_BASIS_REQUIRED", batch_id)
    if not isinstance(spark_eligible, bool):
        return _decision(PARTIAL_BLOCKED, "SPARK_ELIGIBILITY_REQUIRED", batch_id)
    if not isinstance(spark_reasons, Sequence) or isinstance(spark_reasons, (str, bytes)):
        return _decision(PARTIAL_BLOCKED, "SPARK_REASONS_INVALID", batch_id)
    if spark_eligible is False and not spark_reasons:
        return _decision(PARTIAL_BLOCKED, "SPARK_REASONS_REQUIRED", batch_id)
    if spark_eligible is True and spark_reasons:
        return _decision(PARTIAL_BLOCKED, "SPARK_ELIGIBILITY_CONFLICT", batch_id)
    isolation_error = _batch_isolation_error(batch)
    if isolation_error:
        return _decision(PARTIAL_BLOCKED, isolation_error, batch_id)

    usage = request.get("usage")
    usage_error = _snapshot_error(usage, request.get("runtime"))
    if usage_error:
        return _decision(AWAITING_APPROVAL, usage_error, batch_id)

    wave = request.get("wave")
    worker_count = wave.get("worker_count") if isinstance(wave, Mapping) else None
    wave_batch_ids = wave.get("batch_ids") if isinstance(wave, Mapping) else None
    if (
        isinstance(worker_count, bool)
        or not isinstance(worker_count, int)
        or worker_count < 1
        or worker_count > DEFAULT_MAX_PARALLEL_WORKERS
    ):
        return _decision(PARTIAL_BLOCKED, "WAVE_WORKER_COUNT_INVALID", batch_id)
    if (
        not isinstance(wave_batch_ids, Sequence)
        or isinstance(wave_batch_ids, (str, bytes))
        or len(wave_batch_ids) != worker_count
        or any(not isinstance(item, str) or not item for item in wave_batch_ids)
        or batch_id not in wave_batch_ids
    ):
        return _decision(PARTIAL_BLOCKED, "WAVE_SCOPE_INVALID", batch_id)

    weekly_remaining = float(usage["weekly_remaining_percent"])
    today_used = float(usage["today_used_percent"])
    daily_headroom = DAILY_TARGET_PERCENT - today_used
    reserved = worker_count * PER_WORKER_RESERVE_PERCENT

    if weekly_remaining >= 25.0 and daily_headroom >= reserved:
        tier = "terra"
    elif weekly_remaining >= 10.0:
        tier = "luna"
    else:
        tier = "spark"

    catalog_entry = _catalog_entry(request.get("model_catalog"), tier)
    if catalog_entry is None:
        status = PARTIAL_BLOCKED if tier == "spark" else AWAITING_APPROVAL
        return _decision(
            status,
            f"{tier.upper()}_UNAVAILABLE",
            batch_id,
            selected_tier=tier,
            daily_headroom_percent=daily_headroom,
            reserved_percent=reserved,
        )
    selected_model, supported_efforts = catalog_entry

    selected_effort = effort
    requires_effort_raise = tier == "luna" and effort == "high"
    if requires_effort_raise:
        selected_effort = "xhigh"

    if tier == "spark" and spark_eligible is not True:
        return _decision(
            PARTIAL_BLOCKED,
            "SPARK_BATCH_INELIGIBLE",
            batch_id,
            selected_tier=tier,
            selected_model=selected_model,
            reasoning_effort=selected_effort,
            daily_headroom_percent=daily_headroom,
            reserved_percent=reserved,
        )

    if selected_effort not in supported_efforts:
        return _decision(
            PARTIAL_BLOCKED,
            "MODEL_EFFORT_UNSUPPORTED",
            batch_id,
            selected_tier=tier,
            selected_model=selected_model,
            reasoning_effort=selected_effort,
            daily_headroom_percent=daily_headroom,
            reserved_percent=reserved,
        )

    if tier in {"luna", "spark"}:
        authorization_error = _authorization_error(
            request.get("authorization"),
            request=request,
            batch_id=batch_id,
            tier=tier,
            period_id=usage["period_id"],
            requires_effort_raise=requires_effort_raise,
        )
        if authorization_error:
            return _decision(
                AWAITING_APPROVAL,
                authorization_error,
                batch_id,
                selected_tier=tier,
                selected_model=selected_model,
                reasoning_effort=selected_effort,
                daily_headroom_percent=daily_headroom,
                reserved_percent=reserved,
            )

    return _decision(
        ALLOW,
        "ROUTE_ALLOWED",
        batch_id,
        selected_tier=tier,
        selected_model=selected_model,
        reasoning_effort=selected_effort,
        daily_headroom_percent=daily_headroom,
        reserved_percent=reserved,
    )


def _normalized_worktree(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip() or not posixpath.isabs(value):
        return None
    return posixpath.normpath(value.strip())


def _normalized_branch(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    branch = value.strip()
    prefix = "refs/heads/"
    return branch[len(prefix) :] if branch.startswith(prefix) else branch


def _normalized_file(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    if posixpath.isabs(value.strip()):
        return None
    normalized = posixpath.normpath(value.strip())
    if normalized in {"", ".", ".."} or normalized.startswith("../"):
        return None
    return normalized


def _normalized_resource(value: Any) -> str | None:
    if not isinstance(value, str) or ":" not in value:
        return None
    kind, raw_identifier = value.split(":", 1)
    kind = kind.strip().lower()
    identifier = raw_identifier.strip()
    if not kind or not identifier:
        return None
    if kind == "port":
        try:
            port = int(identifier)
        except ValueError:
            return None
        if not 1 <= port <= 65535:
            return None
        identifier = str(port)
    elif kind in {"artifact", "file", "lockfile", "path"}:
        normalized = _normalized_file(identifier)
        if normalized is None:
            return None
        identifier = normalized
    return f"{kind}:{identifier}"


def _normalized_values(
    values: Any, normalizer: Callable[[Any], str | None], *, require_nonempty: bool
) -> set[str] | None:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        return None
    normalized = [normalizer(value) for value in values]
    if any(value is None for value in normalized):
        return None
    result = {value for value in normalized if value is not None}
    if require_nonempty and not result:
        return None
    return result


def _batch_isolation_error(batch: Mapping[str, Any]) -> str | None:
    if _normalized_worktree(batch.get("worktree")) is None:
        return "BATCH_WORKTREE_INVALID"
    if _normalized_branch(batch.get("branch")) is None:
        return "BATCH_BRANCH_INVALID"
    if _normalized_values(batch.get("owned_files"), _normalized_file, require_nonempty=True) is None:
        return "BATCH_OWNED_FILES_INVALID"
    if _normalized_values(
        batch.get("runtime_resources"), _normalized_resource, require_nonempty=False
    ) is None:
        return "BATCH_RUNTIME_RESOURCES_INVALID"
    dependencies = batch.get("depends_on")
    if not isinstance(dependencies, Sequence) or isinstance(dependencies, (str, bytes)):
        return "BATCH_DEPENDENCIES_INVALID"
    if any(not isinstance(item, str) or not item for item in dependencies):
        return "BATCH_DEPENDENCIES_INVALID"
    return None


def _batch_conflicts(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_identity = left.get("worktree_identity")
    right_identity = right.get("worktree_identity")
    if (
        isinstance(left_identity, str)
        and isinstance(right_identity, str)
        and left_identity == right_identity
    ):
        return True

    for key in ("worktree", "branch"):
        normalizer = _normalized_worktree if key == "worktree" else _normalized_branch
        left_value = normalizer(left.get(key))
        right_value = normalizer(right.get(key))
        if left_value is None or right_value is None:
            return True
        if left_value == right_value:
            return True

    for key, normalizer, require_nonempty in (
        ("owned_files", _normalized_file, True),
        ("runtime_resources", _normalized_resource, False),
    ):
        left_values = _normalized_values(
            left.get(key), normalizer, require_nonempty=require_nonempty
        )
        right_values = _normalized_values(
            right.get(key), normalizer, require_nonempty=require_nonempty
        )
        if left_values is None or right_values is None:
            return True
        if left_values & right_values:
            return True
    return False


def plan_execution_waves(
    batches: Sequence[Mapping[str, Any]],
    *,
    completed_batch_ids: Iterable[str] = (),
    max_parallel_workers: int = DEFAULT_MAX_PARALLEL_WORKERS,
) -> list[list[Mapping[str, Any]]]:
    """按依赖、文件所有权和运行时资源把 Batch 分配到可并行波次。"""

    if (
        isinstance(max_parallel_workers, bool)
        or not isinstance(max_parallel_workers, int)
        or not 1 <= max_parallel_workers <= DEFAULT_MAX_PARALLEL_WORKERS
    ):
        raise ValueError("max_parallel_workers 必须是 1 到 3")

    pending = list(batches)
    batch_ids = [batch.get("id") for batch in pending]
    if any(not isinstance(batch_id, str) or not batch_id for batch_id in batch_ids):
        raise ValueError("每个 Batch 必须有非空字符串 id")
    known_ids = set(batch_ids)
    if len(known_ids) != len(pending):
        raise ValueError("每个 Batch 必须有唯一 id")

    completed = set(completed_batch_ids)
    waves: list[list[Mapping[str, Any]]] = []
    while pending:
        ready = []
        for batch in pending:
            dependencies = batch.get("depends_on", [])
            if not isinstance(dependencies, Sequence) or isinstance(dependencies, (str, bytes)):
                raise ValueError(f"Batch {batch['id']} 的 depends_on 无效")
            if any(not isinstance(item, str) or not item for item in dependencies):
                raise ValueError(f"Batch {batch['id']} 的 depends_on 无效")
            unknown_dependencies = set(dependencies) - known_ids - completed
            if unknown_dependencies:
                raise ValueError(f"Batch {batch['id']} 存在未知依赖")
            if set(dependencies) <= completed:
                ready.append(batch)

        if not ready:
            raise ValueError("Batch 依赖存在循环")

        wave: list[Mapping[str, Any]] = []
        for batch in ready:
            if len(wave) >= max_parallel_workers:
                break
            if all(not _batch_conflicts(batch, existing) for existing in wave):
                wave.append(batch)

        if not wave:
            wave = [ready[0]]

        waves.append(wave)
        selected_ids = {batch["id"] for batch in wave}
        pending = [batch for batch in pending if batch["id"] not in selected_ids]
        completed.update(selected_ids)
    return waves


def dispatch_wave(
    requests: Sequence[Mapping[str, Any]], launcher: Launcher
) -> dict[str, Any]:
    """唯一 worker 调度入口，只把 ALLOW 决策交给注入的启动器。"""

    if not callable(launcher):
        return {
            "status": PARTIAL_BLOCKED,
            "decisions": [],
            "reason_code": "WORKER_LAUNCHER_INVALID",
            "launched_batch_ids": [],
            "launch_results": [],
            "may_enter_full_gate": False,
        }

    wave_error = _wave_contract_error(requests)
    if wave_error:
        return {
            "status": PARTIAL_BLOCKED,
            "decisions": [],
            "reason_code": wave_error,
            "launched_batch_ids": [],
            "launch_results": [],
            "may_enter_full_gate": False,
        }

    decisions = [decide_batch_route(request) for request in requests]
    awaiting = [decision for decision in decisions if decision["status"] == AWAITING_APPROVAL]
    blocked = [decision for decision in decisions if decision["status"] == PARTIAL_BLOCKED]

    if awaiting:
        return {
            "status": AWAITING_APPROVAL,
            "decisions": decisions,
            "launched_batch_ids": [],
            "launch_results": [],
            "may_enter_full_gate": False,
        }

    launch_results = []
    launched_batch_ids = []
    for request, decision in zip(requests, decisions, strict=True):
        if decision["status"] != ALLOW:
            continue
        launch_results.append(launcher(request["batch"], decision))
        launched_batch_ids.append(decision["batch_id"])

    status = PARTIAL_BLOCKED if blocked else ALLOW
    return {
        "status": status,
        "decisions": decisions,
        "launched_batch_ids": launched_batch_ids,
        "launch_results": launch_results,
        "may_enter_full_gate": status == ALLOW,
    }


def _wave_contract_error(requests: Sequence[Mapping[str, Any]]) -> str | None:
    if not requests:
        return "WAVE_REQUESTS_REQUIRED"
    if len(requests) > DEFAULT_MAX_PARALLEL_WORKERS:
        return "WAVE_PARALLEL_LIMIT_EXCEEDED"

    batch_ids: list[str] = []
    for request in requests:
        if not isinstance(request, Mapping):
            return "WAVE_REQUEST_INVALID"
        batch = request.get("batch")
        if not isinstance(batch, Mapping) or not isinstance(batch.get("id"), str):
            return "WAVE_BATCH_INVALID"
        batch_ids.append(batch["id"])
    if len(set(batch_ids)) != len(batch_ids):
        return "WAVE_BATCH_IDS_DUPLICATED"

    first = requests[0]
    first_batch = first.get("batch")
    first_repository_identity = (
        first_batch.get("repository_identity") if isinstance(first_batch, Mapping) else None
    )
    first_wave = first.get("wave")
    if not isinstance(first_wave, Mapping):
        return "WAVE_METADATA_REQUIRED"
    expected_batch_ids = first_wave.get("batch_ids")
    completed_batch_ids = first_wave.get("completed_batch_ids", [])
    if (
        not isinstance(expected_batch_ids, Sequence)
        or isinstance(expected_batch_ids, (str, bytes))
        or any(not isinstance(item, str) or not item for item in expected_batch_ids)
        or set(expected_batch_ids) != set(batch_ids)
        or first_wave.get("worker_count") != len(requests)
    ):
        return "WAVE_SCOPE_MISMATCH"
    if not isinstance(completed_batch_ids, Sequence) or isinstance(
        completed_batch_ids, (str, bytes)
    ):
        return "WAVE_COMPLETED_BATCHES_INVALID"
    if any(not isinstance(item, str) or not item for item in completed_batch_ids):
        return "WAVE_COMPLETED_BATCHES_INVALID"

    snapshot_fields = (
        "period_id",
        "captured_at",
        "weekly_remaining_percent",
        "today_used_percent",
    )
    first_usage = first.get("usage")
    if not isinstance(first_usage, Mapping):
        return None

    for index, request in enumerate(requests):
        wave = request.get("wave")
        usage = request.get("usage")
        batch = request.get("batch")
        repository_identity = (
            batch.get("repository_identity") if isinstance(batch, Mapping) else None
        )
        if first_repository_identity is not None or repository_identity is not None:
            if (
                not isinstance(first_repository_identity, str)
                or not isinstance(repository_identity, str)
                or repository_identity != first_repository_identity
            ):
                return "WAVE_REPOSITORY_MISMATCH"
        if request.get("run_id") != first.get("run_id"):
            return "WAVE_RUN_MISMATCH"
        if request.get("model_catalog") != first.get("model_catalog"):
            return "WAVE_MODEL_CATALOG_MISMATCH"
        if request.get("runtime") != first.get("runtime"):
            return "WAVE_RUNTIME_MISMATCH"
        if not isinstance(wave, Mapping) or dict(wave) != dict(first_wave):
            return "WAVE_METADATA_MISMATCH"
        if not isinstance(usage, Mapping) or any(
            usage.get(field) != first_usage.get(field) for field in snapshot_fields
        ):
            return "WAVE_USAGE_MISMATCH"

        dependencies = request["batch"].get("depends_on", [])
        if not isinstance(dependencies, Sequence) or isinstance(dependencies, (str, bytes)):
            return "WAVE_DEPENDENCIES_INVALID"
        if any(not isinstance(item, str) or not item for item in dependencies):
            return "WAVE_DEPENDENCIES_INVALID"
        if not set(dependencies) <= set(completed_batch_ids):
            return "WAVE_DEPENDENCIES_UNSATISFIED"

        for other in requests[index + 1 :]:
            if _batch_conflicts(request["batch"], other["batch"]):
                return "WAVE_ISOLATION_CONFLICT"
    return None


def _manifest_launcher(batch: Mapping[str, Any], decision: Decision) -> dict[str, Any]:
    return {
        "batch_id": decision["batch_id"],
        "model": decision["selected_model"],
        "reasoning_effort": decision["reasoning_effort"],
        "worktree": _normalized_worktree(batch.get("worktree")),
        "branch": _normalized_branch(batch.get("branch")),
        "owned_files": sorted(
            _normalized_values(batch.get("owned_files"), _normalized_file, require_nonempty=True)
            or []
        ),
        "runtime_resources": sorted(
            _normalized_values(
                batch.get("runtime_resources"),
                _normalized_resource,
                require_nonempty=False,
            )
            or []
        ),
    }


def _git_output(worktree: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(worktree), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _canonicalize_batch(batch: Mapping[str, Any]) -> dict[str, Any] | None:
    worktree_value = batch.get("worktree")
    if not isinstance(worktree_value, str) or not posixpath.isabs(worktree_value):
        return None
    try:
        worktree = Path(worktree_value).resolve(strict=True)
    except OSError:
        return None
    git_root_value = _git_output(worktree, "rev-parse", "--show-toplevel")
    git_common_dir_value = _git_output(worktree, "rev-parse", "--git-common-dir")
    actual_branch = _git_output(worktree, "branch", "--show-current")
    if (
        git_root_value is None
        or git_common_dir_value is None
        or actual_branch is None
        or not actual_branch
    ):
        return None
    try:
        git_root = Path(git_root_value).resolve(strict=True)
    except OSError:
        return None
    if git_root != worktree:
        return None
    if _normalized_branch(batch.get("branch")) != _normalized_branch(actual_branch):
        return None
    common_dir_candidate = Path(git_common_dir_value)
    if not common_dir_candidate.is_absolute():
        common_dir_candidate = worktree / common_dir_candidate
    try:
        git_common_dir = common_dir_candidate.resolve(strict=True)
    except OSError:
        return None

    owned_files = batch.get("owned_files")
    normalized_owned = _normalized_values(owned_files, _normalized_file, require_nonempty=True)
    if normalized_owned is None:
        return None
    canonical_owned: list[str] = []
    for relative_path in normalized_owned:
        target = (worktree / relative_path).resolve(strict=False)
        try:
            canonical_owned.append(target.relative_to(worktree).as_posix())
        except ValueError:
            return None

    resources = batch.get("runtime_resources")
    if not isinstance(resources, Sequence) or isinstance(resources, (str, bytes)):
        return None
    canonical_resources: list[str] = []
    for resource in resources:
        normalized = _normalized_resource(resource)
        if normalized is None:
            return None
        kind, identifier = normalized.split(":", 1)
        if kind in {"artifact", "file", "lockfile", "path"}:
            target = (worktree / identifier).resolve(strict=False)
            try:
                identifier = target.relative_to(worktree).as_posix()
            except ValueError:
                return None
        canonical_resources.append(f"{kind}:{identifier}")

    canonical = dict(batch)
    worktree_stat = worktree.stat()
    common_dir_stat = git_common_dir.stat()
    canonical["worktree"] = str(worktree)
    canonical["worktree_identity"] = f"{worktree_stat.st_dev}:{worktree_stat.st_ino}"
    canonical["repository_identity"] = f"{common_dir_stat.st_dev}:{common_dir_stat.st_ino}"
    canonical["branch"] = actual_branch
    canonical["owned_files"] = sorted(set(canonical_owned))
    canonical["runtime_resources"] = sorted(set(canonical_resources))
    return canonical


def _trusted_cli_requests(
    requests: Sequence[Mapping[str, Any]], current_period_id: str
) -> list[Mapping[str, Any]] | None:
    current_period_id = current_period_id.strip()
    if not current_period_id:
        return None
    trusted_now = datetime.now(timezone.utc).isoformat()
    trusted_requests = copy.deepcopy(list(requests))
    for request in trusted_requests:
        if not isinstance(request, dict):
            return None
        batch = request.get("batch")
        if not isinstance(batch, Mapping):
            return None
        canonical_batch = _canonicalize_batch(batch)
        if canonical_batch is None:
            return None
        request["batch"] = canonical_batch
        request["runtime"] = {
            "current_period_id": current_period_id,
            "now": trusted_now,
            "snapshot_max_age_seconds": DEFAULT_SNAPSHOT_MAX_AGE_SECONDS,
        }
    return trusted_requests


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成唯一可执行的 Autopilot worker 启动清单")
    parser.add_argument("--input", required=True, help="包含 requests 数组的 JSON 文件")
    parser.add_argument(
        "--current-period-id",
        required=True,
        help="从本次官方用量来源或用户刚提供的 /usage 快照读取的当前额度周期",
    )
    args = parser.parse_args(argv)

    try:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(json.dumps({"status": PARTIAL_BLOCKED, "reason_code": "INPUT_INVALID"}))
        print(str(error), file=sys.stderr)
        return 2
    requests = payload.get("requests") if isinstance(payload, Mapping) else None
    if not isinstance(requests, Sequence) or isinstance(requests, (str, bytes)):
        print(json.dumps({"status": PARTIAL_BLOCKED, "reason_code": "REQUESTS_INVALID"}))
        return 2

    trusted_requests = _trusted_cli_requests(requests, args.current_period_id)
    if trusted_requests is None:
        print(json.dumps({"status": PARTIAL_BLOCKED, "reason_code": "CLI_TRUST_BOUNDARY_INVALID"}))
        return 2

    result = dispatch_wave(trusted_requests, _manifest_launcher)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if result["status"] == ALLOW:
        return 0
    if result["status"] == PARTIAL_BLOCKED and result["launch_results"]:
        return 0
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
