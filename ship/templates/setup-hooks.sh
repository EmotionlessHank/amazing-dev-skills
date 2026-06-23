#!/bin/sh
# Idempotently mount the local CI gate. Run once after a fresh clone / on a new machine.
# The gate = local git config (core.hooksPath) + hook files; neither survives `git clone`
# automatically — hence this installer (also call it from your onboarding / setup flow).

ROOT=$(git rev-parse --show-toplevel) || exit 1
cd "$ROOT" || exit 1

git config core.hooksPath {HOOKS_DIR}
# executable bit on hook scripts only (skip docs like README.md)
find {HOOKS_DIR} -type f ! -name '*.md' -exec chmod +x {} + 2>/dev/null

echo "✓ local CI gate mounted: core.hooksPath={HOOKS_DIR}"
echo "  hooks: $(ls {HOOKS_DIR} 2>/dev/null | tr '\n' ' ')"

missing=
for t in {TOOLS}; do
  command -v "$t" >/dev/null 2>&1 || missing="$missing $t"
done
[ -n "$missing" ] && echo "  ⚠️ missing tools:$missing"

echo "  → git push now runs your CI chain locally; red blocks the push."
