#!/usr/bin/env bash
set -euo pipefail

plugin_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
codex_skill="$plugin_root/skills/review/SKILL.md"
personal_skill="${1:-}"
scanner="$plugin_root/scripts/check-review-patch.sh"
review_runner="$plugin_root/scripts/run-deepseek-review.py"
delegate_runner="${2:-}"

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
    'HANK_REVIEW_SECURITY_CONTRACT_V2' \
    'run-deepseek-review.py' \
    'review-input.patch' \
    '120 秒' \
    'permission denied' \
    'agent fallback' \
    'error 事件' \
    '输出为空' \
    '明确授权本次' \
    '敏感信息' \
    '隔离的 HOME'; do
    grep -Fq "$required" "$skill_file" || fail "missing-security-contract"
  done
}

check_skill "$codex_skill"
if [[ -n "$personal_skill" ]]; then
  [[ -f "$personal_skill" ]] || fail "personal-skill-missing"
  check_skill "$personal_skill"
fi

[[ -f "$review_runner" ]] || fail "review-runner-missing"

for runner in "$review_runner" ${delegate_runner:+"$delegate_runner"}; do
  [[ -f "$runner" ]] || fail "delegate-runner-missing"
  forbidden_flag="$(printf '%s%s' '--' 'auto')"
  if grep -Fq -- "$forbidden_flag" "$runner"; then
    fail "runner-automatic-approval"
  fi
  for required in \
    'TIMEOUT_SECONDS = 120' \
    'capture_output=True' \
    '"--pure"' \
    '"--format"' \
    '"json"' \
    'non_json_output' \
    'permission_denied' \
    'agent_fallback' \
    'error_event' \
    'unexpected_tool_use' \
    'empty_output' \
    'refusal_only' \
    'outbound_consent_missing' \
    'OPENCODE_CONFIG_DIR' \
    'OPENCODE_DISABLE_CLAUDE_CODE' \
    'OPENCODE_DISABLE_DEFAULT_PLUGINS' \
    '_load_isolated_config' \
    '_isolated_environment' \
    '_remaining'; do
    grep -Fq "$required" "$runner" || fail "runner-contract-missing"
  done
done

grep -Fq 'MAX_PATCH_BYTES = 2 * 1024 * 1024' "$review_runner" \
  || fail "review-size-limit-missing"
grep -Fq '_review_permission' "$review_runner" \
  || fail "review-absolute-permission-missing"
grep -Fq 'stdin=subprocess.DEVNULL' "$review_runner" \
  || fail "review-stdin-contract-missing"
if [[ -n "$delegate_runner" ]]; then
  grep -Fq 'MAX_PROMPT_BYTES = 2 * 1024 * 1024' "$delegate_runner" \
    || fail "delegate-size-limit-missing"
  grep -Fq 'input=prompt' "$delegate_runner" \
    || fail "delegate-stdin-contract-missing"
fi

python3 - "$review_runner" ${delegate_runner:+"$delegate_runner"} <<'PY'
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
assert module.parse_jsonl(
    '{"type":"tool_use","part":{"tool":"read","state":{"status":"completed"}}}\n'
    '{"type":"text","part":{"type":"text","text":"读取后发现问题"}}\n',
    "",
    0,
) == "读取后发现问题"

