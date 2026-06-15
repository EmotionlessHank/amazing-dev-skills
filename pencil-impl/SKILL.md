---
name: pencil-impl
description: Enforced pixel-perfect implementation workflow for Pencil design files. Triggers on "/pencil-impl", "restore design", "implement from design", "pixel-perfect", "design implementation", or "pen restore". Converts .pen design files into Vue code via a 6-step SOP with gate checks at every step, eliminating rework caused by skipping steps.
version: 1.0.0
---

# /pencil-impl — Pixel-Perfect Pencil Design Implementation

Converts .pen design files into Vue code through a structured workflow. Each step has a gate check — you cannot proceed to the next step until the current one is complete.

**Design rationale**: Skipping screenshot capture and visual comparison is the leading root cause of rework in design implementation tasks. This skill eliminates step-skipping through a structured gate-controlled workflow.

**Core principle**: .pen files are encrypted. They must be read and written exclusively through Pencil MCP tools. Never use Read/Grep directly on .pen files.

---

## Inputs

Collect the following from the user (ask if missing):

| Parameter | Required | Description |
|-----------|----------|-------------|
| .pen file path | Yes | Design file under the `UIUX/` directory (e.g. `UIUX/pricing-page.pen`) |
| Target node name or ID | No | The specific Frame/component to implement (if omitted, list top-level nodes for selection) |
| Target file path | No | Vue component file to modify/create (can be determined after Step 1) |
| Implementation scope | No | Single component / full page (default: single component; full page auto-splits into components) |

---

## Pre-flight Actions (Mandatory)

Before starting implementation, you must:

1. Read `.progress/rewind-docs/LESSONS.md` and find sections relevant to the current task
2. Read `.progress/dev-docs/research/RES-000-reusable-assets.md` to understand existing reusable assets in the project
3. Read `UIUX/README.md` and `UIUX/DESIGN-PRACTICES.md` to understand design conventions

---

## Full-Page Split Rules (Mandatory)

If the user provides a full-page node (not a single component), **split it into a component list first**, then run through the full Cycle for each one individually.

```
Full-page node
  → Use batch_get to identify sub-component boundaries (readDepth: 2)
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
  1. Call batch_get({
       filePath: "UIUX/xxx.pen",
       patterns: [{ name: "<user-provided node name>" }],
       readDepth: 2,
       searchDepth: 3
     }) to inspect node hierarchy
  2. If the user did not specify a node, call without patterns first to list top-level nodes
  3. Confirm the node is the outermost container (Page → top-level Frame, Card → outermost frame)
  4. If the user gave a child node → proactively find its parent container and inform the user

Gate condition: Node granularity must be confirmed before continuing
Output: "Node confirmed: {nodeId} — {node name} ({hierarchy position})"
```

### Step 2: Fetch Design Data ⛔ Gate

```
Actions:
  1. Call batch_get({
       filePath: "UIUX/xxx.pen",
       nodeIds: [confirmed nodeId],
       readDepth: 4,
       resolveVariables: true,
       resolveInstances: true
     }) to fetch the full node tree (with variable resolution and component expansion)

  2. Call snapshot_layout({
       filePath: "UIUX/xxx.pen",
       parentId: nodeId,
       maxDepth: 3
     }) to get layout structure (dimensions, positions, spacing)

  3. Call get_variables({
       filePath: "UIUX/xxx.pen"
     }) to get design variables (color, typography tokens, etc.)

  4. If node data is too large (readDepth: 4 returns "..."), fetch child nodes in layers

Gate condition: Must obtain complete node data + layout data + variable data
Output: Save the returned structured data; tag all design tokens and color values
```

### Step 3: Capture Visual Baseline ⛔ Hard Block Gate (Most Critical)

```
Actions:
  Call export_nodes({
    filePath: "UIUX/xxx.pen",
    nodeIds: [nodeId],
    outputDir: ".screenshots",
    format: "png",
    scale: 2
  }) to export design screenshot

  OR call get_screenshot({
    filePath: "UIUX/xxx.pen",
    nodeId: nodeId
  }) for an inline screenshot

Gate condition: Screenshot must be successfully captured
  - Exported screenshot path: .screenshots/{nodeId}.png
  - On failure: retry once; if still failing, pause and notify the user

Output: "Visual baseline captured: .screenshots/{nodeId}.png"

⛔ This is a hard block: implementing without a visual baseline = coding blind. Do not proceed.
```

### Step 4: Design → Code Mapping Analysis

```
Actions:
  1. Analyze the design data from Step 2 and establish mappings:

  A. Color mapping:
     - Design variables ($xxx) → match project CSS variables (var(--color-xxx))
     - Hard-coded color values → check base.scss for corresponding variables
     - No matching variable found → use raw value + /* @design-hardcoded */ comment

  B. Component mapping:
     - Design system components (ref nodes) → match existing Vue components in the project
     - Button → Element Plus ElButton or custom button component
     - Card/Badge/Input → check app/components/ for corresponding components
     - No matching component → flag as needing creation

  C. Icon mapping:
     - icon_font nodes in the design → map to Phosphor icons or custom SVGs
     - Brand/custom icons → export SVG via export_nodes, extract as components/icons/XxxIcon.vue
     - Ambiguous icons → list with descriptions and ask the user

  D. Text mapping:
     - Check whether text content needs i18n handling
     - Hard-coded copy → must be added to en.json / ja.json / zh-TW.json

Output: Mapping inventory (each item labeled: existing component / needs creation / pending confirmation)
```

