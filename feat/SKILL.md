---
name: feat
description: Full lifecycle for the "planning phase" of feature development. Triggers when the user says "/feat", "develop feature", "add feature", "implement XX feature", "write a plan", or "write DD". Workflow: requirement scope analysis → real codebase research (code is ground truth · pull latest · read-only server verification when needed) → collaborative DD plan authoring → 1–3 review agents based on risk level → main flow handles review findings → confirmation gate → hand off to autopilot for development. Solves three high-frequency problems: "forgot to create a branch/worktree", "assumed code behavior from training data", and "coded before plan was reviewed and confirmed".
version: 2.0.0
---

# /feat — Feature Development Planning Phase (Research → Plan → Review → Confirm)

> **Multi-project universal version.** `{placeholders}` are project-specific customization points. Replace them per `SETUP.md` before migrating.
> **feat owns the first half (producing a researched, reviewed, and confirmed DD); autopilot owns the second half (batch development per DD + code review + delivery).**

Core belief: **Code is ground truth.** Every plan conclusion must be grounded in "actually-read real code / locally-pulled latest repo / read-only-verified real server data". Conclusions based on training data, generic framework assumptions, or guesswork are **prohibited**.

---

## Scope and Boundaries

| Phase | Owner | Artifact |
|-------|-------|----------|
| Requirement scope analysis → code research → DD plan → plan review → confirmation | **feat (this skill)** | Reviewed and confirmed DD (inside requirement subfolder) |
| Batch development → code review → fixes → archiving + acceptance | **autopilot** | Code + acceptance documents |

feat ends = DD confirmed by a human; autopilot naturally follows.

---

## Phase 0: Pre-flight Checks

### 0.1 Development Environment (worktree default)

