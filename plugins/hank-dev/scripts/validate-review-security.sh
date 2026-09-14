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
    '600 秒' \
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
  'TIMEOUT_SECONDS = 600' \
  'capture_output=True' \
  '"--profile"' \
  '"headless"' \
  'empty_output' \
  'refusal_only' \
  'nonzero_exit' \
  'GATE: PASS' \
  'GATE: BLOCK' \
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
assert module.TIMEOUT_SECONDS == 600
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
        assert args[0] == module.shutil.which("dsh")
        assert args[1:] == ["--profile", "headless", module.PROMPT]
        assert 0 < kwargs["timeout"] <= calls[0][1]["timeout"] <= 600
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

        def scan_only_run(args, **kwargs):
            assert Path(args[0]).name == "check-review-patch.sh"
            return subprocess.CompletedProcess(args, 0, "SCAN_PASS count:0\n", "")

        with mock.patch.object(module.subprocess, "run", side_effect=scan_only_run), \
             mock.patch.object(module.shutil, "which", return_value=None):
            try:
                module.run_review(patch)
            except module.ResultError as exc:
                assert exc.category == "dsh_not_found"
            else:
                raise AssertionError("dsh 缺失必须失败关闭")
        assert not list(Path(temp_root).glob("hank-review.*"))

        fake_bin = Path(temp_root) / "untrusted-bin"
        fake_bin.mkdir()
        fake_dsh = fake_bin / "dsh"
        fake_dsh.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        fake_dsh.chmod(0o777)
        original_path = os.environ.get("PATH")
        os.environ["PATH"] = str(fake_bin) + os.pathsep + (original_path or os.defpath)
        try:
            with mock.patch.object(module.subprocess, "run", side_effect=scan_only_run):
                try:
                    module.run_review(patch)
                except module.ResultError as exc:
                    assert exc.category == "dsh_untrusted_binary"
                else:
                    raise AssertionError("group/other 可写的 dsh 候选必须失败关闭")
        finally:
            if original_path is None:
                os.environ.pop("PATH", None)
            else:
                os.environ["PATH"] = original_path
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

# Every credential-shaped fixture below is assembled at runtime. A literal one
# would make this file's own source match check-review-patch.sh, which scans the
# patch that changes it, and every push touching this file would be blocked.
fv="fixture""value1234567890"
dq='"'

printf 'diff --git a/a.txt b/a.txt\n+safe fixture\n' > "$scratch_dir/safe.patch"
"$scanner" "$scratch_dir/safe.patch" | grep -Fq 'SCAN_PASS count:0' || fail "safe-scan"

printf 'diff --git a/a.txt b/a.txt\n+%s\n' "Authorization"": Bearer $fv" > "$scratch_dir/unsafe.patch"
set +e
unsafe_output="$("$scanner" "$scratch_dir/unsafe.patch" 2>&1)"
unsafe_status=$?
set -e
[[ "$unsafe_status" -eq 1 ]] || fail "unsafe-scan-status"
grep -Fq 'AUTH_HEADER unsafe.patch:2' <<<"$unsafe_output" || fail "unsafe-scan-rule"
grep -Fq 'SCAN_BLOCKED count:' <<<"$unsafe_output" || fail "unsafe-scan-summary"
if grep -Fq "$fv" <<<"$unsafe_output"; then
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
  "AWS_SECRET_ACCESS_KEY=$fv" \
  'GENERIC_SECRET'
make_unsafe_fixture "stripe.patch" \
  "stripe_api_key=$fv" \
  'GENERIC_SECRET'
make_unsafe_fixture "openai.patch" \
  "sk-proj-$fv$fv" \
  'KNOWN_TOKEN'
make_unsafe_fixture "google.patch" \
  "AIza$fv$fv" \
  'KNOWN_TOKEN'
make_unsafe_fixture "private.patch" \
  "-----BEGIN PRIVATE"" KEY-----" \
  'PRIVATE_KEY'
make_unsafe_fixture "cookie.patch" \
  "Cookie"": session=$fv" \
  'COOKIE_HEADER'
make_unsafe_fixture "url.patch" \
  "https:""//fixture-user:fixture-password@example.invalid/path" \
  'CREDENTIAL_URL'

# The AUTH_HEADER rule is anchored to the credential position, so a documented
# header whose value is a shell or template placeholder must not block a push,
# while a real token on the same shape of line still must.
make_safe_fixture() {
  local filename="$1"
  local content="$2"
  printf 'diff --git a/a.txt b/a.txt\n+%s\n' "$content" > "$scratch_dir/$filename"
  "$scanner" "$scratch_dir/$filename" | grep -Fq 'SCAN_PASS count:0' \
    || fail "auth-placeholder-false-positive"
}

