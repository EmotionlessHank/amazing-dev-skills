# feat — Migrating to a New Project (SETUP)

After copying `SKILL.md` into the target project's skills directory, replace all `{placeholders}` per the table below, then run the verification steps.
Used together with `autopilot` (feat produces the plan → autopilot develops it); keep placeholders consistent between the two.

## Placeholder Replacement Checklist

| Placeholder | Meaning | Example (oddfi-frontend) |
|-------------|---------|--------------------------|
| `{DOCS_ROOT}` | Root directory for requirements/plan documents | `.progress` |
| `{type}` / `{ID}` | Requirement type / ID format | `designs`·`bug` / `DD-NNN`·`BUG-NNN` |
| `{LESSONS}` | Lessons learned document (optional; delete §0.3 if absent) | `docs/LESSONS.md` |
| `{WORKTREE_SKILL}` | Worktree-isolated development workflow (if absent, change to "create a feature branch") | `/worktree-dev` |
| `{SMALL_FILE_THRESHOLD}` | File count threshold for a "small" feature (may skip DD) | `2` |
| `{MAX_FILES_PER_BATCH}` | Max files per batch | `3` |
| `{DESIGN_IMPL_SKILL}` | UI pixel-perfect implementation workflow (delete §2.5 + related lines if no UI tasks) | `/figma-impl` |
| `{REPO_MAP}` | Cross-repo map (paths + each repo's development branch) | See below |
| `{REPO_PATH}` | Local path for a repo in `{REPO_MAP}` (command template variable; instantiate per repo — do not replace globally in SKILL) | `~/work/oddfi-backend` |
| `{DEV_BRANCH}` | Active development branch for that repo in `{REPO_MAP}` (command template variable) | `dev` (backend) / `main` (contracts) |
| `{SSH_INVENTORY}` | SSH server inventory file (alias → purpose mapping) | `~/.ssh/SERVERS.md` |
| `{SERVER_ALIAS}` | Server alias (multiple servers listed in `{SSH_INVENTORY}`) | `oddfi-backend` / `oddfi-dev` |

> `{SMALL_FILE_THRESHOLD}` (threshold for skipping the DD) and `{MAX_FILES_PER_BATCH}` (batch split limit) have different semantics and may have different values — do not mistakenly set them to the same value.

## {REPO_MAP} — Cross-Repo Map (Critical Customization Point)

**Each repository may have a different development branch** — this must be specified here; §2.1 pulls based on this map. oddfi example:

| Repo | Path | Development branch | API overview entry point |
|------|----- |--------------------|--------------------------|
| Backend | `~/work/oddfi-backend` | **dev** (backend iterates on dev) | Sub-service handler/model |
| Contracts | `~/work/oddfi-ODD` | **main** | `docs/development/api.md` |
| Frontend (this repo) | `~/work/oddfi-frontend` | **main** | — |

Blank template (fill in when switching projects):

| Repo | Path | Development branch | API overview entry point |
|------|----- |--------------------|--------------------------|
| `{...}` | `{...}` | `{...}` | `{...}` |

> When switching projects: list all related repos + each one's "active development branch" (this is the most error-prone customization point — pulling the wrong branch means researching stale code).
> **Unsure about a repo's active development branch** → run `git -C <path> branch -r --sort=-committerdate | head -3` to see the most recently active branches, or ask that repo's owner.

## Optional Modules (trim per project)

- No other repos (pure single-repo project) → delete the cross-repo parts of §2.1/§2.2; keep "read this repo's real code"
- No server / no runtime verification needed → delete §2.3
- No UI / no design files → delete §0 UI detection + §2.5 + `{DESIGN_IMPL_SKILL}` references
- No lessons learned document → delete §0.3

## Required Plan-Review Agents

Subagents used in Phase 4 (project must provide or substitute equivalents):
- `critic` (medium/large requirements) — plan flaws/edge cases/feasibility
- `design-distiller` (optional for medium requirements) — sharpen soft plan boundaries
- `architect` (large requirements) — architecture/reversibility
- `security-reviewer` / `document-specialist` (large requirements, by domain)

If no corresponding agents exist → fall back to 1 generic review agent, or have the main conversation self-check then hand to the user for sign-off.

## Verification

0. Placeholder residue check: `grep -oE '\{[A-Za-z_|]+\}' SKILL.md | sort -u` — confirm only **runtime dynamic quantities** remain in the whitelist (`{ID}` `{type}` `{platform}` `{agent}` `{N}` `{K}` `{M}` `{REPO_PATH}` `{DEV_BRANCH}` `{DD|ENH|BUG}`); no unresolved **config placeholders**
1. All placeholders replaced; `{REPO_MAP}` filled with this project's real repos + development branches
2. Run through a cross-repo requirement end-to-end: confirm §2.1 checked out the correct branch and pulled the latest, the DD §Research section contains "real code path+line numbers / commit / curl HTTP code" evidence, and Phase 4 truly spawned the appropriate number of plan-review agents
3. Confirm server operations were **read-only throughout** and **no code was written before the confirmation gate**
