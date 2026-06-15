# Design System Selection Guide

Source: https://github.com/VoltAgent/awesome-design-md/tree/main/design-md

## Selection Decision Tree

```
1. Check memory/creator-styles.json
   → Creator known? → Use the stored design_style, skip to step 4
   → Unknown? → Continue to step 2

2. Analyze video theme keywords
   → Match against theme_keywords table
   → Match found? → Use the corresponding style
   → No match? → Continue to step 3

3. Make an active judgment:
   → Read video title + first 30s of captions
   → Assess emotional tone: serious / upbeat / technical / emotional / entertainment
   → Use the selection matrix below to pick the best-fit style
   → Confirm with user ("I think ElevenLabs style fits best because… — does that work for you?")

4. Fetch the corresponding DESIGN.md tokens from the VoltAgent repo
   → URL: https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/{style}/DESIGN.md
   → Extract: colors / typography / spacing / component tokens
   → If network is unavailable, use the built-in tokens in memory/creator-styles.json

5. Update memory/creator-styles.json (for new creators or new themes)
```

## Style Selection Matrix

| Video mood / theme          | Recommended style | Rationale                                        |
|-----------------------------|-------------------|--------------------------------------------------|
| Finance · wealth · life     | elevenlabs        | Dark cinematic feel, authoritative, suits serious content |
| AI · tech · future          | minimax           | Neon bold, high visual impact                    |
| Dev · tools · SaaS          | cursor            | Code aesthetic, restrained and precise           |
| Music · entertainment · creative | spotify      | Green energy, album-art-driven                   |
| Minimal · product · launch  | vercel            | Pure black-and-white, zero noise                 |
| Design · creative · visual  | figma             | Colorful and lively, professional design feel    |
| Health · lifestyle · emotion | claude           | Warm brown tones, soft and approachable          |

## ElevenLabs Tokens (built-in — no network required)

```css
/* Verified usable in this session */
--bg:       #0c0a09;   /* canvas-deep */
--elev:     #1c1917;   /* surface-dark-elevated */
--soft:     #a8a29e;   /* on-dark-soft */
--muted:    #777169;
--mint:     #a7e5d3;   /* gradient-mint */
--peach:    #f4c5a8;   /* gradient-peach */
--lavender: #c8b8e0;   /* gradient-lavender */
--sky:      #a8c8e8;   /* gradient-sky */
--rose:     #e8b8c4;   /* gradient-rose */
--font-d:   'Noto Serif SC', 'Times New Roman', serif;  /* Waldenburg fallback */
--font-b:   'Noto Sans SC', system-ui, sans-serif;
/* display: weight 300, letter-spacing -1.92px, line-height 1.05 */
/* pill: border-radius 9999px */
/* no neon, no saturated CTA, atmospheric photography aesthetic */
```

## File Naming Convention

```
{seq}-{creator}-{title}.html
{seq}-{creator}-{title}.vtt

seq:     three-digit number, incremented per creator (tracked in memory)
creator: lowercase, no spaces (e.g. 孙哥→sunge, 李笑来→lxl)
title:   condensed video title, Chinese characters preserved, special chars stripped, spaces replaced with hyphens

Examples:
  001-sunge-财务目标从100万到一个亿.html
  001-sunge-财务目标从100万到一个亿.vtt
  002-sunge-如何选择人生第一份工作.html
  001-lxl-时间的朋友.html
```
