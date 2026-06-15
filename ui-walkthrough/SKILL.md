---
name: ui-walkthrough
description: UI walkthrough and fix workflow. Triggers on "/ui-walkthrough", "UI walkthrough", "walkthrough fix", "design review", or "UI alignment". Accepts designer screenshots with annotated fix points or Figma links, organizes a fix checklist, waits for user confirmation, then applies fixes item by item.
version: 1.0.0
---

# /ui-walkthrough — UI Walkthrough Fix Workflow

Elevates UI walkthrough from "eyeballing screenshots and guessing what to change" to a structured **analyze → checklist → confirm → fix** workflow. Core principle: **always produce the checklist first; only edit code after user confirmation**.

---

## Trigger Conditions

- User sends designer-annotated screenshots with fix point descriptions
- User sends a Figma link + specifies the area to review
- User says "UI walkthrough", "walkthrough fix", or "design review"

---

## Inputs

| Parameter | Required | Description |
|-----------|----------|-------------|
| Screenshots + fix descriptions | One of these | Designer-annotated screenshots with written fix point descriptions |
| Figma link + area reference | One of these | Figma node link; user specifies the area/component to review |
| Platform scope | No | H5 only / PC only / both (default: inferred from the description) |

---

## Workflow

### Mode A: Screenshot-driven (designer annotations)

```
Step 1 — Analyze screenshots
  ├── Analyze each screenshot's annotations (spacing / color / font size / corner radius / etc.)
  ├── Extract specific CSS properties and target values from the annotations
  └── Note platform scope (H5 / PC / both)

Step 2 — Locate code
  ├── Use Glob/Grep to locate the relevant component files
  ├── Read the files and find the current values for the annotated class/style attributes
  └── Compare annotation target values vs current code values

Step 3 — Output fix checklist (⏸️ Wait for confirmation)
  ├── Group by platform (H5 only / PC+H5 / PC only)
  ├── Table format: Screenshot # | Location | Current → Target | File:Line | Status
  ├── Status labels: Needs fix / ✅ Already correct
  └── Summary at the bottom: N items need fixing across M files; K items already correct

Step 4 — Apply fixes item by item
  ├── After user confirms, apply each Edit per the checklist
  ├── Run type-check after all edits are complete
  └── Report fix results

Step 5 — Commit
  └── Commit after user confirmation
```

### Mode B: Figma link-driven

```
Step 1 — Fetch design data
  ├── Extract node-id from the URL
  ├── Call mcp__figma-desktop__get_metadata to get node structure
  ├── Call mcp__figma-desktop__get_design_context (forceCode: true)
  ├── Call mcp__figma-desktop__get_screenshot for visual reference
  └── Focus on the specific area/component as directed by the user

Step 2 — Code comparison
  ├── Read the corresponding component files
  ├── Compare property by property: spacing / color / font size / corner radius / font weight / etc.
  ├── Map CSS variables to project Design Tokens
  └── Flag all discrepancy items

Step 3 — Output fix checklist (⏸️ Wait for confirmation)
  └── (Same format as Mode A Step 3)

Step 4 — Apply fixes item by item
  └── (Same as Mode A Step 4)

Step 5 — Browser verification (optional)
  ├── Take a screenshot of the current implementation
  ├── Compare against Figma screenshot
  └── Fix any remaining discrepancies on the spot

Step 6 — Commit
  └── Commit after user confirmation
```

---

## Fix Checklist Format (Required)

```markdown
### H5 Only

| # | Screenshot | Location | Current → Target | File:Line | Status |
|---|-----------|----------|-----------------|-----------|--------|
| H1 | #7 | Spacing below Tab group | `mb-[42px]` → H5 `mb-[24px]` | `PoolsPage.tsx:32` | Needs fix |
| H2 | #11 | Stats 2×2 grid spacing | — | — | ✅ Already correct |

### PC + H5
...

### PC Only
...

**Needs fix: N items across M files | Already correct: K items**
```

---

## Constraints

1. **Checklist before code**: Never skip the checklist and edit code directly. User confirmation is required.
2. **List "already correct" items too**: If an annotated target value matches the current code, mark it "✅ Already correct" rather than omitting it — the user needs to know.
3. **Group by platform**: Group fixes by platform scope (H5 only / PC+H5 / PC only) to avoid editing the wrong breakpoint.
4. **Design Token first**: Color values must be mapped to Tokens, not written as raw hex (unless the value is hard-coded in Figma itself — add an `@figma-hardcoded` comment in that case).
5. **File limit per pass**: Aim for ≤ 6 files; split into batches if needed.
6. **type-check must pass**: Run `pnpm type-check` after all edits and ensure it passes.
7. **No scope creep**: Only fix the issues the user pointed out; do not opportunistically change surrounding code.

---

## Success Criteria

- [ ] Every annotated fix point in the screenshots/Figma has been analyzed
- [ ] Fix checklist includes current values, target values, and file locations
- [ ] Changes are only applied after user confirmation
- [ ] type-check passes
- [ ] Modifications strictly match the checklist — no extra changes
