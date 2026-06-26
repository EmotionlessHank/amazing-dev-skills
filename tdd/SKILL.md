---
name: tdd
description: Test-driven development discipline. Use when the user says "/tdd", "tdd", "test-driven", "red-green-refactor", or "写测试先行". Enforces vertical-slice RED→GREEN cycles (one test, one implementation, repeat) over horizontal slicing (all tests first). Can be invoked standalone or called from autopilot Phase 1.2 for a single batch. Quality gate: {TYPECHECK} / {LINT} / {TEST} three-way AND.
version: 1.0.0
---

# /tdd — Test-Driven Development

> **Multi-project universal version.** `{placeholders}` are project-specific customization points — replace them per `SETUP.md` before migrating.
> Quality gate: `{TYPECHECK} && {LINT} && {TEST}`. Vertical slice = one Batch (≤`{MAX_FILES_PER_BATCH}` files). This skill can be called standalone (`/tdd`) or from autopilot Phase 1.2 for a single batch execution.

---

## Philosophy

**Core principle**: Tests should verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't.

**Good tests** are integration-style: they exercise real code paths through public APIs. They describe _what_ the system does, not _how_ it does it. A good test reads like a specification — "retrieval returns top-3 results with citations" tells you exactly what capability exists. These tests survive refactors because they don't care about internal structure.

**Bad tests** are coupled to implementation. They mock internal collaborators, test private methods, or verify through external means (like querying a storage layer directly instead of using the service interface). The warning sign: your test breaks when you refactor, but behavior hasn't changed.

---

## Anti-Pattern: Horizontal Slices

**DO NOT write all tests first, then all implementation.** This is "horizontal slicing" — treating RED as "write all tests" and GREEN as "write all code."

This produces **crap tests**:

- Tests written in bulk test _imagined_ behavior, not _actual_ behavior.
- You end up testing the _shape_ of things (data structures, function signatures) rather than user-facing behavior.
- Tests become insensitive to real changes — they pass when behavior breaks, fail when behavior is fine.
- You outrun your headlights, committing to test structure before understanding the implementation.

**Correct approach**: Vertical slices. One test → one implementation → repeat. Each test responds to what you learned from the previous cycle.

```
WRONG (horizontal):
  RED:   test1, test2, test3, test4, test5
  GREEN: impl1, impl2, impl3, impl4, impl5

RIGHT (vertical):
  RED→GREEN: test1→impl1
  RED→GREEN: test2→impl2
  RED→GREEN: test3→impl3
  ...
```

Each vertical slice = one Batch (≤`{MAX_FILES_PER_BATCH}` files). Never write tests for Batch N+1 before Batch N is green.

---

## Workflow

### 1. Planning (before any code)

Before writing any code:

- Read `{LESSONS}` tag map and match to the task's key terms. Read any hit lessons (`L-NNN-<slug>.md` files alongside `{LESSONS}`) before writing a single test.
- Confirm with the user what **interface changes** are needed (public API shape, service method signatures, external call contracts).
- Confirm with the user which **behaviors to test** (prioritize critical paths and complex logic; you cannot test everything).
- List the behaviors to test in dependency order — upstream behaviors first.
- Get user approval on the list before proceeding.

Ask: "What should the public interface look like? Which behaviors are most important to test?"

| Behavior priority | Examples |
|-------------------|---------|
| P0 (must test) | Core business logic returning correct output; critical error propagation |
| P1 (important) | Schema validation; API endpoint contracts; service ordering |
| P2 (nice-to-have) | Edge cases; config defaults |

### 2. Tracer Bullet (first vertical slice)

Write ONE test that confirms ONE thing about the system — the most fundamental behavior, end-to-end:

```
RED:   Write test for first behavior → test runner reports it fails
GREEN: Write minimal code to pass → test runner reports it passes
```

Run after RED:

```bash
{TYPECHECK}          # type check before any green (if applicable)
{TEST} path/to/test_first_behavior
```

This is your tracer bullet — proves the path works end-to-end.

### 3. Incremental RED→GREEN Loop

For each remaining behavior, in the order agreed in Planning:

```
RED:   Write next test → test fails
GREEN: Minimal code to pass → test passes
```

Rules:

- **One test at a time.** Never write test N+1 before test N is green.
- **Only enough code to pass the current test.** No speculative features.
- **Don't anticipate future tests.** If the current test passes with a stub, ship the stub.
- **Keep tests focused on observable behavior.** Public interface only.
- Run `{TYPECHECK}` after each GREEN to catch type drift early (if the project uses static typing).

### 4. Refactor (only after all tests are green)

After all planned behaviors are green, look for refactor candidates:

- [ ] Extract duplication
- [ ] Deepen modules (move complexity behind simpler interfaces)
- [ ] Tighten type annotations where the implementation revealed better types (language-appropriate)
- [ ] Consider what new code reveals about existing code
- [ ] Run `{TYPECHECK} && {LINT} && {TEST}` after each refactor step

**Never refactor while RED.** Get to GREEN first. RED is for making it work; refactor is for making it clean.

---

## Full Quality Gate (required before declaring batch done)

```bash
{TYPECHECK} && {LINT} && {TEST}
```

All three must pass. This is the same gate used by autopilot Phase 1.3. If any fails:

| Failure | Action |
|---------|--------|
| `{TYPECHECK}` type error | Fix type annotations in production code, not suppression comments |
| `{LINT}` lint error | Fix the lint violation; do not add ignore comments unless truly unavoidable and documented |
| `{TEST}` failure | Fix the production code; if a test is wrong (tests implementation, not behavior), rewrite the test — never comment it out |

---

## Checklist Per RED→GREEN Cycle

```
[ ] Test describes behavior, not implementation
[ ] Test uses public interface only
[ ] Test would survive internal refactor
[ ] Code is minimal for this test
[ ] No speculative features added
[ ] {TYPECHECK} passes after GREEN (if applicable)
```

---

## Integration with autopilot

This skill maps directly onto autopilot Phase 1.2 (Single Batch Execution):

| autopilot step | /tdd equivalent |
|----------------|-----------------|
| Step 1 — Code | Phase 3 GREEN (minimal code to pass) |
| Step 2 — Appropriate test verification | Phase 3 RED → GREEN loop + full gate |
| Step 3 — Commit | After all planned behaviors for the batch are green and gate passes |

When called from autopilot: the "batch" boundary (≤`{MAX_FILES_PER_BATCH}` files) acts as the natural scope limit. Tests for behaviors outside the current batch are deferred to subsequent batches — do not write them early.

When called standalone (`/tdd`): determine the scope boundary with the user in Planning (step 1) before starting.

---

## Safety Red Lines

1. **Never refactor while RED** — make it pass first; clean it after.
2. **Never write test N+1 before test N is green** — horizontal slicing is prohibited.
3. **Tests must use public interfaces only** — testing internals couples tests to implementation and defeats the purpose.
4. **Full gate must pass before declaring the batch done** — `{TYPECHECK} && {LINT} && {TEST}` all three.
5. **Do not skip the Planning step** — interface agreement with the user before writing any test prevents rewrites.

---

> Adapted from [mattpocock/skills](https://github.com/mattpocock/skills) (MIT).
