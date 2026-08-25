#!/usr/bin/env bash
set -euo pipefail

plugin_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
delegate_skill="$plugin_root/skills/dsh-deepseek-delegate/SKILL.md"
delegate_runner="$plugin_root/scripts/run-dsh-delegate.py"

fail() {
  printf 'FAIL %s\n' "$1" >&2
  exit 1
}

forbidden_flag="$(printf '%s%s' '--' 'auto')"

if grep -Fq -- "$forbidden_flag" "$delegate_skill"; then
  fail "automatic-approval"
fi

for required in \
  'HANK_DELEGATE_SECURITY_CONTRACT_V1' \
  'run-dsh-delegate.py' \
  'task.md' \
  '120 秒' \
  'DSH_PERMISSION_MODE' \
  'DEEPSEEK_API_KEY' \
  '输出为空' \
  '明确授权本次' \
  '隔离的 HOME'; do
  grep -Fq "$required" "$delegate_skill" || fail "missing-security-contract"
done

[[ -f "$delegate_runner" ]] || fail "delegate-runner-missing"

if grep -Fq -- "$forbidden_flag" "$delegate_runner"; then
  fail "runner-automatic-approval"
fi

for required in \
  'TIMEOUT_SECONDS = 120' \
  'MAX_PROMPT_BYTES = 2 * 1024 * 1024' \
  'capture_output=True' \
  'stdin=subprocess.DEVNULL' \
  '"--profile"' \
  '"headless"' \
  'empty_output' \
  'refusal_only' \
  'unexpected_stderr' \
  'outbound_consent_missing' \
  'shutil.which("dsh")' \
  'dsh_not_found' \
  'dsh_untrusted_binary' \
  '_resolve_trusted_dsh' \
  'DSH_PERMISSION_MODE' \
  'DSH_HOME' \
  'DEEPSEEK_API_KEY' \
  '_isolated_environment' \
  '_remaining'; do
  grep -Fq "$required" "$delegate_runner" || fail "runner-contract-missing"
done

python3 - "$delegate_runner" <<'PY'
import json
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

runner_path = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("delegate_runner", runner_path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
assert module.TIMEOUT_SECONDS == 120
assert module.parse_output("委派完成\n", "", 0) == "委派完成"

with tempfile.TemporaryDirectory() as temp_root:
    tracked_env = (
        "TMPDIR",
        module.CONSENT_ENV,
        module.API_KEY_ENV,
        "AWS_SECRET_ACCESS_KEY",
        "CLAUDE_CONFIG_DIR",
    )
    original_env = {key: os.environ.get(key) for key in tracked_env}
    os.environ["TMPDIR"] = temp_root
    os.environ[module.CONSENT_ENV] = "1"
    os.environ[module.API_KEY_ENV] = "fixture-deepseek-key"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "must-not-reach-child"
    os.environ["CLAUDE_CONFIG_DIR"] = "/private/global-claude"
    calls = []

    def timeout_run(args, **kwargs):
        calls.append((args, kwargs))
        assert args[0] == module.shutil.which("dsh")
        assert args[1:] == ["--profile", "headless", module.TASK_PROMPT]
        assert 0 < kwargs["timeout"] <= 120
        assert kwargs["stdin"] is subprocess.DEVNULL
        assert kwargs["capture_output"] is True
        child_env = kwargs["env"]
        scratch = Path(kwargs["cwd"])
        assert child_env["HOME"] == str(scratch / "home")
        assert child_env["DSH_HOME"] == str(scratch / "dsh-home")
        assert child_env["DSH_PERMISSION_MODE"] == "read-only"
        assert child_env["DSH_TELEMETRY_MODE"] == "DISABLED"
        assert child_env[module.API_KEY_ENV] == "fixture-deepseek-key"
        assert "AWS_SECRET_ACCESS_KEY" not in child_env
        assert "CLAUDE_CONFIG_DIR" not in child_env
        assert (scratch / "task.md").read_text(encoding="utf-8") == "安全的测试任务"
        assert (scratch / "task.md").stat().st_mode & 0o777 == 0o600
        assert (scratch / "AGENTS.md").read_text(encoding="utf-8") == "当前目录没有附加指令。\n"
        raise subprocess.TimeoutExpired(args, kwargs["timeout"])

    try:
        with mock.patch.object(module.subprocess, "run", side_effect=timeout_run):
            try:
                module.run_delegate("安全的测试任务")
            except module.ResultError as exc:
                assert exc.category == "timeout"
            else:
                raise AssertionError("超时必须失败关闭")
        assert len(calls) == 1
        assert not list(Path(temp_root).glob("deepseek-delegate.*"))

        calls.clear()
        with mock.patch.object(module.subprocess, "run", side_effect=AssertionError("不应启动子进程")):
            oversized = "x" * (module.MAX_PROMPT_BYTES + 1)
            try:
                module.run_delegate(oversized)
            except module.ResultError as exc:
                assert exc.category == "input_too_large"
            else:
                raise AssertionError("超限 prompt 必须失败关闭")
        assert calls == []
        assert not list(Path(temp_root).glob("deepseek-delegate.*"))

        with mock.patch.object(module.subprocess, "run", side_effect=AssertionError("不应启动子进程")), \
             mock.patch.object(module.shutil, "which", return_value=None):
            try:
                module.run_delegate("安全的测试任务")
            except module.ResultError as exc:
                assert exc.category == "dsh_not_found"
            else:
                raise AssertionError("dsh 缺失必须失败关闭")
        assert not list(Path(temp_root).glob("deepseek-delegate.*"))

        fake_bin = Path(temp_root) / "untrusted-bin"
        fake_bin.mkdir()
        fake_dsh = fake_bin / "dsh"
        fake_dsh.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        fake_dsh.chmod(0o777)
        original_path = os.environ.get("PATH")
        os.environ["PATH"] = str(fake_bin) + os.pathsep + (original_path or os.defpath)
        try:
            with mock.patch.object(module.subprocess, "run", side_effect=AssertionError("不应启动子进程")):
                try:
                    module.run_delegate("安全的测试任务")
                except module.ResultError as exc:
                    assert exc.category == "dsh_untrusted_binary"
                else:
                    raise AssertionError("group/other 可写的 dsh 候选必须失败关闭")
        finally:
            if original_path is None:
                os.environ.pop("PATH", None)
            else:
                os.environ["PATH"] = original_path
        assert not list(Path(temp_root).glob("deepseek-delegate.*"))
    finally:
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
PY

scratch_dir="$(mktemp -d "${TMPDIR:-/tmp}/hank-delegate-validation.XXXXXX")"
case "$scratch_dir" in
  "${TMPDIR:-/tmp}"/hank-delegate-validation.*) ;;
  *) fail "unsafe-temp-path" ;;
