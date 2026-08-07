from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import json
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from autopilot_quota_router import (  # noqa: E402
    ALLOW,
    AWAITING_APPROVAL,
    PARTIAL_BLOCKED,
    decide_batch_route,
    dispatch_wave,
    plan_execution_waves,
)


class FakeLauncher:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, batch, decision):
        self.calls.append(batch["id"])
        return decision["selected_model"]


def base_request() -> dict:
    return {
        "run_id": "run-001",
        "batch": {
            "id": "Batch-1",
            "reasoning_effort": "high",
            "effort_basis": "复用现有实现模式，测试路径明确",
            "spark_eligible": True,
            "spark_ineligibility_reasons": [],
            "depends_on": [],
            "worktree": "/tmp/worktree-1",
            "branch": "feat/batch-1",
            "owned_files": ["src/a.py"],
            "runtime_resources": ["port:4101"],
        },
        "wave": {
            "worker_count": 1,
            "batch_ids": ["Batch-1"],
            "completed_batch_ids": [],
        },
        "usage": {
            "period_id": "2026-W32",
            "captured_at": "2026-08-07T10:00:00+10:00",
            "weekly_remaining_percent": 26,
            "today_used_percent": 5,
        },
        "runtime": {
            "current_period_id": "2026-W32",
            "now": "2026-08-07T10:05:00+10:00",
            "snapshot_max_age_seconds": 900,
        },
        "model_catalog": {
            "terra": {
                "available": True,
                "model": "gpt-5.6-terra",
                "reasoning_efforts": ["high", "xhigh", "max"],
            },
            "luna": {
                "available": True,
                "model": "gpt-5.6-luna",
                "reasoning_efforts": ["xhigh", "max"],
            },
            "spark": {
                "available": True,
                "model": "runtime-spark",
                "reasoning_efforts": ["high"],
            },
        },
    }


def approve(request: dict, tier: str, *, raise_effort: bool = False) -> None:
    request["authorization"] = {
        "approved": True,
        "run_id": request["run_id"],
        "period_id": request["usage"]["period_id"],
        "model_tier": tier,
        "batch_ids": [request["batch"]["id"]],
        "high_to_xhigh_batch_ids": [request["batch"]["id"]] if raise_effort else [],
        "authorization_text": f"批准 {tier}",
        "valid_until": "2026-08-07T12:00:00+10:00",
    }


def init_git_worktree(path: Path, branch: str) -> Path:
    subprocess.run(
        ["git", "init", "-q", "-b", branch, str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "Autopilot Test"],
        capture_output=True,
        text=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "autopilot@test.invalid"],
        capture_output=True,
        text=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "commit", "-q", "--allow-empty", "-m", "initial"],
        capture_output=True,
        text=True,
        check=True,
    )
    return path.resolve()


