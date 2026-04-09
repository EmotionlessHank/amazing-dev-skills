---
name: live-photo
description: 将视频转为 iPhone Live Photo 素材。当用户说 "/live-photo"、"做成 live photo"、"动态壁纸"、"live wallpaper" 时触发。从视频提取封面 + 转 HEVC MOV + makelive 配对，最后提示用户拖入 Mac 照片 app。
user_invocable: true
---

# Live Photo — 视频转 iPhone Live Photo 素材

## 触发条件

用户说 `/live-photo`、"做成 live photo"、"动态壁纸"、"live wallpaper"，并提供一个视频文件路径。

## 前置依赖

- `ffmpeg` / `ffprobe` — 视频处理
- `makelive` — Live Photo 元数据配对（`pipx install makelive --python python3.13`）
- `exiftool` — 元数据验证（`brew install exiftool`）

如果缺少依赖，先提示用户安装，不要静默跳过。

## 执行流程

### 1. 获取视频信息

```bash
ffprobe -v quiet -print_format json -show_streams "<视频路径>"
```

确认分辨率、编码、时长。告知用户视频基本信息。

### 2. 提取封面图

从第一帧提取 JPEG 封面（用户可指定时间点，默认第一帧）：

```bash
ffmpeg -y -i "<视频路径>" -vframes 1 -q:v 2 -update 1 "<输出目录>/<基础名>.jpg"
```

### 3. 转换视频为 HEVC MOV

将视频转为 iPhone Live Photo 兼容格式：
- **编码**：HEVC (H.265)，使用 `hevc_videotoolbox` 硬件加速
- **时长**：截取前 3 秒（iPhone Live Photo 标准时长），用户可自定义
- **容器**：MOV
- **音频**：去除（`-an`）
- **Tag**：`hvc1`

```bash
ffmpeg -y -i "<视频路径>" -t 3 -c:v hevc_videotoolbox -q:v 65 -tag:v hvc1 -an "<输出目录>/<基础名>.mov"
```

### 4. 写入配对元数据

使用 `makelive` 为图片和视频写入相同的 `ContentIdentifier`：

```bash
makelive "<基础名>.jpg" "<基础名>.mov"
```

> 注意：makelive 要求图片和视频**同名**（仅扩展名不同），放在同一目录下。

### 5. 验证配对

```bash
exiftool -ContentIdentifier "<基础名>.jpg" "<基础名>.mov"
```

确认两个文件的 `ContentIdentifier` 一致。

### 6. 打开文件夹并提示用户

```bash
open "<输出目录>"
```

输出最终提示：

```
Live Photo 素材已生成：
- <基础名>.jpg（封面图，XXX KB）
- <基础名>.mov（动态视频，XXX MB）

请在 Finder 中同时选中这两个文件，一起拖入 Mac 照片 app。
导入后确认照片显示 "LIVE" 标记，开启 iCloud 照片会自动同步到 iPhone。
```

## 命名规则

- 输出文件与源视频放在**同一目录**
- 基础名 = 源视频文件名去掉扩展名，空格替换为下划线
- 示例：`911 touring 5s video.mp4` → `911_touring_5s_video.jpg` + `911_touring_5s_video.mov`

## 用户可选参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 封面时间点 | `0` | 从视频哪一秒提取封面，如 `1.5` |
| 视频时长 | `3` 秒 | Live Photo 动态部分时长 |
| 起始时间 | `0` | 从视频哪一秒开始截取 |

用户未指定时使用默认值，不主动询问。

## 注意事项

- 如果 `makelive` 未安装，引导用户执行：`pipx install makelive --python python3.13`
- 不要用 AirDrop 传输，AirDrop 可能丢失配对元数据
- 必须通过 Mac 照片 app 导入才能正确识别 Live Photo
