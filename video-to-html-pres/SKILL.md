---
name: video-to-html-pres
description: 把视频（文件或链接）转换成手机端短视频风格的交互式 HTML 演示文稿，带同步字幕。用户提供视频 + 社媒用户名（如 @Hank），输出标准命名的 .html 和 .vtt 文件。触发词：视频转 HTML、视频转演示、生成字幕 HTML、视频知识卡片、video to slides、制作孙哥风格 HTML。适合内容创作者把 KOL 视频精华做成可分享的手机端知识卡片。
---

# Video → HTML Presentation Skill

把视频内容转为**移动端短视频风格的单文件交互 HTML**，含精准音频同步字幕（VTT）。

## 快速参考

- 参考文件: `references/design-systems.md`（设计系统选择逻辑）
- 参考文件: `references/html-template-guide.md`（HTML 生成规范）
- 记忆文件: `memory/creator-styles.json`（creator → 风格持久记忆）

---

## 输入

| 参数 | 说明 | 示例 |
|------|------|------|
| `video` | 视频文件路径或 URL | `/uploads/sunge.mp4` |
| `handle` | 用户社媒账号 | `@Hank` |
| `creator` | 视频创作者（可选，有助于记忆匹配） | `孙哥` |
| `title` | 视频标题（可选，用于文件命名） | `财务目标从100万到一个亿` |

## 输出

```
{seq}-{creator_slug}-{title_slug}.html   ← 完整交互 HTML（单文件，含音频）
{seq}-{creator_slug}-{title_slug}.vtt    ← 对应字幕文件
```

---

## 完整工作流

### Step 1 — 读取记忆，确定设计风格

```python
import json

with open('memory/creator-styles.json') as f:
    memory = json.load(f)

# 1a. creator 匹配
creator_key = None
for key, data in memory['creators'].items():
    if any(alias in (creator or '') for alias in data['aliases']):
        creator_key = key
        design_style = data['design_style']
        break

# 1b. 主题关键词匹配（如果 creator 未知）
if not creator_key:
    for keyword, style in memory['theme_keywords'].items():
        if keyword in (title or '') + (creator or ''):
            design_style = style
            break
    else:
        design_style = None  # 需要主动判断

# 1c. 如果仍未知，分析视频内容后选择（见 references/design-systems.md）
# 并向用户确认："我判断应该用 ElevenLabs 风格，因为…，你确认吗？"
```

**关键规则**: 同一 creator 的所有视频必须用同一设计风格（体验一致性）。  
只有全新 creator + 全新主题才走风格判断逻辑。

### Step 2 — 提取音频和视频帧

```bash
# 提取音频（32kbps MP3，平衡质量与文件大小）
ffmpeg -i {video} -vn -ar 16000 -ac 1 -ab 32k audio.mp3

# 如果需要 Whisper 处理，转 WAV
ffmpeg -i audio.mp3 audio.wav

# 提取帧（每3秒一帧，用于字幕识别）
ffmpeg -i {video} -vf fps=1/3 dense_%04d.jpg

# 记录总帧数和时长
ffprobe -v quiet -show_entries format=duration -of csv=p=0 {video}
```

### Step 3 — 构建字幕时间轴

**优先级顺序：**

**3a. Whisper（最精准，词级时间戳）**
```python
import whisper
try:
    model = whisper.load_model("small")  # 需要模型已缓存
    result = model.transcribe("audio.wav", language="zh", word_timestamps=True)
    # 提取段落级时间戳 → 映射到 slide transitions
except:
    pass  # fallback to 3b
```

**3b. 帧字幕 OCR（备选，±3秒精度）**
```bash
# 安装中文 tessdata（如未安装）
apt-get install -y tesseract-ocr-chi-sim
```
```python
from PIL import Image, ImageEnhance
import pytesseract, re

def ocr_frame(path):
    img = Image.open(path)
    w, h = img.size
    crop = img.crop((0, int(h*0.77), w, int(h*0.91)))  # 字幕区域
    gray = crop.convert("L").point(lambda p: 0 if p > 160 else 255)
    big  = gray.resize((w*4, crop.height*4), Image.NEAREST)
    text = pytesseract.image_to_string(big, lang="chi_sim", config="--psm 7")
    return re.sub(r'[^\u4e00-\u9fff，。？！、：；A-Za-z0-9\s]', '', text).strip()

# 每帧时间戳: t = (frame_num - 1) * 3 秒
```

