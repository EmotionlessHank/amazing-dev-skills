---
name: worktree-dev
description: Enforced worktree-isolated development. Triggers when the user says "/worktree-dev", "worktree dev", "isolated dev", "open a worktree for this", or "wt dev". Automatically executes: pull a new branch from main → create worktree → sync env → inject isolation context → lock working directory throughout. Solves two high-frequency problems: "agent drifts out of the worktree and contaminates the main workspace" and "forgot to branch off main before starting".
version: 2.0.0
---

# /worktree-dev — Enforced Worktree-Isolated Development

> **Multi-project universal version.** `{placeholders}` are project-specific customization points. Replace them per `SETUP.md` before migrating.
> Works together with feat/autopilot: worktree-dev handles **isolated environment setup + cwd locking**; feat plans inside it, autopilot develops inside it.

**Core rule: once inside a worktree, all file reads/writes, git operations, and build commands must execute within the worktree directory. Jumping back to the main workspace is strictly prohibited.**

---

## Phase 0: Parameter Collection

### 0.1 Collect Required Information

| Parameter | Source | Example |
|-----------|--------|---------|
| Feature name | User description | "lend page development" |
| Branch name | Auto-inferred (user can override) | `feat/lend-page` |
| Plan document | Match in `{DOCS_ROOT}/{type}/` | `{ID}` subfolder |

**Branch naming conventions** (inherited from project rules): `feat/` (new feature) · `fix/` (bug fix) · `chore/` (config/dependencies) · `refactor/` (refactoring).

### 0.2 Pre-flight Check

```bash
git fetch origin {MAIN_BRANCH}
git log HEAD..origin/{MAIN_BRANCH} --oneline   # warn user to pull first if behind
```

---

## Phase 1: Worktree Creation

### 1.1 Create Worktree (Enforced Path)

```bash
# ✅ Only legal path: {WORKTREE_BASE}/<name>
git worktree add {WORKTREE_BASE}/<name> -b <branch-name> {MAIN_BRANCH}

# ❌ All other paths prohibited (/tmp, outside the repo, arbitrary directories)
```

> If the project has a helper script `{WT_HELPER}` (creates worktree + auto-symlinks env/config in one step) → use it preferentially.

### 1.2 Sync Environment / Runtime Files (symlink — mandatory)

All `{ENV_FILES}` (and personal config such as local permission allowlists) must use **symlinks**, not `cp` — copies are static snapshots; if the main workspace later updates the env file (changing RPC endpoints, API keys), the worktree won't see it, sending troubleshooting in the wrong direction.

```bash
# Run from the main workspace root; symlink each env file back to the main workspace
# (adjust the relative path depth based on {WORKTREE_BASE} nesting level)
ln -sf {relative-path-to-main-workspace}/{ENV_FILE} {WORKTREE_BASE}/<name>/{ENV_FILE}
```

> **Consequence of missing symlinks**: missing env files often **silently fall back** to a default/wrong environment (no error thrown) — this is the most insidious pitfall. Verify each symlink points to a valid file. See `SETUP.md` for the specific `{ENV_FILES}` list and the consequence of each missing file.

### 1.3 Install Dependencies

```bash
{INSTALL}   # run inside the worktree directory; fast if deps use a global store with hard links (e.g., pnpm)
```

### 1.4 Output Creation Confirmation

```
🌿 Worktree created
📂 Path: {WORKTREE_BASE}/<name>
🔀 Branch: <branch-name> (based on {MAIN_BRANCH})
📋 Plan: <plan document path | none>
🔒 Isolation mode: active
⚠️ From this point on, all operations are locked to the worktree directory.
```

---

## Phase 2: Isolated Development (Core Constraints)

### 2.0 Pre-batch Read Checklist (Mandatory — First Step Before Any Edits)

**After entering the worktree and before any Edit/Write operations**, read all files involved in this batch concurrently in a single pass.

**Why you cannot interleave Edit and Read**:
- Edit/Write/MultiEdit have a hard constraint — the same path must be Read before it can be Edited
- **Path exact match**: the main workspace path and the worktree path are two different files from the tool's perspective (`src/x.ts` ≠ `{WORKTREE_BASE}/X/src/x.ts`) — a Read of the main workspace path does not allow an Edit of the worktree path
- Interleaving Edit-fail and Read → each file incurs one "Edit fails → Read → retry" round trip; N files = N round trips, constantly interrupting the work rhythm

**Correct approach**: ① List all files planned for this batch (including same-directory batch files, i18n all locales, co-located tests, adjacent components) → ② **Concurrently Read the entire list in one message** → ③ Edit continuously.

