#!/usr/bin/env bash
# AI review runner for the pre-push main gate, backed by DeepSeek via dsh.
#
# Contract expected by scripts/run-main-ai-review.sh:
#   argv[1] = patch file path
#   stdout  = review report
#   exit 0  = review passed, nonzero = review failed
#
# OUTBOUND DATA NOTICE: configuring AMAZING_DEV_SKILLS_AI_REVIEW_CMD to this
# script is a standing authorization to send every main-bound patch to the
# DeepSeek API. plugins/hank-dev/scripts/check-review-patch.sh runs first and
# aborts the send when the patch contains credential-shaped content.
#
# Failure policy:
#   - delegation failure (no key, no dsh, timeout, empty/refusal output,
#     blocked secret scan) always fails the gate; the gate never degrades to
#     "no review happened, push anyway".
#   - findings fail the gate when the review's closing GATE: line says BLOCK,
#     and also when that line is missing, since an unreadable judgement is not
#     a pass. Set AMAZING_DEV_SKILLS_AI_REVIEW_ADVISORY=1 to report findings
#     without ever blocking on them.

set -euo pipefail

patch_file="${1:-}"
if [[ -z "$patch_file" || ! -f "$patch_file" ]]; then
  printf 'dsh review runner failed: patch file argument is missing or not a file.\n' >&2
  exit 1
fi

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
review_runner="$root/plugins/hank-dev/scripts/run-deepseek-review.py"

if [[ ! -x "$review_runner" ]]; then
  printf 'dsh review runner failed: %s is missing or not executable.\n' "$review_runner" >&2
  exit 1
fi

if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  printf 'dsh review runner failed: DEEPSEEK_API_KEY is not set in the push environment.\n' >&2
  printf 'Export it from your shell profile so git hooks inherit it.\n' >&2
  exit 1
fi

report="$(mktemp "${TMPDIR:-/tmp}/ai-review-dsh.XXXXXX")"
errors=""
cleanup() {
  rm -f "$report" ${errors:+"$errors"}
}
trap cleanup EXIT
errors="$(mktemp "${TMPDIR:-/tmp}/ai-review-dsh-err.XXXXXX")"

set +e
HANK_DEEPSEEK_OUTBOUND_APPROVED=1 \
  "$review_runner" "$patch_file" >"$report" 2>"$errors"
delegate_status=$?
set -e

if [[ "$delegate_status" -ne 0 ]]; then
  printf 'DeepSeek review delegation failed. The gate fails closed.\n' >&2
  cat "$errors" >&2
  exit 1
fi

printf '# DeepSeek review report\n\n'
cat "$report"
printf '\n'

if [[ "${AMAZING_DEV_SKILLS_AI_REVIEW_ADVISORY:-}" == "1" ]]; then
  printf 'VERDICT: advisory mode, findings do not block the push.\n'
  exit 0
fi

# The review is asked to close with a single machine-readable verdict line. Read
# that, rather than pattern-matching the prose: a report that merely discusses
# the word "critical", or quotes a severity table, is not a finding. Only the
# report's own closing line counts, so a GATE-shaped line in the body cannot
# stand in for a verdict the review never reached.
set +e
last_line="$(grep -v '^[[:space:]]*$' "$report" | tail -1)"
read_status=$?
set -e
if [[ "$read_status" -gt 1 ]]; then
  printf 'VERDICT: blocked. The report could not be read (exit %s).\n' "$read_status" >&2
  exit 1
fi
verdict="$(printf '%s\n' "$last_line" \
  | sed -nE 's/^[[:space:]]*GATE:[[:space:]]*(PASS|BLOCK)([^A-Za-z].*)?$/\1/p')"

case "$verdict" in
  BLOCK)
    printf 'VERDICT: blocked. The review reported at least one high or critical severity finding.\n' >&2
    printf 'Fix the finding, or re-push with AMAZING_DEV_SKILLS_AI_REVIEW_ADVISORY=1 after judging it a false positive.\n' >&2
    exit 1
    ;;
  PASS)
    printf 'VERDICT: passed. The review reported no high or critical severity finding.\n'
    ;;
  *)
    printf 'VERDICT: blocked. The report does not end with a GATE: PASS or GATE: BLOCK line,\n' >&2
    printf 'so its judgement is unknown and the gate fails closed.\n' >&2
    exit 1
    ;;
esac
