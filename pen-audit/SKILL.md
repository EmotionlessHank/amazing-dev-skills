---
name: pen-audit
description: Deterministic lint gate for Pencil design file structure. Detects absolute-positioning regressions, text overflow, component boundary violations, ghost nodes, and other structural errors using machine-checkable rules. Outputs an actionable audit report. Triggers on "design review", "design audit", "pen audit", "prototype review", "lint design", "check design".
---

# Pencil Design File Audit (pen-audit)

Replaces "eyeballing screenshots to see if the prototype looks right" with **deterministic, machine-checkable lint rules**. This is the first gate check in the `/pen2swift` pipeline — a design file that doesn't pass lint does not proceed to SwiftUI implementation.

## Applicable Files

- Design file: `design/pen/health-ai.pen`
- Component library node: `r2f7P` (Component Library, 53 components; registry at `design/briefs/component-library.md`)
- Use only `pencil` MCP tools to read .pen files. **Never** use Read/Grep on .pen files (they are encrypted).

## Core Diagnostic Model

A healthy screen = **components (ref) + flexbox (vertical/horizontal) + fill_container/fit_content + padding tokens**.
A diseased screen = **absolute positioning (layout:none) + hard-coded x/y + zero component refs**. The latter makes overflow, misalignment, and inconsistency structurally inevitable — no per-screen manual fix can keep up. The screen must be redrawn, not patched.

## Execution Steps

### 1. Full Overflow Scan (deterministic, single call)
```
snapshot_layout(filePath, problemsOnly=true, maxDepth=14)
```
Returns all `partially clipped` / `fully clipped` nodes. Record each node's id, width, x, and parent screen.

### 2. Per-Section Structure Read
```
batch_get(filePath, parentId=<each US group>, readDepth=2)
```
Check each screen frame for `layout` mode and whether child nodes contain `ref` references.

### 3. Run 5 Lint Rules

| # | Rule | Detection method | Verdict |
|---|------|-----------------|---------|
| **L1** | Absolute positioning regression | Screen **content frame** (not the phone shell) has `layout:"none"` AND `ref` ratio in subtree < 30% | 🔴 **REBUILD** (redraw, do not patch) |
| **L2** | Overflow / clipping | Step 1 `problemsOnly` result is non-empty | 🟡 Fix node by node |
| **L3** | Non-wrapping text overflow | `text` node has no `textGrowth` (default: auto) AND rendered width > parent container width | 🟡 Set `textGrowth:"fixed-width"` + `width:"fill_container"` |
| **L4** | Component boundary violation | Child node (including ref) width > parent container width (e.g. StatusBar 390 stuffed into a 375-pt screen) | 🟡 Set ref `width:"fill_container"` |
| **L5** | Ghost nodes | Node is off-canvas (x ≤ -100 or width=0/height=0) AND `fully clipped` | 🟡 Delete dead node |
| **L6** | Non-wrapping chip/tag cloud | Variable-count horizontal chip/tag/badge/filter groups are **single-row** and may overflow (or are already clipped) | 🟡 Convert to multi-line wrap container, name with `*-wrap` suffix (SwiftUI: FlowLayout). See [[feedback_ui_dynamic_wrap]] |

> L1 `ref` ratio threshold: < 30% on an interactive content screen is diseased. Pure display/illustration screens may be exempted, but the reason must be documented in the report ("no-silent-exemption" principle: exemptions must be explicitly recorded).

### 4. Output Audit Report

List findings by section. For each section provide: drawing method (components + flex / absolute positioning) · verdict (🟢/🟡/🔴) · rules triggered · node inventory.

**Fix priority rule**: L1 (rebuild) first, then L3/L4/L5 (bulk mechanical fixes). Do not fix L2/L3 on an L1-diseased screen — those issues disappear automatically after the screen is redrawn.

## Mandatory Checks (health app specific, layered on top of structural lint)

When reading component instances, additionally verify (violation = immediate 🔴):
- `Lib/AllergenBanner` has exactly three states: Hit / CannotConfirm / NoMatch — **no Safe state**
- `Org/EDModeView` / ED variants contain **no kcal figures whatsoever**
- `Lib/CrisisResourceCard` fill is always `$mint`, not red/not warn
- `Org/ChatThread` has the AI disclaimer banner sticky at the top
- Any component with nutritional data must include a `Lib/SourceChip` attribution label

## Rebuild Guidelines (when L1 is triggered)

This is not about fixing coordinates — it's a Component-First rebuild per `design-hifi.md`:
1. Check `r2f7P` for an existing matching component → if missing, add the component/state first
2. Screens use `layout:"vertical"`, sections use `fill_container` + a consistent `padding` token
3. Use `ref` references throughout; no bare rectangle+text elements placed by hand
4. After rebuilding, rerun this skill — the result must be all-green before the task is done

## Completion Criteria

- `snapshot_layout problemsOnly` is empty (or only contains explicitly exempted items)
- No L1-diseased screens
- All mandatory checks pass
- Report written to `docs/impl/phase1/` (or current phase directory) for audit trail