**3c. 手动逐帧观察（最后备选）**  
用 `view` 工具读取关键帧，提取字幕文本，建立时间轴。  
重点读取：第1、5、10、15、20、30、40、50... 等帧，识别 slide 切换点。

### Step 4 — 生成 VTT 文件

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
# 同时保存为独立 .vtt 文件
```

### Step 5 — 分析内容，建立 slideData

从时间轴中识别主题切换点，建立 slideData：

```javascript
// 每个 slide 需要：
{ id: 'slide-xxx', start: T, end: T, chapter: '章节名' }
```

**识别规则：**
- 视频标题卡 / 字幕转折词（"第一"、"第二"、"Rule 01"、"首先"）→ 新 slide
- 同一主题连续 ≥15秒 → 合并为一个 slide
- 最多 20 个 slide（超过则合并相关内容）

### Step 6 — 生成 HTML

读取 `references/html-template-guide.md` 获取完整规范。

**核心要素清单：**

```
□ <meta viewport> 含 maximum-scale=1,user-scalable=no
□ 顶部 Story Bar：17段进度条 + 章节标签
□ .slide padding: var(--top) var(--lp) var(--bot) var(--lp)
□ .sc justify-content: center（内容垂直居中）
□ 底部 HUD：字幕行 + 时间行（无导航点）
□ 无右侧按钮列
□ Overlay：仅 handle + 标题 + 副标题，无播放按钮，点击即播
□ 音频：base64 嵌入 <audio>
□ VTT：JS 变量 + Blob URL（setupVTT 在 click 后调用）
□ timeupdate 主驱动 + cuechange 安全兜底
□ touchend 左右滑动切换 slide
□ keydown: Space=播放, ←→=±10s, ↑↓=上下slide
□ 所有 getElementById 调用的元素必须存在于 DOM
```

**应用设计 tokens**（从选定风格取）：
```python
tokens = memory['design_catalog'][design_style]
# 或从 VoltAgent repo 实时获取：
# https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/{style}/DESIGN.md
```

### Step 7 — 生成文件，更新记忆

**文件命名：**
```python
# 获取序号
creator_data = memory['creators'].get(creator_key, {})
seq = creator_data.get('counter', 1)
next_seq = seq + 1

creator_slug = creator_key or creator.lower().replace(' ', '')
title_slug   = re.sub(r'[^\w\u4e00-\u9fff]', '', title).replace(' ', '')

filename_base = f"{seq:03d}-{creator_slug}-{title_slug}"
html_file = f"{filename_base}.html"
vtt_file  = f"{filename_base}.vtt"
```

**保存文件：**
```python
with open(f"/mnt/user-data/outputs/{html_file}", 'w', encoding='utf-8') as f:
    f.write(html_content)

with open(f"/mnt/user-data/outputs/{vtt_file}", 'w', encoding='utf-8') as f:
    f.write(vtt_content)
```

**更新记忆：**
```python
# 新 creator → 添加记录
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
    # 递增计数器
    memory['creators'][creator_key]['counter'] = next_seq

with open('memory/creator-styles.json', 'w', encoding='utf-8') as f:
    json.dump(memory, f, ensure_ascii=False, indent=2)
```

---

## 常见问题处理

### 网络受限，无法下载 Whisper 模型
→ 使用帧 OCR（Step 3b）或逐帧观察（Step 3c）

### VTT 字幕文件无法在 `<track>` 中用 data URI
→ 必须用 Blob URL（`URL.createObjectURL`），参见 html-template-guide.md

### Slide 数量过多（>20）
→ 合并相关内容，优先保留每个章节的开头和结尾

### 设计风格不确定
→ 读取 references/design-systems.md 的选择矩阵
→ 向用户说明判断理由后确认

### 新的 creator，但与已知 creator 主题相近
→ 仍然创建独立记录，**不复用**其他 creator 的条目
→ 但可以使用相同的 design_style

### JS 报错 `Cannot read properties of null (reading 'addEventListener')`
→ 检查所有 `getElementById` 调用，对应元素必须存在于 DOM
→ 删除了某个 DOM 元素后，必须同时删除其 JS 引用

---

## 输出验证清单

```
□ HTML 文件可在手机浏览器直接打开
□ 点击屏幕可播放音频
□ 字幕与音频内容同步（±5秒内）
□ Slide 在正确时间切换
□ Story Bar 进度条实时更新
□ 手机竖屏下内容不挤压，有垂直居中感
□ VTT 文件独立保存，可供后续复用
□ memory/creator-styles.json 已更新
□ 文件命名符合规范：{seq:03d}-{creator}-{title}.html
```
