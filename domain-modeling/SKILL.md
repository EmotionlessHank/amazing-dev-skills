---
name: domain-modeling
description: Actively build and sharpen the project's domain model and ubiquitous language during design work. Triggers when the user says "/domain-modeling", "domain model", "ubiquitous language", "领域建模", or "术语对齐". Workflow: challenge vague or conflicting terms → stress-test with scenarios → cross-reference against real code → maintain {GLOSSARY_DOC} as the single glossary → record hard decisions as ADRs inside the relevant {PLAN_DOC} (§3/§5), not a separate ADR system.
version: 1.0.0
---

# /domain-modeling — Build and Sharpen the Domain Model

> **Multi-project universal version.** `{placeholders}` are project-specific customization points — replace per `SETUP.md` before migrating.
> **Domain modeling is a feat sub-activity**: invoke during feat Phase 2 research or Phase 3.1 grill to nail shared language before locking the {PLAN_DOC}. The glossary lives at `{GLOSSARY_DOC}`; ADRs live inside the relevant {PLAN_DOC} (§3 design / §5 decision matrix), not in a separate ADR directory.

---

## Why This Matters

Ambiguous language is the most common source of bugs that cannot be caught by a type checker. When "order" means a pending cart in one service and a completed transaction in another, two engineers (or two agents) write code that silently disagrees. This skill forces that conflict to the surface before any code is written.

---

## Responsibilities

### 1. Challenge and Sharpen Language

When vague or conflicting terms appear in the requirement, conversation, or existing code — pause and challenge them:

- Propose a canonical alternative for each vague term.
- Ask: does this term mean the same thing everywhere it appears in the codebase? (grep to verify)
- Surface contradictions: "In `services/ingest.py` this is called `record`, but the router calls it `entry`. Which is canonical?"

Do not accept "it's obvious from context" — write the definition explicitly.

### 2. Stress-Test with Scenarios

When a relationship or boundary is being discussed, force precision with a concrete scenario:

```
Scenario: A user submits an order with three line items. Is each line item an Order? Or is the whole submission one Order and each line item a LineItem? What if two orders share an identical product — is that one LineItem or two?
```

A term that cannot survive a concrete scenario is not yet defined. Keep probing until the boundary is unambiguous.

### 3. Cross-Reference Against Real Code

Before writing any term into `{GLOSSARY_DOC}`, grep the actual codebase to see what name is already in use:

```bash
grep -rn "{term_a}\|{term_b}\|{term_c}" {PROJECT_ROOT}/src --include="*.py" | head -40
```

If the code disagrees with the proposed term, explicitly decide: rename the code (preferred when the codebase is small) or accept the divergence and document it. Never silently let code and glossary drift.

### 4. Maintain `{GLOSSARY_DOC}`

This is the single glossary for the project's domain language. Update it inline as terms resolve during the modeling session.

**Rules for `{GLOSSARY_DOC}`:**

- **Domain language only** — no implementation details, no class names, no database column names, no code snippets
- **One entry per canonical term** — if a synonym exists, list it under the canonical term as "also called X in legacy code"
- **Plain-English definitions** — written so a new analyst, not just a developer, can understand them
- **Create if absent** — if `{GLOSSARY_DOC}` does not yet exist, create it with the section structure below on first write

Glossary entry format:

```markdown
## {CanonicalTerm}

**Definition**: {One sentence — what this concept is in the project domain.}

**Boundary**: {What it is NOT — the most common confusion to rule out.}

**Also called**: {synonym in legacy code or external sources, if any}

**Resolved**: {YYYY-MM-DD} | {{PLAN_DOC}-NNN it was settled in}
```

### 5. Record Hard Decisions as ADRs Inside the {PLAN_DOC}

Only record an ADR when **all three** conditions hold:

| Condition | Test |
|-----------|------|
| Hard to reverse | Changing this decision later would require renaming across multiple files, migrating data, or breaking an external contract |
| Future readers will question it | A new contributor reading the code will reasonably ask "why not X instead?" |
| Genuine trade-offs existed | At least two viable options were seriously considered |

When the three conditions hold, **do not create a separate ADR file or directory**. Instead, append the ADR to the relevant {PLAN_DOC} under **§3 Plan Design** or **§5 Decision Matrix**:

```markdown
#### ADR: {short title}

- **Decision**: {what was chosen}
- **Context**: {why this decision was needed}
- **Options considered**: {option A — rejected because X} · {option B — rejected because Y}
- **Consequences**: {what becomes easier / harder as a result}
- **Resolved**: {YYYY-MM-DD} | {aligned with: human/team}
```

If the three conditions do not all hold, skip the ADR — a comment in the code or a glossary entry is sufficient.

---

## Modeling Session Flow

```
1. Collect raw terms from the requirement / conversation / grep output
2. For each term: propose canonical name → stress-test with scenario → grep real code → resolve conflicts
3. Draft or update {GLOSSARY_DOC} entries (domain language only)
4. For each hard decision: check the three ADR conditions → if all hold, append to {PLAN_DOC} §3 or §5
5. Announce: "Domain model update complete. N terms added/revised in {GLOSSARY_DOC}. M ADRs recorded in {PLAN_DOC}."
```

---

## File Structure

| Artifact | Location | Content |
|----------|----------|---------|
| Unified glossary | `{GLOSSARY_DOC}` | Canonical domain terms only — no code, no specs |
| Architectural decisions | Inside the relevant {PLAN_DOC}, `§3 Plan Design` or `§5 Decision Matrix` | ADRs for hard-to-reverse choices made during that feature's design |

No separate ADR directory. No secondary glossary files — a single bounded context uses a single glossary; revisit if the project grows into distinct domains requiring separate bounded contexts.

---

## Anti-Patterns to Avoid

| Anti-pattern | Correct move |
|-------------|-------------|
| Writing implementation terms into `{GLOSSARY_DOC}` (e.g., "`Order` is a database row with a `status` column") | Keep glossary at concept level; schema details live in models / migrations |
| Creating an ADR for every decision | Reserve ADRs for genuinely hard-to-reverse, legitimately questioned choices |
| Letting glossary and code drift silently | Grep before writing; if code disagrees with the proposed term, decide explicitly |
| Modeling in isolation without stress-testing | Every term must survive at least one concrete edge-case scenario before it is written |
| Inventing a new ADR directory or body of docs | All ADRs belong inside the {PLAN_DOC} that made the decision |

---

> Domain modeling is complete when: every key noun in the requirement has a canonical entry in `{GLOSSARY_DOC}`, all term conflicts between code and requirement are explicitly resolved, and any hard decisions are recorded as ADRs in the {PLAN_DOC}. Then return to feat Phase 3.2 to write the {PLAN_DOC} §3 plan design using the settled language.

> Adapted from [mattpocock/skills](https://github.com/mattpocock/skills) (MIT).
