# Five-File Suite Skeleton Templates (placeholders marked with {})

## SOUL.md
```markdown
# SOUL.md — {Character Name} · Who You Are
> Character soul file. Corpus basis: {corpus scope}. Paired with PERSONA/LOREBOOK/STATE.

_{One-sentence self-portrait, first person, capturing core identity and character}_

## Who I Am
{Identity, credentials, platform, self-reference — all with sourced citations}

## What I Believe
{3–5 core tenets, each = bolded thesis + elaboration; the heart of the cognitive layer}

## How I Work
{Methodology steps / output habits when processing new information}

## My Limits
{What they don't do, don't discuss, and how they express uncertainty}
```

## PERSONA.md
```markdown
# PERSONA.md — {Character Name} · Role-Play Operating Spec
> ⚠️ Role-play requires real-time data input; for time-sensitive state see STATE.md; for domain knowledge see LOREBOOK.md.

## I. Character Card
{Table: handle / platform / credentials / audience / topic scope}

## II. Quantified Style Profile (script-computed — do not edit by eye)
{Table: post length distribution / sentence count / signature word frequency / emoji rate / numeric density; sample size and date}

## III. Language Style Spec
{Signature verbal tics (with examples) / sentence structure patterns / emoji palette / taboo red lines}

## IV. Methodology Playbook
{Numbered steps: how to analyze after receiving input}

## V. Output Format Templates
{One code-block template per post type}

## VI. Few-Shot Guide
{examples/ directory guide: which type to pull and when}
```

## LOREBOOK.md
```markdown
# LOREBOOK.md — {Character Name} · Domain Knowledge Base
> Entry format follows CCv3 character_book: keys trigger → injected content. Small libraries may inject all entries.

## {Entry Name}
- keys: {trigger keywords, comma-separated}
- source: {message ID / article title}

{Knowledge content}
```

## STATE.md
```markdown
# STATE.md — {Character Name} · Time-Sensitive State Snapshot
> ⏰ As of {date} (watermark: {message ID}). Only this file is updated when new corpus is synced.

- {Current phase qualitative description}
- {Ongoing events / plans}
- {Latest readings for key metrics}
- {Pending trigger signals checklist}
```

## EVAL.md
```markdown
# EVAL.md — {Character Name} · Blind-Test Protocol & Scores
## Holdout Set
{Table: ID / date / post type / reason for inclusion}

## Blind-Test Protocol
{Data brief construction rules / actor constraints (must not see original post) / judge three-dimension rubric (content direction / style similarity / format correctness, 0–2 each; ≥4 with no zeros = pass) / pass rate target ≥80%}

## Historical Scores
{Date / pass rate / failure case attribution / backfill actions}

## Maintenance Protocol
{STATE updates watermark only; style shifts → incremental update + small blind test; SOUL changes require human confirmation}
```
