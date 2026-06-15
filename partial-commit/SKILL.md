---
allowed-tools: Bash(git *), Bash(pnpm type-check*), Bash(pnpm test*), Bash(pnpm lint*)
description: Partial commit — commit only changes made in the current session, leaving other tabs' modifications untouched
---

# Partial Commit — Session-Scoped Commit

Commit only the changes produced in the current session, excluding modifications from other parallel tabs.

## Step 1: Extract Initial Dirty Files

From the `gitStatus:` system message at the start of this conversation, extract the list of dirty files (modified / untracked / deleted) that existed when the session began.
Record this as `INITIAL_DIRTY`.

If the Status in gitStatus was clean at session start, then `INITIAL_DIRTY = []`.

## Step 2: Get Current State

Run `git status --porcelain` and `git diff --name-only` to get all currently dirty files.
Record this as `CURRENT_DIRTY`.

## Step 3: Classify

Review the current conversation history and identify which files were modified using the Write / Edit / Bash(sed/awk/cp/mv) tools. Record these as `SESSION_EDITED`.

Classify each file in `CURRENT_DIRTY` into one of three categories:

| Condition | Classification | Marker |
|-----------|---------------|--------|
| Not in INITIAL_DIRTY | Changed in this session | ✅ |
| In INITIAL_DIRTY **and** in SESSION_EDITED | Uncertain — needs confirmation | ⚠️ |
| In INITIAL_DIRTY **and not in** SESSION_EDITED | Changed by another tab | 🚫 |

## Step 4: Display and Confirm

Show the classification to the user:

```
✅ Changed in this session (will be committed):
  M  app/[locale]/not-found.tsx
  A  app/[locale]/[...rest]/page.tsx

⚠️ Uncertain (dirty before session + also edited this session — confirm inclusion):
  M  components/ui/Button.tsx

🚫 Changed by another tab (will not be committed):
  M  components/referral/ReferralPage.tsx
```

Wait for the user to confirm the final commit scope. The user may:
- Approve as-is
- Request to include or exclude specific files
- Cancel the commit

**Do not run `git add` or `git commit` without explicit user confirmation.**

## Step 5: Commit

Once the user confirms:

1. Run `git diff -- <files>` to review the exact changes being committed
2. Run `git log --oneline -5` to reference the commit message style
3. Run `git add <file1> <file2> ...` to stage only the confirmed files one by one (never use `git add -A` or `git add .`)
4. Generate a commit message and commit

## Constraints

- Commit messages must be in English; Co-Authored-By is not required
- Run type-check before committing to confirm there are no type errors (lint/test run automatically via pre-commit hook)
- If both ✅ and ⚠️ are empty (no new changes this session), inform the user "No new changes to commit in this session" and perform no git operations
