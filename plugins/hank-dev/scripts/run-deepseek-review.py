#!/usr/bin/env python3
"""以最小权限执行 DeepSeek 单文件审查，通过 dsh headless profile 调用。"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path


TIMEOUT_SECONDS = 120
MAX_PATCH_BYTES = 2 * 1024 * 1024
CONSENT_ENV = "HANK_DEEPSEEK_OUTBOUND_APPROVED"
API_KEY_ENV = "DEEPSEEK_API_KEY"
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


def parse_output(stdout: str, stderr: str, returncode: int) -> str:
    """把 dsh headless 的纯文本输出解析为结果，任何不确定状态都失败关闭。"""

    if returncode != 0:
        raise ResultError("nonzero_exit")
    if stderr.strip():
        raise ResultError("unexpected_stderr")
    result = stdout.strip()
    if not result:
        raise ResultError("empty_output")
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


def _resolve_trusted_dsh() -> str:
    """解析 dsh 绝对路径，并拒绝任何非当前用户独占、group/other 可写的候选。

    这不能防御一个已经被攻破的账户，只能挡住"PATH 里更早的目录被人放了一个
    group/other 可写或非本用户拥有的同名文件"这类经典 PATH 投毒。
    """

    resolved = shutil.which("dsh")
    if resolved is None:
        raise ResultError("dsh_not_found")
    info = os.stat(resolved)
    if info.st_uid != os.geteuid() or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise ResultError("dsh_untrusted_binary")
    return resolved


def _isolated_environment(scratch: Path) -> dict[str, str]:
    child_env = {
        key: value
        for key in SAFE_ENV_KEYS
        if (value := os.environ.get(key)) is not None
    }
    api_key = os.environ.get(API_KEY_ENV)
    if not api_key:
        raise ResultError("provider_config_missing")
    for name in ("home", "dsh-home"):
        (scratch / name).mkdir(mode=0o700)
    local_rules = scratch / "AGENTS.md"
    local_rules.write_text("当前目录没有附加指令。\n", encoding="utf-8")
    local_rules.chmod(0o600)
    child_env.update(
        {
            "HOME": str(scratch / "home"),
            "DSH_HOME": str(scratch / "dsh-home"),
            "DSH_PERMISSION_MODE": "read-only",
            "DSH_TELEMETRY_MODE": "DISABLED",
            API_KEY_ENV: api_key,
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
        dsh_bin = _resolve_trusted_dsh()
        child_env = _isolated_environment(scratch)
        try:
            completed = subprocess.run(
                [dsh_bin, "--profile", "headless", PROMPT],
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
        return parse_output(completed.stdout, completed.stderr, completed.returncode)
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
            result = parse_output(stdout, stderr, returncode)
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
