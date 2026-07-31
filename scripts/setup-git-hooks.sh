#!/usr/bin/env bash
set -euo pipefail

root="$(git rev-parse --show-toplevel)"
cd "$root"

git config core.hooksPath .githooks
find .githooks -type f -exec chmod +x {} +
chmod +x scripts/check-commit-message.py scripts/check-bilingual-docs.py scripts/run-main-ai-review.sh

printf 'Git hooks installed: core.hooksPath=.githooks\n'
printf 'Main push gate requires AMAZING_DEV_SKILLS_AI_REVIEW_CMD.\n'
