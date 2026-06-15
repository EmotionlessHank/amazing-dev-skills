---
name: figma-impl
description: Enforced pixel-perfect Figma implementation workflow. Triggers on "/figma-impl", "implement from Figma", "Figma pixel-perfect", "Figma adaptation". Elevates the 6-step SOP from LESSONS §14 from a reference document into a structured enforced process with gate checks at every step, eliminating rework caused by skipping steps.
version: 1.0.0
---

# /figma-impl — Pixel-Perfect Figma Implementation

Elevates the 6-step SOP from LESSONS §14 from "advisory document" to "enforced process". Each step has a gate check — you cannot proceed to the next step until the current one is complete.

**Design rationale**: Historical data shows fix-commit rates > 50% on Figma implementation tasks (swap-figma 50%, betslip 78%). The root cause is AI skipping screenshot capture and visual comparison steps. This skill eliminates step-skipping through a structured gate-controlled workflow.

---

## Inputs

Collect the following from the user (ask if missing):

| Parameter | Required | Description |
|-----------|----------|-------------|
| Figma node ID or link | Yes | The design node to implement |
| Target file path | No | Component file to modify/create (can be determined after Step 1) |
| Implementation scope | No | Single component / full page (default: single component; full page auto-splits) |

---

## Full-Page Split Rules (Mandatory)

If the user provides a full-page node (not a single component), **split it into a component list first**, then run through the full Cycle for each one individually.

```
Full-page node
  → Use get_metadata to identify sub-component boundaries
  → Split into N independent components/sections
  → List implementation order (top-to-bottom, outer-to-inner)
  → User confirms the split plan
  → Run the 6-step Cycle below for each component
```

**Prohibited**: Implementing the entire page at once and only then comparing screenshots.

---

## 6-Step Cycle (Run once per component/section)

### Step 1: Node Confirmation ⛔ Gate

```
Actions:
  1. Call get_metadata({nodeId}) to inspect node hierarchy
  2. Confirm the node is the outermost container (Modal → overlay layer, Card → outermost frame)
  3. If the user gave a child node → proactively find its parent container and inform the user

Gate condition: Node granularity must be confirmed before continuing
Output: "Node confirmed: {nodeId} — {node name} ({hierarchy position})"
```

### Step 2: Fetch Design Data ⛔ Gate

```
Actions:
  Call get_design_context({
    nodeId: "...",
    forceCode: true,
    clientLanguages: "typescript,css",
    clientFrameworks: "react,next.js,tailwindcss",
    artifactType: "COMPONENT_WITHIN_A_WEB_PAGE_OR_APP_SCREEN"
  })

Gate condition: forceCode: true must be passed (the hook also checks for this)
Output: Save the returned structured code; flag all localhost asset URLs
```

### Step 3: Capture Visual Baseline ⛔ Hard Block Gate (Most Critical)

```
Actions:
  Call get_screenshot({nodeId}) to capture the Figma screenshot

Gate condition: Screenshot must be successfully captured and saved
  - Save path: .screenshots/figma-{nodeId}-baseline.png
  - On failure: retry once; if still failing, pause and notify the user

Output: "Visual baseline captured: .screenshots/figma-{nodeId}-baseline.png"

⛔ This is a hard block: implementing without a visual baseline = coding blind. Do not proceed.
```

### Step 4: Asset Handling

```
Actions:
  1. Scan all http://localhost:3845/assets/ URLs in the Step 2 code output
  2. Classify and handle each by the following rules:

  A. Generic UI icons (menu / arrow / search / close / settings / etc.):
     → Do NOT download the SVG
     → Find the corresponding icon in @phosphor-icons/react (must include the Icon suffix)
     → If not found in Phosphor → immediately notify the user and wait for instructions

  B. Brand / custom icons (Logo / tokens / event-specific icons / etc.):
     → curl download to the appropriate subdirectory under public/
     → Extract custom SVG icons as components/icons/XxxIcon.tsx

  C. Ambiguous icons:
     → List screenshots/descriptions of each icon and ask the user whether it falls under A or B

Output: Asset handling inventory (each item labeled: Phosphor / downloaded / pending confirmation)
```

### Step 5: Implement Code

```
Actions:
  1. Transcribe exact pixel values from MCP output (do not substitute Tailwind semantic classes):
     - gap-[32px] → write gap-[32px], NOT gap-8
     - p-[40px] → write p-[40px], NOT p-10
     - rounded-bl-[16px] → write rounded-bl-[16px], NOT rounded-l-2xl
     Only exception: an exact matching Design Token exists in tailwind.config.ts

  2. Color handling:
     - Has a var(--xxx) → use the corresponding Design Token
     - Bare hex/rgba (Figma hard-coded) → write raw value + @figma-hardcoded comment
     - Do NOT create new tokens on your own

  3. Effect properties (opacity / blur / shadow / gradient):
     - First grep the project for existing implementations of the same effect type
     - Adapt using existing project parameters as the baseline; do not copy Figma values directly
     - Must account for the actual rendering environment

  4. File modification limit: no more than 3 files per pass

Output: Implemented code (already passed PostToolUse type-check hook)
```

