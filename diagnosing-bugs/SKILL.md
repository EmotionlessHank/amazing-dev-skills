---
name: diagnosing-bugs
description: Diagnosis loop for hard bugs and performance regressions. Use when the user says "/diagnosing-bugs", "diagnose bug", "debug this", "hard bug", "性能回归", or "root cause". Follows a six-phase discipline — tight feedback loop → reproduce + minimise → falsifiable hypotheses → single-variable instrumentation → regression test before fix → cleanup + lessons-rag backfill.
version: 1.0.0
---

# /diagnosing-bugs — Bug Diagnosis Discipline

> **Multi-project universal version.** `{placeholders}` are project-specific customization points — replace them per `SETUP.md` before migrating.
> Bug artifacts go to `{DOCS_ROOT}/{type}/{ID}/`. Quality gate: `{TYPECHECK} && {LINT} && {TEST}`. Diagnosed bugs must be backfilled to lessons-rag (`{LESSONS}` + sibling `L-NNN-<slug>.md` files).

A discipline for hard bugs. Skip phases only when explicitly justified.

Before starting: read `{LESSONS}` and match tags to the symptom area — you may already have a root-cause shortcut from a prior bug.

---

## Phase 1 — Build a Feedback Loop

**This is the skill.** Everything else is mechanical. If you have a **tight** pass/fail signal for the bug — one that goes red on _this_ bug — you will find the cause; bisection, hypothesis-testing, and instrumentation all just consume it. If you don't have one, no amount of staring at code will save you.

Spend disproportionate effort here. **Be aggressive. Be creative. Refuse to give up.**

### Ways to construct one — try in roughly this order

1. **Failing test** at whatever seam reaches the bug — unit, integration, e2e (run via `{TEST}`).
2. **Real-environment smoke** via the project harness: `{SMOKE_CMD}` (live-acceptance-smoke). §1 deterministic gates are your first red signal.
3. **Direct HTTP script** — `curl` against a running dev server with a fixture payload.
4. **CLI invocation** with a fixture input, diffing stdout against a known-good snapshot.
5. **Replay a captured trace.** Save a real request/payload/log to disk; replay it through the code path in isolation.
6. **Throwaway harness.** Spin up a minimal subset (one service, mocked deps) that exercises the bug code path with a single function call.
7. **Property / fuzz loop.** If the bug is "sometimes wrong output", run many random inputs and look for the failure mode.
8. **Bisection harness.** If the bug appeared between two known states (commit, dataset, version), automate "boot at state X, check, repeat" to `git bisect run` it.
9. **Differential loop.** Run the same input through two configs/versions and diff outputs.

Build the right feedback loop, and the bug is 90% fixed.

### Tighten the loop

Treat the loop as a product. Once you have _a_ loop, **tighten** it:

- Can I make it faster? (Cache setup, skip unrelated init, narrow the test scope.)
- Can I make the signal sharper? (Assert on the specific symptom, not "didn't crash".)
- Can I make it more deterministic? (Pin time, seed RNG, isolate filesystem, freeze network.)

A 30-second flaky loop is barely better than no loop; a 2-second deterministic one is a debugging superpower.

### Non-deterministic bugs

The goal is not a clean repro but a **higher reproduction rate**. Loop the trigger 100×, parallelise, add stress, narrow timing windows, inject sleeps. A 50%-flake bug is debuggable; 1% is not — keep raising the rate until it's debuggable.

### When you genuinely cannot build a loop

Stop and say so explicitly. List what you tried. Ask the user for: (a) access to whatever environment reproduces it, (b) a captured artifact (log dump, export, network capture), or (c) permission to add temporary instrumentation. Do **not** proceed to hypothesise without a loop.

### Completion criterion — a tight loop that goes red

Phase 1 is done when the loop is **tight** and **red-capable**: you can name **one command** — a script path, a test invocation, a curl — that you have **already run at least once** (paste the invocation and its output), and that is:

- [ ] **Red-capable** — it drives the actual bug code path and asserts the **user's exact symptom**, so it can go red on this bug and green once fixed.
- [ ] **Deterministic** — same verdict every run (flaky bugs: a pinned, high reproduction rate, per above).
- [ ] **Fast** — seconds, not minutes.
- [ ] **Agent-runnable** — you can run it unattended.

If you catch yourself reading code to build a theory before this command exists, **stop — jumping straight to a hypothesis is the exact failure this skill prevents.** No red-capable command, no Phase 2.

---

## Phase 2 — Reproduce + Minimise

Run the loop. Watch it go red.

Confirm:

- [ ] The loop produces the failure mode the **user** described — not a different failure nearby. Wrong bug = wrong fix.
- [ ] The failure is reproducible across multiple runs (or, for non-deterministic bugs, at a high enough rate to debug against).
- [ ] You have captured the exact symptom (error message, wrong output, slow timing).