with tempfile.TemporaryDirectory() as temp_root:
    config_root = Path(temp_root) / "source-config"
    config_file = config_root / "opencode" / "opencode.json"
    config_file.parent.mkdir(parents=True)
    config_file.write_text(
        json.dumps(
            {
                "model": "deepseek/deepseek-v4-pro",
                "provider": {
                    "deepseek": {
                        "npm": "@ai-sdk/openai-compatible",
                        "name": "DeepSeek",
                        "options": {
                            "baseURL": "https://example.invalid/v1",
                            "apiKey": "fixture-provider-key",
                        },
                        "models": {"deepseek-v4-pro": {"name": "fixture"}},
                    }
                },
                "agent": {
                    "deepseek-worker": {
                        "model": "deepseek/deepseek-v4-pro",
                        "description": "不能进入隔离配置",
                    }
                },
                "instructions": ["/private/global-instruction.md"],
                "plugin": ["global-plugin"],
                "mcp": {"global-server": {"type": "local"}},
            }
        ),
        encoding="utf-8",
    )
    patch = Path(temp_root) / "input.patch"
    patch.write_text("diff --git a/a b/a\n+safe\n", encoding="utf-8")
    oversized = Path(temp_root) / "oversized.patch"
    oversized.write_bytes(b"x" * (module.MAX_PATCH_BYTES + 1))
    tracked_env = (
        "TMPDIR",
        "XDG_CONFIG_HOME",
        module.CONSENT_ENV,
        "AWS_SECRET_ACCESS_KEY",
        "CLAUDE_CONFIG_DIR",
    )
    original_env = {key: os.environ.get(key) for key in tracked_env}
    os.environ["TMPDIR"] = temp_root
    os.environ["XDG_CONFIG_HOME"] = str(config_root)
    os.environ[module.CONSENT_ENV] = "1"
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
        assert args[0] == "opencode"
        assert 0 < kwargs["timeout"] <= calls[0][1]["timeout"] <= 120
        assert kwargs["stdin"] is subprocess.DEVNULL
        assert kwargs["capture_output"] is True
        child_env = kwargs["env"]
        scratch = Path(kwargs["cwd"])
        assert child_env["HOME"] == str(scratch / "home")
        assert child_env["XDG_CONFIG_HOME"] == str(scratch / "config")
        assert child_env["XDG_DATA_HOME"] == str(scratch / "data")
        assert child_env["XDG_CACHE_HOME"] == str(scratch / "cache")
        assert child_env["XDG_STATE_HOME"] == str(scratch / "state")
        assert child_env["OPENCODE_CONFIG_DIR"] == str(scratch / "config" / "opencode")
        assert child_env["OPENCODE_DISABLE_CLAUDE_CODE"] == "1"
        assert child_env["OPENCODE_DISABLE_DEFAULT_PLUGINS"] == "1"
        assert (scratch / "AGENTS.md").read_text(encoding="utf-8") == "当前目录没有附加指令。\n"
        assert (scratch / "AGENTS.md").stat().st_mode & 0o777 == 0o600
        assert "AWS_SECRET_ACCESS_KEY" not in child_env
        assert "CLAUDE_CONFIG_DIR" not in child_env
        isolated = json.loads(child_env["OPENCODE_CONFIG_CONTENT"])
        assert isolated["instructions"] == []
        assert isolated["plugin"] == []
        assert isolated["mcp"] == {}
        assert isolated["share"] == "disabled"
        assert isolated["provider"]["deepseek"]["options"]["apiKey"] == "fixture-provider-key"
        assert isolated["agent"]["deepseek-worker"].get("description") is None
        permission = isolated["agent"]["deepseek-worker"]["permission"]
        assert permission["*"] == "deny"
        assert list(permission["read"].items()) == [
            ("*", "deny"),
            ("*/review-input.patch", "allow"),
        ]
        assert permission["external_directory"] == "deny"
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

        permission_scratch = Path(temp_root) / "permission-scratch"
        permission_scratch.mkdir()
        allowed_patch = permission_scratch / "review-input.patch"
        allowed_patch.write_text("允许读取的夹具\n", encoding="utf-8")
        (permission_scratch / "second.patch").write_text("拒绝读取\n", encoding="utf-8")
        external_patch = Path(temp_root) / "review-input.patch"
        external_patch.write_text("拒绝外部读取\n", encoding="utf-8")
        permission_env = module._isolated_environment(permission_scratch, allowed_patch)

        def debug_read(file_path):
            return subprocess.run(
                [
                    "opencode",
                    "debug",
                    "agent",
                    "deepseek-worker",
                    "--pure",
                    "--tool",
                    "read",
                    "--params",
                    json.dumps({"filePath": file_path}),
                ],
                cwd=permission_scratch,
                env=permission_env,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

        allowed_result = debug_read("review-input.patch")
        second_result = debug_read("second.patch")
        external_result = debug_read(str(external_patch))
        assert allowed_result.returncode == 0
        assert second_result.returncode != 0
        assert external_result.returncode != 0
    finally:
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

if len(sys.argv) > 2:
    delegate_path = Path(sys.argv[2])
    delegate_spec = importlib.util.spec_from_file_location("delegate_runner", delegate_path)
    delegate = importlib.util.module_from_spec(delegate_spec)
    assert delegate_spec.loader is not None
    delegate_spec.loader.exec_module(delegate)
    with tempfile.TemporaryDirectory() as temp_root:
        config_root = Path(temp_root) / "source-config"
        config_file = config_root / "opencode" / "opencode.json"
        config_file.parent.mkdir(parents=True)
        config_file.write_text(
            json.dumps(
                {
                    "model": "deepseek/deepseek-v4-pro",
                    "provider": {
                        "deepseek": {
                            "npm": "@ai-sdk/openai-compatible",
                            "options": {
                                "baseURL": "https://example.invalid/v1",
                                "apiKey": "fixture-provider-key",
                            },
                            "models": {"deepseek-v4-pro": {"name": "fixture"}},
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        tracked_env = (
            "TMPDIR",
            "XDG_CONFIG_HOME",
            delegate.CONSENT_ENV,
            "AWS_SECRET_ACCESS_KEY",
            "PATH",
        )
        original_env = {key: os.environ.get(key) for key in tracked_env}
        os.environ["TMPDIR"] = temp_root
        os.environ["XDG_CONFIG_HOME"] = str(config_root)
        os.environ[delegate.CONSENT_ENV] = "1"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "must-not-reach-child"
        delegate_calls = []

        def delegate_run(args, **kwargs):
            delegate_calls.append((args, kwargs))
            child_env = kwargs["env"]
            assert args[0] == "opencode"
            assert args[-1] == "json"
            assert kwargs["input"]
            assert 0 < kwargs["timeout"] <= 120
            assert "AWS_SECRET_ACCESS_KEY" not in child_env
            assert child_env["OPENCODE_CONFIG_DIR"].endswith("/config/opencode")
            assert child_env["OPENCODE_DISABLE_CLAUDE_CODE"] == "1"
            assert child_env["OPENCODE_DISABLE_DEFAULT_PLUGINS"] == "1"
            isolated = json.loads(child_env["OPENCODE_CONFIG_CONTENT"])
            assert isolated["instructions"] == []
            assert isolated["plugin"] == []
            assert isolated["mcp"] == {}
            assert isolated["agent"]["deepseek-worker"]["permission"]["*"] == "deny"
            return subprocess.CompletedProcess(
                args,
                0,
                '{"type":"text","text":"委派完成"}\n',
                "",
            )

        try:
            with mock.patch.object(delegate.subprocess, "run", side_effect=delegate_run):
                assert delegate.run_delegate("安全的测试任务") == "委派完成"
                near_limit = "x" * delegate.MAX_PROMPT_BYTES
                assert delegate.run_delegate(near_limit) == "委派完成"
            assert len(delegate_calls) == 2
            assert delegate_calls[0][1]["input"] == "安全的测试任务"
            assert delegate_calls[1][1]["input"] == near_limit
            with mock.patch.object(
                delegate.subprocess,
                "run",
                side_effect=AssertionError("不应启动子进程"),
            ):
                try:
                    delegate.run_delegate("x" * (delegate.MAX_PROMPT_BYTES + 1))
                except delegate.ResultError as exc:
                    assert exc.category == "input_too_large"
                else:
                    raise AssertionError("超限 prompt 必须失败关闭")

            fake_bin = Path(temp_root) / "fake-bin"
            fake_bin.mkdir()
            fake_opencode = fake_bin / "opencode"
            fake_opencode.write_text(
                """#!/usr/bin/env python3
import json
import sys

payload = sys.stdin.buffer.read()
if len(payload) != 2 * 1024 * 1024:
    raise SystemExit(9)
if sum(len(arg.encode("utf-8")) for arg in sys.argv) > 4096:
    raise SystemExit(8)
print(json.dumps({"type": "text", "text": "stdin boundary ok"}))
""",
                encoding="utf-8",
            )
            fake_opencode.chmod(0o700)
            os.environ["PATH"] = (
                str(fake_bin) + os.pathsep + (original_env["PATH"] or os.defpath)
            )
            assert (
                delegate.run_delegate("x" * delegate.MAX_PROMPT_BYTES)
                == "stdin boundary ok"
            )
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
  '{"stdout":"{\"type\":\"text\",\"text\":\"发现明确问题\"}\n","stderr":"","returncode":0}' \
  > "$scratch_dir/success.json"
printf '%s\n' \
  '{"stdout":"","stderr":"permission denied","returncode":0}' \
  > "$scratch_dir/permission.json"
printf '%s\n' \
  '{"stdout":"","stderr":"Falling back to default agent","returncode":0}' \
  > "$scratch_dir/fallback.json"
printf '%s\n' \
  '{"stdout":"not json\n","stderr":"","returncode":0}' \
  > "$scratch_dir/non-json.json"
printf '%s\n' \
  '{"stdout":"{\"type\":\"error\",\"message\":\"fixture\"}\n","stderr":"","returncode":0}' \
  > "$scratch_dir/error.json"
printf '%s\n' \
  '{"stdout":"{\"type\":\"tool_use\",\"part\":{\"type\":\"tool\"}}\n","stderr":"","returncode":0}' \
  > "$scratch_dir/tool.json"
printf '%s\n' \
  '{"stdout":"","stderr":"","returncode":0}' \
  > "$scratch_dir/empty.json"
printf '%s\n' \
  '{"stdout":"{\"type\":\"text\",\"text\":\"I cannot comply\"}\n","stderr":"","returncode":0}' \
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
permission|permission_denied
fallback|agent_fallback
non-json|non_json_output
error|error_event
tool|unexpected_tool_use
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
if [[ -n "$delegate_runner" ]]; then
  check_parser "$delegate_runner"
fi

printf 'PASS hank-dev review security\n'
