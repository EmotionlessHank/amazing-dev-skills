---
name: autopilot
description: Fully automated development pipeline after a plan has been confirmed. Triggers when the user confirms a development plan ("confirm"/"OK"/"start"), or says "/autopilot", "auto dev", "run pipeline", or "autopilot". Automatically executes: batch development (with appropriate tests per batch) → 1–3 parallel review agents as needed → main flow auto-handles review findings → archives process/acceptance docs in the requirement subfolder → development summary (fixed template, mandatory before acceptance) → notifies user for acceptance. Should be invoked proactively when a "plan confirmed, ready to develop" pattern is detected.
version: 2.2.0
---

# /autopilot — Fully Automated Development Pipeline

> **Multi-project universal version.** `{placeholders}` are project-specific customization points. Before migrating to a new project, replace all placeholders with actual values per `SETUP.md`.
> feat produces the plan → autopilot delivers it: **batch development (with appropriate tests per batch) → 1–3 parallel review agents as needed → main flow auto-handles findings → docs archived + acceptance notification**.

Simulates a real engineering team: product confirms PRD → engineers implement in batches with self-testing → 1–3 senior engineers review in parallel → engineer addresses findings → delivery docs assembled → human acceptance.

---

## Core Principles

1. **Only start after a plan is confirmed** — this skill does not design plans; it executes already-confirmed plans (DD/ENH/BUG)
2. **No human intervention required throughout** — no pauses from the first line of code through review resolution
3. **Appropriate tests per batch** — each batch runs tests relevant to that batch (co-located unit tests + type checks), not just type checks alone; full gate runs after all batches complete
4. **Reviews use real subagents, 1–3 in parallel as needed** — not the main conversation switching to "review mode" for self-review (code-writing context cannot self-approve); scale is determined by change size and risk
5. **Main flow auto-handles review findings** — Critical/Major items are fixed automatically; Minor/low-ROI items are automatically deferred to a backlog
6. **Process and acceptance docs archived in requirement subfolder** — all artifacts go to `{DOCS_ROOT}/{type}/{ID}/` (see §Doc Archiving Convention)
7. **Notify user for acceptance on completion** — output an acceptance checklist and surface it explicitly to the user in the conversation
8. **Never auto-push/merge to remote** — stops at local main branch squash commit; user decides on pushing
9. **Strictly follow project conventions** — project `{RULES_DIR}` / conventions (Batch ≤N files, lessons-first, worktree default, tiered review fixes) all apply

---

## Doc Archiving Convention (Mandatory)

All autopilot artifacts go into the **requirement subfolder** `{DOCS_ROOT}/{type}/{ID}/`. Flat placement is prohibited.

```
{DOCS_ROOT}/{designs|enh|bug|...}/{ID}/
├── INDEX.md                  Directory index (artifact list + phase timeline + key commits)
├── {DD|ENH|BUG}.md           Plan document (exists before autopilot starts)
├── reviews/                  Review reports (plan-review from feat / code-review from this skill)
│   ├── REV-plan-v1-A-{agent}.md   (feat phase plan review)
│   ├── REV-code-v1-A-{agent}.md   (autopilot code review)
│   └── REV-code-v1-B-{agent}.md   (v2 = second review pass, does not overwrite v1)
├── CHANGES.md                Phase 4: commit list + added/modified/deleted files
├── TEST_PLAN.md              Phase 4: AI-automated test items (type/unit/full/build/review)
├── ACCEPTANCE.md             Phase 4: mandatory human acceptance items (browser/integration/edge cases)
└── enh-todo-additions.md     Phase 3: deferred Class-B items
```

> Multi-platform tasks (e.g., PC + mobile) may split into `TEST_PLAN-{platform}.md` / `ACCEPTANCE-{platform}.md`.
> Previously flat-organized legacy requirements remain as-is; all new tasks must use the subfolder structure.
> ⚠️ If `{DOCS_ROOT}` is gitignored, worktree cleanup must `cp` the subfolder back to the main workspace (see §Cleanup).
> Reference example: `{EXAMPLE_REQUIREMENT_FOLDER}`.

---

## Phase 0: Startup Checks

### 0.1 Locate Plan Document + Requirement Subfolder

```
Resolution order:
1. {ID} path explicitly mentioned in the conversation
2. Infer from current branch name (feat/xxx → designs/{ID}/, fix/xxx → bug/{ID}/)
3. Most recently modified plan file
```

**Handoff priority**: If handed off from feat (the conversation already contains a confirmed DD path from a gate announcement) → **reuse that path directly**, skip the three-level inference below; the inference is only for standalone `/autopilot` entry points.