### Minimise

Once it's red, shrink the repro to the **smallest scenario that still goes red**. Cut inputs, callers, config, data, and steps **one at a time**, re-running the loop after each cut.

Why bother: a minimal repro shrinks the hypothesis space in Phase 3 and becomes the clean regression test in Phase 5.

Done when **every remaining element is load-bearing** — removing any one of them makes the loop go green.

Do not proceed until you have reproduced **and** minimised.

---

## Phase 3 — Hypothesise

Generate **3–5 ranked hypotheses** before testing any of them.

Each hypothesis must be **falsifiable**: state the prediction it makes.

> Format: "If \<X\> is the cause, then \<changing Y\> will make the bug disappear / \<changing Z\> will make it worse."

If you cannot state the prediction, the hypothesis is a vibe — discard or sharpen it.

**Show the ranked list to the user before testing.** They often have domain knowledge that re-ranks instantly. Don't block on it — proceed with your ranking if the user is AFK.

---

## Phase 4 — Instrument

Each probe must map to a specific prediction from Phase 3. **Change one variable at a time.**

Tool preference:

1. **Debugger / REPL inspection** (language-appropriate) if the environment supports it. One breakpoint beats ten logs.
2. **Targeted logs** at the boundaries that distinguish hypotheses.
3. Never "log everything and grep".

**Tag every debug log** with a unique prefix, e.g. `[DEBUG-a4f2]`. Cleanup at the end becomes a single grep. Untagged logs survive; tagged logs die.

**Perf branch.** For performance regressions (e.g., slow database queries, slow external service calls), logs are usually wrong. Instead: establish a baseline measurement (timing harness, profiler, query plan analysis), then bisect. Measure first, fix second.

---

## Phase 5 — Fix + Regression Test

Write the regression test **before the fix** — but only if there is a **correct seam** for it.

A correct seam is one where the test exercises the **real bug pattern** as it occurs at the call site. If no correct seam exists, that itself is the finding — note it.

If a correct seam exists:

1. Turn the minimised repro into a **failing test** — watch it go red (run via `{TEST}`).
2. Apply the fix.
3. Watch the test go green.
4. Re-run the Phase 1 feedback loop against the original (un-minimised) scenario.

Run the full quality gate to confirm no regressions introduced:

```bash
{TYPECHECK} && {LINT} && {TEST}
```

Archive the test and fix context to the bug subfolder:

```
{DOCS_ROOT}/{type}/{ID}/
├── BUG.md          Root cause, fix summary, affected files
└── regression/     Minimised repro + regression test reference
```

---

## Phase 6 — Cleanup + Post-mortem

Required before declaring done:

- [ ] Original repro no longer reproduces (re-run the Phase 1 loop).
- [ ] Regression test passes (or absence of seam is documented in `BUG.md`).
- [ ] All `[DEBUG-...]` instrumentation removed (`grep` the prefix across the repo).
- [ ] Throwaway prototypes deleted.
- [ ] The hypothesis that turned out correct is stated in the commit message — so the next debugger learns.
- [ ] **lessons-rag backfill (mandatory):** create an `L-NNN-<slug>.md` file alongside `{LESSONS}` with root cause + fix + trigger + how to avoid; add one line to `{LESSONS}` tag map (increment NNN, no skipping, no reuse).

**Ask: what would have prevented this bug?** If the answer involves architectural change (no good test seam, tangled callers, hidden coupling), hand off to the relevant skill or flag for the next planning cycle — but make the recommendation **after** the fix is in, when you have full information.

---

## BUG-NNN Workflow Integration

| Phase | Artifact / Action |
|-------|-------------------|
| Before Phase 1 | Create `{DOCS_ROOT}/{type}/{ID}/` subfolder + `BUG.md` with symptom description |
| Phase 1–2 | Record feedback loop command + repro output in `BUG.md` |
| Phase 3 | Record ranked hypotheses in `BUG.md` |
| Phase 5 | Record root cause, fix location, regression test path in `BUG.md` |
| Phase 6 | Backfill `L-NNN` lesson; close `BUG.md` with resolution summary |

---

## Safety Red Lines

1. **No hypothesis before a red-capable loop exists** — Phase 2–6 are blocked until the loop is built.
2. **Never skip the regression test phase** — if no correct seam, document the gap explicitly.
3. **Never skip lessons-rag backfill** — every diagnosed bug is a lesson; the backfill is non-negotiable.
4. **Debug instrumentation must be fully removed** before declaring done — grep the tag prefix.
5. **Quality gate must pass before declaring done** — `{TYPECHECK} && {LINT} && {TEST}` all green.

---

> Adapted from [mattpocock/skills](https://github.com/mattpocock/skills) (MIT).
