#!/usr/bin/env python3
"""以最小权限执行 DeepSeek 单文件审查，并严格解析 OpenCode JSONL。"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


TIMEOUT_SECONDS = 120
MAX_PATCH_BYTES = 2 * 1024 * 1024
MAX_CONFIG_BYTES = 1024 * 1024
CONSENT_ENV = "HANK_DEEPSEEK_OUTBOUND_APPROVED"
PROMPT = (
    "只读当前目录的 review-input.patch。审查 bug、边界条件和简化复用空间。"
    "禁止修改文件，禁止执行命令。每条 finding 包含文件、行号、触发场景、"
    "严重程度、置信度和证据。"
)
SAFE_ENV_KEYS = (
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "NODE_EXTRA_CA_CERTS",
    "PATH",
    "SSL_CERT_DIR",
    "SSL_CERT_FILE",
    "TERM",
)
REFUSAL_MARKERS = (
    "i cannot",
    "i can't",
    "unable to comply",
    "cannot comply",
    "无法执行",
    "不能执行",
    "无法完成",
    "不能完成",
    "拒绝执行",
)


class ResultError(Exception):
    """表示外部复核结果不可采信。"""

    def __init__(self, category: str):
        super().__init__(category)
        self.category = category


def _event_type(event: dict[str, Any]) -> str:
    value = event.get("type")
    return value.lower() if isinstance(value, str) else ""


def _text_from_event(event: dict[str, Any]) -> str:
    event_type = _event_type(event)
    candidates: list[Any] = []
    if event_type == "text":
        candidates.extend((event.get("text"), event.get("content")))

    for container_name in ("part", "data", "properties"):
        container = event.get(container_name)
        if not isinstance(container, dict):
            continue
        container_type = str(container.get("type") or "").lower()
        if event_type == "text" or container_type == "text":
            candidates.extend((container.get("text"), container.get("content")))
        nested_part = container.get("part")
        if isinstance(nested_part, dict) and str(nested_part.get("type") or "").lower() == "text":
            candidates.extend((nested_part.get("text"), nested_part.get("content")))

    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return ""


def _is_completed_read(event: dict[str, Any]) -> bool:
    part = event.get("part")
    if not isinstance(part, dict) or part.get("tool") != "read":
        return False
    state = part.get("state")
    return isinstance(state, dict) and state.get("status") == "completed"


def parse_jsonl(stdout: str, stderr: str, returncode: int) -> str:
    """把 OpenCode JSONL 解析为文本，任何不确定状态都失败关闭。"""

    combined_lower = f"{stdout}\n{stderr}".lower()
    if returncode != 0:
        raise ResultError("nonzero_exit")
    if (
        "permission denied" in combined_lower
        or "permission_denied" in combined_lower
        or ("permission requested" in combined_lower and "auto-rejecting" in combined_lower)
    ):
        raise ResultError("permission_denied")
    if (
        "agent fallback" in combined_lower
        or "fallback agent" in combined_lower
        or "falling back to default agent" in combined_lower
    ):
        raise ResultError("agent_fallback")
    if not stdout.strip():
        raise ResultError("empty_output")

    texts: list[str] = []
    parsed_count = 0
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ResultError("non_json_output") from exc
        if not isinstance(event, dict):
            raise ResultError("invalid_json_event")
        parsed_count += 1
        event_type = _event_type(event)
        if event_type == "error" or event_type.endswith(".error") or "error" in event:
            raise ResultError("error_event")
        if event_type == "tool_use" and not _is_completed_read(event):
            raise ResultError("unexpected_tool_use")
        text = _text_from_event(event)
        if text:
            texts.append(text)

    if parsed_count == 0:
        raise ResultError("empty_output")
    result = "\n".join(texts).strip()
    if not result:
        raise ResultError("no_text_event")
    normalized = " ".join(result.lower().split())
    if len(normalized) <= 240 and any(marker in normalized for marker in REFUSAL_MARKERS):
        raise ResultError("refusal_only")
    return result


def _load_fixture(path: Path) -> tuple[str, str, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("fixture 必须是对象")
    return (
        str(data.get("stdout") or ""),
        str(data.get("stderr") or ""),
        int(data.get("returncode") or 0),
    )


def _safe_cleanup(path: Path, temp_root: Path) -> None:
    resolved = path.resolve()
    root = temp_root.resolve()
    if resolved.parent != root or not resolved.name.startswith("hank-review."):
        raise RuntimeError("拒绝清理未验证的临时目录")
    shutil.rmtree(resolved)


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ResultError("timeout")
    return remaining


def _copy_bounded(source: Path, target: Path, deadline: float) -> None:
    total = 0
    with source.open("rb") as source_file, target.open("xb") as target_file:
        target.chmod(0o600)
        while True:
            _remaining(deadline)
            chunk = source_file.read(min(64 * 1024, MAX_PATCH_BYTES + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_PATCH_BYTES:
                raise ResultError("input_too_large")
            target_file.write(chunk)


def _source_config_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        return Path(config_home) / "opencode" / "opencode.json"
    return Path.home() / ".config" / "opencode" / "opencode.json"


def _review_permission(target: Path) -> dict[str, Any]:
    return {
        "*": "deny",
        "read": {"*": "deny", f"*/{target.name}": "allow"},
        "external_directory": "deny",
    }


def _load_isolated_config(target: Path) -> dict[str, Any]:
    config_path = _source_config_path()
    try:
        with config_path.open("rb") as config_file:
            raw_config = config_file.read(MAX_CONFIG_BYTES + 1)
        if len(raw_config) > MAX_CONFIG_BYTES:
            raise ResultError("provider_config_invalid")
        source = json.loads(raw_config.decode("utf-8"))
    except FileNotFoundError as exc:
        raise ResultError("provider_config_missing") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResultError("provider_config_invalid") from exc
    if not isinstance(source, dict):
        raise ResultError("provider_config_invalid")

    providers = source.get("provider")
    agents = source.get("agent")
    provider = providers.get("deepseek") if isinstance(providers, dict) else None
    source_agent = agents.get("deepseek-worker") if isinstance(agents, dict) else None
    model = (
        source_agent.get("model") if isinstance(source_agent, dict) else None
    ) or source.get("model")
    if not isinstance(provider, dict) or not isinstance(model, str) or not model.startswith("deepseek/"):
        raise ResultError("provider_config_missing")

    isolated = {
        "model": model,
        "provider": {"deepseek": provider},
        "agent": {
            "deepseek-worker": {
                "mode": "primary",
                "model": model,
                "permission": _review_permission(target),
            }
        },
        "plugin": [],
        "instructions": [],
        "mcp": {},
        "share": "disabled",
    }
    return isolated


def _isolated_environment(scratch: Path, target: Path) -> dict[str, str]:
    child_env = {
        key: value
        for key in SAFE_ENV_KEYS
        if (value := os.environ.get(key)) is not None
    }
    for name in ("home", "config", "data", "cache", "state"):
        (scratch / name).mkdir(mode=0o700)
    config_dir = scratch / "config" / "opencode"
    config_dir.mkdir(mode=0o700)
    local_rules = scratch / "AGENTS.md"
    local_rules.write_text("当前目录没有附加指令。\n", encoding="utf-8")
    local_rules.chmod(0o600)
    child_env.update(
        {
            "HOME": str(scratch / "home"),
            "XDG_CONFIG_HOME": str(scratch / "config"),
            "XDG_DATA_HOME": str(scratch / "data"),
            "XDG_CACHE_HOME": str(scratch / "cache"),
            "XDG_STATE_HOME": str(scratch / "state"),
            "OPENCODE_CONFIG_DIR": str(config_dir),
            "OPENCODE_DISABLE_CLAUDE_CODE": "1",
            "OPENCODE_DISABLE_DEFAULT_PLUGINS": "1",
            "OPENCODE_CONFIG_CONTENT": json.dumps(
                _load_isolated_config(target), ensure_ascii=False, separators=(",", ":")
            ),
        }
    )
    return child_env


def run_review(patch_path: Path) -> str:
    if os.environ.get(CONSENT_ENV) != "1":
        raise ResultError("outbound_consent_missing")
    if not patch_path.is_file():
        raise ResultError("input_missing")

    deadline = time.monotonic() + TIMEOUT_SECONDS
    temp_root = Path(os.environ.get("TMPDIR") or "/tmp")
    scratch = Path(tempfile.mkdtemp(prefix="hank-review.", dir=temp_root))
    try:
        target = scratch / "review-input.patch"
        _copy_bounded(patch_path, target, deadline)
        script_root = Path(__file__).resolve().parent
        scanner = script_root / "check-review-patch.sh"
        try:
            scan = subprocess.run(
                [str(scanner), str(target)],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=_remaining(deadline),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ResultError("timeout") from exc
        if scan.returncode != 0:
            raise ResultError("sensitive_scan_blocked")
        child_env = _isolated_environment(scratch, target)
        try:
            completed = subprocess.run(
                [
                    "opencode",
                    "run",
                    "--pure",
                    "--agent",
                    "deepseek-worker",
                    "--format",
                    "json",
                    PROMPT,
                ],
                cwd=scratch,
                env=child_env,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=_remaining(deadline),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ResultError("timeout") from exc
        return parse_jsonl(completed.stdout, completed.stderr, completed.returncode)
    finally:
        _safe_cleanup(scratch, temp_root)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("patch", nargs="?", type=Path)
    parser.add_argument("--parse-fixture", type=Path)
    args = parser.parse_args()

    try:
        if args.parse_fixture:
            stdout, stderr, returncode = _load_fixture(args.parse_fixture)
            result = parse_jsonl(stdout, stderr, returncode)
        else:
            if args.patch is None:
                raise ResultError("input_missing")
            result = run_review(args.patch.resolve())
    except (ResultError, ValueError, OSError, RuntimeError, json.JSONDecodeError) as exc:
        category = exc.category if isinstance(exc, ResultError) else "runner_error"
        print(f"DEEPSEEK_REVIEW_MISSING category:{category}", file=sys.stderr)
        return 1

    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
