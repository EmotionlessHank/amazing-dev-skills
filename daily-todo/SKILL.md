---
name: daily-todo
description: Daily to-do management. Triggers when the user says "/daily-todo", "today's tasks", "add tasks for today", "update todo", "daily todo", or "todo". Supports task entry, CRUD operations, status updates, and archiving, with optional sync to macOS Reminders.app.
version: 1.0.0
---

# /daily-todo — Daily To-Do Management

A semi-automated, user-triggered daily to-do list management workflow. Supports task entry, CRUD operations, status sync, and automatic archiving.

---

## Trigger Conditions

Activate on any of the following keywords:
- `/daily-todo`
- `today's tasks`, `add tasks for today`, `update todo`, `todo`
- `daily todo`, `update todo`

---

## Core Files

| File | Purpose |
|------|---------|
| `.progress/REMINDERS.md` | Active to-dos (today's + future undone tasks) |
| `.progress/archive/reminders/{YYYY-MM}.md` | Completed tasks archived by month |

---

## Execution Steps

### Mode A: Daily Entry (first call of the day / new day)

When the user invokes this skill at the start of a day and describes their plans:

#### Step 1: Read Current State

Read `.progress/REMINDERS.md` and check:
- Whether there are uncompleted tasks from yesterday or earlier (decide whether to carry them forward)
- Whether a section for today already exists

#### Step 2: Parse User Input

Extract the following from the user's natural language description:
- **Task title**: concise summary (max 20 characters)
- **Priority**: `High` / `Medium` / `Low` (inferred from tone and context)
- **Sub-items**: key details, one line each
- **Date assignment**: determine whether the task belongs to today, tomorrow, or another date

**Date inference rules**:
- "do today", "today", no time qualifier → current date
- "tomorrow", "next week" → corresponding absolute date
- "this week", "before the weekend" → convert to a specific deadline
- When date cannot be determined, ask the user

#### Step 3: Update REMINDERS.md

Write entries under `## Daily Work Reminders`, organized by date section:

```markdown
### {YYYY-MM-DD}

- [ ] **{task title}** `{priority}`
  - {sub-item 1}
  - {sub-item 2}
```

**Ordering rules**: date sections in reverse chronological order (newest on top); within the same day, ordered by priority (High > Medium > Low).

#### Step 4: Output Confirmation

Output the recorded tasks in a concise table for the user to review:

```
To-dos recorded for {YYYY-MM-DD}:

| # | Task | Priority |
|---|------|----------|
| 1 | ... | High |
| 2 | ... | Medium |

{N} item(s) total. Say what you'd like to change.
```

#### Step 5: Reminders.app Sync Prompt

Prompt the user to decide whether to sync to system reminders:

> Want to sync to Reminders.app? Say "write reminders" and I'll use AppleScript to bulk-create them in the Work list.

If confirmed, use AppleScript to create them in bulk:

```bash
osascript -e '
tell application "Reminders"
    if not (exists list "Work") then
        make new list with properties {name:"Work"}
    end if
    tell list "Work"
        make new reminder with properties {name:"{task title}", body:"{notes}", due date:date "{YYYY-MM-DD}", priority:{0|1|5|9}}
    end tell
end tell'
```

**Priority mapping**: High → 1, Medium → 5, Low → 9

---

### Mode B: CRUD Operations (subsequent calls)

When the user invokes this skill again on the same day, or issues update commands within the conversation:

#### Add a Task
- User says "add XX" → append to today's section
- Update REMINDERS.md accordingly

#### Complete a Task
- User says "XX is done" or "number 2 is complete" → change `- [ ]` to `- [x]` and note the completion time
- Trigger archiving check (see Mode C)

#### Delete a Task
- User says "drop XX" or "remove number 3" → delete from REMINDERS.md
- If already synced to Reminders.app, prompt the user to delete it manually (AppleScript deletion requires exact matching and carries higher risk)

#### Modify a Task
- User says "change XX to YY" or "lower the priority of number 1" → update in place

#### View Tasks
- User says "what's left today" or "show my todo list" → read REMINDERS.md and output today's incomplete items

**After every CRUD operation**, you must:
1. Update `.progress/REMINDERS.md` immediately
2. Output the latest state after the operation

---

### Mode C: Archiving

#### Trigger Conditions
- A task is marked as complete
- A new day begins before entering new tasks (auto-clean the previous day's completed items)

#### Archiving Process

1. Find all `- [x]` completed tasks in REMINDERS.md
2. Write them to `.progress/archive/reminders/{YYYY-MM}.md` organized by completion month
3. Remove the archived tasks from REMINDERS.md
4. If all tasks under a date section have been archived, remove the empty section

#### Archive File Format

```markdown
# Completed To-Dos Archive — {YYYY-MM}

## {YYYY-MM-DD}

- [x] **{task title}** `{priority}` (completed at {HH:MM})
  - {sub-item}
```

---

## Handling Leftover Tasks

When a new day begins and REMINDERS.md contains **uncompleted tasks from the previous day or earlier**:

1. List all leftover tasks
2. Ask the user to handle each one:
   - **Carry forward to today**: move to today's section
   - **Defer to a specific date**: move to the corresponding section
   - **Drop it**: remove entirely (not archived)
3. Silent ignoring is not allowed — the user must make a decision for each item

---

## REMINDERS.md Structure Specification

```markdown
# Reminders — Daily To-Do Tracker

> Maintenance rules (keep unchanged)

---

## Daily Work Reminders

### {latest date}

- [ ] **Task A** `High`
  - Details
- [ ] **Task B** `Medium`

### {earlier date}

- [ ] **Leftover task** `High`

---

## Ongoing Follow-ups

(Non-daily tasks; long-term tracking items)

---
```

**Key constraints**:
- Under `## Daily Work Reminders`, keep only **active, uncompleted** tasks
- Completed tasks are removed from this section after archiving
- `## Ongoing Follow-ups` retains long-term items and is not subject to daily archiving

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| User does not specify priority | Infer from tone; research tasks default to Medium, development tasks default to High |
| User describes tasks spanning multiple days | Split into corresponding date sections |
| Task not completed by end of day | Trigger leftover task handling on next invocation |
| REMINDERS.md does not exist | Create a new file following the structure specification |
| Archive month file does not exist | Create automatically |
| User says "all done" | Mark all of today's tasks as complete and archive them |
| Invoked multiple times on the same day | Treat as Mode B (CRUD); do not create duplicate date sections |
