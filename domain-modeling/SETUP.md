# domain-modeling — Migrating to a New Project (SETUP)

After copying `SKILL.md` into the target project's skills directory, replace all `{placeholders}` per the table below, then run the verification steps.
Used during feat Phase 2 / Phase 3.1; keep `{PLAN_DOC}` and `{DOCS_ROOT}` consistent with the `feat` skill.

## Placeholder Replacement Checklist

| Placeholder | Meaning | Example (moat) |
|-------------|---------|----------------|
| `{GLOSSARY_DOC}` | Path to the single domain glossary file | `docs/CONTEXT.md` |
| `{PLAN_DOC}` | Plan document type / filename stem used in your feat workflow | `DD` |
| `{PROJECT_ROOT}` | Absolute path to the project repo (used in grep commands) | `~/AI/rag-demo` |

## Verification

0. Placeholder residue check: `grep -oE '\{[A-Za-z_|]+\}' SKILL.md | sort -u` — confirm only runtime dynamic quantities remain (`{CanonicalTerm}`, `{YYYY-MM-DD}`, `{short title}`, `{term_a}`, etc.); no unresolved config placeholders.
1. Verify `{GLOSSARY_DOC}` path exists or is ready to be created on first write.
2. Confirm `{PLAN_DOC}` matches the value used in the `feat` skill so ADR cross-references are consistent.
3. Run a dry walkthrough: pick one vague term from an in-flight requirement, stress-test it with a scenario, grep `{PROJECT_ROOT}/src`, and confirm the entry format renders correctly in `{GLOSSARY_DOC}`.
