# diagnosing-bugs — Migrating to a New Project (SETUP)

After copying `SKILL.md` into the target project's skills directory, replace all `{placeholders}` per the table below, then run the verification steps.

## Placeholder Replacement Checklist

| Placeholder | Meaning | Example (moat) |
|-------------|---------|----------------|
| `{DOCS_ROOT}` | Root directory for requirement/bug documents | `.progress` |
| `{type}` | Requirement type subdirectory | `bug` |
| `{ID}` | Bug/requirement ID format | `BUG-NNN` |
| `{LESSONS}` | Lessons learned index document | `docs/LESSONS.md` |
| `{TYPECHECK}` | Static type checking command | `mypy .` |
| `{LINT}` | Lint command | `ruff check .` |
| `{TEST}` | Test runner command | `pytest` |
| `{SMOKE_CMD}` | Smoke / real-environment test command | `BASE_URL=http://localhost:8000 bash scripts/smoke.sh` |

> `{LESSONS}` is optional — if the project has no lessons-rag document, delete the "Before starting" paragraph and the Phase 6 lessons backfill bullet.
> `{SMOKE_CMD}` is optional — if the project has no smoke script, delete the item from Phase 1's ordered list and note an alternative equivalent.

## Optional Modules (trim per project)

- No lessons-rag → delete the "Before starting: read `{LESSONS}`" paragraph and the Phase 6 backfill bullet.
- No smoke script → remove `{SMOKE_CMD}` from Phase 1's way-list; replace with the closest real-environment equivalent.
- No static type checker → remove `{TYPECHECK}` from the quality gate command and the Phase 5 code block; update Safety Red Line 5 accordingly.
- No linter → same treatment as above for `{LINT}`.

## Verification

1. Placeholder residue check:
   ```bash
   grep -oE '\{[A-Za-z_]+\}' SKILL.md | sort -u
   ```
   Confirm only runtime-dynamic tokens remain (`{type}`, `{ID}`); all config placeholders should be gone.
2. Walk Phase 5 mentally: confirm the quality gate command is a real, runnable one-liner for this project.
