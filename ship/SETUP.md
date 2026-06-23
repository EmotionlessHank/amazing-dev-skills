# ship — Migrating to a New Project (SETUP)

Copy `SKILL.md` into the target project's skills directory (commonly `.claude/skills/ship/`), copy the templates into the project, replace `{placeholders}`, then verify.

## Placeholder Replacement Checklist

| Placeholder | Meaning | Example (iOS) | Example (Node/web) |
|-------------|---------|---------------|--------------------|
| `{CI_CHAIN}` | The CI-equivalent chain the gate runs before push | `xcodegen generate → swiftlint --strict → xcodebuild test` | `pnpm lint && pnpm type-check && pnpm test` |
| `{HOOKS_DIR}` | Directory holding the git hooks (committed to the repo) | `.githooks` | `.githooks` |
| `{TOOLS}` | Tools the gate needs (warn + stop if missing) | `xcodegen, swiftlint, xcodebuild, xcrun` | `node, pnpm` |
| `{DEFAULT_ACCOUNT}` | `gh` account to switch back to after a push (the one matching `git config user.email`) | `your-default-gh-user` | `your-default-gh-user` |

> **Single `gh` account?** Delete the `gh auth switch` steps from `SKILL.md` §2 and the account row above — they only matter with multiple logged-in accounts.

## Install Steps

1. Copy `templates/setup-hooks.sh` → `bin/setup-hooks.sh` (replace `{HOOKS_DIR}`, `{TOOLS}`); `chmod +x bin/setup-hooks.sh`.
2. Copy `templates/pre-push` → `{HOOKS_DIR}/pre-push`; replace the `{CI_CHAIN}` block with your real commands (each step must exit non-zero on failure so the gate blocks). `chmod +x {HOOKS_DIR}/pre-push`.
3. Run `bash bin/setup-hooks.sh` once → sets `core.hooksPath={HOOKS_DIR}` + chmods the hooks.
4. (Optional) Register a one-line pointer in your project's AI rules / CONTRIBUTING so "push" routes here.

## Verification

- `git config core.hooksPath` prints `{HOOKS_DIR}`.
- Make a trivial commit, run `git push` → you should see the gate run `{CI_CHAIN}`; on green it pushes, on red it blocks (non-zero) and nothing is pushed.
- Confirm `--no-verify` is treated as a red line in your rules (only for genuine hook false-positives).

## Notes

- The gate is a **hard backstop**; this skill is its **front door** (self-heal + account automation). Keep a separate "run the CI chain locally" habit for in-dev verification so failures surface before the push attempt.
- `core.hooksPath` is **local git config**, not committed — that's why `setup-hooks.sh` exists (fresh-clone / new-machine self-heal). Call it from your onboarding / setup flow too.
- The hook always runs the full chain regardless of what changed (docs-only commits included). That's intentional — the gate makes no assumptions about which change is "safe".
