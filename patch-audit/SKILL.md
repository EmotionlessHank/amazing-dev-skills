---
name: patch-audit
description: Patch accumulation audit and refactoring. Triggers when the user says "/patch-audit", "patch audit", "is this patches on top of patches", "review today's changes", or "check patch accumulation". Analyzes the current branch's commit history, identifies patch-on-patch patterns, and provides refactoring recommendations or executes the refactor directly.
version: 1.0.0
---

# /patch-audit — Patch Accumulation Audit and Refactoring

Analyze the current feature branch's commit history to identify "patch-on-patch" anti-patterns (feat → fix → fix → fix...) and evaluate whether a consolidating refactor to an optimal solution is warranted.

---

## Trigger Scenarios

- Multiple fix commits patching the same area during feature development
- The user feels changes are patching symptoms rather than solving root causes
- Fix commit count on the branch >= feat commit count

---

## Phase 1: Collect Branch History

### 1.1 Determine Branch Scope

```bash
# Current branch name
BRANCH=$(git branch --show-current)

# Branch divergence point (from main)
BASE=$(git merge-base main HEAD)

# All commits (oldest to newest)
git log --oneline --reverse $BASE..HEAD
```

### 1.2 Count Commit Types

Classify by conventional commit prefix:

| Type | Match Pattern |
|------|---------------|
| feat | `feat(` or `feat:` |
| fix | `fix(` or `fix:` |
| refactor | `refactor(` or `refactor:` |
| chore | `chore(` or `chore:` |
| other | No standard prefix |

### 1.3 Identify File Hotspots

```bash
# Number of times each file was modified within the branch
git log --name-only --pretty=format: $BASE..HEAD | sort | uniq -c | sort -rn
```

**Hotspot files**: Files modified by >= 3 commits are high-risk zones for patch accumulation.

### 1.4 Output Branch Overview

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Patch Audit — Branch Overview
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Branch: {branch_name}
Total commits: {N}
  feat: {n} | fix: {n} | refactor: {n} | other: {n}
Patch ratio: {fix_count / total * 100}%

Hotspot files (modified by >= 3 commits):
  {file_path} — {N} modifications
  {file_path} — {N} modifications
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phase 2: Per-Commit Evolution Analysis

For each hotspot file, trace its evolution in commit chronological order:

### 2.1 Read Each Commit's Diff

```bash
# For each hotspot file, view changes from each commit
git log --reverse -p $BASE..HEAD -- {hot_file}
```

### 2.2 Identify Patch Patterns

For the commit chain of each hotspot file, flag the following anti-patterns:

| Anti-Pattern | Characteristics | Severity |
|--------------|-----------------|----------|
| **Add then immediately fix** | Code added in a feat commit is modified in the very next fix | High |
| **Incremental condition appending** | Initial implementation lacks boundary handling; subsequent fixes add if/else one by one | High |
| **Repeated style adjustments** | The same element's className/style is modified multiple times | Medium |
| **Logic reversal** | Logic A is added, then later removed and replaced with B | High |
| **Defensive patching** | Guards added for a specific scenario only (e.g., `if (isPC) return`) | Medium |
| **State management oscillation** | State variables added, removed, changed repeatedly | High |

### 2.3 Output Evolution Analysis

For each hotspot file:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 {file_path}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Modifications: {N} times ({commit_list})

Evolution chain:
  1. {commit_hash} feat: {description} — initial implementation
  2. {commit_hash} fix: {description} — {patch analysis}
  3. {commit_hash} fix: {description} — {patch analysis}

Detected anti-patterns:
  🔴 {anti-pattern name}: {specific description}
  🟡 {anti-pattern name}: {specific description}
```

---

## Phase 3: Comprehensive Assessment

### 3.1 Patch Accumulation Score

Provide an overall score based on Phase 2 findings:

| Score | Verdict | Recommendation |
|-------|---------|----------------|
| 🟢 Low (0–2 Medium) | Normal iteration | No refactoring needed; safe to merge |
| 🟡 Medium (1–2 High or 3+ Medium) | Mild patch accumulation | Tidy up before merging, but not a blocker |
| 🔴 High (3+ High) | Severe patch accumulation | Strongly recommend refactoring before merging |

### 3.2 Output Assessment Conclusion

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Patch Accumulation Assessment
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Patch ratio: {fix_count}/{total_count} = {percentage}%
Hotspot files: {N}
Anti-patterns:
  🔴 High: {N}
  🟡 Medium: {N}

Overall score: 🟢/🟡/🔴 {score explanation}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phase 4: Refactoring Plan (triggered only for 🟡/🔴)

### 4.1 Generate Refactoring Plan

For each hotspot file requiring refactoring:

1. **Read the file's current final state** (via `Read` tool)
2. **Compare against "what would the optimal implementation look like if written from scratch"**
3. **List specific refactoring items**:
   - Which guards/conditions can be merged or moved to a more appropriate location
   - Which state logic can be simplified
   - Which styles/classNames can be consolidated
   - Which scattered logic can be extracted into functions/hooks

Output format:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛠️ Refactoring Plan
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 {file_path}
  Problem: {specific issues left by patches}
  Plan: {refactoring approach}
  Expected outcome: {result after refactoring}

📄 {file_path}
  Problem: {specific issues left by patches}
  Plan: {refactoring approach}
  Expected outcome: {result after refactoring}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 4.2 Confirmation Gate ⛔

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏸️ Confirmation Gate
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The refactoring plan above requires confirmation before execution.
Please reply:
  "refactor"        — execute everything
  "refactor {file}" — refactor only the specified file
  "skip"            — skip refactoring, keep as-is
⛔ No code will be modified until confirmation is received.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 4.3 Execute Refactoring

After receiving confirmation:

1. **Refactor file by file** — after each file:
   - Run `pnpm type-check` to confirm no type errors
   - Take a browser screenshot to verify no UI regressions (for visual components)
2. **Commit a single consolidating commit after all refactoring is done**:
   ```
   refactor({scope}): consolidate {N} patches into optimal implementation
   ```
3. **Output comparison summary**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Refactoring Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Files refactored: {N}
Line count: {before} → {after} ({diff})
Anti-patterns eliminated: {N}
Commit: {hash} {message}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Optional Parameters

| Parameter | Description |
|-----------|-------------|
| `--report-only` | Output analysis report only; do not generate a refactoring plan |
| `--auto-refactor` | Skip the confirmation gate and execute refactoring immediately |
| `--file <path>` | Analyze patch history for the specified file only |
| `--since <date>` | Analyze only commits after the specified date (default: entire branch) |

---

## Relationship to Other Skills

| Skill | Relationship |
|-------|-------------|
| `/quality-scan` | Checks code style violations; patch-audit checks commit evolution quality |
| `/enh-review` | Manages long-term technical debt; patch-audit focuses on short-term patches in the current branch |
| `simplify` | General code simplification; patch-audit performs targeted consolidation based on git history |

---

## Notes

- **Do not modify git history**: No rebasing/squashing of existing commits; only append a final refactor commit
- **Preserve external behavior**: Refactoring only changes internal implementation, not external behavior
- **Respect Figma-aligned UI**: Do not touch UI structure already aligned to Figma; only clean up logic and state
- **Respect file limits**: No more than 3 files per refactoring pass (per CLAUDE.md rules); split into batches if exceeded