Lock the requirement subfolder `{DOCS_ROOT}/{type}/{ID}/`. Read the plan document and extract: implementation plan (Batch/Phase list), component breakdown (which files change), key technical decisions.

**No implementation plan → BLOCK**: The plan must contain an executable implementation plan; otherwise prompt the user to add one.

### 0.2 Branch Check

| Current Branch | Behavior |
|----------------|----------|
| Main branch (main/master) | **BLOCK** — prompt to create a feature branch or use worktree |
| `feat/*` / `fix/*` / `refactor/*` / `chore/*` | Pass — record branch name + worktree absolute path |

### 0.3 Lessons Learned Lookup (if project has `{LESSONS}`)

Read `{LESSONS}`, match relevant sections to the plan's technical domain, surface key pitfall reminders. **Continue without waiting for confirmation.**

### 0.4 Workspace State + Task Type

Run `git status --porcelain` to check for uncommitted changes. Identify task type: contains design node IDs / "design/pixel-perfect" keywords / JSX rendering → **UI task** (Phase 1 adds design-driven implementation + visual acceptance, see `{DESIGN_IMPL_SKILL}`); otherwise standard task.

### 0.5 Startup Announcement

```
🚀 Autopilot Pipeline Starting
Plan: {ID title} | Branch: {branch} | Type: {UI/Standard}
Requirement folder: {DOCS_ROOT}/{type}/{ID}/
Pipeline:
  Phase 1: Batch development → {N} Batches (with appropriate tests per batch)
  Phase 2: {1-3} parallel review agents as needed → reviews/REV-v1-*.md
  Phase 3: Main flow auto-handles findings (Class-A fix / Class-B → enh-todo-additions)
  Phase 4: Archive CHANGES/TEST_PLAN/ACCEPTANCE/INDEX → development summary (fixed template) → acceptance notification
```

---

## Phase 1: Batch Development

### 1.1 Batch Breakdown

Extract batches from the implementation plan. Each batch: **≤ {MAX_FILES_PER_BATCH} files**, logically complete minimal unit (can independently pass type checks), strict ordering for dependencies. Auto-subdivide if granularity is too coarse.

### 1.2 Single Batch Execution

