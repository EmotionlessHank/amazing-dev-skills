#!/usr/bin/env bash
set -euo pipefail

plugin_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
review_skill="$plugin_root/skills/review/SKILL.md"
scanner="$plugin_root/scripts/check-review-patch.sh"
review_runner="$plugin_root/scripts/run-deepseek-review.py"

fail() {
  printf 'FAIL %s\n' "$1" >&2
  exit 1
}

check_skill() {
  local skill_file="$1"
  local forbidden_flag
  forbidden_flag="$(printf '%s%s' '--' 'auto')"

  if awk -v needle="$forbidden_flag" '
    index($0, needle) {
      printf "FORBIDDEN %s:%d\n", FILENAME, FNR
      found = 1
    }
    END { exit found ? 0 : 1 }
  ' "$skill_file"; then
    fail "automatic-approval"
  fi

  for required in \
    'HANK_REVIEW_SECURITY_CONTRACT_V3' \
    'run-deepseek-review.py' \
    'review-input.patch' \
    '120 秒' \
    'DSH_PERMISSION_MODE' \
    'DEEPSEEK_API_KEY' \
    '输出为空' \
    '明确授权本次' \
    '敏感信息' \
    '隔离的 HOME'; do
    grep -Fq "$required" "$skill_file" || fail "missing-security-contract"
  done
}

check_skill "$review_skill"

[[ -f "$review_runner" ]] || fail "review-runner-missing"

forbidden_flag="$(printf '%s%s' '--' 'auto')"
if grep -Fq -- "$forbidden_flag" "$review_runner"; then
  fail "runner-automatic-approval"
fi
for required in \
  'TIMEOUT_SECONDS = 120' \
  'capture_output=True' \
  '"--profile"' \
  '"headless"' \
  'empty_output' \
  'refusal_only' \
  'outbound_consent_missing' \
  'DSH_PERMISSION_MODE' \
  'DSH_HOME' \
  'DEEPSEEK_API_KEY' \
  '_isolated_environment' \
  '_remaining'; do
  grep -Fq "$required" "$review_runner" || fail "runner-contract-missing"
done

grep -Fq 'MAX_PATCH_BYTES = 2 * 1024 * 1024' "$review_runner" \
  || fail "review-size-limit-missing"
grep -Fq 'stdin=subprocess.DEVNULL' "$review_runner" \
  || fail "review-stdin-contract-missing"

python3 - "$review_runner" <<'PY'
import json
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

runner_path = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("review_runner", runner_path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
assert module.TIMEOUT_SECONDS == 120
assert module.parse_output("读取后发现问题\n", "", 0) == "读取后发现问题"

with tempfile.TemporaryDirectory() as temp_root:
    patch = Path(temp_root) / "input.patch"
    patch.write_text("diff --git a/a b/a\n+safe\n", encoding="utf-8")
    oversized = Path(temp_root) / "oversized.patch"
    oversized.write_bytes(b"x" * (module.MAX_PATCH_BYTES + 1))
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
        if Path(args[0]).name == "check-review-patch.sh":
            copied = Path(args[1])
            assert copied.name == "review-input.patch"
            assert copied.parent.parent == Path(temp_root)
            assert copied.stat().st_mode & 0o777 == 0o600
            return subprocess.CompletedProcess(args, 0, "SCAN_PASS count:0\n", "")
        assert args == ["dsh", "--profile", "headless", module.PROMPT]
        assert 0 < kwargs["timeout"] <= calls[0][1]["timeout"] <= 120
        assert kwargs["stdin"] is subprocess.DEVNULL
        assert kwargs["capture_output"] is True
        child_env = kwargs["env"]
        scratch = Path(kwargs["cwd"])
        assert child_env["HOME"] == str(scratch / "home")
        assert child_env["DSH_HOME"] == str(scratch / "dsh-home")
        assert child_env["DSH_PERMISSION_MODE"] == "read-only"
        assert child_env["DSH_TELEMETRY_MODE"] == "DISABLED"
        assert child_env[module.API_KEY_ENV] == "fixture-deepseek-key"
        assert (scratch / "AGENTS.md").read_text(encoding="utf-8") == "当前目录没有附加指令。\n"
        assert (scratch / "AGENTS.md").stat().st_mode & 0o777 == 0o600
        assert "AWS_SECRET_ACCESS_KEY" not in child_env
        assert "CLAUDE_CONFIG_DIR" not in child_env
        raise subprocess.TimeoutExpired(args, kwargs["timeout"])

    try:
        with mock.patch.object(module.subprocess, "run", side_effect=timeout_run):
            try:
                module.run_review(patch)
            except module.ResultError as exc:
                assert exc.category == "timeout"
            else:
                raise AssertionError("超时必须失败关闭")
        assert len(calls) == 2
        assert not list(Path(temp_root).glob("hank-review.*"))

        calls.clear()
        with mock.patch.object(module.subprocess, "run", side_effect=AssertionError("不应启动子进程")):
            try:
                module.run_review(oversized)
            except module.ResultError as exc:
                assert exc.category == "input_too_large"
            else:
                raise AssertionError("超限输入必须失败关闭")
        assert calls == []
        assert not list(Path(temp_root).glob("hank-review.*"))
    finally:
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
PY

scratch_dir="$(mktemp -d "${TMPDIR:-/tmp}/hank-review-validation.XXXXXX")"
case "$scratch_dir" in
  "${TMPDIR:-/tmp}"/hank-review-validation.*) ;;
  *) fail "unsafe-temp-path" ;;
