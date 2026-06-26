# codebase-design — Migrating to a New Project (SETUP)

This skill is largely project-agnostic — the design vocabulary (depth, seam, adapter, leverage, locality) applies to any language and domain. Copy `SKILL.md` into the target project's skills directory as-is; only one placeholder needs adjusting.

## Placeholder Replacement Checklist

| Placeholder | Meaning | Example (moat) |
|-------------|---------|----------------|
| `{PLAN_DOC}` | Plan document type / filename stem used in your feat workflow | `DD` |

## Verification

0. Placeholder residue check: `grep -oE '\{[A-Za-z_|]+\}' SKILL.md | sort -u` — only `{PLAN_DOC}` should appear; replace it with your project's plan doc stem (e.g. `DD`).
1. No other changes required. Load the skill at the start of any design discussion and verify both human and AI are using the vocabulary terms (depth, seam, adapter, leverage, locality) consistently before writing the plan design section.
