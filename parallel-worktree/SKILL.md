---
name: parallel-worktree
description: Parallel worktree development orchestration. Triggers when the user says "/parallel", "parallel dev", "open worktree", "parallel tasks", "parallel development", or "split parallel". Automatically executes: task decomposition → file ownership check → worktree creation → focused context injection → merge guidance. Solves two core problems: "merge conflicts from poor task splitting" and "out-of-scope edits from agents lacking focused context".
version: 1.0.0
---

# /parallel — Parallel Worktree Development Orchestration

When the user needs to develop multiple tasks in parallel, execute the following phases in order. Core principle: **isolate tasks by file ownership so each agent only sees what it needs to do.**

---

## Phase 0: Parallelism Feasibility Assessment

### 0.1 Collect Task List

Extract all pending tasks from the user's description. If unclear, read `.progress/tasks/todo.md` to get active work items.

### 0.2 File Ownership Analysis

For each task, infer its affected file scope:

```
Task → route directory + component directory + type files + Mock Handlers
```

Natural isolation boundaries in the project:

| Route | Component Directory | Independence |
|-------|---------------------|--------------|
| `app/markets/` | `components/market/` | High |
| `app/stake/` | `components/stake/` | High |
| `app/swap/` | `components/swap/` | High |
| `app/trade/` | `components/trade/` | High |
| `app/invite/` | `components/invite/` | High |

Shared files (conflict hotspots):

| File | Conflict Risk | Handling Strategy |
|------|---------------|-------------------|
| `tailwind.config.ts` | High | Exclusively owned by infrastructure branch |
| `lib/api.ts` | Medium | Adding new endpoints typically doesn't conflict |
| `types/*.ts` | Low | Each task adds its own type definitions |
| `mocks/handlers/index.ts` | Low | Append-only imports |

### 0.3 Feasibility Determination

Check all conditions below — parallel execution is recommended only if all are satisfied:

- [ ] File ownership overlap between tasks ≤ 2 files
- [ ] All overlapping files are "append-only" (e.g., types/, handlers/index.ts), not "modify-in-place"
- [ ] Number of parallel tasks ≤ 3 (cognitive limit for a solo developer)
- [ ] Each task has a clear DD document or requirements description

**If conditions are not met**: Explain the reason to the user and recommend sequential execution or task re-scoping.

### 0.4 Output Parallel Plan

```
📋 Parallel Task Breakdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🅰️ Worktree A: {branch-name}
   Task: {task description}
   File scope: {directory list}
   DD: {DD document path}

🅱️ Worktree B: {branch-name}
   Task: {task description}
   File scope: {directory list}
   DD: {DD document path}

⚠️ Shared files: {list}
   → Handling strategy: {description}

📐 Merge order: A → B (B must rebase)
✅ File conflict risk: {Low/Medium/High}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Wait for user confirmation before proceeding to the next phase.

---

## Phase 1: Worktree Creation and Environment Setup

### 1.1 Create Worktrees

For each parallel task, run:

```bash
git worktree add .worktrees/{name} -b {branch-name}
cd .worktrees/{name} && pnpm install
```

Branch naming follows project conventions: `feat/`, `fix/`, `refactor/`, `chore/`.

### 1.2 Inject Focused Context

Generate `WORKTREE_CONTEXT.md` in the root of each worktree:

```markdown
# Worktree Task Context

## Current Task
{branch-name} — {task description}

## DD Document
{DD document path, or "No DD required" if not applicable}

## File Ownership (only modify the files listed below)
{file/directory list}

## Off-limits (owned by other worktrees)
{file scope of other worktrees}

## Current Progress
{Initially: "Not started"}
```

### 1.3 Output Launch Instructions

Generate ready-to-paste terminal commands for the user:

```
🚀 Launch Parallel Development
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Terminal 1:
  cd .worktrees/{name-a}
  claude
  > Read WORKTREE_CONTEXT.md and start development per the DD document

Terminal 2:
  cd .worktrees/{name-b}
  claude
  > Read WORKTREE_CONTEXT.md and start development per the DD document

Or using native Claude approach:
  Terminal 1: claude --worktree {name-a}
  Terminal 2: claude --worktree {name-b}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phase 2: Merge Guidance (after all worktrees are done)

When the user signals that all parallel tasks are complete, output merge instructions:

### 2.1 Pre-Merge Checks

```bash
# Confirm tests pass in each worktree
cd .worktrees/{name} && pnpm type-check && pnpm test
```

### 2.2 Merge in Order

```bash
# Return to the main directory
cd /Users/hang/work/oddfi-frontend

# Merge the first branch (lowest conflict risk first)
git merge --squash {branch-a}
git commit -m "{commit message}"

# Rebase the second branch, then merge
cd .worktrees/{name-b}
git rebase main
cd /Users/hang/work/oddfi-frontend
git merge --squash {branch-b}
git commit -m "{commit message}"

# Final validation
pnpm type-check && pnpm test && pnpm build
```

### 2.3 Cleanup

```bash
git worktree remove .worktrees/{name-a}
git worktree remove .worktrees/{name-b}
git branch -d {branch-a}
git branch -d {branch-b}
```

---

## Error Handling

| Scenario | Resolution |
|----------|------------|
| Severe file ownership conflicts | Recommend sequential execution — do not force parallel |
| Merge conflicts | Show conflicting files and assist user in manual resolution |
| A worktree task scope expands | Pause that worktree and re-evaluate task boundaries |
| Agent modifies out-of-scope files | Prompt user to revert out-of-scope changes; re-enforce boundaries from WORKTREE_CONTEXT.md |
| Insufficient disk space | Clean up completed worktrees and node_modules |

---

## Additional Resources

### Reference Documents

- **`.progress/dev-docs/parallel-worktree-sop.md`** — Full SOP document (includes decision formulas, pattern reference, and caveats)
- **`.progress/dev-docs/research/worktree-parallel-dev-research.md`** — Industry research report (includes Anthropic C compiler case study and expert workflows)

### Parallel Patterns Quick Reference

| Pattern | Description | Use Case |
|---------|-------------|----------|
| Divide-and-conquer | Split by file ownership, each task in its own worktree | Multiple independent pages/modules |
| Competitive implementation | Two worktrees implement the same feature independently | Design/approach selection |
| Infrastructure + business | Infrastructure changes run in parallel with business features | Avoiding business blockage during refactors |
