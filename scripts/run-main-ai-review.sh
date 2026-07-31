#!/usr/bin/env bash
set -euo pipefail

base_oid="${1:?base oid required}"
head_oid="${2:?head oid required}"

root="$(git rev-parse --show-toplevel)"
cd "$root"

review_cmd="${AMAZING_DEV_SKILLS_AI_REVIEW_CMD:-}"
if [[ -z "$review_cmd" ]]; then
  printf 'AI review gate failed: AMAZING_DEV_SKILLS_AI_REVIEW_CMD is not set.\n' >&2
  printf 'Configure it to a single executable path that accepts one patch-file path and exits nonzero on failed review.\n' >&2
  printf 'Use a wrapper script when the review command needs arguments.\n' >&2
  exit 1
fi

review_dir="$root/.git/ai-review"
mkdir -p "$review_dir"
patch_file="$review_dir/main-${base_oid:0:12}-${head_oid:0:12}.patch"
report_file="$review_dir/main-${base_oid:0:12}-${head_oid:0:12}.md"

git diff --binary "$base_oid" "$head_oid" > "$patch_file"
if [[ ! -s "$patch_file" ]]; then
  printf 'AI review gate: empty patch, skipping review.\n'
  exit 0
fi

printf 'AI review gate: running configured review command.\n'
set +e
"$review_cmd" "$patch_file" > "$report_file" 2>&1
status=$?
set -e

if [[ $status -ne 0 ]]; then
  printf 'AI review gate failed. Report: %s\n' "$report_file" >&2
  tail -40 "$report_file" >&2 || true
  exit "$status"
fi

if [[ ! -s "$report_file" ]]; then
  printf 'AI review gate failed: review command produced an empty report.\n' >&2
  exit 1
fi

printf 'AI review gate passed. Report: %s\n' "$report_file"
