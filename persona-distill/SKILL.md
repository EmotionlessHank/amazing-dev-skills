---
name: persona-distill
description: Distills a layered engineering artifact set (SOUL/PERSONA/LOREBOOK/STATE/EVAL five-file suite) suitable for AI role-play from a character's text corpus (blogger posts/articles/chat logs), including holdout-set blind-test validation. Use when the user requests "distill a person / generate someone's persona / have AI play a real person for professional output".
---

# persona-distill — Persona Distillation Pipeline

> Methodology references (source audit at hermes-setup `docs/DD-009-persona-distillation/research/source-audit.md`):
> Beyond Profile three-layer model (facts/style/cognition, arXiv 2502.12988) · Character Card Spec V3 (lorebook separation) · ChatHaruhi (retrieval-augmented memory) · written-voice-replication (quantified style profile + numerical validation) · InCharacter/RoleBench (evaluation).

## When to Use / When Not to Use

- ✅ You have ≥30 first-person texts (posts/articles/messages) from the character, and want to distill a role that unifies "thinking patterns + language style + domain knowledge".
- ❌ Corpus < 30 samples (few-shot injection into the prompt is sufficient; the pipeline is not worth running). ❌ Fictional character with no corpus (that's creative writing, not distillation).

## Core Principles

1. **Cognitive layer over style layer**: Pure profile + tone imitation misses the person; values, methodology, and reasoning patterns are the "soul" (the central critique in Beyond Profile).
2. **Separate knowledge from persona**: Domain knowledge goes into a standalone LOREBOOK (entries with trigger keywords); time-sensitive state goes into a standalone STATE — the persona file stays stable, and syncing new corpus only requires updating STATE.
3. **Source every claim**: Every extracted conclusion must cite the corpus source (message ID / article title); unsourced "reasonable inference" is prohibited.
4. **Holdout before extraction**: The blind-test set is split off before extraction begins and must never participate in extraction — otherwise validation is invalid.
5. **Quantify style with scripts**: Post length / sentence length / signature word frequency are computed with deterministic scripts, not by LLM eyeballing.
6. **Run stylometrics on raw text**: If the corpus consists of edited notes (with added headings/annotations/formatting), go back to the original source and pull raw text for statistics.

## Pipeline (Five Stages)

### ① Corpus Inventory
- Collect statistics: count, time span, type distribution (categorized by output format).
- **Split holdout set**: 10–15%, covering ≥1 sample of every output format; exclude "time-sensitive state key posts" (posts whose information will go into STATE cannot be held out).
- Quantified style profile (scripts): average/median post length (characters), sentence count distribution, signature word frequency table, emoji usage rate, number/table occurrence rate.

### ② Layered Extraction (4 passes, extraction set only)
| Pass | Layer | What to Extract |
|---|---|---|
| L1 | Fact layer | Identity, platform, credentials, self-reference, relational terms, knowledge boundaries (what they don't discuss) |
| L2 | Style layer | Signature verbal tics, sentence structure patterns, emoji palette, format templates (organized by post type), taboos (things they would never say); overlaid with ① quantified profile |
| L3 | Cognitive layer | Values, worldview, **methodology steps** (how they reason when they receive new information), stance tendencies, uncertainty expression habits |
| L4 | Knowledge layer | Domain knowledge itemized: each entry = trigger keyword `keys` + content + source; time-sensitive content separately marked for STATE |

### ③ Synthesize the Five-File Suite
Output directory structure (templates at `templates/` in this skill):
```
<character>/000_persona/
├── SOUL.md       # L1+L3, first-person "who I am / what I believe / how I work / my limits" → always-on system prompt
├── PERSONA.md    # L2, character card + style spec (qualitative + quantitative profile) + output format templates + taboos → always-on
├── LOREBOOK.md   # L4, knowledge entries (keys + content + source) → retrieval injection; full injection for small libraries
├── STATE.md      # L4 time-sensitive snapshot, annotated with "as-of date + watermark ID" → injected before every conversation
├── EVAL.md       # L5, holdout set manifest + blind-test protocol + scoring rubric + historical scores → not injected, for maintenance
└── examples/     # few-shot original samples, ≥2 per post type, filenames tagged with post type (extraction set only)
```

### ④ Holdout Set Blind Test
For each holdout post:
1. Extract only a **neutral data brief** from the original post (date, metric readings, recent context), stripping all original phrasing;
2. The **actor sub-agent** reads only the five-file suite + data brief and produces the post for that day (the actor must never see the original);
3. The **judge sub-agent** scores against (original post, generated post) on three dimensions (0–2 each; ≥4 with no zeros = pass):
   - Content direction: whether conclusions/signal calls match the original
   - Style similarity: whether signature words, sentence patterns, emoji, and length resemble the person (against PERSONA quantitative profile)
   - Format correctness: whether the correct output template was used for this scenario
4. Pass rate = passing posts / holdout posts; target **≥80%**.

### ⑤ Iterative Convergence
- If below target: attribute failures (missing signature words? wrong methodology steps? wrong format template?) and backfill into the corresponding layer file, then retest failed posts.
- If on target: backfill time-sensitive information from the holdout set into STATE (only allowed at this point), record scores and date in EVAL.md, and finalize.

**Common distortion patterns** (from the first real instance, Crypto Chan, June 2026, converged 3/6→6/6 in two rounds):
1. **Over-imitation / density inflation** (most frequent): The actor inflates the character's minimal output into fully-loaded format with stacked signature elements. Fix: write a "density discipline" in PERSONA — density follows the information volume of the day's material; criteria for when decoration elements are permitted; low-frequency verbal tic quotas (e.g., if a phrase appears in only 10% of corpus posts → don't use it by default).
2. **Signal escalation fabrication** (most dangerous): Rewrites a weak signal from the source material into a heavier signal in the system (e.g., "90-day MA touched 1.0" → "365-day orange-blue crossover"). Fix: write a "content integrity red line" in PERSONA — every completed-state assertion requires literal textual support from the source material; anything without support must use incomplete-state phrasing. Explicitly annotate easily-confused signals in LOREBOOK.
3. **Example coverage gaps**: When a post type has no matching example in `examples/`, the actor borrows the nearest heavy template instead. Fix: include ≥2 examples for every post type (including the most unremarkable minimal type); add a fallback rule: "when in doubt, use the lightest form".

## Maintenance Protocol (write into the output EVAL.md)
- After syncing new corpus: update only STATE.md (watermark ID + new state);
- When the character's style/methodology shows a clear shift (new series, new verbal tic): incrementally update PERSONA/LOREBOOK and add examples, then run a small blind test;
- SOUL should not be changed (changing it = persona overhaul, requires human confirmation).

## Integration Notes
- Claude/DeepSeek system prompt: SOUL + PERSONA always-on, STATE prepended, LOREBOOK on demand (full injection for small libraries);
- Weak intent-completion models (e.g., DeepSeek): always keep the few-shot examples and strict format templates in PERSONA;
- For SillyTavern and similar platforms: the five-file suite maps mechanically to CCv3 fields (description←L1, personality←L3 summary, mes_example←examples, character_book←LOREBOOK).
