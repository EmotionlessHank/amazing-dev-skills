# tdd — Migrating to a New Project (SETUP)

After copying `SKILL.md` into the target project's skills directory, replace all `{placeholders}` per the table below, then run the verification steps.
Used together with `autopilot` (tdd executes one batch → autopilot orchestrates the full pipeline); keep placeholders consistent between the two.

## Placeholder Replacement Checklist

| Placeholder | Meaning | Example (moat) |
|-------------|---------|----------------|
| `{DOCS_ROOT}` | Root directory for requirement documents | `.progress` |
| `{type}` | Requirement type subdirectory | `designs` |
| `{ID}` | Requirement ID format | `DD-NNN` |
| `{LESSONS}` | Lessons learned index document | `docs/LESSONS.md` |
| `{TYPECHECK}` | Static type checking command | `mypy .` |
| `{LINT}` | Lint command | `ruff check .` |
| `{TEST}` | Test runner command | `pytest` |
| `{MAX_FILES_PER_BATCH}` | Max files changed per batch / vertical slice | `3` |

> `{LESSONS}` is optional — if the project has no lessons-rag document, delete the "Read `{LESSONS}` tag map" item from Planning step 1.
> `{TYPECHECK}` is optional — if the project has no static type checker, remove it from the quality gate command and the Checklist; update Safety Red Line 4 accordingly.

## Optional Modules (trim per project)

- No lessons-rag → delete the `{LESSONS}` lookup from Planning step 1.
- No static type checker → remove `{TYPECHECK}` from the quality gate command, tracer bullet block, incremental loop note, refactor checklist, and the per-cycle checklist item.
- No linter → same treatment as above for `{LINT}`.
- Dynamically typed language (no typecheck at all) → the full gate collapses to `{TEST}`; remove all `{TYPECHECK}` references.

## Verification

1. Placeholder residue check:
   ```bash
   grep -oE '\{[A-Za-z_]+\}' SKILL.md | sort -u
   ```
   Confirm only runtime-dynamic tokens remain (`{type}`, `{ID}`, `{MAX_FILES_PER_BATCH}` as a literal label in prose is acceptable if intentional); all config placeholders should be replaced.
2. Run through a single RED→GREEN cycle mentally: confirm the quality gate command (`{TYPECHECK} && {LINT} && {TEST}` after replacement) is a real, runnable one-liner for this project.
