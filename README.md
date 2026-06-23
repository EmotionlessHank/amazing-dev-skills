# Amazing Dev Skills

A curated library of reusable Claude Code skills for AI-augmented software development — covering the full lifecycle from feature planning and UI implementation to deployment, system maintenance, and reporting.

Inspired by [awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills). Battle-tested in production across Web3, fintech, and mobile projects.

---

## What is this?

Claude Code supports custom **skills** — structured prompt files (`.md`) that define reusable AI behaviors triggered by keywords or slash commands. This repository is a personal collection of such skills, version-controlled for continuous iteration.

Each skill lives in its own directory with a `SKILL.md` (the prompt Claude loads) and, for complex multi-project skills, a `SETUP.md` (a migration guide for adapting the skill to a new codebase).

**Problems this solves:**
- Reinventing the same agentic workflows on every project
- Inconsistent quality from ad-hoc prompting
- No institutional memory across sessions

---

## Quick Start

1. **Clone or copy** the skill directory you want into your project's skills folder (commonly `.claude/skills/` or wherever your Claude Code configuration points)
2. For skills with a `SETUP.md`: follow it to replace `{placeholders}` with your project-specific values
3. Trigger the skill in Claude Code using the keywords listed in each `SKILL.md`

```bash
# Example: copy the autopilot skill into your project
cp -r amazing-dev-skills/autopilot .claude/skills/
# Then edit .claude/skills/autopilot/SKILL.md — replace {placeholders} per SETUP.md
```

---

## Skill Catalog

### Dev Workflow

| Skill | Description |
|-------|-------------|
| [autopilot](./autopilot) | Fully autonomous development pipeline: batched coding → parallel subagent code review → auto-triage of review findings → delivery docs → development summary (fixed template, mandatory before acceptance) → handoff to human QA. Multi-project template with placeholder substitution. |
| [feat](./feat) | Feature planning lifecycle (pairs with autopilot): scope analysis → real codebase research → grill/clarification gate (design-tree interview, embeds `grill-me`) → DD/spec writing → 1–3 agent plan review → confirmation gate → handoff to autopilot. |
| [worktree-dev](./worktree-dev) | Enforces git worktree isolation for every development session: branch creation, env symlinks, directory lock, pre-batch read lists, and agent delegation constraints. |
| [parallel-worktree](./parallel-worktree) | Orchestrates parallel worktree development across multiple agents: task decomposition, file-ownership conflict detection, focused context injection, and merge guidance. Includes Anthropic CCC pattern reference. |
| [partial-commit](./partial-commit) | Commits only the current session's changes, ignoring parallel-tab modifications — by diffing against a session-start git snapshot. |
| [patch-audit](./patch-audit) | Detects patch-on-patch anti-patterns in a feature branch (feat → fix → fix → fix…), scores them, and refactors the commit history into a clean implementation. |

### Feature Planning & Design

| Skill | Description |
|-------|-------------|
| [prd-writing](./prd-writing) | Produces production-grade PRDs using 6 proven PM writing patterns: display+rules dual-column, phase drill-down, table comparison, edge case sections, domain education, and analytics specs. |
| [ui-design-plan](./ui-design-plan) | Transforms a vague "design the UI" request into a structured DAG execution plan: reads PRD, builds a competitor analysis matrix, audits reusable design system assets, and assembles a full design pipeline. |
| [ui-walkthrough](./ui-walkthrough) | Generates a structured UI walkthrough document for a feature, covering user flows, component breakdown, interaction states, and edge cases. |
| [grill-me](./grill-me) | Relentlessly interviews you about a plan or design until every branch of the decision tree is resolved. Use it to stress-test ideas before committing to implementation. (Also embedded as Phase 3.1 of `feat` — use this standalone for non-feat plans.) |

### UI Implementation & Design Fidelity

