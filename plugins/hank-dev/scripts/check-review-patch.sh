#!/usr/bin/env bash
set -euo pipefail

patch_file="${1:-}"
[[ -n "$patch_file" && -f "$patch_file" ]] || {
  printf 'SCAN_ERROR input:0\n' >&2
  exit 2
}

max_bytes=$((2 * 1024 * 1024))
size_bytes="$(wc -c < "$patch_file" | tr -d ' ')"
finding_count=0

report() {
  local rule_id="$1"
  local line_number="$2"
  printf '%s %s:%s\n' "$rule_id" "$(basename "$patch_file")" "$line_number"
  finding_count=$((finding_count + 1))
}

if (( size_bytes > max_bytes )); then
  report "SIZE_LIMIT" 0
fi

if [[ -s "$patch_file" ]] && ! LC_ALL=C grep -Iq . "$patch_file"; then
  report "BINARY_CONTENT" 0
fi

while IFS='|' read -r rule_id line_number; do
  report "$rule_id" "$line_number"
done < <(
  awk '
    function emit(rule) {
      printf "%s|%d\n", rule, FNR
    }
    {
      lower = tolower($0)
      if (index($0, "GIT binary patch") || index(lower, "binary files ")) {
        emit("BINARY_PATCH")
      }
      if ($0 ~ /BEGIN ([A-Z0-9 ]+ )?PRIVATE KEY/) {
        emit("PRIVATE_KEY")
      }
      if (lower ~ /(authorization|proxy-authorization)[[:space:]]*:/ ||
          lower ~ /(bearer|basic)[[:space:]]+[a-z0-9._~+\/=%-]{12,}/) {
        emit("AUTH_HEADER")
      }
      if (lower ~ /(set-cookie|cookie)[[:space:]]*:/) {
        emit("COOKIE_HEADER")
      }
      if ($0 ~ /AKIA[0-9A-Z]{16}/ ||
          $0 ~ /gh[pousr]_[A-Za-z0-9]{30,}/ ||
          $0 ~ /npm_[A-Za-z0-9]{30,}/ ||
          $0 ~ /xox[baprs]-[A-Za-z0-9-]{20,}/ ||
          $0 ~ /sk_live_[A-Za-z0-9]{16,}/ ||
          $0 ~ /rk_live_[A-Za-z0-9]{16,}/ ||
          $0 ~ /sk-proj-[A-Za-z0-9_-]{16,}/ ||
          $0 ~ /sk-ant-[A-Za-z0-9_-]{16,}/ ||
          $0 ~ /AIza[A-Za-z0-9_-]{30,}/) {
        emit("KNOWN_TOKEN")
      }
      if (lower ~ /(api[_-]?key|client[_-]?secret|secret[_-]?key|aws[_-]?secret[_-]?access[_-]?key|access[_-]?token|refresh[_-]?token)[[:space:]]*[:=][[:space:]]*["'\'']?[a-z0-9._~+\/=%-]{12,}/) {
        emit("GENERIC_SECRET")
      }
      if (lower ~ /[a-z][a-z0-9+.-]*:\/\/[^[:space:]\/]+:[^[:space:]@]+@/) {
        emit("CREDENTIAL_URL")
      }
    }
  ' "$patch_file"
)

if (( finding_count > 0 )); then
  printf 'SCAN_BLOCKED count:%d\n' "$finding_count"
  exit 1
fi

printf 'SCAN_PASS count:0\n'
