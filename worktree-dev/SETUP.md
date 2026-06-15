# worktree-dev — Migrating to a New Project (SETUP)

After copying `SKILL.md` into the target project's skills directory, replace all `{placeholders}` per the table below, then run the verification steps.
Used together with `feat`/`autopilot` (worktree-dev sets up the isolated environment → feat plans → autopilot develops); keep placeholders consistent across all three.

## Placeholder Replacement Checklist

| Placeholder | Meaning | Example (oddfi-frontend) |
|-------------|---------|--------------------------|
| `{REPO_ROOT}` | Main workspace absolute path | `/Users/hang/work/oddfi-frontend` |
| `{MAIN_BRANCH}` | Main branch | `main` |
| `{WORKTREE_BASE}` | Unified worktree storage directory (relative to main workspace) | `.claude/worktrees` |
| `{WT_HELPER}` | Helper script that creates worktree + symlinks in one step (optional; delete the hint if absent) | `bin/wt-add.sh` (`pnpm wt <name> <branch>`) |
| `{ENV_FILES}` | List of env/personal config files that need symlinking (see below) | See below |
| `{ENV_FILE}` | A single file from `{ENV_FILES}` (§1.2 symlink command template variable; instantiate for each file in the list) | `.env.local` |
| `{INSTALL}` | Dependency install command | `pnpm install` |
| `{TYPECHECK}` / `{LINT}` / `{TEST}` / `{BUILD}` | Verification commands | `pnpm type-check` / `pnpm lint` / `pnpm test` / `pnpm build` |
| `{DOCS_ROOT}` | Requirements/plan doc root (read-only exception; same name as in feat/autopilot) | `.progress` |
| `{type}` / `{ID}` | Requirement type / ID | `designs` / `DD-NNN` |
| `{RULES}` | Project rules read-only path | `CLAUDE.md` + `.claude/rules/` |
| `{MAX_FILES_PER_BATCH}` | Max files per batch | `3` |
| `{COMMIT_CONVENTION}` | Commit message convention | Simplified Chinese + no Co-Authored-By |
| `{EDIT_READ_PREREQ_HOOK}` | "Read before Edit" cooperative hook (optional) | `.claude/hooks/edit-read-prereq.sh` |

## {ENV_FILES} — Files That Need Symlinking (Critical Customization Point)

List all files in this project that "exist in the main workspace, are gitignored, and must be present in the worktree", along with the consequence of each one missing. oddfi example:

| File | Purpose | Consequence if missing |
|------|---------|------------------------|
| `.env.local` | Default environment variables | Route Handler proxy returns 500 |
| `.env.dev.local` | Dev environment (isolated port) | Silently falls back to default env |
| `.env.testnet.local` | Testnet environment | **Silently connects to mainnet** — wrong chain |
| `.claude/settings.local.json` | Personal Bash/MCP permission allowlist | Every operation re-prompts for permission |
| `.claude/skills/` | Workflow skill resources (symlinked for sharing, not copied) | Personal skills unavailable |

> When switching projects: list every gitignored but worktree-required file in your project. Symlinks are not `cp` (a copy is a static snapshot; changes to the main workspace won't be seen by the worktree).
> ⚠️ Symlink relative path depth = `{WORKTREE_BASE}` nesting levels + file levels — verify the number of `../` in each `ln -sf` command individually.

## Verification

0. Placeholder residue check: `grep -oE '\{[A-Za-z_]+\}' SKILL.md | sort -u` — confirm only runtime dynamic quantities remain (`{ID}` `{type}` `<name>` and similar indicative quantities); no unresolved config placeholders
1. Run through end-to-end: create a worktree → confirm all `{ENV_FILES}` symlinked successfully and point to valid files, `{INSTALL}` succeeds, cwd lock is effective (attempting to read a main workspace file outside `{DOCS_ROOT}` should be consciously refused)
2. Confirm the cleanup step **did not auto-push to remote** (merging/pushing is the user's responsibility, unless the project explicitly authorizes AI to finalize the local main branch merge)