def add_linked_worktree(repository: Path, path: Path, branch: str) -> Path:
    subprocess.run(
        ["git", "-C", str(repository), "worktree", "add", "-q", "-b", branch, str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return path.resolve()


def set_current_snapshot(request: dict) -> None:
    request["usage"]["captured_at"] = datetime.now(timezone.utc).isoformat()


class RouteDecisionTests(unittest.TestCase):
    def test_weekly_25_percent_allows_terra(self):
        request = base_request()
        request["usage"]["weekly_remaining_percent"] = 25
        self.assertEqual(decide_batch_route(request)["selected_tier"], "terra")
        self.assertEqual(decide_batch_route(request)["status"], ALLOW)

    def test_weekly_26_percent_allows_terra(self):
        decision = decide_batch_route(base_request())
        self.assertEqual((decision["status"], decision["selected_model"]), (ALLOW, "gpt-5.6-terra"))

    def test_daily_reserve_shortfall_requires_luna_approval(self):
        request = base_request()
        request["usage"]["today_used_percent"] = 22
        decision = decide_batch_route(request)
        self.assertEqual((decision["status"], decision["selected_tier"]), (AWAITING_APPROVAL, "luna"))

    def test_weekly_10_to_24_requires_luna_approval(self):
        request = base_request()
        request["usage"]["weekly_remaining_percent"] = 18
        self.assertEqual(decide_batch_route(request)["reason_code"], "MODEL_APPROVAL_REQUIRED")

    def test_luna_high_requires_explicit_effort_raise(self):
        request = base_request()
        request["usage"]["weekly_remaining_percent"] = 18
        approve(request, "luna")
        decision = decide_batch_route(request)
        self.assertEqual(decision["reason_code"], "EFFORT_RAISE_APPROVAL_REQUIRED")
        request["authorization"]["high_to_xhigh_batch_ids"] = ["Batch-1"]
        self.assertEqual(decide_batch_route(request)["status"], ALLOW)

    def test_spark_missing_is_partial_blocked(self):
        request = base_request()
        request["usage"]["weekly_remaining_percent"] = 9
        del request["model_catalog"]["spark"]
        self.assertEqual(decide_batch_route(request)["reason_code"], "SPARK_UNAVAILABLE")

    def test_spark_requires_approval_and_eligibility(self):
        request = base_request()
        request["usage"]["weekly_remaining_percent"] = 7
        self.assertEqual(decide_batch_route(request)["status"], AWAITING_APPROVAL)
        approve(request, "spark")
        request["batch"]["spark_eligible"] = False
        request["batch"]["spark_ineligibility_reasons"] = ["包含迁移"]
        self.assertEqual(decide_batch_route(request)["status"], PARTIAL_BLOCKED)

    def test_missing_period_mismatch_and_stale_snapshot_deny(self):
        missing = base_request()
        missing["usage"] = None
        self.assertEqual(decide_batch_route(missing)["status"], AWAITING_APPROVAL)

        mismatch = base_request()
        mismatch["runtime"]["current_period_id"] = "2026-W33"
        self.assertEqual(decide_batch_route(mismatch)["reason_code"], "USAGE_PERIOD_MISMATCH")

        stale = base_request()
        stale["runtime"]["now"] = "2026-08-07T10:30:01+10:00"
        self.assertEqual(decide_batch_route(stale)["reason_code"], "USAGE_SNAPSHOT_STALE")

    def test_historical_snapshot_and_expired_authorization_cannot_be_replayed(self):
        historical = base_request()
        historical["usage"]["captured_at"] = "2020-01-01T00:00:00+00:00"
        self.assertEqual(decide_batch_route(historical)["reason_code"], "USAGE_SNAPSHOT_STALE")

        expired = base_request()
        expired["usage"]["weekly_remaining_percent"] = 18
        approve(expired, "luna", raise_effort=True)
        expired["authorization"]["valid_until"] = "2026-08-07T10:04:59+10:00"
        self.assertEqual(decide_batch_route(expired)["reason_code"], "MODEL_APPROVAL_EXPIRED")

    def test_unsupported_effort_blocks_without_downgrade(self):
        request = base_request()
        request["model_catalog"]["terra"]["reasoning_efforts"] = ["xhigh", "max"]
        decision = decide_batch_route(request)
        self.assertEqual((decision["status"], decision["reasoning_effort"]), (PARTIAL_BLOCKED, "high"))

    def test_approval_is_scoped_to_run_period_batch_and_expiry(self):
        request = base_request()
        request["usage"]["weekly_remaining_percent"] = 18
        approve(request, "luna", raise_effort=True)
        request["authorization"]["batch_ids"] = ["Batch-2"]
        self.assertEqual(decide_batch_route(request)["reason_code"], "MODEL_APPROVAL_BATCH_MISMATCH")

    def test_missing_run_id_denies_before_routing(self):
        request = base_request()
        request["run_id"] = ""
        self.assertEqual(decide_batch_route(request)["reason_code"], "RUN_ID_REQUIRED")

    def test_batch_must_belong_to_declared_wave(self):
        request = base_request()
        request["wave"]["batch_ids"] = ["Batch-2"]
        self.assertEqual(decide_batch_route(request)["reason_code"], "WAVE_SCOPE_INVALID")


class WaveTests(unittest.TestCase):
    def test_independent_batches_share_a_wave(self):
        first = base_request()["batch"]
        second = copy.deepcopy(first)
        second.update(
            {
                "id": "Batch-2",
                "worktree": "/tmp/worktree-2",
                "branch": "feat/batch-2",
                "owned_files": ["src/b.py"],
                "runtime_resources": ["port:4102"],
            }
        )
        self.assertEqual(len(plan_execution_waves([first, second])[0]), 2)

    def test_dependencies_files_and_resources_force_serial_waves(self):
        first = base_request()["batch"]
        second = copy.deepcopy(first)
        second.update({"id": "Batch-2", "worktree": "/tmp/worktree-2", "branch": "feat/batch-2"})
        self.assertEqual([len(wave) for wave in plan_execution_waves([first, second])], [1, 1])

    def test_path_branch_and_resource_aliases_force_serial_waves(self):
        first = base_request()["batch"]
        second = copy.deepcopy(first)
        second.update(
            {
                "id": "Batch-2",
                "worktree": "/tmp/./worktree-1",
                "branch": "refs/heads/feat/batch-1",
                "owned_files": ["./src/a.py"],
                "runtime_resources": ["PORT:04101"],
            }
        )
        self.assertEqual([len(wave) for wave in plan_execution_waves([first, second])], [1, 1])

        second["owned_files"] = ["src/b.py"]
        second["runtime_resources"] = ["port:4102"]
        second["depends_on"] = ["Batch-1"]
        self.assertEqual([len(wave) for wave in plan_execution_waves([first, second])], [1, 1])

    def test_awaiting_approval_never_launches(self):
        request = base_request()
        request["usage"]["weekly_remaining_percent"] = 18
        launcher = FakeLauncher()
        result = dispatch_wave([request], launcher)
        self.assertEqual(result["status"], AWAITING_APPROVAL)
        self.assertEqual(launcher.calls, [])

    def test_partial_blocked_batch_never_launches(self):
        request = base_request()
        request["usage"]["weekly_remaining_percent"] = 7
        request["batch"]["spark_eligible"] = False
        request["batch"]["spark_ineligibility_reasons"] = ["包含跨模块状态"]
        approve(request, "spark")
        launcher = FakeLauncher()
        result = dispatch_wave([request], launcher)
        self.assertEqual(result["status"], PARTIAL_BLOCKED)
        self.assertEqual(launcher.calls, [])
        self.assertFalse(result["may_enter_full_gate"])

    def test_mixed_spark_wave_launches_only_allowed_batch_and_blocks_full_gate(self):
        allowed = base_request()
        allowed["usage"]["weekly_remaining_percent"] = 7
        approve(allowed, "spark")

        blocked = copy.deepcopy(allowed)
        blocked["batch"]["id"] = "Batch-2"
        blocked["batch"]["spark_eligible"] = False
        blocked["batch"]["spark_ineligibility_reasons"] = ["包含认证"]
        blocked["authorization"]["batch_ids"] = ["Batch-1", "Batch-2"]
        allowed["authorization"]["batch_ids"] = ["Batch-1", "Batch-2"]
        for request in (allowed, blocked):
            request["wave"] = {
                "worker_count": 2,
                "batch_ids": ["Batch-1", "Batch-2"],
                "completed_batch_ids": [],
            }
        blocked["batch"]["worktree"] = "/tmp/worktree-2"
        blocked["batch"]["branch"] = "feat/batch-2"
        blocked["batch"]["owned_files"] = ["src/b.py"]
        blocked["batch"]["runtime_resources"] = ["port:4102"]

        launcher = FakeLauncher()
        result = dispatch_wave([allowed, blocked], launcher)
        self.assertEqual(result["status"], PARTIAL_BLOCKED)
        self.assertEqual(launcher.calls, ["Batch-1"])
        self.assertFalse(result["may_enter_full_gate"])

    def test_empty_or_conflicting_wave_never_launches(self):
        launcher = FakeLauncher()
        self.assertEqual(dispatch_wave([], launcher)["reason_code"], "WAVE_REQUESTS_REQUIRED")

        first = base_request()
        second = copy.deepcopy(first)
        second["batch"]["id"] = "Batch-2"
        for request in (first, second):
            request["wave"] = {
                "worker_count": 2,
                "batch_ids": ["Batch-1", "Batch-2"],
                "completed_batch_ids": [],
            }
        result = dispatch_wave([first, second], launcher)
        self.assertEqual(result["reason_code"], "WAVE_ISOLATION_CONFLICT")
        self.assertEqual(launcher.calls, [])

    def test_invalid_launcher_and_model_catalog_mismatch_never_launch(self):
        request = base_request()
        self.assertEqual(
            dispatch_wave([request], None)["reason_code"],  # type: ignore[arg-type]
            "WORKER_LAUNCHER_INVALID",
        )

        first = base_request()
        second = copy.deepcopy(first)
        second["batch"].update(
            {
                "id": "Batch-2",
                "worktree": "/tmp/worktree-2",
                "branch": "feat/batch-2",
                "owned_files": ["src/b.py"],
                "runtime_resources": ["port:4102"],
            }
        )
        for item in (first, second):
            item["wave"] = {
                "worker_count": 2,
                "batch_ids": ["Batch-1", "Batch-2"],
                "completed_batch_ids": [],
            }
        second["model_catalog"]["terra"]["model"] = "different-terra"
        launcher = FakeLauncher()
        result = dispatch_wave([first, second], launcher)
        self.assertEqual(result["reason_code"], "WAVE_MODEL_CATALOG_MISMATCH")
        self.assertEqual(launcher.calls, [])

    def test_wave_planner_rejects_invalid_and_cyclic_dependencies(self):
        invalid = base_request()["batch"]
        invalid["id"] = []
        with self.assertRaises(ValueError):
            plan_execution_waves([invalid])

        first = base_request()["batch"]
        second = copy.deepcopy(first)
        first["depends_on"] = ["Batch-2"]
        second.update({"id": "Batch-2", "depends_on": ["Batch-1"]})
        with self.assertRaises(ValueError):
            plan_execution_waves([first, second])

    def test_cli_emits_only_allowed_launch_manifest(self):
        request = base_request()
        with tempfile.TemporaryDirectory() as temp_dir:
            worktree = init_git_worktree(Path(temp_dir) / "worktree-1", "feat/batch-1")
            request["batch"]["worktree"] = str(worktree)
            set_current_snapshot(request)
            payload = {"requests": [request]}
            input_path = Path(temp_dir) / "request.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(PLUGIN_ROOT / "scripts" / "autopilot_quota_router.py"),
                    "--input",
                    str(input_path),
                    "--current-period-id",
                    "2026-W32",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            output = json.loads(result.stdout)
            self.assertEqual(output["status"], ALLOW)
            self.assertEqual(output["launch_results"][0]["batch_id"], "Batch-1")
            self.assertEqual(output["launch_results"][0]["owned_files"], ["src/a.py"])

            request["usage"]["weekly_remaining_percent"] = 18
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            denied = subprocess.run(
                [
                    sys.executable,
                    str(PLUGIN_ROOT / "scripts" / "autopilot_quota_router.py"),
                    "--input",
                    str(input_path),
                    "--current-period-id",
                    "2026-W32",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(denied.returncode, 3)
            denied_output = json.loads(denied.stdout)
            self.assertEqual(denied_output["launch_results"], [])

    def test_cli_rejects_replayed_payload_even_when_payload_runtime_is_forged(self):
        request = base_request()
        request["usage"]["captured_at"] = "2020-01-01T00:00:00+00:00"
        request["runtime"] = {
            "current_period_id": "2026-W32",
            "now": "2020-01-01T00:01:00+00:00",
            "snapshot_max_age_seconds": 999999999,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            worktree = init_git_worktree(Path(temp_dir) / "worktree-1", "feat/batch-1")
            request["batch"]["worktree"] = str(worktree)
            input_path = Path(temp_dir) / "request.json"
            input_path.write_text(json.dumps({"requests": [request]}), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(PLUGIN_ROOT / "scripts" / "autopilot_quota_router.py"),
                    "--input",
                    str(input_path),
                    "--current-period-id",
                    "2026-W32",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 3)
            output = json.loads(result.stdout)
            self.assertEqual(output["decisions"][0]["reason_code"], "USAGE_SNAPSHOT_STALE")
            self.assertEqual(output["launch_results"], [])

    def test_cli_mixed_spark_wave_emits_only_allowed_manifest_and_returns_success(self):
        allowed = base_request()
        blocked = copy.deepcopy(allowed)
        blocked["batch"]["id"] = "Batch-2"
        blocked["batch"]["spark_eligible"] = False
        blocked["batch"]["spark_ineligibility_reasons"] = ["包含认证"]
        captured_at = datetime.now(timezone.utc).isoformat()
        for request in (allowed, blocked):
            request["usage"]["weekly_remaining_percent"] = 7
            request["usage"]["captured_at"] = captured_at
            request["wave"] = {
                "worker_count": 2,
                "batch_ids": ["Batch-1", "Batch-2"],
                "completed_batch_ids": [],
            }
            approve(request, "spark")
            request["authorization"]["batch_ids"] = ["Batch-1", "Batch-2"]
            request["authorization"]["valid_until"] = (
                datetime.now(timezone.utc) + timedelta(hours=1)
            ).isoformat()

        with tempfile.TemporaryDirectory() as temp_dir:
            repository = init_git_worktree(Path(temp_dir) / "coordinator", "main")
            first = add_linked_worktree(
                repository, Path(temp_dir) / "worktree-1", "feat/batch-1"
            )
            second = add_linked_worktree(
                repository, Path(temp_dir) / "worktree-2", "feat/batch-2"
            )
            allowed["batch"]["worktree"] = str(first)
            blocked["batch"].update(
                {
                    "worktree": str(second),
                    "branch": "feat/batch-2",
                    "owned_files": ["src/b.py"],
                    "runtime_resources": ["port:4102"],
                }
            )
            input_path = Path(temp_dir) / "request.json"
            input_path.write_text(
                json.dumps({"requests": [allowed, blocked]}), encoding="utf-8"
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(PLUGIN_ROOT / "scripts" / "autopilot_quota_router.py"),
                    "--input",
                    str(input_path),
                    "--current-period-id",
                    "2026-W32",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            output = json.loads(result.stdout)
            self.assertEqual(output["status"], PARTIAL_BLOCKED)
            self.assertEqual(output["launched_batch_ids"], ["Batch-1"])
            self.assertFalse(output["may_enter_full_gate"])

    def test_cli_rejects_wave_from_unrelated_git_repositories(self):
        first = base_request()
        second = copy.deepcopy(first)
        second["batch"].update(
            {
                "id": "Batch-2",
                "branch": "feat/batch-2",
                "owned_files": ["src/b.py"],
                "runtime_resources": ["port:4102"],
            }
        )
        captured_at = datetime.now(timezone.utc).isoformat()
        for request in (first, second):
            request["usage"]["captured_at"] = captured_at
            request["wave"] = {
                "worker_count": 2,
                "batch_ids": ["Batch-1", "Batch-2"],
                "completed_batch_ids": [],
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            first_repo = init_git_worktree(Path(temp_dir) / "repo-1", "feat/batch-1")
            second_repo = init_git_worktree(Path(temp_dir) / "repo-2", "feat/batch-2")
            first["batch"]["worktree"] = str(first_repo)
            second["batch"]["worktree"] = str(second_repo)
            input_path = Path(temp_dir) / "request.json"
            input_path.write_text(
                json.dumps({"requests": [first, second]}), encoding="utf-8"
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(PLUGIN_ROOT / "scripts" / "autopilot_quota_router.py"),
                    "--input",
                    str(input_path),
                    "--current-period-id",
                    "2026-W32",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 3)
            output = json.loads(result.stdout)
            self.assertEqual(output["reason_code"], "WAVE_REPOSITORY_MISMATCH")
            self.assertEqual(output["launch_results"], [])

    def test_cli_resolves_symlink_worktree_alias_before_wave_isolation_check(self):
        first = base_request()
        second = copy.deepcopy(first)
        second["batch"].update(
            {
                "id": "Batch-2",
                "owned_files": ["src/b.py"],
                "runtime_resources": ["port:4102"],
            }
        )
        for request in (first, second):
            request["wave"] = {
                "worker_count": 2,
                "batch_ids": ["Batch-1", "Batch-2"],
                "completed_batch_ids": [],
            }
            set_current_snapshot(request)

        with tempfile.TemporaryDirectory() as temp_dir:
            worktree = init_git_worktree(Path(temp_dir) / "worktree-1", "feat/batch-1")
            alias = Path(temp_dir) / "worktree-alias"
            alias.symlink_to(worktree, target_is_directory=True)
            first["batch"]["worktree"] = str(worktree)
            second["batch"]["worktree"] = str(alias)
            input_path = Path(temp_dir) / "request.json"
            input_path.write_text(
                json.dumps({"requests": [first, second]}), encoding="utf-8"
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(PLUGIN_ROOT / "scripts" / "autopilot_quota_router.py"),
                    "--input",
                    str(input_path),
                    "--current-period-id",
                    "2026-W32",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 3)
            output = json.loads(result.stdout)
            self.assertEqual(output["reason_code"], "WAVE_ISOLATION_CONFLICT")
            self.assertEqual(output["launch_results"], [])


if __name__ == "__main__":
    unittest.main()