Default to worktree-isolated development (no need to ask the user every time unless they haven't specified). Exceptions: explicitly asked for direct main branch / single-file low-risk / pure documentation.

```bash
git branch --show-current
```

- On main branch and doing real development → use `{WORKTREE_SKILL}` (pull new branch from main + create worktree + sync env)
- Already in a feature worktree → record branch name + worktree absolute path, lock cwd throughout (no `cd` drift)

### 0.2 Locate Requirement Subfolder

Determine requirement ID and subfolder `{DOCS_ROOT}/{type}/{ID}/` (new feature / enhancement / fix).
Small features (≤ {SMALL_FILE_THRESHOLD} files, pure additive/styling/copy) may skip the DD and go directly to the confirmation gate, but the rationale must be stated.

### 0.3 Lessons Learned Lookup (if project has `{LESSONS}`)

Read `{LESSONS}`, match sections to the task's key terms and output a summary of key pitfalls (highlight the most frequent error types in the project). **Non-blocking — continue immediately.**

---

## Phase 1: Requirement Scope Analysis

Break the requirement into a researchable scope list. **Define what to investigate before investigating**:

```
🔍 Requirement Scope Analysis
Requirement: {one sentence}
Modules in this repo: {pages/components/hooks/store/lib — list specific path guesses}
Other repositories: {backend/contracts/services — which routes/methods/events}
Server/runtime data: {does the plan require verifying DB/deploy config/production state/logs}
Third-party libraries: {is a library being introduced or relied upon for a specific capability}
Risk level: {small / medium / large} (determines number of review agents in Phase 4)
Unknowns: {key questions that require research to answer, listed one by one}
```

Risk level determination (drives review scale):

| Level | Signals |
|-------|---------|
| Small | ≤{SMALL_FILE_THRESHOLD} files, pure additive/styling/copy, single module, no cross-repo |
| Medium | Single-module feature, 3–5 files, has business logic, depends on existing interfaces |
| Large | New page / cross-module / architectural decision / new global state / funds·auth·payment / cross-repo contract / new dependency selection |

---

## Phase 2: Real Codebase Research (Non-Negotiable)

**Skipping this phase and writing the plan directly is a violation.** Whenever another repository is involved (backend/contracts/services), pull the latest local repo and read the real code first.

### 2.1 Pull Latest Code (Branch Protocol)

**Each repository may have a different development branch** (e.g., backend iterates on `dev`, frontend/contracts on `main`). Check `{REPO_MAP}` in SETUP.md for the correct branch to check out before pulling:

```bash
# Template (actual repos/branches defined in {REPO_MAP})
git -C {REPO_PATH} checkout {DEV_BRANCH} && git -C {REPO_PATH} pull --ff-only
```

> If `pull --ff-only` fails (local has diverged) → **do not reset/merge**; tell the user to handle it in that repo themselves.
> Use `git -C <path>` for cross-repo operations — **do not pollute the current worktree cwd**.

### 2.2 Read Real Code (Local First, No Assumptions)

| Target | Primary entry point |
|--------|---------------------|
| Cross-service external capabilities | That repo's API overview doc (methods/events/errors/params) → then read source |
| Interface contracts | Go to the service and read handler / DTO / model (check whether fields are required) + data migrations |
| Current state of this repo | grep real call sites / type definitions / hooks / store — confirm existing implementation, do not guess |

Red lines:
- ❌ Assume this project's own code behavior from training data / generic framework knowledge (project-specific code is not in the training set)
- ❌ Use remote web scraping as a substitute for reading code locally (local is faster, greppable, and captures unpushed local branches)
- ✅ If docs conflict with source / docs are marked TBD / pure product decisions → only ask the user after reading both sides

### 2.3 Read-Only Server Verification (when runtime truth is needed)

When the plan depends on **real runtime state** (DB rows, live deploy config, actual API responses, logs) that cannot be determined from code, SSH read-only verification is permitted. All servers are registered in `{SSH_INVENTORY}`. **Always use aliases — `-i <absolute-path>` is prohibited**:

```bash
ssh {SERVER_ALIAS}     # alias + purpose defined in {SSH_INVENTORY}
```

Read-only verification examples: inspect a table's fields, check deploy config, curl an internal endpoint for the real response, tail logs for real errors.

Red lines:
- ⛔ **Read-only only** — prohibited: write to DB / change config / restart services / deploy. Anything involving writes → stop and hand to user
- ⛔ Private key content / credentials / passphrases must never be printed to output
- ⛔ Uncertain whether an operation is read-only → ask the user first

### 2.4 Third-Party Library / Interface Capability Verification

- Claiming a library "supports/does not support" a capability → check official docs (e.g., context7) or read `node_modules` source first; training data inference is prohibited
- Introducing a new dependency → first output a top-N comparison table (stars/downloads/last commit/official demo) for user confirmation before installing
- Uncertain about an API path/ownership → `curl` to test the real path + HTTP status code; include the result in the DD

---

## Phase 3: Collaborative Plan Authoring (Write the DD)

Organize into a DD document, placed in the requirement subfolder `{DOCS_ROOT}/{type}/{ID}/{DD|ENH|BUG}.md` (main filename follows `{type}`) + `INDEX.md`. Must include:

- **§1 Background and Scope**: what problem is being solved, which files/repos/servers are involved
- **§2 Research**: **evidence** from this phase — which real code was read (with path + line numbers), branch commit that was pulled, server verification results, curl HTTP codes, library capability verification
- **§2.5 Design Node Mapping** (required for UI tasks, see `{DESIGN_IMPL_SKILL}`): node ID ↔ file path table
- **§3 Plan Design**: components/data flow/key decisions (including alternatives considered + rationale for rejection); multiple viable options with real trade-offs and hard-to-reverse consequences → extract as an ADR
- **§4 Implementation Plan**: broken into Batches (each ≤{MAX_FILES_PER_BATCH} files), ready for autopilot to execute directly
- **§5 Decision Matrix**: problem/solution matrix with `[severity / trigger scenario / impact scope / ROI]` 4-column format

> If multiple viable options exist and impact spans more than a single file → **list them explicitly for the human to choose**; do not silently pick one.

---

## Phase 4: 1–3 Review Agents Based on Risk Level (Plan Review)

**After the plan is drafted, before the confirmation gate**, spawn independent subagents to review **the plan itself** (not the code), based on the risk level from Phase 1. The plan-writing context cannot self-review.

| Level | Agent count | Composition (plan review perspective) |
|-------|------------|--------------------------------------|
| Small | **0** | Skip plan review, go directly to confirmation gate |
| Medium | **1** | `critic` (plan flaws/edge cases/feasibility) or `design-distiller` (sharpen soft plan boundaries) |
| Large | **2–3** | `critic` + `architect` (architecture/reversibility/cross-module impact) + domain third: `security-reviewer` (funds/auth) or `document-specialist` (SDK/contract correctness) |

Delegate in parallel (multiple Agent calls in one message). Each agent prompt **must explicitly inject** (subagents do not inherit context):

1. DD absolute path + requirement scope summary + key research evidence points
2. Project key conventions + relevant rules (cross-repo/security/design as applicable)
3. Review focus: **is the plan grounded in real code** (any assumptions?), are edge cases/exceptions covered, are there better/more reversible options, is the batch breakdown sensible, were cross-repo contracts verified against real fields
4. Output to the requirement subfolder absolute path `reviews/REV-plan-v1-{A|B|C}-{agent}.md` (orthogonal naming to autopilot's `REV-code-v1-*` — same directory, no name collision; second review pass creates `v2`, does not overwrite v1); final message only reports conclusion summary + report path (no full text — prevents context truncation from swallowing the report)

---

## Phase 5: Main Flow Handles Review Findings → Refine DD → Confirmation Gate

### 5.1 Process Findings

Main flow reads all review reports, deduplicates, and auto-handles:
- **Accept**: plan hard defects/gaps/better alternatives → update the DD directly (add research, revise design, adjust batch breakdown)
- **Dispute**: if the review suggestion itself is questionable/unclear → verify first (read code/ask) before deciding; do not blindly follow
- **Defer**: low-ROI plan-level optimizations → note in the DD, do not block

Append a "Plan Review Resolution Record" to the bottom of the DD.

### 5.2 Confirmation Gate ⛔

```
⏸️  Plan Confirmation Gate
DD: {DOCS_ROOT}/{type}/{ID}/{DD|ENH|BUG}.md
Research evidence: {N} real code references / pulled branches / server verifications / curls
Plan review: {K} agents ({verdict}) → resolved
Implementation plan: {M} Batches

This plan requires your confirmation before coding begins. Reply "confirm"/"OK"/"start" to proceed to autopilot, or provide revision feedback.
⛔ Writing any business code before receiving confirmation is prohibited.
```

- Explicit confirmation → proceed to Phase 6; revision feedback → return to Phase 3/5 to adjust and re-gate; ambiguous/silent → request explicit confirmation again

---

## Phase 6: Hand Off to Autopilot

After confirmation, hand off to `autopilot` (DD is in the requirement subfolder with §4 implementation plan): batch development (with appropriate tests per batch) → 1–3 code review agents → handle findings → archive acceptance.

---

## Exception Handling

| Scenario | Action |
|----------|--------|
| User says "quick fix XX" | ≤{SMALL_FILE_THRESHOLD} files low-risk → simplify (skip DD + skip plan review); otherwise run full flow |
| Other repo `pull --ff-only` fails | Do not reset/merge; tell the user to handle it in that repo |
| Phase 2 research contradicts requirement premise (interface doesn't exist / architecture conflict / technically infeasible) | **Stop writing the DD** — report to user with real code evidence and wait for requirement adjustment (code is ground truth — ground truth can also veto requirements) |
| Need to write to server/deploy | Stop; operations outside the read-only boundary are handed to the user |
| Docs conflict with code | Read both sides before asking the user which is authoritative |
| Plan review determines a redo is needed | Pause, report review conclusions, suggest redesign |
| User changes requirements mid-flow | Return to Phase 1 to re-analyze scope |

---

## Safety Red Lines

1. **Code is ground truth** — conclusions involving other repos/servers must be backed by real code/data; training data assumptions are prohibited
2. **Pull latest before researching** — check out the correct branch per `{REPO_MAP}`; writing a plan without pulling is a violation
3. **Server is read-only** — prohibited: write to DB / change config / deploy / restart; private key credentials must not be printed
4. **Plan review uses independent subagents** — main conversation self-review is prohibited
5. **No coding before confirmation gate** — only enter autopilot after receiving explicit confirmation
6. **Let humans choose among multiple viable options** — when impact spans more than a single file and there are real trade-offs, list options explicitly

---

> To migrate to a new project: see `SETUP.md` in the same directory.