| Skill | Description |
|-------|-------------|
| [figma-impl](./figma-impl) | Enforces pixel-perfect Figma-to-code fidelity via a 6-step SOP with hard gates: node confirmation → forceCode → screenshot baseline → asset processing → precise transcription → visual acceptance. |
| [pencil-impl](./pencil-impl) | Pixel-perfect implementation from Pencil (.pen) design files to Vue code. 6-step gated SOP adapted for the Pencil MCP toolchain; enforces three-language i18n and CSS variable color mapping. |
| [pen-audit](./pen-audit) | Deterministic lint gate (L1–L6) for Pencil design files: detects absolute-positioning regression, text/component overflow, unwrapped chip clouds, and ghost nodes before code generation. |
| [pen2swift](./pen2swift) | Full pipeline from Pencil design files to SwiftUI: design lint → token-driven code generation → XcodeBuildMCP worst-case screenshot matrix → visual verdict → swift-snapshot-testing CI gate. |
| [page-perf-audit](./page-perf-audit) | Full-chain page performance audit along the Request → TTFB → FCP → TTI → LCP path, across five dimensions. Outputs ROI-ranked optimization recommendations with six common pattern quick-reference. |
| [sync-tokens](./sync-tokens) | Syncs Figma design tokens to project code: copies exported JSON, runs the sync script, generates CSS variables and TypeScript constants, and shows the diff. |

### CI/CD & Quality

| Skill | Description |
|-------|-------------|
| [sentry](./sentry) | Two-mode Sentry integration: **bulk patrol** (fetch unresolved Fatal/Error issues via API, filter by threshold, generate regression test skeletons) and **single-issue diagnosis** (URL → root-cause decision tree → source trace → fix verification). |
| [vercel-build-doctor](./vercel-build-doctor) | Diagnoses and fixes Vercel build failures directly from the Vercel API — no browser scraping, no local reproduction. Triggers on "build failed / deploy error" keywords. |
| [ship](./ship) | Local-CI-gate-then-push: when paid cloud CI is off, a local `pre-push` git hook becomes the single gate (lint → build → test). Standard "green-then-push" front door — gate self-heal (fresh-clone install), guard green, `gh` multi-account-aware push, switch back. Never `--no-verify`. Includes pre-push hook + installer templates. |

### Reporting & Productivity

| Skill | Description |
|-------|-------------|
| [daily-report](./daily-report) | One-command daily dev report: scans all branches and worktrees for today's git commits, groups by module, outputs a structured table, and archives to `.progress/daily-reports/`. |
| [weekly-sync](./weekly-sync) | Generates a weekly work sync for product managers: scans last week's and this week's commits across all branches, summarizes by business dimension, outputs Lark-friendly bullet-list format. |
| [daily-todo](./daily-todo) | Daily task management: parse natural-language plans into structured todos, write to `.progress/REMINDERS.md`, sync to macOS Reminders.app, auto-archive completed items by month. |
| [today-summary](./today-summary) | Quick end-of-day summary: surfaces what was shipped, what's pending, and what's blocked. |
| [project-rules-initialization](./project-rules-initialization) | Initializes a project's AI rules infrastructure: generates common rules, syncs agent rules, sets up multi-agent workflow files, and creates the standard `.progress/` directory structure. |

### Finance & Personal

| Skill | Description |
|-------|-------------|
| [finance-analyze](./finance-analyze) | Parses bank statement PDFs, auto-categorizes transactions, generates categorized summaries and Excel reports, compares against prior period, and flags anomalous changes. |
| [finance-health](./finance-health) | Runs a household finance health check: computes cash flow, emergency fund coverage (months), goal-funding adequacy, and outputs a scored health report card with improvement recommendations. |
| [finance-update](./finance-update) | Updates financial context via natural language: auto-routes edits to the correct YAML file (income / expenses / goals / exchange rates / household info) and handles goal status transitions. |
| [finance-forecast](./finance-forecast) | Projects 6–12-month cash flow from current income/expense data and assumption parameters; flags risk nodes (balance hitting safety threshold, reserve depletion time). |
| [finance-summary](./finance-summary) | One-page household finance snapshot: account balances, monthly spending, active goals, exchange rates, overseas runway — with stale-data warnings. |

### System & Deploy

