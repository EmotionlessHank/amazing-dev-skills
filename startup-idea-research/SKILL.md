---
name: startup-idea-research
description: "Standardized startup-idea research pipeline: multi-domain trend mining (pain points) → idea distillation → three-axis scoring → [MANDATORY first-hand competitive audit that deflates fake blue-ocean scores] → ranked matrix + summary + market sizing, archived by dated batch. Triggers on: 'startup idea research', 'idea research', 'run an idea scan', 'find startup ideas', 'idea matrix', 'market opportunity scan'."
argument-hint: "startup-idea-research [domain1 domain2 domain3 ... (default: pick relevant markets)]"
allowed-tools: Agent, Bash, Read, Write, Edit, Skill, AskUserQuestion
user-invocable: true
metadata:
  openclaw:
    emoji: "🧭"
---

# Startup Idea Research — Standardized Idea-Scouting Pipeline

Turns "mine pain points → distill ideas → score → **first-hand competitive audit** → ranked matrix + summary + market sizing" into a repeatable, dated-batch pipeline for retrospective comparison across runs.

> **The soul of this skill is Phase 3, the mandatory competitive audit.** Hard-won lesson: scoring ideas off trend-discovery tools alone produced 5 "green-light" ideas that ALL got downgraded after a first-hand audit (13→10, 12→8…). Discovery tools systematically misread "incumbents ignore this tier", "free tools don't count as competitors", and "API-lockout gaps" as *blue ocean*. **Any blue-ocean score that has not passed Phase 3 is untrusted.** Companion methodology: the `market-opportunity-audit` harness (see References).

## Configuration
- `{INCUBATOR_ROOT}` — base output folder for this pipeline. Default: `startup-incubator/`. Set it to wherever your knowledge base / repo keeps incubation work.
- `{TREND_SKILL}` — the trend-mining skill used in Phase 1 (e.g. `last30days`, or any "what people said recently across Reddit/X/HN/YouTube/GitHub" skill). If none is installed, fall back to `WebSearch` across the same platforms.

## Global discipline (every phase)
- **Source audit / anti-GEO**: prefer first-party official, authoritative, and real user posts; heavily down-weight SEO/affiliate listicles, founder self-reported traction, and mirror directory sites. On coordinated-promotion signals → emit an explicit "⚠️ source-pollution warning" and down-weight. No marketing superlatives.
- **Reddit is often rate-limited (API 403)**: if unreachable, use App Store / Capterra real reviews instead, **never fabricate quotes**, and honestly flag the data gap.
- **Subagents run on a mid-tier model (e.g. sonnet)**, launched in parallel (research is the bottleneck — fire first).
- **Conclusions follow first-hand evidence, even when they contradict the initial hunch.**

---

## Phase 0 · Setup
1. Determine domains: from args; if none, propose relevant markets and confirm via AskUserQuestion.
2. Get today's `<date>` (YYYY-MM-DD).
3. Create the batch skeleton (first run also creates methodology + index — see "First-time init"):
   ```
   {INCUBATOR_ROOT}/batches/<date>/{research,ideas}/
   ```

