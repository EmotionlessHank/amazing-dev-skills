---
name: prototype
description: Write throwaway prototype code that answers a single design question during the feat planning phase. Triggers when the user says "/prototype", "prototype", "spike", "验证设计假设", or "throwaway prototype". Workflow: identify the question → pick the right branch (state/logic vs API shape) → build the smallest possible runnable artifact in scratchpad → extract the answer → write it back into {PLAN_DOC} §2/§3 → delete the prototype.
version: 1.0.0
---

# /prototype — Throwaway Spike to Answer a Design Question

> **Multi-project universal version.** `{placeholders}` are project-specific customization points — replace per `SETUP.md` before migrating.
> **A prototype lives entirely in a throwaway scratchpad directory outside the project tree and is deleted once the question is answered. Its only output is a written conclusion folded back into the {PLAN_DOC}.**

A prototype is **throwaway code that answers a question**. The question decides the shape. Do not build more than the minimum needed to get the answer.

---

## Step 1: Name the Question

State the single design question being answered before writing a line of code:

```
Prototype question: {one sentence — e.g. "Does streaming responses through a Server-Sent Events endpoint lose chunks under load?"}
Expected outcome: {what a definitive yes/no/number/shape would look like}
Branch: {logic-spike | api-shape}
```

If the question is genuinely ambiguous and the user is not reachable, default to the branch that best matches the surrounding context (pure data flow / state → `logic-spike`; route contract / response shape → `api-shape`) and state the assumption.

---

## Step 2: Pick a Branch

| Branch | Use when | Artifact |
|--------|----------|----------|
| **logic-spike** | Validating a state machine, data transformation pipeline, retrieval algorithm, or async flow that is hard to reason about on paper | Minimal terminal script that exercises the hard cases interactively; prints full state after every step |
| **api-shape** | Validating an HTTP route contract, request/response schema, or external service payload structure before wiring into the real service layer | Single self-contained server app or HTTP client script with hardcoded stubs; exposes 2–3 variants switchable by a query param or CLI flag |

---

## Step 3: Build the Prototype (Rules, No Exceptions)

1. **Scratchpad only.** All prototype files go under a throwaway scratchpad directory outside the project tree. Never write prototype files into the project tree (`{PROJECT_ROOT}`).

   ```
   Scratchpad path: a session-specific temp directory outside the project tree, e.g. /tmp/proto-{slug}/
   ```

2. **One command to run.** The user must be able to start it without thinking:

   ```bash
   python /path/to/scratchpad/proto-{slug}/main.py
   # or a single server start command for api-shape spikes
   ```

3. **No persistence by default.** State lives in memory. If the question explicitly involves a database, use a local SQLite file named `PROTOTYPE-wipe-me.db` inside the scratchpad — never connect to the real production database.

4. **Skip all polish.** No type hints beyond what makes the script runnable, no error handling beyond preventing a crash, no abstractions, no tests.

5. **Surface the state.** After every action (`logic-spike`) or on every variant switch (`api-shape`), print the full relevant state so the answer is observable on the terminal.

6. **Hard cap: 150 lines.** If the spike needs more than 150 lines, the question is too big — split it into two smaller questions and run two separate spikes.

---

## Step 4: Run and Observe

Run the prototype, observe the output, and form a clear verdict:

```
Verdict: {CONFIRMED / REFUTED / INCONCLUSIVE}
Evidence: {what the output showed — paste the relevant terminal lines}
Answer to the original question: {one paragraph}
```

If `INCONCLUSIVE`, state what would be needed to get a definitive answer and whether the cost is worth it.

---

## Step 5: Write the Answer Back into the {PLAN_DOC}, Then Delete

The answer — not the code — is the only artifact worth keeping.

1. Open the active plan document (`{DOCS_ROOT}/{type}/{ID}/{PLAN_DOC}.md`).
2. Append the verdict and evidence to **§2 Research** (under a `#### Spike: {question slug}` heading).
3. If the answer changes the design, update **§3 Plan Design** accordingly.
4. Delete the scratchpad prototype directory:

   ```bash
   rm -rf /path/to/scratchpad/proto-{slug}/
   ```

5. Announce: "Prototype deleted. Answer folded into {PLAN_DOC} §2."

---

## Rules That Apply in All Cases

| Rule | Reason |
|------|--------|
| Prototype never enters the project tree | Avoids accidentally shipping throwaway code; keeps `git status` clean |
| Never connect to production databases or external services with real billing | Prototypes are non-deterministic probes; cost and data side-effects must be zero |
| Delete immediately after extracting the answer | Rotting prototypes become load-bearing; prevent that at the source |
| No real credentials in prototype files | Scratchpad may not be gitignored within the session; no secrets |

---

## Exception: Question Answerable Without Code

If the design question can be answered by reading existing code (`grep`, `Read`) or the official SDK docs, do that instead — **do not build a prototype**. A prototype is warranted only when the answer genuinely requires observing runtime behavior.

---

> Prototype is a **feat sub-tool**: it is invoked during the feat Phase 2 research or Phase 3.1 grill when a design assumption cannot be settled by code-reading alone. Return to feat after the answer is captured.

> Adapted from [mattpocock/skills](https://github.com/mattpocock/skills) (MIT).