### Step 6: Visual Acceptance ⛔ Delivery Gate

```
Actions:
  1. Open the implementation in a browser
  2. Take a screenshot of the current implementation: browser_take_screenshot or chrome-devtools take_screenshot
     - Save to: .screenshots/impl-{component}-current.png
  3. Compare against the Figma baseline screenshot from Step 3:

  Comparison checklist:
  □ Overall layout structure (element arrangement / hierarchy)
  □ Spacing (padding / margin / gap)
  □ Colors (text / background / border)
  □ Border radius
  □ Font size / font weight
  □ Icons (correctness / size / color)
  □ Effects (shadow / blur / gradient)

  4. Handling discrepancies:
     - Discrepancy found → fix immediately → re-screenshot → compare again
     - Maximum 3 correction rounds per component; if still not matching after 3 rounds, pause and report to the user
     - No discrepancies → proceed to delivery

Gate condition: Implementation screenshot must have no visible deviation from the Figma baseline
Output:
  "✅ Visual acceptance passed: {component_name}
   Figma baseline: .screenshots/figma-{nodeId}-baseline.png
   Implementation: .screenshots/impl-{component}-current.png"
```

---

## After Each Cycle

```
1. Clean up screenshots:
   - Screenshots that have passed acceptance can be deleted (to save space)
   - Or keep them until the entire task is complete, then clean up all at once

2. If in full-page split mode:
   - Mark the current component as ✅
   - Output progress: "Completed {M}/{N} components"
   - Automatically start the Cycle for the next component

3. If in single-component mode:
   - Task complete
```

---

## Overall Task Completion Summary

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Figma Implementation Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Components: {N}
Files modified: {files list}
Correction rounds: {total rounds} (target: <= 1 round/component)
Steps skipped: 0 (guaranteed by enforced workflow)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Optional Flags

| Flag | Description |
|------|-------------|
| `--pc-only` | Implement PC (≥768px) only, skip mobile |
| `--h5-only` | Implement mobile (<768px) only, skip PC |
| `--skip-effects` | Skip effect properties (shadow/blur/gradient) for separate handling later |
| `--dry-run` | Run Steps 1–4 only (analysis + assets), do not write code |

---

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| get_design_context output is truncated | Check that forceCode: true was passed; if still truncated, split into sub-nodes and fetch in segments |
| get_screenshot fails | Retry once; if still failing, ask the user to provide a screenshot manually |
| Invalid Figma node ID | Ask the user to confirm the node ID; offer get_metadata to help locate it |
| Implementation screenshot diverges too much from Figma | After 3 correction rounds with no match → pause, output a diff list, await user instructions |
| Browser not running | Prompt the user to start the dev server (pnpm dev) and open a browser |
| Effect properties don't match in the actual environment | Prioritize existing project parameters for the same effect type; document the adaptation rationale |

---

## Integration with Other Infrastructure

| Infrastructure | Integration |
|----------------|------------|
| `figma-checkpoint.sh` Hook | The hook reminds to take a screenshot after get_design_context; this skill enforces it in the workflow |
| `type-check.sh` Hook | Automatically triggers type checking after code is written in Step 5 |
| `/patch-audit` Skill | Use patch-audit after implementation to check for patch accumulation |
| `/quality-scan` Skill | Use quality-scan after implementation to check code standards |
| LESSONS §14 | This skill is the executable form of §14; the rules are consistent |

---

## Anti-Pattern Warnings (Historical Lessons)

The following behaviors caused > 50% rework rates in past sessions. This skill structurally prevents them through gate checks:

| Anti-pattern | Historical consequence | How this skill prevents it |
|-------------|----------------------|--------------------------|
| Implementing without a screenshot | swap-figma: 10 fix commits | Step 3 hard block |
| Comparing only after full-page implementation | Accumulated discrepancies hard to isolate | Full page is forced to split into per-component cycles |
| Using approximate Tailwind semantic classes | Spacing/radius deviations throughout | Step 5 transcription rules |
| Ignoring localhost asset URLs | Components missing icons/images | Step 4 mandatory asset handling |
| Copying effect properties directly from Figma | Frosted glass/shadow invisible in actual environment | Step 5 environment adaptation workflow |
| Using Phosphor icons for custom brand icons | User repeatedly corrects it | Step 4 classification rules + ask when uncertain |
