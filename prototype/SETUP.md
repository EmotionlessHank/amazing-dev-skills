# prototype — Migrating to a New Project (SETUP)

After copying `SKILL.md` into the target project's skills directory, replace all `{placeholders}` per the table below, then run the verification steps.
Used together with `feat` (feat identifies the design question → prototype answers it → answer folds back into the plan doc).

## Placeholder Replacement Checklist

| Placeholder | Meaning | Example (moat) |
|-------------|---------|----------------|
| `{PROJECT_ROOT}` | Absolute path to the project repo | `~/AI/rag-demo` |
| `{DOCS_ROOT}` | Root directory for requirements/plan documents | `.progress` |
| `{type}` / `{ID}` | Requirement type / ID format | `designs` / `DD-001` |
| `{PLAN_DOC}` | Plan document filename stem (DD / ENH / BUG) | `DD` |

## Verification

0. Placeholder residue check: `grep -oE '\{[A-Za-z_|]+\}' SKILL.md | sort -u` — confirm only runtime dynamic quantities remain (`{slug}`, `{question slug}`, `{type}`, `{ID}`, `{PLAN_DOC}` value already substituted, `{CONFIRMED / REFUTED / INCONCLUSIVE}`, etc.); no unresolved config placeholders.
1. Run a dry walkthrough: create a throwaway spike in the scratchpad directory, confirm it writes no files inside the project tree (`{PROJECT_ROOT}`).
2. Confirm the answer writes back to `{DOCS_ROOT}/{type}/{ID}/{PLAN_DOC}.md §2` under a `#### Spike:` heading.
3. Confirm the scratchpad directory is deleted after the verdict is recorded.
