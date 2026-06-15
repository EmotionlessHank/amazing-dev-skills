---
name: daily-report
description: Generate a daily development report with one command. Triggers when the user says "/daily-report", "daily report", "today's summary", "generate report", or "daily summary". Automatically scans all branch commits across worktrees for the current day, outputs a structured report in a professional format, and archives it to .progress/daily-reports/.
version: 1.0.0
---

# /daily-report — Daily Development Report Generator

Automatically scans all development activity for the day, generates a structured report, and archives it to the project's `.progress/daily-reports/` directory.

---

## Trigger Conditions

Activate on any of the following keywords:
- `/daily-report`
- `daily report`, `today's summary`, `generate report`, `daily summary`

---

## Execution Steps

### Step 1: Data Collection

Run the following git commands in parallel to gather all development activity for the day:

```bash
# 1. Get today's date
DATE=$(date +%Y-%m-%d)

# 2. All commits across all branches today (including worktrees)
git log --all --since="${DATE}T00:00:00" --format="%h %s (%D)" --date=short

# 3. List active worktrees
git worktree list

# 4. Diff stat between each feature branch and main
git diff --stat main...<branch> | tail -3
```

For each active worktree, enter its directory and run the same `git log` command.

### Step 2: Data Analysis

Group the collected commits along the following dimensions:

1. **By branch**: list each feature branch separately
2. **Identify status**:
   - Branch merged into main → `✅ Merged to main`
   - Branch has commits but not yet merged → `🔵 Complete, pending merge` or `🟡 In progress`
   - Branch has review-fix commits → count the number of review rounds
3. **Aggregate stats**: total commit count, total lines changed, number of files touched

### Step 3: Generate Report

Output the report using the following template:

```markdown
# Frontend Daily Report | {YYYY-MM-DD}

## Today's Progress

| # | Feature Module | Status | Notes |
|---|---------------|--------|-------|
| 1 | {module name} | {status marker} | {one-line description} |
| 2 | ... | ... | ... |

## Key Metrics

- Commits: {N} | Lines added/modified: ~{N} | Files touched: {N}
- Code Review: {N} round(s) ({version}), {key fixes}
(Omit this line if no review activity today)

## Commit Details

### {branch name} → {merge status}

| Commit | Description |
|--------|-------------|
| `{hash}` | {commit message} |

(One sub-table per active branch)

## Tomorrow's Plan

- {Infer top priorities from today's 🟡 in-progress tasks}
- {Suggest merging 🔵 pending-merge branches}
- {Other reasonable suggestions}

---

> Status markers: ✅ Done  🔵 Pending merge  🟡 In progress  🔴 Blocked
```

### Step 4: Archive

1. Write the report to `.progress/daily-reports/{YYYY-MM-DD}.md`
2. Update the `.progress/daily-reports/INDEX.md` index by appending an entry for today
3. Output the full report in the conversation so the user can copy it directly

---

## Template Field Rules

| Field | Rule |
|-------|------|
| Feature module name | Extract from the scope in the commit message (e.g., `feat(wallet)` → Wallet Connect Modal); merge commits with the same scope into one row |
| Status marker | ✅ Merged to main / 🔵 Pending merge / 🟡 In progress / 🔴 Blocked |
| Notes | Max 15 words, focus on "what was done" rather than "how it was done" |
| Key metrics | Aggregated from `git diff --stat` and `git log --oneline` |
| Tomorrow's plan | Inferred from today's incomplete items; no more than 3 entries |

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| No commits today | Output "No code commits recorded today" and skip archiving |
| Worktree deleted but branch still exists | Still retrievable via `git log --all`; list normally |
| Cross-midnight development | Use `--since` today 00:00 as the cutoff; do not look back further |
| Multiple authors on one branch | Filter by author; count only the current user's commits |
| User specifies a date | Support `/daily-report 2026-03-15` format; update the DATE variable accordingly |

---

## Output Specification

- Output the full report markdown in the conversation for easy copying
- Display the archive path at the end of the output: `📁 Archived to .progress/daily-reports/{date}.md`