| Skill | Description |
|-------|-------------|
| [mac-cleanup](./mac-cleanup) | macOS system cleanup audit: scans for long-unused applications, redundant Homebrew/npm/pip packages, system caches, Xcode DerivedData. Outputs a risk-rated report with space estimates; waits for confirmation before deleting. |
| [disk-cleanup](./disk-cleanup) | Developer storage cleanup (complements mac-cleanup, which handles system-level apps). Four-phase process: tiered investigation → per-category safety checks → cleanup → `df` verification. Includes hard-won lessons from worktree orphan detection and Docker sparse-file reclamation. |
| [headless-web-deploy](./headless-web-deploy) | Deploys small web apps (Flask/FastAPI/Node/static) to a domain-less server via Caddy + sslip.io (auto Let's Encrypt), systemd user service, and HMAC token auth. Produces a shareable HTTPS URL. Includes RUNBOOK, Caddyfile, systemd unit, and token auth templates. |
| [back-to-cn-proxy](./back-to-cn-proxy) | One-command deployment of a China-IP reverse proxy (sing-box, Shadowsocks-2022 + Hysteria2) for accessing mainland Chinese apps from abroad via Shadowrocket. Includes deploy script, client config generator, and QR code output. |
| [live-photo](./live-photo) | Converts a video to iPhone Live Photo assets: extracts cover frame, transcodes to HEVC MOV (3s), writes paired metadata via makelive, then prompts to import via macOS Photos. |

### AI & Agent Workflows

| Skill | Description |
|-------|-------------|
| [agent-handoff](./agent-handoff) | Agent-to-agent collaboration protocol via self-describing zip packages. Two Claude Code instances (on separate machines) hand off work through a zip containing INSTRUCTIONS.md + manifest.json — human action reduced to "forward the zip in IM." Includes security gate against zip-injection attacks. Lightweight variant: a single self-describing HANDOFF markdown committed into the target repo when both agents share a codebase. |
| [persona-distill](./persona-distill) | Distills a person's writing corpus (blog posts, transcripts, chat logs) into a layered AI persona engineering file: fact/style/reasoning/knowledge extraction → five-file output (SOUL/PERSONA/LOREBOOK/STATE/EVAL) → holdout-set blind evaluation → iterative refinement. |
| [video-to-html-pres](./video-to-html-pres) | Converts a video (file or URL) into a mobile-style interactive HTML presentation with synchronized subtitles. Supports multiple visual themes, persists creator→style mappings in `memory/creator-styles.json`, and supports Whisper word-level timestamps. |

---

## How Skills Work

Each skill directory contains a `SKILL.md` with a YAML frontmatter block:

```yaml
---
name: skill-name
description: Trigger keywords and what this skill does
version: 1.0.0
---
```

The `description` field contains the trigger phrases Claude Code matches against. When triggered, Claude loads the full skill prompt and executes the defined workflow.

**Multi-project skills** additionally include a `SETUP.md` that lists every `{placeholder}` in `SKILL.md` and the project-specific value to substitute. Run `grep -n "{.*}" SKILL.md` after setup to verify no unresolved placeholders remain.

---

## Repository Structure

```
amazing-dev-skills/
├── autopilot/          # SKILL.md + SETUP.md
├── feat/               # SKILL.md + SETUP.md
├── worktree-dev/       # SKILL.md + SETUP.md
├── headless-web-deploy/
│   ├── SKILL.md
│   └── references/     # Caddyfile, systemd unit, RUNBOOK, token auth templates
├── video-to-html-pres/
│   ├── SKILL.md
│   ├── memory/         # Persistent creator→style mappings
│   └── references/     # HTML template guide, design system selection guide
├── persona-distill/
│   ├── SKILL.md
│   └── templates/      # Persona file templates
├── back-to-cn-proxy/
│   ├── SKILL.md
│   └── scripts/        # deploy-singbox.sh, gen-client.py
├── parallel-worktree/
│   ├── SKILL.md
│   └── references/     # Anthropic CCC parallel agent patterns
└── [30+ other skills]/
    └── SKILL.md
```

---

## Contributing

This is a personal skills library — PRs are welcome if you have improvements or new skills that follow the same patterns. To add a skill:

1. Create a new directory with a kebab-case name
2. Add `SKILL.md` with YAML frontmatter (`name`, `description`, `version`)
3. If the skill has project-specific configuration, add `SETUP.md` with a placeholder substitution table
4. Add an entry to the catalog table in this README

---

## License

MIT
