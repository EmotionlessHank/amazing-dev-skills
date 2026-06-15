# autopilot — Migrating to a New Project (SETUP)

After copying `SKILL.md` into the target project's skills directory, replace all `{placeholders}` with actual project values per the table below, then run the verification steps.

## Placeholder Replacement Checklist

| Placeholder | Meaning | Example (oddfi-frontend) |
|-------------|---------|--------------------------|
| `{DOCS_ROOT}` | Root directory for requirements/plan documents | `.progress` |
| `{type}` | Requirement type subdirectory set | `designs` / `enh` / `bug` / `ud` / `ad` |
| `{ID}` | Requirement ID format | `DD-NNN` / `ENH-NNN` / `BUG-NNN` |
| `{RULES_DIR}` | Project rules directory | `.claude/rules/` |
| `{LESSONS}` | Lessons learned document (optional; delete §0.3 if absent) | `docs/LESSONS.md` |
| `{MAX_FILES_PER_BATCH}` | Max files per batch | `3` |
| `{TYPECHECK}` | Type check command | `pnpm type-check` |
| `{LINT}` | Lint command | `pnpm lint` |
| `{TEST}` | Test command (supports passing file/dir for subset runs) | `pnpm test` |
| `{BUILD}` | Build command | `pnpm build` |
| `{GEN_ASSETS}` | Asset index refresh command (optional; delete related lines if absent) | `pnpm gen-assets` |
| `{QUALITY_SCANNER}` | High-frequency pitfall quick-scan agent (if absent, use a different second agent or fall back to 1) | `quality-scanner` |
| `{DESIGN_IMPL_SKILL}` | UI pixel-perfect implementation workflow (delete Step 1.5 if no UI tasks) | `/figma-impl` |
| `{PROJECT_CONVENTIONS}` | Key conventions injected into review agents | Runtime output in English / decimal.ts / Design Token / testing.md |
| `{EXAMPLE_REQUIREMENT_FOLDER}` | A complete requirement subfolder example path | `.progress/designs/DD-132-invest-page-redesign/` |
| `{SUBAGENT_TRANSCRIPT}` | Persisted subagent transcript path for recovering swallowed reports (delete the fallback sentence if this mechanism is unavailable) | `<session>/subagents/agent-<id>.jsonl` |

> The `ud`/`ad` examples in `{type}` are oddfi-specific types. Remove them for new projects and keep only the generic `designs`/`enh`/`bug` as needed.

## Required Review Agents

Subagent types used in Phase 2 (project must provide these or equivalent substitutes):
- `code-reviewer` (required) — deep code review
- `{QUALITY_SCANNER}` (used as the second agent in default 2-agent mode) — high-frequency pitfall quick scan
- `security-reviewer` / `test-engineer` / `performance-engineer` (for the third agent in 3-agent mode, chosen by domain)

**Minimum requirement**: the project must have at least 1 review subagent that can be spawned in parallel and write its report to a specified absolute path. If none exist → Phase 2 falls back to main-flow self-review + user sign-off (sacrifices the "no self-approval" principle; this must be declared in the report).

> Note: feat uses plan-review perspective agents (critic/architect/design-distiller); autopilot uses code-review perspective agents (code-reviewer/quality-scanner). **They are not interchangeable.**

## Optional Modules (trim per project)

- No UI/design workflow → delete §0.4 UI detection + §1.2 Step 1.5
- No lessons learned document → delete §0.3
- No asset index script → delete the `{GEN_ASSETS}` line in §1.3
- Not using worktree → simplify §4.2 cleanup to in-branch commits, delete "sync docs back to main workspace"
- **No test infrastructure** (early prototype / pure static site) → §1.2 Step 2 falls back to `{TYPECHECK}` only; delete `{TEST}` from §1.3; declare "this project has no automated tests — all acceptance is manual" in ACCEPTANCE.md
- No output hook report-swallowing issue → delete the `{SUBAGENT_TRANSCRIPT}` recovery fallback sentence in §2.2 item 6

## Verification

1. All placeholders replaced (`grep -n "{.*}" SKILL.md` should only show indicative runtime quantities like `{ID}`/`{platform}`, no unresolved config placeholders)
2. Run through an existing requirement end-to-end: confirm Phase 1 ran relevant tests per batch, Phase 2 truly spawned 1–3 subagents that each wrote their own REV file, Phase 4 produced all three artifacts and surfaced the acceptance checklist in the conversation
3. Confirm the cleanup step **did not auto-push/merge to remote**