make_safe_fixture "auth-shell-placeholder.patch" \
  '  -H "Authorization: Basic ${FIXTURE_API_KEY}" \'
make_safe_fixture "auth-bare-placeholder.patch" \
  'Authorization: Bearer $FIXTURE_TOKEN'
make_safe_fixture "auth-angle-placeholder.patch" \
  '"Authorization": "<YOUR_API_KEY>"'
make_safe_fixture "auth-template-placeholder.patch" \
  'Authorization: Bearer {{token}}'
make_safe_fixture "auth-valueless.patch" \
  'Authorization:'

make_unsafe_fixture "auth-token-beside-var.patch" \
  "curl -H \"Authorization"": Bearer $fv\" -d \"\$PAYLOAD\"" \
  'AUTH_HEADER'
make_unsafe_fixture "auth-proxy.patch" \
  "proxy-authorization"": Bearer $fv" \
  'AUTH_HEADER'

# Self-referential paths are skipped, and only those paths. The same credential
# line must still block under any other path, including a neighbouring one.
printf 'diff --git a/x b/x\n--- a/x\n+++ b/%s\n+%s\n' \
  'plugins/hank-dev/scripts/validate-review-security.sh' \
  "Authorization"": Bearer $fv" > "$scratch_dir/exempt.patch"
"$scanner" "$scratch_dir/exempt.patch" | grep -Fq 'SCAN_PASS count:0' \
  || fail "self-reference-exemption-missing"

printf 'diff --git a/x b/x\n--- a/x\n+++ b/%s\n+%s\n' \
  'plugins/hank-dev/scripts/run-deepseek-review.py' \
  "Authorization"": Bearer $fv" > "$scratch_dir/non-exempt.patch"
set +e
non_exempt_output="$("$scanner" "$scratch_dir/non-exempt.patch" 2>&1)"
non_exempt_status=$?
set -e
[[ "$non_exempt_status" -eq 1 ]] || fail "self-reference-exemption-too-broad"
grep -Fq 'AUTH_HEADER non-exempt.patch:4' <<<"$non_exempt_output" \
  || fail "self-reference-exemption-too-broad"

# The placeholder exemption covers the header, never the whole line: a real
# token further along the same line must still block.
make_unsafe_fixture "auth-masked-token.patch" \
  "curl -H \"Authorization"": Bearer \$SOME_VAR\" -H \"X-Trace"": Bearer $fv\"" \
  'AUTH_HEADER'

# The exemption resets at each file boundary, so a credential in a later,
# non-exempt file of the same patch still blocks.
{
  printf 'diff --git a/a b/a\n+++ b/%s\n+%s\n' \
    'plugins/hank-dev/scripts/check-review-patch.sh' \
    "Authorization"": Bearer $fv"
  printf 'diff --git a/b b/b\n+++ b/%s\n+%s\n' \
    'other.txt' \
    "Authorization"": Bearer $fv"
} > "$scratch_dir/exempt-reset.patch"
set +e
reset_output="$("$scanner" "$scratch_dir/exempt-reset.patch" 2>&1)"
reset_status=$?
set -e
[[ "$reset_status" -eq 1 ]] || fail "self-reference-exemption-leaks-across-files"
grep -Fq 'AUTH_HEADER exempt-reset.patch:6' <<<"$reset_output" \
  || fail "self-reference-exemption-leaks-across-files"

# git quotes a path containing spaces or non-ASCII, and a patch can arrive with
# CRLF endings; both must still resolve to the exempt path.
printf 'diff --git a/a b/a\n+++ "b/%s"\n+%s\n' \
  'plugins/hank-dev/scripts/check-review-patch.sh' \
  "Authorization"": Bearer $fv" > "$scratch_dir/exempt-quoted.patch"
"$scanner" "$scratch_dir/exempt-quoted.patch" | grep -Fq 'SCAN_PASS count:0' \
  || fail "self-reference-exemption-quoted-path"

printf 'diff --git a/a b/a\r\n+++ b/%s\r\n+%s\r\n' \
  'plugins/hank-dev/scripts/check-review-patch.sh' \
  "Authorization"": Bearer $fv" > "$scratch_dir/exempt-crlf.patch"
"$scanner" "$scratch_dir/exempt-crlf.patch" | grep -Fq 'SCAN_PASS count:0' \
  || fail "self-reference-exemption-crlf-path"

