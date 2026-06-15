---
name: today-summary
description: Generate a concise summary of today's commits with one command. Triggers when the user says "/today-summary", "today's summary", "today's commit summary", or "today summary". Scans all commits to the main branch made today and outputs a clean, tightly formatted summary in the user's writing style.
user_invocable: true
---

# Today Summary — Daily Commit Summary

## Trigger Conditions

User says `/today-summary`, "today's summary", "today's commit summary", or "today summary".

## Execution Flow

1. Run `git log --oneline --since="$(date +%Y-%m-%d) 00:00:00" main` to get all of today's commits on main
2. If there are more than 5 commits, use `git show <hash> --stat --format="%s%n%b"` to fetch details for each commit
3. Output the summary following the style guidelines below

## Style Guidelines (strictly enforced)

Mimic the user's writing style with the following characteristics:

- **One item per line**, each starting with `- `
- **Group by functional area**, consolidating related changes into one entry, joined by semicolons `;`
- **Omit the subject** — write action + object directly
- **English throughout**; keep technical terms as-is (H5/PC/Sentry/FAB/WAAPI, etc.)
- **No commit hashes**
- **No file paths**
- **No timestamps**
- **Maximum conciseness**: use one word where one word will do

### Good examples

```
- H5/PC betting animations: flying chips, FAB bounce, panel pulse, BetCard enter/exit transitions
- Navbar: show avatar + dropdown arrow after login instead of hamburger icon; fix user menu frosted glass opacity regression
- Sentry: filter out wallet injection script noise to reduce false alerts
```

### Bad examples (avoid these)

```
- `5b3e53e` fix(sentry): filter wallet injection script noise   ← no hashes
- Fixed opacity in components/wallet/UserAvatarDropdown.tsx   ← no file paths
- 2026-04-04 13:15 committed Sentry filter   ← no timestamps
- I completed the full betting animation implementation today   ← no subject "I"
```

## Merge Rules

- Multiple commits in the same functional area merge into one entry (e.g., 3 betslip fixes → fold into the betting animation entry)
- Infrastructure items (Sentry/CI/config) get their own entry
- UI fixes related to a feature get folded into that feature's entry; standalone fixes get their own entry

## Output Format

Output the summary directly — no title, no preamble, no "here is the summary" filler. The user should be able to copy it immediately.

If there are no commits today, output: `No new commits to main today.`
