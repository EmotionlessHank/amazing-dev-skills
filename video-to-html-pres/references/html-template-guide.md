# HTML Template Specification (Mobile-First)

## Safe Zone Layout (required)

```
┌──────────────────────────────┐
│  Story Bar  (top: 52px)      │  ← 17-segment progress bar + chapter label
├──────────────────────────────┤
│                              │
│     CONTENT SAFE ZONE        │  ← padding: 52px 16px 170px 16px
│     (no right button column) │
│                              │
├──────────────────────────────┤
│  Bottom HUD  (170px)         │  ← captions + time + playback state
└──────────────────────────────┘
```

## CSS Variable Specification

```css
:root {
  --top: 52px;   /* story bar height */
  --bot: 170px;  /* bottom HUD height */
  --lp:  16px;   /* left/right padding */
}
.slide {
  padding-top:    var(--top);
  padding-right:  var(--lp);   /* full width — no right button column */
  padding-bottom: var(--bot);
  padding-left:   var(--lp);
}
.sc {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  overflow: hidden;
  justify-content: center;   /* vertically center content */
}
```

## Story Bar (top progress)

- 17 thin segments corresponding to the 17 slides in slideData
- Active segment fills in real time (driven by timeupdate)
- Chapter label displayed on the right side

## Bottom HUD (info bar)

```
Line 1: VTT caption text (driven by cuechange)
Line 2: ▶/⏸ icon · timestamp · audio waveform animation
(Navigation dots removed — redundant with the top progress bar)
```

## Audio + VTT Embedding

```html
<!-- Audio: base64-embedded, fully offline -->
<audio id="bgm">
  <source src="data:audio/mpeg;base64,{BASE64}" type="audio/mpeg">
</audio>

<!-- VTT: runtime Blob URL (track does not support data URIs) -->
<script>
function setupVTT() {
  const blob = new Blob([VTT_CONTENT], {type:'text/vtt'});
  const track = document.createElement('track');
  track.kind = 'metadata';   // metadata mode ensures cuechange fires
  track.src  = URL.createObjectURL(blob);
  track.default = true;
  audio.appendChild(track);
  track.addEventListener('cuechange', () => { ... });
}
// Call setupVTT() after the user taps to play
</script>
```

## Dual Slide-Switching Mechanism

```javascript
// Primary driver: timeupdate (fires every ~250ms)
audio.addEventListener('timeupdate', () => {
  const cur = slideData.find(s => t >= s.start && t < s.end);
  if (cur) switchTo(cur index);
});

// Safety fallback: cuechange keyword matching
// When cue text contains specific keywords, verify and correct the current slide
```

## Playback Start

```javascript
// Overlay tap starts playback — no separate play button needed
overlay.addEventListener('click', () => {
  audio.play().then(() => {
    overlay.style.opacity = '0';
    overlay.style.pointerEvents = 'none';
    setTimeout(() => overlay.style.display='none', 700);
    setupVTT();
    switchTo(0);
  });
});
```

## Touch Gestures

```javascript
// Swipe left/right → jump to the corresponding slide's start time
document.addEventListener('touchend', e => {
  const dx = e.changedTouches[0].clientX - tx0;
  if (Math.abs(dx) > 40) {
    const next = dx < 0 ? curIdx+1 : curIdx-1;
    audio.currentTime = slideData[clamp(next)].start + 0.1;
  }
});
```

## Slide Content Component Library

| Component      | Purpose                                              |
|----------------|------------------------------------------------------|
| `.rule-row`    | Rule list item (number + title + description)        |
| `.wealth-rung` | Wealth ladder (left label + right large number)      |
| `.phase-box`   | Phase card (icon + title + year)                     |
| `.sin-card`    | 2×3 grid of small cards                              |
| `.check-item`  | Checklist entry (verdict + rule + detail)            |
| `.funnel-row`  | Funnel bar (decreasing width)                        |
| `.formula`     | Formula display (var × op = result)                  |
| `.stat`        | Large-number statistic display                       |
| `.bar-chart`   | Bar chart (bar-fill height animation)                |
| `.tbl`         | Table (grid-template-columns)                        |
| `.card`        | General-purpose card, supports .g-mint/.g-red/.g-gold color variants |

## Expected File Sizes

- Video audio (32 kbps MP3): ~2.7 MB base64 → 3.6 MB
- VTT (93 cues): ~8 KB
- HTML + CSS + JS: ~100 KB
- Total: ~3.5–4 MB (single file, fully offline)