esac

cleanup() {
  rm -rf "$scratch_dir"
}
trap cleanup EXIT

printf '%s\n' \
  '{"stdout":"委派完成","stderr":"","returncode":0}' \
  > "$scratch_dir/success.json"
printf '%s\n' \
  '{"stdout":"","stderr":"","returncode":0}' \
  > "$scratch_dir/empty.json"
printf '%s\n' \
  '{"stdout":"I cannot comply","stderr":"","returncode":0}' \
  > "$scratch_dir/refusal.json"
printf '%s\n' \
  '{"stdout":"委派完成","stderr":"permission requested","returncode":0}' \
  > "$scratch_dir/stderr.json"

"$delegate_runner" --parse-fixture "$scratch_dir/success.json" \
  | grep -Fq '委派完成' || fail "parser-success"

while IFS='|' read -r fixture category; do
  set +e
  output="$("$delegate_runner" --parse-fixture "$scratch_dir/$fixture.json" 2>&1)"
  status=$?
  set -e
  [[ "$status" -eq 1 ]] || fail "parser-failure-status"
  grep -Fq "category:$category" <<<"$output" || fail "parser-failure-category"
done <<'CASES'
empty|empty_output
refusal|refusal_only
stderr|unexpected_stderr
CASES

set +e
consent_output="$(
  env -u HANK_DEEPSEEK_OUTBOUND_APPROVED \
    "$delegate_runner" "安全的测试任务" 2>&1
)"
consent_status=$?
set -e
[[ "$consent_status" -eq 1 ]] || fail "consent-status"
grep -Fq 'category:outbound_consent_missing' <<<"$consent_output" \
  || fail "consent-category"

set +e
conflict_output="$(
  HANK_DEEPSEEK_OUTBOUND_APPROVED=1 \
    "$delegate_runner" "some prompt" --prompt-file "$scratch_dir/success.json" 2>&1
)"
conflict_status=$?
set -e
[[ "$conflict_status" -eq 1 ]] || fail "prompt-file-conflict-status"

# Empirical, non-mocked proof that DSH_PERMISSION_MODE=read-only actually blocks
# writes against the real dsh binary (not just asserted in a mock). Exit code
# is checked explicitly: a nonzero/timed-out call means dsh never actually ran
# the task, and "file absent" in that case would be a false proof, not a real one.
if command -v dsh >/dev/null 2>&1 && command -v timeout >/dev/null 2>&1 \
  && [[ -n "${DEEPSEEK_API_KEY:-}" ]]; then
  write_scratch="$scratch_dir/write-proof"
  mkdir -p "$write_scratch/home" "$write_scratch/dsh-home"
  write_proof_output="$write_scratch/dsh-output.txt"
  set +e
  HOME="$write_scratch/home" DSH_HOME="$write_scratch/dsh-home" \
    DSH_PERMISSION_MODE=read-only DSH_TELEMETRY_MODE=DISABLED \
    timeout 60 dsh --profile headless \
    "创建一个文件 blocked.txt，内容为 x，然后报告是否成功。" \
    >"$write_proof_output" 2>&1
  write_proof_status=$?
  set -e
  if [[ "$write_proof_status" -ne 0 ]]; then
    tail -20 "$write_proof_output" >&2 || true
    fail "dsh-write-proof-did-not-run"
  fi
  if [[ -f "$write_scratch/blocked.txt" ]]; then
    fail "dsh-read-only-write-not-blocked"
  fi
else
  printf 'SKIP dsh-write-proof (dsh, timeout, or DEEPSEEK_API_KEY not available)\n' >&2
fi

printf 'PASS hank-dev dsh-deepseek-delegate security\n'
