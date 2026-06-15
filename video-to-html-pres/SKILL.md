---
name: video-to-html-pres
description: Convert a video (file or URL) into a mobile-first, short-form interactive HTML presentation with synchronized captions. The user provides a video and a social media handle (e.g. @Hank); the skill outputs canonically named .html and .vtt files. Trigger phrases: video to HTML, video to slides, generate captioned HTML, video knowledge card, video to presentation, make KOL-style HTML. Ideal for content creators who want to turn KOL video highlights into shareable mobile knowledge cards.
---

# Video → HTML Presentation Skill

Convert video content into a **mobile-first, short-form single-file interactive HTML** presentation with precisely synchronized audio captions (VTT).

## Quick Reference

- Reference: `references/design-systems.md` — design system selection logic
- Reference: `references/html-template-guide.md` — HTML generation specification
- Memory: `memory/creator-styles.json` — persistent creator → style mapping

---

## Inputs

| Parameter | Description | Example |
|-----------|-------------|---------|
| `video` | Video file path or URL | `/uploads/sunge.mp4` |
| `handle` | User's social media handle | `@Hank` |
| `creator` | Video creator (optional, aids memory lookup) | `孙哥` |
| `title` | Video title (optional, used for file naming) | `财务目标从100万到一个亿` |

## Outputs

```
{seq}-{creator_slug}-{title_slug}.html   ← full interactive HTML (single file, with audio)
{seq}-{creator_slug}-{title_slug}.vtt    ← corresponding caption file
```

---

## Full Workflow

### Step 1 — Load Memory, Determine Design Style

```python
import json

with open('memory/creator-styles.json') as f:
    memory = json.load(f)

# 1a. Match by creator
creator_key = None
for key, data in memory['creators'].items():
    if any(alias in (creator or '') for alias in data['aliases']):
        creator_key = key
        design_style = data['design_style']
        break

# 1b. Match by theme keyword (if creator is unknown)
if not creator_key:
    for keyword, style in memory['theme_keywords'].items():
        if keyword in (title or '') + (creator or ''):
            design_style = style
            break
    else:
        design_style = None  # needs active judgment

# 1c. If still unknown, analyze video content and choose (see references/design-systems.md)
# Then confirm with user: "I think ElevenLabs style fits best because… — does that work for you?"
```

**Key rule**: All videos from the same creator must use the same design style (experience consistency).  
Only run the style-selection logic for a brand-new creator with a brand-new theme.

### Step 2 — Extract Audio and Video Frames

```bash
# Extract audio (32 kbps MP3, balancing quality and file size)
ffmpeg -i {video} -vn -ar 16000 -ac 1 -ab 32k audio.mp3

# Convert to WAV if Whisper processing is needed
ffmpeg -i audio.mp3 audio.wav

# Extract frames (one frame every 3 seconds, for caption recognition)
ffmpeg -i {video} -vf fps=1/3 dense_%04d.jpg

# Record total frame count and duration
ffprobe -v quiet -show_entries format=duration -of csv=p=0 {video}
```

### Step 3 — Build Caption Timeline

**Priority order:**

**3a. Whisper (most accurate — word-level timestamps)**
```python
import whisper
try:
    model = whisper.load_model("small")  # requires cached model
    result = model.transcribe("audio.wav", language="zh", word_timestamps=True)
    # Extract segment-level timestamps → map to slide transitions
except:
    pass  # fallback to 3b
```

**3b. Frame caption OCR (fallback — ±3s accuracy)**
```bash
# Install Chinese tessdata if not already present
apt-get install -y tesseract-ocr-chi-sim
```
```python
from PIL import Image, ImageEnhance
import pytesseract, re

def ocr_frame(path):
    img = Image.open(path)
    w, h = img.size
    crop = img.crop((0, int(h*0.77), w, int(h*0.91)))  # subtitle region
    gray = crop.convert("L").point(lambda p: 0 if p > 160 else 255)
    big  = gray.resize((w*4, crop.height*4), Image.NEAREST)
    text = pytesseract.image_to_string(big, lang="chi_sim", config="--psm 7")
    return re.sub(r'[^一-鿿，。？！、：；A-Za-z0-9\s]', '', text).strip()

# Frame timestamp: t = (frame_num - 1) * 3 seconds
```

**3c. Manual frame inspection (last resort)**  
Use the `view` tool to read key frames, extract caption text, and build a timeline.  
Focus on frames 1, 5, 10, 15, 20, 30, 40, 50… to identify slide transition points.

### Step 4 — Generate VTT File