# An added line whose content starts with "++ " renders as "+++ ...", textually
# identical to a file header. Inside a hunk it must be scanned as content, and
# must not be able to forge an exemption for the lines that follow it.
printf 'diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1 +2 @@\n+++ %s\n' \
  "Authorization"": Bearer $fv" > "$scratch_dir/hunk-content.patch"
set +e
hunk_output="$("$scanner" "$scratch_dir/hunk-content.patch" 2>&1)"
hunk_status=$?
set -e
[[ "$hunk_status" -eq 1 ]] || fail "hunk-content-mistaken-for-header"
grep -Fq 'AUTH_HEADER hunk-content.patch:5' <<<"$hunk_output" \
  || fail "hunk-content-mistaken-for-header"

printf 'diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1 +2 @@\n+++ b/%s\n+%s\n' \
  'plugins/hank-dev/scripts/check-review-patch.sh' \
  "Authorization"": Bearer $fv" > "$scratch_dir/forged-header.patch"
set +e
forged_output="$("$scanner" "$scratch_dir/forged-header.patch" 2>&1)"
forged_status=$?
set -e
[[ "$forged_status" -eq 1 ]] || fail "forged-header-grants-exemption"
grep -Fq 'AUTH_HEADER forged-header.patch:6' <<<"$forged_output" \
  || fail "forged-header-grants-exemption"

# Deleting an exempt file points +++ at /dev/null, so the old path decides.
printf 'diff --git a/p b/p\n--- a/%s\n+++ /dev/null\n@@ -1 +0 @@\n-%s\n' \
  'plugins/hank-dev/scripts/check-review-patch.sh' \
  "Authorization"": Bearer $fv" > "$scratch_dir/exempt-delete.patch"
"$scanner" "$scratch_dir/exempt-delete.patch" | grep -Fq 'SCAN_PASS count:0' \
  || fail "self-reference-exemption-delete"

# Header names and auth schemes are case insensitive, and a scheme with no value
# carries no credential. Neither may raise a false positive.
make_safe_fixture "auth-upper-header.patch" \
  'AUTHORIZATION: Bearer ${FIXTURE_TOKEN}'
make_safe_fixture "auth-upper-scheme.patch" \
  'Authorization: BEARER ${FIXTURE_TOKEN}'
make_safe_fixture "auth-scheme-only.patch" \
  'Authorization: Bearer'

make_unsafe_fixture "auth-upper-real.patch" \
  "AUTHORIZATION"": BEARER $fv" \
  'AUTH_HEADER'

# The placeholder exemption covers the header only while the rest of the line is
# clean: a credential riding in behind a placeholder must still block.
make_unsafe_fixture "auth-ride-along.patch" \
  "Authorization"": \$TOKEN X-Custom: my-custom-secret-abcdef123456" \
  'AUTH_HEADER'
make_unsafe_fixture "auth-after-placeholder.patch" \
  "Authorization"": Bearer \${VAR} $fv" \
  'AUTH_HEADER'

# A rename must not carry the exemption to its new, non-exempt path.
printf 'diff --git a/p b/e\n--- a/%s\n+++ b/evil.sh\n@@ -1 +1 @@\n+%s\n' \
  'plugins/hank-dev/scripts/check-review-patch.sh' \
  "Authorization"": Bearer $fv" > "$scratch_dir/exempt-rename.patch"
set +e
rename_output="$("$scanner" "$scratch_dir/exempt-rename.patch" 2>&1)"
rename_status=$?
set -e
[[ "$rename_status" -eq 1 ]] || fail "self-reference-exemption-follows-rename"
grep -Fq 'AUTH_HEADER exempt-rename.patch:5' <<<"$rename_output" \
  || fail "self-reference-exemption-follows-rename"

# A JSON or object literal quotes the header name, so the colon does not sit
# right after it. Without that, a quoted credential goes unscanned and the
# quoted-placeholder fixture below would pass for the wrong reason.
make_unsafe_fixture "auth-json-digest.patch" \
  "${dq}Authorization${dq}: ${dq}Digest $fv${dq}" \
  'AUTH_HEADER'
make_unsafe_fixture "auth-json-bearer.patch" \
  "${dq}Authorization${dq}: ${dq}Bearer $fv${dq}" \
  'AUTH_HEADER'

# Shell expansions carry defaults and modifiers, and all of them are placeholders.
make_safe_fixture "auth-expand-default.patch" \
  'Authorization: Bearer ${FIXTURE_TOKEN:-}'
make_safe_fixture "auth-expand-error.patch" \
  'Authorization: Bearer ${FIXTURE_TOKEN?missing}'
make_safe_fixture "auth-expand-trim.patch" \
  'Authorization: Bearer ${FIXTURE_TOKEN#prefix}'

