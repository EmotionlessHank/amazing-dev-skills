# HTML Template Specification (Mobile-First)

## Safe Zone Layout（必须遵守）

```
┌──────────────────────────────┐
│  Story Bar  (top: 52px)      │  ← 17段进度条 + 章节名
├──────────────────────────────┤
│                              │
│     CONTENT SAFE ZONE        │  ← padding: 52px 16px 170px 16px
│     (无 right btn col)        │
│                              │
├──────────────────────────────┤
│  Bottom HUD  (170px)         │  ← 字幕 + 时间 + 播放状态
└──────────────────────────────┘
```

## CSS 变量规范

```css
:root {
  --top: 52px;   /* story bar height */
  --bot: 170px;  /* bottom HUD height */
  --lp:  16px;   /* left/right padding */
}
.slide {
  padding-top:    var(--top);
  padding-right:  var(--lp);   /* 全宽，无右侧按钮列 */
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
  justify-content: center;   /* 内容垂直居中 */
}
```

## Story Bar（顶部进度）

- 17段细进度条，对应 slideData 的 17 张幻灯片
- 当前段实时填充（timeupdate 驱动）
- 右侧显示章节名（chapter label）

## Bottom HUD（底部信息栏）

```
第一行：VTT 字幕文字（cuechange 驱动）
第二行：▶/⏸ 图标 · 时间 · 音频波形动画
（删除导航点——与顶部进度条重复）
```

## 音频 + VTT 嵌入方式

```html
<!-- 音频：base64 嵌入，完全离线 -->
<audio id="bgm">
  <source src="data:audio/mpeg;base64,{BASE64}" type="audio/mpeg">
</audio>

<!-- VTT：运行时 Blob URL（track 不支持 data URI）-->
<script>
function setupVTT() {
  const blob = new Blob([VTT_CONTENT], {type:'text/vtt'});
  const track = document.createElement('track');
  track.kind = 'metadata';   // metadata 模式确保 cuechange 触发
  track.src  = URL.createObjectURL(blob);
  track.default = true;
  audio.appendChild(track);
  track.addEventListener('cuechange', () => { ... });
}
// 点击播放后调用 setupVTT()
</script>
```

## Slide 切换双重机制

```javascript
// 主驱动：timeupdate（每 ~250ms）
audio.addEventListener('timeupdate', () => {
  const cur = slideData.find(s => t >= s.start && t < s.end);
  if (cur) switchTo(cur index);
});

// 安全兜底：cuechange 关键词匹配
// 当 cue 文本包含特定关键词时，验证并修正当前 slide
```

## 播放启动

```javascript
// Overlay 点击即播放，不需要独立播放按钮
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

## Touch 手势

```javascript
// 左右滑动 → 跳转到对应 slide 时间点
document.addEventListener('touchend', e => {
  const dx = e.changedTouches[0].clientX - tx0;
  if (Math.abs(dx) > 40) {
    const next = dx < 0 ? curIdx+1 : curIdx-1;
    audio.currentTime = slideData[clamp(next)].start + 0.1;
  }
});
```

## Slide 内容组件库

| 组件名        | 用途                        |
|-------------|---------------------------|
| `.rule-row` | 规则列表项（数字 + 标题 + 描述）  |
| `.wealth-rung` | 财富梯级（左标签 + 右大数字）   |
| `.phase-box` | 阶段卡片（icon + 标题 + 年份） |
| `.sin-card` | 2×3 grid 小卡片              |
| `.check-item` | 核查条目（verdict + rule + detail）|
| `.funnel-row` | 漏斗条形（宽度递减）           |
| `.formula`  | 公式展示（var × op = res）    |
| `.stat`     | 大数字统计展示                |
| `.bar-chart` | 柱状图（bar-fill height 动画）|
| `.tbl`      | 表格（grid-template-columns）|
| `.card`     | 通用卡片，支持 .g-mint/.g-red/.g-gold 配色|

## 文件大小预期

- 视频音频（32kbps MP3）: ~2.7MB base64 → 3.6MB
- VTT（93条目）: ~8KB
- HTML + CSS + JS: ~100KB
- 总计: ~3.5–4MB（单文件，完全离线）
