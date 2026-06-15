---
name: pen2swift
description: Full pipeline for high-fidelity Pencil design → SwiftUI implementation. Gate check (pen-audit) → export reference → generate SwiftUI → XcodeBuild screenshot → visual-verdict comparison → snapshot tests. Closed-loop design fidelity. Triggers on "implement SwiftUI", "pen2swift", "design to code", "implement from design", "implement this screen".
---

# Pencil → SwiftUI High-Fidelity Implementation (pen2swift)

Transforms "implement the design" from manual eyeballing into a **closed-loop visual comparison** workflow. `pen-audit` is the first gate; this skill is the complete pipeline.

## Stack
SwiftUI · iOS 17.4+ · Design file: `design/pen/health-ai.pen` · Tokens: `docs/DESIGN_SYSTEM.md` · XcodeBuildMCP (configured in `.mcp.json` as `xcodebuild`)

## Pipeline (per screen)

### ① Design Gate — `/pen-audit`
The design file must pass audit (L1–L6 all green) before implementation begins. **Screens with absolute positioning, overflow, or non-wrapping elements do not enter SwiftUI** — otherwise you are just translating bugs into code.

### ② Export Reference Truth
- `export_nodes` on screen node → `design/exports/vN/<screen>.png` (pixel reference, not eyeballing)
- `get_variables` → token values (spacing / color / font size) — the ruler for implementation

### ③ Generate SwiftUI (token-driven, not freehand transcription)
- **Token mapping** (see table below): everything goes through `DesignSystem` constants, no hard-coded values
- **Chip / tag clouds** → custom `FlowLayout` via the `Layout` protocol (no built-in wrap; `ViewThatFits` does not wrap). Chips get `.fixedSize()` to prevent internal clipping. See [[feedback_ui_dynamic_wrap]]
- **Any dynamic text** → `.lineLimit` + `.minimumScaleFactor(0.7)` or `.fixedSize(horizontal:false, vertical:true)`
- **Component correspondence**: each Pencil `Lib/*` / `Org/*` maps to one SwiftUI View; the component-first ref relationship maps to View reuse
- **Mandatory rules applied to UI** (see checklist below)

### ④ Build + Screenshot (XcodeBuildMCP)
Device/simulator render — **worst-case matrix**: largest Dynamic Type (`.accessibility5`) × longest locale (de)

### ⑤ Compare & Verdict — `visual-verdict`
SwiftUI screenshot vs ② reference PNG, structured diff list (not "close enough"). Discrepancies → iterate back to ③

### ⑥ Snapshot Test Gate (CI regression)
`pointfreeco/swift-snapshot-testing`: snapshot each component in a `[default, .accessibility5] × [en, de]` matrix; any diff is a regression. Locks down overflow/clipping issues in CI.

### ⑦ Iterate Until visual-verdict Passes + Snapshots Green

## Token → SwiftUI Mapping

| Pencil variable | Value | SwiftUI |
|----------------|-------|---------|
| `$primary` | #FF6B6B | `Color.primaryCoral` (CTA / accent) |
| `$primarySoft` | #FFE8E8 | Selected-state background |
| `$danger` | #FF3B30 | **Only** destructive actions (delete / Clear All) |
| `$warn` / `$warnSoft` | #F5A623 / #FFF3DC | **Exclusive** color for allergy alerts |
| `$surface` / `$surface2` | #FFF / #F2F2F0 | Card / secondary container |
| `$ink` / `$inkMuted` / `$inkSubtle` | #1A1A1A / #6B6B6B / #9A9A95 | Three-tier text hierarchy |
| `$radiusChip` / `$radiusCard` | 10 / 16 | `cornerRadius` |

## Mandatory Rules in the UI Layer (non-negotiable)
- Allergy Banner is **never green / "safe"** — only "may contain" / "cannot confirm" (warn-amber)
- ED Mode View **completely removes kcal figures** (not greyed out — removed)
- Crisis card uses `$mint` warm green, not red / not warn
- AI disclaimer banner is session-level sticky — it is a structural part of the view, not removable
- Any View with nutritional data must include a source label (SourceChip / SourceBadge)
- Nutritional numbers must not be produced directly by the LLM (decompose ingredients → USDA → sum)

## Completion Criteria
- `/pen-audit` all green (design side)
- `visual-verdict` passed (implementation vs reference)
- Worst-case matrix (AX5 × de) has no overflow or clipping
- Snapshot tests green
- No hard-coded colors or spacing (all tokens)
