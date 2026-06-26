---
name: codebase-design
description: Shared design vocabulary reference for deep module thinking — interface depth, seams, adapters, leverage, locality, testability. Triggers when the user says "/codebase-design", "deep module", "seam", "设计深模块", or "module design". Use during the feat code-research and design phase to establish a shared language before writing the {PLAN_DOC} §3 plan design section.
version: 1.0.0
---

# /codebase-design — Deep Module Design Vocabulary

> **Multi-project universal version. Minimal customization needed** — the design vocabulary is language- and domain-agnostic. Only `{PLAN_DOC}` (your plan document type) may need adjusting per `SETUP.md`.
> **This skill is a vocabulary reference, not a workflow.** Load it at the start of a feat design discussion so both human and AI use the same terms when authoring {PLAN_DOC} §3.

---

## Core Concept: Deep vs. Shallow Modules

A **deep module** concentrates complex behavior behind a small interface. A **shallow module** exposes nearly as much surface area as it contains logic — it taxes every caller without paying back much.

The goal of module design is to **maximize depth**: callers accomplish a lot while needing to know little.

```
Depth = behavioral leverage ÷ interface complexity
```

Shallow example (avoid):

```python
# Caller must know sort order, page size, include-deleted flag, and cache TTL
def find_users(sort: str, page_size: int, include_deleted: bool, cache_ttl: int) -> list[User]: ...
```

Deep example (prefer):

```python
# Caller states intent only — query strategy is a config concern
def find_users(query: UserQuery) -> list[User]: ...
```

---

## Key Vocabulary

| Term | Definition | Example |
|------|-----------|---------|
| **Module** | Any unit with an interface and implementation: function, class, service, router, pipeline | `repositories/user.py`, `services/payment.py`, `api/routers/orders.py` |
| **Interface** | Everything a caller must know: signatures, type contracts, invariants, errors raised, performance expectations | The public methods + type schemas a router imports from a service |
| **Depth** | Behavioral leverage per unit of interface complexity; more behavior per thing the caller must learn | A single `UserRepository.find(id)` that hides SQL, caching, and retry |
| **Seam** | The location where an interface sits; the point where behavior can be swapped without editing the caller | A `Repository` `Protocol` that both `PostgresRepository` and `InMemoryRepository` satisfy |
| **Adapter** | A concrete implementation that satisfies an interface at a seam | `PostgresUserRepository(UserRepository)`, `HttpPaymentGateway(PaymentGateway)` |
| **Leverage** | The caller benefit — more capability per interface unit learned | Hiding HTTP retry logic and auth headers inside `client.send()` |
| **Locality** | The maintainer benefit — related change and knowledge concentrated in one place, not scattered | All database query logic in `repositories/postgres.py`, not spread across routers |

---

## Design Moves

### Reduce the Interface

Before adding a parameter, ask: can this be a configuration concern rather than a call-site concern?

```python
# Before: caller decides query strategy
repository.find(id, include_deleted=True, cache=False, timeout=30)

# After: caller states intent only
repository.find(id)  # strategy lives in RepositoryConfig, injected at startup
```

### Apply the Deletion Test

If you removed this module, would its complexity scatter across N callers? If yes — and N ≥ 2 — the module is earning its position. If N = 0 or 1 and the logic is trivial, the module is overhead.

### One Seam vs. Two Seams

| Seam count | Meaning |
|------------|---------|
| **One adapter exists** | Fake seam — the interface just describes the one real implementation. Often premature. |
| **Two+ adapters exist** | Real seam — the interface genuinely hides a decision that can vary (e.g., `PostgresRepository` vs `InMemoryRepository`). Worth the indirection. |

When a second adapter is real or imminent, extract the seam. A new interface with only one known implementation is premature until the second adapter materialises.

### Three Moves for Testability

| Move | Pattern |
|------|---------|
| **Accept dependencies, don't create them** | Inject via constructor or dependency injection framework, not `import` inside functions |
| **Return results, don't mutate shared state** | Functions return values rather than appending to a global cache |
| **Keep the surface small** | Fewer public methods = fewer test cases needed for full coverage |

---

## What This Skill Rejects

- **Line-count as a proxy for depth** — a 10-line function can be deep; a 500-line class can be shallow
- **Language-level constructs as modules** — "class" and "module" are not synonyms for deep module; the design property is about interface vs. behavior ratio
- **Premature seam extraction** — do not create a `Protocol` / interface until a second adapter is real or imminent; abstraction has a carry cost

---

## How to Use During {PLAN_DOC} §3

When drafting the plan design section:

1. Name each new or changed module and state its **depth score** informally ("hides X from Y callers").
2. For every new `Protocol` / interface / ABC, state which two adapters justify it.
3. Apply the deletion test to any proposed utility module before adding it.
4. Mark testability: does the design accept dependencies or create them?

This vocabulary is shared with the human; when a design choice is disputed, refer back to the terms above rather than intuition.

---

> Reference: John Ousterhout, *A Philosophy of Software Design* (2018) — the source of the depth/interface/seam framing used here.

> Adapted from [mattpocock/skills](https://github.com/mattpocock/skills) (MIT).