# A quoted value must not stop the scheme from being stripped, or an ordinary
# JSON placeholder reads as a credential and blocks an honest push.
make_safe_fixture "auth-json-placeholder.patch" \
  "${dq}Authorization${dq}: ${dq}Bearer \${FIXTURE_KEY}${dq}"
make_safe_fixture "auth-squote-placeholder.patch" \
  'Authorization: '"'"'Basic ${FIXTURE_TOKEN}'"'"''

# Shell positional parameters are placeholders too.
make_safe_fixture "auth-positional-brace.patch" \
  'Authorization: ${1}'
make_safe_fixture "auth-positional-bare.patch" \
  'Authorization: Bearer $1'

# A merge commit renders combined hunks with @@@, which must also count as a
# hunk so its content lines cannot pose as file headers.
printf 'diff --cc x\n--- a/x\n+++ b/x\n@@@ -1,1 -1,1 +1,1 @@@\n+++ %s\n' \
  "Authorization"": Bearer $fv" > "$scratch_dir/combined.patch"
set +e
combined_output="$("$scanner" "$scratch_dir/combined.patch" 2>&1)"
combined_status=$?
set -e
[[ "$combined_status" -eq 1 ]] || fail "combined-diff-hunk-state"
grep -Fq 'AUTH_HEADER combined.patch:5' <<<"$combined_output" \
  || fail "combined-diff-hunk-state"

# A combined diff separates files with "diff --cc", so the exemption must reset
# there too, or it leaks from a self-referential file onto the next one.
{
  printf 'diff --cc %s\n--- a/%s\n+++ b/%s\n@@@ -1,1 -1,1 +1,1 @@@\n+%s\n' \
    'plugins/hank-dev/scripts/check-review-patch.sh' \
    'plugins/hank-dev/scripts/check-review-patch.sh' \
    'plugins/hank-dev/scripts/check-review-patch.sh' \
    "Authorization"": Bearer $fv"
  printf 'diff --cc other.txt\n--- a/other.txt\n+++ b/other.txt\n@@@ -1,1 -1,1 +1,1 @@@\n+%s\n' \
    "Authorization"": Bearer $fv"
} > "$scratch_dir/combined-reset.patch"
set +e
combined_reset_output="$("$scanner" "$scratch_dir/combined-reset.patch" 2>&1)"
combined_reset_status=$?
set -e
[[ "$combined_reset_status" -eq 1 ]] || fail "combined-diff-exemption-leaks"
grep -Fq 'AUTH_HEADER combined-reset.patch:10' <<<"$combined_reset_output" \
  || fail "combined-diff-exemption-leaks"

printf '%s\n' \
  '{"stdout":"发现明确问题","stderr":"","returncode":0}' \
  > "$scratch_dir/success.json"
printf '%s\n' \
  '{"stdout":"","stderr":"","returncode":0}' \
  > "$scratch_dir/empty.json"
printf '%s\n' \
  '{"stdout":"I cannot comply","stderr":"","returncode":0}' \
  > "$scratch_dir/refusal.json"
printf '%s\n' \
  '{"stdout":"发现明确问题","stderr":"dsh: reasoning:\nthinking out loud","returncode":0}' \
  > "$scratch_dir/reasoning.json"
printf '%s\n' \
  '{"stdout":"发现明确问题","stderr":"","returncode":1}' \
  > "$scratch_dir/nonzero.json"

check_parser() {
  local runner="$1"
  "$runner" --parse-fixture "$scratch_dir/success.json" \
    | grep -Fq '发现明确问题' || fail "parser-success"

  # dsh --profile headless streams reasoning to stderr by design, so a
  # non-empty stderr on a zero exit must still parse as a usable result.
  "$runner" --parse-fixture "$scratch_dir/reasoning.json" \
    | grep -Fq '发现明确问题' || fail "parser-reasoning-stderr-ignored"

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
nonzero|nonzero_exit
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
    "创建一个文件 blocked.txt，内容为 x。报告成功与否，并把工具返回的原始报错文本逐字引用，不要转述或省略。" \
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
  # File absence alone doesn't prove the model actually attempted the write
  # and got denied, as opposed to e.g. refusing the task outright. Require
  # positive evidence: dsh's own sandbox denial text quoted back.
  if ! grep -qi 'read-only' "$write_proof_output"; then
    tail -20 "$write_proof_output" >&2 || true
    fail "dsh-write-proof-inconclusive"
  fi
else
  printf 'SKIP dsh-write-proof (dsh, timeout, or DEEPSEEK_API_KEY not available)\n' >&2
fi

printf 'PASS hank-dev review security\n'
