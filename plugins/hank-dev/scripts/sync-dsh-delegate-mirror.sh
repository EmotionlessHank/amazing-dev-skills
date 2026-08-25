#!/usr/bin/env bash
# Copies the canonical dsh-deepseek-delegate skill + runner into the two
# personal-library mirror locations that deepseek-developer/SKILL.md hardcodes
# an absolute path into. Run this after editing either file; the companion
# check in validate-dsh-delegate-security.sh fails closed if the mirrors drift.
set -euo pipefail

plugin_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
skill_source="$plugin_root/skills/dsh-deepseek-delegate/SKILL.md"
runner_source="$plugin_root/scripts/run-dsh-delegate.py"

[[ -f "$skill_source" ]] || { printf 'missing %s\n' "$skill_source" >&2; exit 1; }
[[ -f "$runner_source" ]] || { printf 'missing %s\n' "$runner_source" >&2; exit 1; }

for mirror_root in "$HOME/.agents/skills/dsh-deepseek-delegate" "$HOME/.claude/skills/dsh-deepseek-delegate"; do
  mkdir -p "$mirror_root/scripts"
  cp "$skill_source" "$mirror_root/SKILL.md"
  cp "$runner_source" "$mirror_root/scripts/run-dsh-delegate.py"
  chmod +x "$mirror_root/scripts/run-dsh-delegate.py"
  printf 'synced %s\n' "$mirror_root"
done