| Task type | Required reads |
|-----------|----------------|
| Modify 1 component | That file + its tests + same-directory referenced sub-components |
| Modify i18n copy | All locale message files in one pass |
| Modify hook behavior | Hook file + tests + calling components (up to 3–5) |
| Modify infrastructure | File to change + 1 reference file of the same kind (style alignment) |

> Cooperative hook (optional): `{EDIT_READ_PREREQ_HOOK}` emits a strong reminder to batch-Read when "File has not been read yet" is detected.

### 2.0.1 Working Directory Lock (Highest Priority Rule)

After entering the worktree, the following are all prohibited without exception:

| Prohibited | Notes |
|------------|-------|
| ❌ `cd {REPO_ROOT}` back to main workspace | — |
| ❌ Read/Edit/Write paths in the main workspace | — |
| ❌ Run `git commit/push/merge` in the main workspace | — |
| ❌ Run `build/test/dev` in the main workspace | — |

**Only legal exception (read-only)**: reading documents under `{DOCS_ROOT}/` (plans/todos/lessons) and reading `{RULES}` (project rules).

### 2.1 Path Guard (Self-check before every tool call)

```
Legal read/write prefix: {REPO_ROOT}/{WORKTREE_BASE}/<name>/
Read-only prefix: {REPO_ROOT}/{DOCS_ROOT}/ · {REPO_ROOT}/{RULES}
All other main workspace paths → 🚫 BLOCK
```

### 2.2 Batch Development

Follow the batch rules from `/feat` → `/autopilot`: ≤ `{MAX_FILES_PER_BATCH}` files per batch; after each batch completes, verify inside the worktree:

```bash
cd {WORKTREE_BASE}/<name> && {TYPECHECK} && {TEST}
```

### 2.3 Batch Announcement (with worktree context)

```
📦 Batch N/M complete
📂 Worktree: {WORKTREE_BASE}/<name> | 🔀 <branch-name>
Modified files: <worktree-relative paths>...
Verification: type-check ✅ | test ✅
🔒 Isolation status: clean (main workspace untouched)
```

---

## Phase 3: Commit and Cleanup

### 3.1 Commit Inside the Worktree

```bash
cd {WORKTREE_BASE}/<name>
git add <specific files> && git commit -m "<commit message>"
```

Commit message follows project conventions (`{COMMIT_CONVENTION}`, e.g., language/no AI attribution).

### 3.2 Final Verification

```bash
cd {WORKTREE_BASE}/<name> && {TYPECHECK} && {LINT} && {TEST} && {BUILD}
```

### 3.3 Completion Announcement + Cleanup Guide

```
✅ Worktree development complete
📂 {WORKTREE_BASE}/<name> | 🔀 <branch-name> | 📝 <commit count>
🔒 Isolation status: main workspace untouched throughout ✅

💡 Next steps (AI handles by default / or user manually, per project convention):
  1. Sync {DOCS_ROOT} docs back to main workspace (if gitignored and won't flow back via merge)
  2. In main workspace, squash merge: git merge --squash <branch-name> → commit
  3. Cleanup: git worktree remove {WORKTREE_BASE}/<name> + git branch -d <branch-name>
```

> **Merging back to main + pushing to remote is the user's responsibility** — AI stops at the local main branch squash commit by default and does not auto-push (unless the project explicitly authorizes AI to finalize the local merge; pushing is always the user's decision).

---

## Exception Handling

| Scenario | Action |
|----------|--------|
| Worktree path already exists | Prompt user: reuse or delete and recreate |
| `{ENV_FILES}` symlink missing or pointing to nonexistent file | Check all env symlinks point to main workspace; fix them, then restart the dev server |
| Dependency install fails | Check runtime version, output error log |
| Agent accidentally returns to main workspace | Stop immediately, declare the violation, switch back to worktree and continue |
| Type check has pre-existing errors | Mark as "legacy errors", continue if unrelated to this change |
| User asks to "also quickly fix XX in the main workspace" | 🚫 Decline — suggest opening a separate session to handle it in the main workspace |

---

## Agent Delegation Scenario

When the main agent delegates worktree development to a subagent via the `Agent tool`, the prompt must include:

```
⚠️ Isolation constraint (highest priority):
- Working directory locked to: {REPO_ROOT}/{WORKTREE_BASE}/<name>/
- All Read/Edit/Write/Bash must operate within this directory
- Reading or writing files under {REPO_ROOT}/ outside of {DOCS_ROOT}/ is prohibited
- Running any git/build commands in the main workspace is prohibited
```

---

> To migrate to a new project: see `SETUP.md` in the same directory.
