#!/usr/bin/env bash
# 问 JEV 一道 Choice 题并把请求与回答原文存档，用法：
#   jev-ask.sh <research/jev 目录> <名字前缀> <request.json>   真问
#   jev-ask.sh --dry <request.json>                           只校验 JSON 形状，不联网
# 密钥：环境变量 JEV_KEY_VAR 指定变量名（默认 TYPESAFE_API_KEY）；该变量没有值时读
# JEV_KEY_FILE（默认 <git 根>/.dev.vars）里的同名一行。密钥不打印，也不进 curl 的命令行参数。
# 存档只在成功时留下：回答先写临时文件，HTTP 200 且 answers 非空才改成正式名字。
# 名字前缀的请求文件用原子方式认领，已被占用（成功存档或另一个进程正在问）就拒绝；
# 失败时请求副本和临时回答一并删掉，同一个名字可以重试。
# 退出码：1 参数或 JSON 形状有误，2 名字已被占用，3 没有可用密钥，4 请求失败、HTTP 非 200 或 answers 为空。
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
usage:
  jev-ask.sh <research/jev dir> <name prefix> <request.json>
  jev-ask.sh --dry <request.json>
env: JEV_KEY_VAR (default TYPESAFE_API_KEY), JEV_KEY_FILE (default <git root>/.dev.vars)
USAGE
  exit 1
}

# --dry 和真问共用的形状校验，坏请求在任何东西落盘之前就被拒绝。
validate_request() {
  python3 - "$1" <<'PY'
import json, sys
try:
    r = json.load(open(sys.argv[1]))
    assert isinstance(r, dict), "request must be a JSON object"
    assert r.get("model") == "jev-latest", "model must be jev-latest"
    assert isinstance(r.get("state"), dict), "state must be an object"
    qs = r.get("questions")
    assert isinstance(qs, dict) and qs, "questions must be a non-empty object"
    for k, q in qs.items():
        assert isinstance(q, dict), f"{k}: a question must be an object"
        assert q.get("type") == "choice", f"{k}: type must be choice"
        c = q.get("criteria")
        assert isinstance(c, dict), f"{k}: criteria must be an object"
        assert sum(isinstance(v, str) for v in c.values()) >= 2, f"{k}: a choice needs at least two string criteria"
except (OSError, ValueError, AssertionError) as e:
    print(f"invalid request: {e}", file=sys.stderr)
    sys.exit(1)
PY
}

if [ "${1:-}" = "--dry" ]; then
  [ $# -eq 2 ] || usage
  validate_request "$2"
  echo "shape ok"
  exit 0
fi

[ $# -eq 3 ] || usage
dir="$1"; name="$2"; req="$3"
[ -f "$req" ] || { echo "request file not found: $req" >&2; exit 1; }
validate_request "$req"
case "$name" in ""|*/*|.*) echo "bad name prefix: $name" >&2; exit 1;; esac

var="${JEV_KEY_VAR:-TYPESAFE_API_KEY}"
[[ "$var" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || { echo "JEV_KEY_VAR is not a valid variable name: $var" >&2; exit 1; }
key=""
if [ -n "${!var:-}" ]; then
  key="${!var}"
else
  keyfile="${JEV_KEY_FILE:-}"
  if [ -z "$keyfile" ]; then
    root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
    [ -n "$root" ] && keyfile="$root/.dev.vars"
  fi
  if [ -n "$keyfile" ] && [ -r "$keyfile" ]; then
    line="$(grep -m1 "^$var=" "$keyfile" 2>/dev/null || true)"
    key="${line#*=}"
    key="${key//$'\r'/}"
    case "$key" in
      \"?*\") key="${key#\"}"; key="${key%\"}";;
      \'?*\') key="${key#\'}"; key="${key%\'}";;
    esac
  fi
fi
case "$key" in *$'\n'*) echo "$var value contains a newline; refusing" >&2; exit 3;; esac
[ -n "$key" ] || { echo "no $var (set it in the environment, or in JEV_KEY_FILE, default <git root>/.dev.vars)" >&2; exit 3; }

mkdir -p "$dir"
reqf="$dir/$name-request.json"
resp="$dir/$name-response.json"
[ ! -e "$resp" ] || { echo "$resp already exists; use a new name" >&2; exit 2; }
# 原子认领：noclobber 下创建请求文件，已存在就失败，两个同名并发只有一个能过。
( set -o noclobber; : > "$reqf" ) 2>/dev/null || { echo "$reqf already exists; use a new name, or wait for the other run" >&2; exit 2; }
tmp="$(mktemp "$dir/.$name-response.XXXXXX")"
done_ok=0
cleanup() { [ "$done_ok" -eq 1 ] || rm -f "$tmp" "$reqf"; }
trap cleanup EXIT
cp "$req" "$reqf"

# 密钥经 stdin 交给 curl 的配置，不出现在 ps 里；转义反斜杠和双引号。
esc="${key//\\/\\\\}"; esc="${esc//\"/\\\"}"
rc=0
code="$(printf 'oauth2-bearer = "%s"\n' "$esc" | curl -K - -s -m 60 -X POST https://api.typesafe.ai/v1/systemone \
  -H "Content-Type: application/json" -d @"$req" -o "$tmp" -w '%{http_code}')" || rc=$?
if [ "$rc" -ne 0 ]; then
  echo "curl failed (exit $rc: DNS, connection or timeout); no answer, nothing archived, the same name can be retried" >&2
  exit 4
fi
if [ "$code" != "200" ]; then
  echo "JEV answered HTTP $code; no answer, nothing archived, the same name can be retried" >&2
  exit 4
fi
out="$(python3 - "$tmp" <<'PY'
import json, sys
try:
    answers = json.load(open(sys.argv[1])).get("answers")
    assert isinstance(answers, dict) and answers, "no answers"
    lines = []
    for qid, a in answers.items():
        assert isinstance(a, dict), "bad answer"
        p = a.get("probabilities", {})
        lines.append(" ".join([str(qid), str(a.get("choice")), "confidence", str(a.get("confidence")), json.dumps(p, ensure_ascii=False)]))
except (OSError, ValueError, AssertionError, AttributeError):
    sys.exit(1)
print("\n".join(lines))
PY
)" || { echo "JEV answered HTTP 200 but with no usable answers; nothing archived, the same name can be retried" >&2; exit 4; }
mv "$tmp" "$resp"
done_ok=1
printf '%s\n' "$out"
