---
name: ui-design-plan
description: UI design plan prompt optimizer. Triggers on "/ui-design-plan", "UI design plan", "design spec plan", "UI design prompt", "create UI plan", or "design plan". Reads the PRD, researches competitors, analyzes the project design system, and outputs a structured UI design plan as a DAG execution schedule.
user_invocable: true
---

# UI Design Plan — UI Design Prompt Optimizer

## Purpose

Transforms a vague "help me create a UI design plan" request into a structured, executable DAG design pipeline.
This skill is a **prompt optimizer** — it does not produce design artifacts directly; it produces a complete plan that can be executed by ultrawork/team.

## Trigger Conditions

User says `/ui-design-plan`, "UI design plan", "design spec plan", "create UI plan", or "design plan".

---

## Execution Workflow

### Phase 0: Requirements Understanding (Must complete first)

1. **Locate the PRD**: Search `documents/需求文档/` for a PRD matching the user's description
2. **Read the PRD**: Extract the following key information:
   - Feature list + priorities
   - Page layout descriptions
   - Element specification tables (display rules / interaction logic / edge cases)
   - Competitor reference URLs (as specified in the PRD)
   - Non-functional requirements (performance / responsiveness / internationalization)
3. **Read linked requirements**: If the PRD references other requirement documents, read those too
4. **If no PRD exists**: Ask the user to provide a requirements description or specify a document path — do not make assumptions

### Phase 1: Competitor List Construction

Based on competitors specified in the PRD plus AI-supplemented same-category competitors, build a list of **approximately 5** competitors:

```markdown
| # | Competitor | URL | Rationale |
|---|------------|-----|-----------|
| 1 | XXX        | ... | Specified in PRD |
| 2 | YYY        | ... | Market leader in the same space; strong at XX feature |
| ...
```

**Principles for selecting supplemental competitors**:
- Prefer same category (e.g. AI video → Pika/Runway/Kling)
- Secondary: same model/pattern (e.g. masonry community → Dribbble/Behance/Pinterest)
- Avoid scope creep; maximum 5–6 total

**Competitor analysis dimensions** (fixed 7 dimensions):

| Dimension | What to extract |
|-----------|----------------|
| 1. Page layout structure | Banner-to-content ratio, hierarchy, visual weight distribution |
| 2. Card visual treatment | Corner radius, spacing, shadows, hover effects, aspect ratio strategy |
| 3. Card information hierarchy | Position, font size, and stacking of tags / user info / action buttons |
| 4. Media preview interaction | Hover-to-play, autoplay, preload strategy |
| 5. CTA area presentation | Background treatment, typography hierarchy, button style, visual appeal |
| 6. State design | Empty / loading / error / skeleton screen handling |
| 7. Responsive strategy | Breakpoints, column count changes, spacing scaling rules |

### Phase 2: Project Design System Analysis

Read the following project files and extract reusable assets:

| File | What to extract |
|------|----------------|
| CSS variable file (e.g. `base.scss`) | Color variables, spacing system, typography system |
| Theme variable file (e.g. `element-variables.scss`) | Component library theme customizations |
| Tailwind config | Breakpoints, extended config, custom values |
| Existing similar components | Visual patterns from card and list components |
| Existing layout implementations | Masonry / grid layout approaches |
| `RES-000-reusable-assets.md` | Existing reusable asset inventory |

> If any of these files don't exist in the project, skip them without error.

### Phase 3: Assemble Output — Structured Design Prompt

Combine the results from Phases 0–2 into a **structured DAG execution plan** using the following format:

```markdown
## {Feature Name} — UI Design Plan

### Background
Based on PRD `{filename}`, a UI design plan is required.

### Execution strategy: `/omc ultrawork` (DAG scheduling)

T1 Competitor research (N competitors, screenshot + analysis in parallel)   ← parallel
T2 Project design system analysis                                            ← parallel with T1
T3 /ui-ux-pro-max generate design direction options                         ← depends on T1+T2
T4 /design-with-claude granular design decisions                            ← depends on T3 confirmation
T5 Output DD design document                                                ← depends on T4
T6 /omc visual-verdict visual QA                                            ← depends on T5 implementation

### T1: Competitor Research (parallel, chrome MCP headless)

{Competitor table}

**Extraction dimensions**: {7-dimension table}

> Screenshots saved to `.screenshots/{feature}-research/`; clean up when done

### T2: Project Design System Analysis (parallel with T1)

{Specific file list and analysis targets extracted from Phase 2}

### T3: Design Direction Generation (depends on T1+T2)

Call `/ui-ux-pro-max`, based on competitor research results + project design system constraints,
generate 2–3 design direction options. Each direction includes:
- Overall visual tone (which elements from which competitors were referenced)
- Color scheme (based on existing project CSS variables)
- Core component style + layout strategy

**→ Wait for human to confirm direction before proceeding to T4**

### T4: Granular Design Decisions (depends on T3 confirmation)

Call `/design-with-claude` to refine the confirmed direction:
1. Page structure: {customized based on PRD page layout descriptions}
2. Core component specifications: {customized based on PRD element spec table}
3. Responsive strategy: column counts + spacing rules per breakpoint
4. State design: {customized based on PRD edge cases}
5. Colors / typography: specific values based on project CSS variables
6. Reusable asset inventory: which existing components can be used or lightly adapted

### T5: Output DD Design Document

Save to `.progress/dev-docs/designs/DD-XXX-{feature}-ui.md`

### T6: Visual QA (depends on implementation)

Call `/omc visual-verdict` — screenshot implementation output vs competitor reference to verify visual quality
```

---

## Key Constraints

1. **Never skip Phase 0**: Do not start building the competitor list without reading the PRD first — the PRD may already specify competitors and layout requirements
2. **Competitor URLs must be real and accessible**: Do not fabricate URLs; verify uncertain ones with chrome MCP headless first
3. **Validate design system file paths**: Confirm files exist with Glob before hardcoding paths
4. **Human confirmation gate at T3**: Do not proceed to granular design before the direction is confirmed — avoids wasted effort from going off-track
5. **Centralize screenshot management**: Save competitor screenshots to `.screenshots/`; remind to clean up when done
6. **Output is a prompt, not a design artifact**: This skill produces an executable plan, not a final design

## Success Criteria

- [ ] PRD key information fully extracted (feature list, page layout, element specs, competitor references)
- [ ] Competitor list has ≥ 3 entries and includes PRD-specified references
- [ ] All 7 extraction dimensions are complete
- [ ] Project design system files are located with specific analysis targets listed
- [ ] DAG dependencies are correct (T1/T2 parallel → T3 → confirmation gate → T4 → T5 → T6)
- [ ] 3 design skills integrated (ui-ux-pro-max / design-with-claude / visual-verdict)
- [ ] Output format is directly executable by `/omc ultrawork`

## When Not to Use This Skill

- Pure style tweaks (just edit the code directly, no design plan needed)
- Design file already exists and only needs implementation (use `/pencil-impl`)
- Single-component design (use `/design-with-claude` directly)