### Step 5: Implement Code

```
Actions:
  1. Transcribe exact pixel values from design data (preserve design values precisely):
     - Design specifies gap: 32 → write gap-[32px], NOT gap-8
     - Design specifies padding: 40 → write p-[40px], NOT p-10
     - Design specifies borderRadius: [16,16,0,0] → write rounded-t-[16px], NOT rounded-t-2xl
     Only exception: an exact matching Design Token exists in tailwind.config.ts

  2. Color handling:
     - Has a corresponding CSS variable → use var(--color-xxx) or Tailwind class
     - Hard-coded color value → write raw value + /* @design-hardcoded */ comment
     - Do NOT create new CSS variables on your own

  3. Effect properties (opacity / blur / shadow / gradient):
     - First grep the project for existing implementations of the same effect type
     - Adapt using existing project parameters as the baseline; do not copy design values directly
     - Must account for the actual rendering environment

  4. Vue component conventions:
     - Use Composition API (<script setup>)
     - Component names in PascalCase
     - i18n: use const { t } = useI18n(), never $t
     - Routing: use NuxtLink / navigateTo()
     - API calls through app/api/ modules

  5. File modification limit: no more than 3 files per pass

Output: Implemented code
```

### Step 6: Visual Acceptance ⛔ Delivery Gate

```
Actions:
  1. Open the implementation in a browser (dev server should already be running)
  2. Take a screenshot of the current implementation:
     - Use chrome-devtools take_screenshot or playwright browser_take_screenshot
     - Save to: .screenshots/impl-{component}-current.png
  3. Compare against the design baseline screenshot from Step 3:

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

Gate condition: Implementation screenshot must have no visible deviation from the design baseline
Output:
  "Visual acceptance passed: {component_name}
   Design baseline: .screenshots/{nodeId}.png
   Implementation: .screenshots/impl-{component}-current.png"
```

---

## After Each Cycle

```
1. Clean up screenshots:
   - Screenshots that have passed acceptance can be deleted (to save space)
   - Or keep them until the entire task is complete, then clean up all at once

2. If in full-page split mode:
   - Mark the current component as done
   - Output progress: "Completed {M}/{N} components"
   - Automatically start the Cycle for the next component

3. If in single-component mode:
   - Task complete
```

---

## Overall Task Completion Summary

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pencil Design Implementation Complete
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
| `--desktop-only` | Implement desktop only, skip mobile adaptation |
| `--mobile-only` | Implement mobile only |
| `--skip-effects` | Skip effect properties (shadow/blur/gradient) for separate handling later |
| `--skip-i18n` | Skip i18n handling, implement default language only |
| `--dry-run` | Run Steps 1–4 only (analysis + mapping), do not write code |

---

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| batch_get returns "..." for child nodes | Increase readDepth or fetch child nodes by ID in segments |
| export_nodes / get_screenshot fails | Retry once; if still failing, ask the user to confirm the Pencil editor is running |
| Invalid node ID | Use batch_get with patterns to search by node name and relocate |
| Implementation screenshot diverges too much from design | After 3 correction rounds with no match → pause, output a diff list, await user instructions |
| Browser not running | Prompt the user to start the dev server (npm run dev) and open a browser |
| Effect properties don't match in the actual environment | Prioritize existing project parameters for the same effect type; document the adaptation rationale |
| Design variable has no corresponding CSS variable | Use raw value + comment annotation; do not create new variables |

---

## Integration with Project Infrastructure

| Infrastructure | Integration |
|----------------|------------|
| `UIUX/design-system.pen` | Component reuse and color/typography token source |
| `app/assets/css/base.scss` | CSS variable reference table |
| `UIUX/DESIGN-PRACTICES.md` | Pencil operational conventions |
| `/review` Skill | Trigger a code review after implementation is complete |
| `/quality-scan` Skill | Check code standards after implementation is complete |
| `CLAUDE.md` | Authoritative source for architecture conventions and code standards |

---

## Anti-Pattern Warnings

The following behaviors cause significant rework. This skill structurally prevents them through gate checks:

| Anti-pattern | Consequence | How this skill prevents it |
|-------------|-------------|--------------------------|
| Implementing without a screenshot | Coding blind, errors accumulate | Step 3 hard block |
| Comparing only after full-page implementation | Discrepancies are hard to isolate | Full page is forced to split into per-component cycles |
| Using approximate Tailwind semantic classes | Spacing/radius deviations throughout | Step 5 exact pixel transcription rules |
| Hard-coding color values | Inconsistent theming | Step 4 color mapping + Step 5 CSS variable rules |
| Reading .pen files with Read/Grep | Content is encrypted, output is garbled | Entire workflow enforces Pencil MCP tools exclusively |
| Skipping i18n | Copy exists in only one language | Step 4 text mapping check |
| Copying effect properties directly from design values | Inconsistent rendering in the actual environment | Step 5 environment adaptation workflow |