esac

cleanup() {
  rm -rf "$scratch_dir"
}
trap cleanup EXIT

printf 'diff --git a/a.txt b/a.txt\n+safe fixture\n' > "$scratch_dir/safe.patch"
"$scanner" "$scratch_dir/safe.patch" | grep -Fq 'SCAN_PASS count:0' || fail "safe-scan"

printf 'diff --git a/a.txt b/a.txt\n+Authorization: Bearer fixture-secret-value\n' > "$scratch_dir/unsafe.patch"
set +e
unsafe_output="$("$scanner" "$scratch_dir/unsafe.patch" 2>&1)"
unsafe_status=$?
set -e
[[ "$unsafe_status" -eq 1 ]] || fail "unsafe-scan-status"
grep -Fq 'AUTH_HEADER unsafe.patch:2' <<<"$unsafe_output" || fail "unsafe-scan-rule"
grep -Fq 'SCAN_BLOCKED count:' <<<"$unsafe_output" || fail "unsafe-scan-summary"
if grep -Fq 'fixture-secret-value' <<<"$unsafe_output"; then
  fail "unsafe-scan-leak"
fi

make_unsafe_fixture() {
  local filename="$1"
  local content="$2"
  local expected_rule="$3"
  printf 'diff --git a/a.txt b/a.txt\n+%s\n' "$content" > "$scratch_dir/$filename"
  set +e
  local output
  output="$("$scanner" "$scratch_dir/$filename" 2>&1)"
  local status=$?
  set -e
  [[ "$status" -eq 1 ]] || fail "credential-fixture-status"
  grep -Fq "$expected_rule $filename:2" <<<"$output" || fail "credential-fixture-rule"
  if grep -Fq -- "$content" <<<"$output"; then
    fail "credential-fixture-leak"
  fi
}

make_unsafe_fixture "aws.patch" \
  'AWS_SECRET_ACCESS_KEY=fixturevalue1234567890' \
  'GENERIC_SECRET'
make_unsafe_fixture "stripe.patch" \
  'stripe_api_key=fixturevalue1234567890' \
  'GENERIC_SECRET'
make_unsafe_fixture "openai.patch" \
  'sk-proj-fixturevalue12345678901234567890' \
  'KNOWN_TOKEN'
make_unsafe_fixture "google.patch" \
  'AIzaFixtureValue1234567890123456789012' \
  'KNOWN_TOKEN'
make_unsafe_fixture "private.patch" \
  '-----BEGIN PRIVATE KEY-----' \
  'PRIVATE_KEY'
make_unsafe_fixture "cookie.patch" \
  'Cookie: session=fixturevalue1234567890' \
  'COOKIE_HEADER'
make_unsafe_fixture "url.patch" \
  'https://fixture-user:fixture-password@example.invalid/path' \
  'CREDENTIAL_URL'

printf '%s\n' \
  '{"stdout":"发现明确问题","stderr":"","returncode":0}' \
  > "$scratch_dir/success.json"
printf '%s\n' \
  '{"stdout":"","stderr":"","returncode":0}' \
  > "$scratch_dir/empty.json"
printf '%s\n' \
  '{"stdout":"I cannot comply","stderr":"","returncode":0}' \
  > "$scratch_dir/refusal.json"

check_parser() {
  local runner="$1"
  "$runner" --parse-fixture "$scratch_dir/success.json" \
    | grep -Fq '发现明确问题' || fail "parser-success"

  local fixture
  local category
  while IFS='|' read -r fixture category; do
    set +e
    local output
    output="$("$runner" --parse-fixture "$scratch_dir/$fixture.json" 2>&1)"
    local status=$?
    set -e
    [[ "$status" -eq 1 ]] || fail "parser-failure-status"
    grep -Fq "category:$category" <<<"$output" || fail "parser-failure-category"
  done <<'CASES'
empty|empty_output
refusal|refusal_only
CASES

  set +e
  local consent_output
  consent_output="$(
    env -u HANK_DEEPSEEK_OUTBOUND_APPROVED \
      "$runner" "$scratch_dir/safe.patch" 2>&1
  )"
  local consent_status=$?
  set -e
  [[ "$consent_status" -eq 1 ]] || fail "consent-status"
  grep -Fq 'category:outbound_consent_missing' <<<"$consent_output" \
    || fail "consent-category"
}

check_parser "$review_runner"

# Empirical, non-mocked proof that DSH_PERMISSION_MODE=read-only actually blocks
# writes against the real dsh binary (not just asserted in a mock).
if command -v dsh >/dev/null 2>&1 && [[ -n "${DEEPSEEK_API_KEY:-}" ]]; then
  write_scratch="$scratch_dir/write-proof"
  mkdir -p "$write_scratch/home" "$write_scratch/dsh-home"
  set +e
  HOME="$write_scratch/home" DSH_HOME="$write_scratch/dsh-home" \
    DSH_PERMISSION_MODE=read-only DSH_TELEMETRY_MODE=DISABLED \
    timeout 60 dsh --profile headless \
    "创建一个文件 blocked.txt，内容为 x，然后报告是否成功。" \
    >/dev/null 2>&1
  set -e
  if [[ -f "$write_scratch/blocked.txt" ]]; then
    fail "dsh-read-only-write-not-blocked"
  fi
else
  printf 'SKIP dsh-write-proof (dsh or DEEPSEEK_API_KEY not available)\n' >&2
fi

printf 'PASS hank-dev review security\n'