**Step 1 — Code**: Implement per plan design at the **test seam the DD §6 picked** (reuse the highest existing seam; don't invent new ones mid-batch), follow project code conventions, apply lessons learned to avoid known pitfalls. For batches that touch real behavior, prefer a test-driven discipline (RED→GREEN→refactor, one tracer-bullet slice at a time; see the `tdd` skill) over write-code-then-test.
**Step 1.5 — Design-driven (UI tasks only)**: Use `{DESIGN_IMPL_SKILL}` workflow to fetch design data → code to exact values → per-component visual acceptance; subagent delegates must include design node IDs.

**Step 2 — Appropriate test verification (required per batch)** — not just type checks; run tests matching this batch's change nature:

```bash
{TYPECHECK}                          # always run
{TEST} {test files/dirs for this batch}   # run co-located unit tests for changed code
```

| Batch change type | What to run |
|-------------------|-------------|
| Pure functions / utility libraries | Corresponding co-located unit tests (P0 required) |
| Global state / store | Corresponding store tests |
| Hook logic | Corresponding hook tests (hook changes should include tests) |
| Component rendering/interaction | Component tests in the component directory |
| Type contracts / API layer | Affected integration tests |
| Pure styling / copy | Skip unit tests, mark `visual-fix`/`copy-fix`, type check only |

No corresponding tests but changed core logic → write a failing test (red) first then fix (green) per the `tdd` skill (assert **external behavior**, not implementation), or explicitly mark "pre-existing gap, log to enh-todo". Type/test failures → **fix immediately**, do not proceed to the next batch.

**Step 3 — Commit**: `git commit`, message follows project language conventions, no AI attribution.
**Step 4 — Batch announcement**: List changed files + verification results + commit.

### 1.3 After All Batches Complete (Full Gate)

```bash
{TYPECHECK} && {LINT} && {TEST} && {BUILD}
```

- If new files were created that are indexed by `{GEN_ASSETS}` → run `{GEN_ASSETS}` first to refresh (otherwise pre-commit hook will block)
- Any failure → fix the root cause; `--no-verify`/`SKIP_*` bypasses are prohibited; fixes are **appended as independent commits** (not amending batch history), to be squashed together later
- If files were deleted → grep to confirm no leftover imports + index is synced

---

## Phase 2: 1–3 Parallel Review Agents As Needed

**Core: use real subagents for review — not the main conversation switching to "review mode" for self-review** (code-writing context cannot self-approve). Review agents are independent subagents running in parallel, each producing their own REV report.

### 2.1 Determine Agent Count As Needed (1–3, size/risk-driven)

| Agent count | When | Composition |
|-------------|------|-------------|
| **1** | Small change (≤~5 files, low risk, mechanical changes like contract migration/copy/config) | `code-reviewer` |
| **2** (default) | Standard feature / multi-file / has business logic | `code-reviewer` (deep review) + `{QUALITY_SCANNER}` (high-frequency pitfall quick scan; if unavailable, use `test-engineer` or a generic reviewer as the second agent) |
| **3** | Large / security-sensitive / funds·auth·payments / cross-module | Above + domain third: `security-reviewer` or `test-engineer` or `performance-engineer` |

When in doubt, use 2.

### 2.2 Parallel Delegation (Agent tool, multiple Agent calls in one message)

Each review agent prompt **must explicitly inject** (subagents do not inherit main conversation context):

1. **Working directory** (worktree absolute path) + commit range under review
2. **Task background**: plan document path + requirement summary
3. **Required context**: project key conventions (`{PROJECT_CONVENTIONS}`: e.g., runtime output language, precision arithmetic, design tokens, testing standards); UI tasks additionally include design node IDs
4. **Review focus**: listed by change domain, highest-risk items first
5. **Output destination**: complete REV report written to subfolder absolute path `{DOCS_ROOT}/{type}/{ID}/reviews/REV-code-v1-{A|B|C}-{agent}.md`, following project review standards (🚨Critical/⚠️Major/ℹ️Minor + per-issue `[severity/trigger scenario/impact scope/fix ROI]` 4-column format + test coverage review section + Deletion Test section)
6. **Final message only reports**: N Crit/M Major/K Minor + overall verdict + report absolute path (**do not paste full text** — prevents context truncation/output hook from swallowing the report; if the report is swallowed, retrieve it from the subagent's persisted transcript per `{SUBAGENT_TRANSCRIPT}` by extracting the longest assistant text block)

> Multi-agent reviews **must each produce a separate file** (REV-code-v1-A/-B/-C); merging them is prohibited.
> **Version convention**: first pass is `v1`; if code is modified and a second review pass is needed (triggered by human instruction), create a new `v2` file — do not overwrite v1.

### 2.3 Aggregate Findings

After all reports are collected, the main flow reads each REV, deduplicates findings, and produces a combined verdict: 🟢 Ship It / 🟡 Needs Changes / 🔴 Major Rework + Crit/Major/Minor counts.

---

## Phase 3: Main Flow Auto-Handles Review Findings (Tiered Fix)

### 3.1 Triage

| Class | Covers | Action |
|-------|--------|--------|
| **Class A (fix immediately)** | Critical, Major Bug, blocking logic, severe performance, architecture violation, missing tests (core logic with no corresponding tests) | Fix code immediately |
| **Class B (defer)** | Minor, refactor suggestions, low ROI, high-risk non-urgent items, pre-existing gaps | Move to subfolder `enh-todo-additions.md` |

> **Downgrade judgment**: A Major item that is pre-existing, behavior-preserving, and low-risk may be downgraded to Class B and logged — but this must be explicitly stated in the REV writeback + final report with **a clear rationale for the downgrade**.

### 3.2 Class A Fixes

- Fix directly; if > `{MAX_FILES_PER_BATCH}` files, split into sub-batches, each running relevant tests + type checks; committed separately from development commits for traceability
- **Serial execution**: Class A fixes are done serially by the main flow — do not spawn parallel fix agents (avoids multi-agent conflicts on the same file)
- **Escalation exit**: If a Class A root cause is outside this plan's scope (e.g., pre-existing architectural defect) / the same error fails to fix after N attempts → do not force it or silently downgrade; pause and report to the user (include the exception table). "Downgrade to B" only applies to pre-existing + low-risk situations — **it is not an escape hatch for Criticals**

### 3.3 Class B Transfer

Write to `{DOCS_ROOT}/{type}/{ID}/enh-todo-additions.md`, format includes trigger scenario + downgrade rationale for human decision-making.

### 3.4 REV Writebacks

Append a "Dev Agent Fix Record" to the bottom of each REV: Class A items checked off `[x]` + how fixed; items downgraded to B marked `⏭️` + rationale; fix commit + retest conclusion.

### 3.5 Post-Fix Verification

`{TYPECHECK} && {LINT} && {TEST}` to confirm no new failures introduced.

---

## Phase 4: Doc Archiving + User Acceptance Notification

### 4.1 Produce Delivery Documents (write to requirement subfolder)

| File | Content |
|------|---------|
| `CHANGES.md` | Commit list + categorized added/modified/deleted files + "unchanged (confirmed)" |
| `TEST_PLAN.md` | AI-automated test items (type/lint/full test/build/per-batch unit tests/review) + key contract assertion coverage table |
| `ACCEPTANCE.md` | Mandatory human acceptance items (browser interaction, integration, cross-platform, non-automated verification declarations); split by `-{platform}` for multi-platform |
| `INDEX.md` | Artifact list + timeline + key commits + review verdict |

### 4.2 Cleanup (default worktree path)

1. **Sync docs back to main workspace**: if `{DOCS_ROOT}` is gitignored → `cp -r` the subfolder back to the main workspace (diff first to avoid overwriting a more authoritative version)
2. **Squash merge to local main branch**: `git merge --squash {branch}` → commit (pre-commit hook re-runs the gate). **Do not push**
3. **Remove worktree**: `git worktree remove` + `git branch -D`
4. **Follow-ups**: cross-team dependencies or release coordination mentioned casually by the user are logged to the project reminder file

### 4.3 Development Summary (fixed template · mandatory before acceptance)

**After all development + review + verification is done and before handing over the acceptance checklist, you MUST emit a development summary in the fixed template below** — so the user grasps "what was built / how correctness is guaranteed / what honest caveats remain" before validating. All eight sections required; the **Honest Disclosure section is non-omittable** (forward-compat / currently-unreachable-but-tested / scope-narrowed / deferred items are surfaced, not buried in docs).

```markdown
# {REQ ID} Dev Summary · {Feature Name}

## One-liner
{What changed and what it achieves — one line, including the baseline it upgrades from}

## Deliverables
| Category | Content |
|---|---|
| New code | {new files + one-line responsibility} |
| Changed code | {changed files + change highlights} |
| Tests | {new case areas + total-test-count delta (e.g. 284→291)} |
| Docs | {DD status + 3-piece set + REV count + acceptance screenshot} |

## Key Architecture Decisions (with rationale + rejected options)
1. {decision → why this, what was rejected}
(2–4 items covering the most informative trade-offs)

## Invariant / Constraint Guards
- {each project red-line/iron-law + how this change does not violate it}

## Verification Evidence
- {lint result} · {N}/{suites} tests green · {visual/fidelity gate result/path} · {N}-agent review {verdicts}

## Review Handling
- {N agents · each verdict} → {what Critical/Major were fixed, where Minor were deferred}

## Honest Disclosure (non-defects)
- {forward-compat / currently-unreachable-but-tested / scope narrowed to a later requirement / known deferrals — stated proactively, not hidden}

## Status + Next Steps
- {branch + key commits} · main workspace untouched · merge + push = user's call (give the commands) · acceptance checklist in `ACCEPTANCE.md`
```

> Template purpose = make the "author/review separation + honest verification (self-verify-first / acceptance triage)" outcomes explicit; **do not** report only "all green, please accept" without explaining decisions and honest caveats. Adapt section labels (iron laws, build/lint commands, fidelity gate) to the project via `SETUP.md` placeholders.

### 4.4 Acceptance Notification

Immediately after the summary, **pull 3–6 of the most critical acceptance items from ACCEPTANCE.md and list them directly in the conversation**, with the full checklist path attached. UI changes must include the reminder: "Visual acceptance was not automated — please manually verify hover/entrance/edge states."

Push/merge to remote is left to the user's discretion.

---

## Exception Handling

| Scenario | Action |
|----------|--------|
| Plan has no implementation plan | BLOCK — prompt user to add one |
| On main branch | BLOCK — prompt to create feature branch/worktree |
| Same type check error fails after N fix attempts | Pause, report details, request user intervention |
| Test failure not introduced by this change | Mark as "legacy failure", continue |
| Review aggregate verdict 🔴 Major Rework | Pause, report to user, suggest redesign |
| Single batch requires > `{MAX_FILES_PER_BATCH}` files | Auto-split into sub-batches |
| Class A fix introduces new issues | Roll back that fix, mark as needing user intervention, continue other Class A items |
| User sends a message mid-pipeline / halts the pipeline | Pause, keep committed branch without removing worktree, report current progress, hand to user to decide continue/abort |

---

## Safety Red Lines

1. **Never auto-push / merge to remote** — stops at local main branch squash commit
2. **Reviews must use independent subagents** — main conversation self-review is prohibited
3. **Never modify non-code files outside business code + requirement docs** (e.g., global config, secrets, env)
4. **Never skip gate failures** — type/lint/test/build must pass; bypasses are prohibited; fix the root cause
5. **Major Rework must pause** — red light requires user decision
6. **Confirm before destructive/external actions** — production deploys, cross-team contracts (e.g., front/back-end release sequencing) require evidence verification and explanation before acting; do not execute blindly

---

> To migrate to a new project: see `SETUP.md` in the same directory for the placeholder replacement list + verification steps.
