# Weekly Sync — Weekly Work Summary Report Generator

Generates a weekly work summary report for product managers, formatted for Lark messaging. Triggers when the user says "/weekly-sync", "weekly sync", "weekly report", "work summary", or "sync report".

## Execution Steps

### Step 1: Determine Time Range

- Get the current date and calculate the date ranges for "last Monday ~ last Sunday" and "this Monday ~ today"
- If the user specifies a custom range, use that instead

### Step 2: Collect Git Data

Run against all branches (including worktrees):

```bash
# Last week's commits
git log --all --after="{last Monday}" --before="{this Monday}" --format="%h %ad %s" --date=short

# This week's commits
git log --all --after="{last Sunday}" --format="%h %ad %s" --date=short
```

### Step 3: Analyze and Categorize

Group commits into the following categories (not all categories need to appear — include only what's relevant):

- Web3 / on-chain features
- UI implementation
- Infrastructure (i18n, deployment, CI/CD, dev tooling, etc.)
- API / data layer
- Bug fixes
- Other

**Categorization principles**:
- Consolidate related items: multiple commits for the same feature become a single description
- Use business language rather than raw commit messages — product managers should be able to understand it
- Emphasize delivered outcomes ("completed", "shipped") rather than implementation details

### Step 4: Request User Input

After generating the first draft, confirm with the user:

1. **This week's work plan**: AI cannot automatically retrieve planned items — ask the user to fill in this week's to-dos and estimated completion dates
2. **External support needed**: any items requiring help from product, backend, or design
3. **Content corrections**: any missing or incorrect items in last week's summary (e.g., non-code work such as domain configuration or alignment meetings)

### Step 5: Generate Final Report

Output in the following fixed format, ready to paste directly into Lark:

```
Frontend — Hank

I. Last Week's Work

1. {Topic A}
   - Item 1
   - Item 2

2. {Topic B}
   - Item 1

II. This Week's Plan

- Item 1 (estimated completion date)
- Item 2 (estimated completion date)
- Item 3 (ongoing)

> Note: {blocker description, if any}

III. External Support Needed

- {support item and reason}
```

## Format Constraints

- **No tables**: Lark's message input does not render tables well; use unordered lists throughout
- **No emojis**: keep it professional and clean
- **Language**: English
- **Length**: 2–5 bullet points per topic; the entire report should be readable in one screen
- **Bold**: use only for section headings (I, II, III + topic numbers); no bold in body text