## Phase 1 · Multi-domain pain-point research (parallel subagents, one per domain)
Spawn one subagent per domain using `references/research-agent-prompt.md`. Require structured output:
- High-frequency pain points P1..Pn (each: concrete description / frequency + emotion evidence + source platform / who's affected / **what vendors already do + the gap**)
- Blank-opportunity candidates G1..Gn
- Sources & credibility notes (with pollution warnings + data gaps)

Then the main loop writes each domain to `research/<domain>-painpoints.md` with compliant frontmatter and back-links.

## Phase 2 · Idea distillation + initial scoring (main loop)
1. Convert blank opportunities + high-value pains into ideas; one file each: `ideas/<domain>-NN-<name>.md`.
2. Each idea file: one-liner / pain source (back-link) / approach / competitors & gap / **three-axis score** / MVP path / risks / links.
3. Scoring per `references/scoring-rubric.md`: Demand + BlueOcean + Feasibility, each 1-5, total 15.
   - **⚠️ At this stage every BlueOcean is provisional — mark UNAUDITED, cap BlueOcean at 3, cannot reach 🟢.**

## Phase 3 · Mandatory first-hand competitive audit (the core — never skip)
Spawn one subagent **per idea** using `references/competitive-audit-prompt.md` (ideas with overlapping competitor sets may share one). Require first-hand checks:
- **Official pricing pages** (no guessing), **App Store / extension store** ratings + review counts + last-updated recency, **Capterra / real reviews** for negative voices.
- **Three-way squeeze**: big players' stripped-down tiers pushing down ↓ / same-price players / free tools + bare-bones cheap apps eating the bottom.
- **Find the incumbent's wound** (data lock-in / crashes / fee creep / no native app) = the entry wedge; no wound = no gap.
- **Gap verdict, pick one**: truly empty / someone does it badly / being filled — and **name the biggest down-market threat**.
- Output competition intensity 1-5 (5 = red ocean) → `BlueOcean = 6 − intensity`, with "initial vs audited" delta.

After audits: ① update each idea file's score to "audited", strike through the old (`~~old~~`) + add a correction note; ② write an audit roundup `research/competitive-audit-<batch>.md` (the recurring death-cause patterns + a change table).

## Phase 4 · Market sizing (for the top 🟡/🟢 picks)
For the 1-3 highest audited ideas, spawn a subagent for TAM/SAM/SOM + willingness-to-pay:
- Prefer first-party (industry associations / official labor stats / SEC filings); tag second-hand survey numbers "order-of-magnitude only".
- Use a software-revenue-pool lens (not industry GMV), state ARPU assumptions, and be honest about the ceiling (lifestyle business vs venture-scale).
- Write `<idea-name>-deepdive-path-and-market.md` in the batch root: why they pay / pains / why incumbents can't satisfy / market size / implementation path / validation gate.

## Phase 5 · Wrap-up
1. **README** (`<date>-idea-batch-README.md`): overview + **ranked matrix table** (cols: Demand/BlueOcean/Feasibility/Total/Tier/Audited✅/Intensity), `BlueOcean = 6 − intensity`; one-line insights (incl. the audited-vs-initial downgrades).
2. **Summary** (`<date>-idea-batch-summary.md`): dev recommendations (by tier) + execution advice (validate demand before building, single-wedge entry, reuse mature infra, GTM, source audit, next-batch iteration).
3. Update `{INCUBATOR_ROOT}/INDEX.md` batch list (idea count / 🟢 count / status).
4. **Dead-link self-check**: diff `.md` basenames against every `[[wikilink]]` target; fix any dangling link.

## Tiers & gate (hard rules)
- Total: 🟢12-15 validate now / 🟡9-11 watchlist / 🔴≤8 shelve.
- **Any 🟢 "validate now" verdict MUST have passed Phase 3**, else demote to 🟡; unaudited ideas cap BlueOcean at 3.
- The matrix MUST carry an "Audited" column so inflated/unaudited items are obvious at a glance.

## First-time init (if `{INCUBATOR_ROOT}` doesn't exist)
Also create: `methodology/idea-scoring-rubric.md` (copy references/scoring-rubric.md), `{INCUBATOR_ROOT}/INDEX.md` (pipeline index), `greenlit/`, `archive/` subfolders.

## Related assets
- Harness: `market-opportunity-audit` (the methodology source for Phase 3), `source-audit` (source vetting).
- Dependency skill: a trend-mining skill (`{TREND_SKILL}`, e.g. `last30days`) for Phase 1.

## Notes for adaptation
This is a generalized, English port of a pipeline originally built for a personal Obsidian knowledge base (Chinese, output under `03_项目/创业孵化/`). For a vault deployment, set `{INCUBATOR_ROOT}` to your incubator path and localize folder/file names + frontmatter to your vault conventions.