```python
def fmt_vtt(seconds):
    h, m = divmod(int(seconds), 3600)
    m, s = divmod(m, 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

vtt_lines = ["WEBVTT", ""]
for i, (start, end, text) in enumerate(timeline):
    vtt_lines += [str(i+1), f"{fmt_vtt(start)} --> {fmt_vtt(end)}", text, ""]

vtt_content = "\n".join(vtt_lines)
# Also save as a standalone .vtt file
```

### Step 5 — Analyze Content, Build slideData

Identify theme-transition points in the timeline and build slideData:

```javascript
// Each slide requires:
{ id: 'slide-xxx', start: T, end: T, chapter: 'Chapter Name' }
```

**Detection rules:**
- Video title cards / transitional caption phrases ("第一", "第二", "Rule 01", "首先") → new slide
- Same topic running continuously for ≥15 seconds → merge into one slide
- Maximum 20 slides (merge related content if exceeded)

### Step 6 — Generate HTML

Read `references/html-template-guide.md` for the full specification.

**Core checklist:**

```
□ <meta viewport> with maximum-scale=1,user-scalable=no
□ Top Story Bar: 17-segment progress bar + chapter label
□ .slide padding: var(--top) var(--lp) var(--bot) var(--lp)
□ .sc justify-content: center (vertically centered content)
□ Bottom HUD: caption line + time line (no navigation dots)
□ No right-side button column
□ Overlay: handle + title + subtitle only, no play button — tap to play
□ Audio: base64-embedded <audio>
□ VTT: JS variable + Blob URL (setupVTT called after click)
□ timeupdate as primary driver + cuechange as safety fallback
□ touchend left/right swipe to switch slides
□ keydown: Space=play/pause, ←→=±10s, ↑↓=prev/next slide
□ Every element referenced by getElementById must exist in the DOM
```

**Apply design tokens** (from the selected style):
```python
tokens = memory['design_catalog'][design_style]
# Or fetch live from the VoltAgent repo:
# https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/{style}/DESIGN.md
```

### Step 7 — Write Files, Update Memory

**File naming:**
```python
# Get sequence number
creator_data = memory['creators'].get(creator_key, {})
seq = creator_data.get('counter', 1)
next_seq = seq + 1

creator_slug = creator_key or creator.lower().replace(' ', '')
title_slug   = re.sub(r'[^\w一-鿿]', '', title).replace(' ', '')

filename_base = f"{seq:03d}-{creator_slug}-{title_slug}"
html_file = f"{filename_base}.html"
vtt_file  = f"{filename_base}.vtt"
```

**Save files:**
```python
with open(f"/mnt/user-data/outputs/{html_file}", 'w', encoding='utf-8') as f:
    f.write(html_content)

with open(f"/mnt/user-data/outputs/{vtt_file}", 'w', encoding='utf-8') as f:
    f.write(vtt_content)
```

**Update memory:**
```python
# New creator → add record
if creator_key not in memory['creators']:
    memory['creators'][creator_key] = {
        "aliases": [creator],
        "themes": extracted_themes,
        "design_style": design_style,
        "design_note": "...",
        "counter": 1,
        "first_seen": today,
        "sample_file": html_file
    }
else:
    # Increment counter
    memory['creators'][creator_key]['counter'] = next_seq

with open('memory/creator-styles.json', 'w', encoding='utf-8') as f:
    json.dump(memory, f, ensure_ascii=False, indent=2)
```

---

## Troubleshooting

### Network restricted — cannot download Whisper model
→ Fall back to frame OCR (Step 3b) or manual frame inspection (Step 3c)

### VTT file cannot be used with `<track>` via data URI
→ Must use Blob URL (`URL.createObjectURL`) — see html-template-guide.md

### Too many slides (>20)
→ Merge related content; prioritize keeping the opening and closing of each chapter

### Design style unclear
→ Consult the selection matrix in `references/design-systems.md`
→ Explain your reasoning to the user before confirming

### New creator whose themes are similar to a known creator
→ Still create a separate record — do **not** reuse another creator's entry
→ The same `design_style` may be shared, however

### JS error: `Cannot read properties of null (reading 'addEventListener')`
→ Audit all `getElementById` calls — every referenced element must exist in the DOM
→ If a DOM element is removed, its JS references must be removed at the same time

---

## Output Validation Checklist

```
□ HTML file opens directly in a mobile browser
□ Tapping the screen starts audio playback
□ Captions are synchronized with audio (within ±5 seconds)
□ Slides switch at the correct timestamps
□ Story Bar progress updates in real time
□ Content is not cramped in portrait mode — feels vertically centered
□ VTT file saved separately for future reuse
□ memory/creator-styles.json updated
□ File naming follows the convention: {seq:03d}-{creator}-{title}.html
```
