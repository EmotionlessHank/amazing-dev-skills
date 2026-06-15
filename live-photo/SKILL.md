---
name: live-photo
description: Convert a video into iPhone Live Photo assets. Triggers when the user says "/live-photo", "make it a live photo", "live wallpaper", or "dynamic wallpaper". Extracts a cover frame + transcodes to HEVC MOV + pairs with makelive, then prompts the user to drag the files into the Mac Photos app.
user_invocable: true
---

# Live Photo — Convert Video to iPhone Live Photo Assets

## Trigger Conditions

User says `/live-photo`, "make it a live photo", "live wallpaper", or "dynamic wallpaper", and provides a video file path.

## Prerequisites

- `ffmpeg` / `ffprobe` — video processing
- `makelive` — Live Photo metadata pairing (`pipx install makelive --python python3.13`)
- `exiftool` — metadata verification (`brew install exiftool`)

If any dependency is missing, prompt the user to install it before proceeding — do not silently skip.

## Execution Flow

### 1. Inspect the video

```bash
ffprobe -v quiet -print_format json -show_streams "<video_path>"
```

Confirm resolution, codec, and duration. Report the basic video info to the user.

### 2. Extract the cover image

Extract a JPEG cover from the first frame (user may specify a timestamp; default is the first frame):

```bash
ffmpeg -y -i "<video_path>" -vframes 1 -q:v 2 -update 1 "<output_dir>/<base_name>.jpg"
```

### 3. Transcode video to HEVC MOV

Convert the video to an iPhone Live Photo-compatible format:
- **Codec**: HEVC (H.265) using `hevc_videotoolbox` hardware acceleration
- **Duration**: clip to 3 seconds (iPhone Live Photo standard), user-configurable
- **Container**: MOV
- **Audio**: stripped (`-an`)
- **Tag**: `hvc1`

```bash
ffmpeg -y -i "<video_path>" -t 3 -c:v hevc_videotoolbox -q:v 65 -tag:v hvc1 -an "<output_dir>/<base_name>.mov"
```

### 4. Write pairing metadata

Use `makelive` to write a shared `ContentIdentifier` to both the image and the video:

```bash
makelive "<base_name>.jpg" "<base_name>.mov"
```

> Note: `makelive` requires the image and video to have **the same base name** (differing only in extension) and be in the same directory.

### 5. Verify pairing

```bash
exiftool -ContentIdentifier "<base_name>.jpg" "<base_name>.mov"
```

Confirm both files share the same `ContentIdentifier`.

### 6. Open folder and prompt the user

```bash
open "<output_dir>"
```

Display the final prompt:

```
Live Photo assets generated:
- <base_name>.jpg (cover image, XXX KB)
- <base_name>.mov (motion video, XXX MB)

In Finder, select both files simultaneously and drag them into the Mac Photos app.
After import, confirm the photo shows the "LIVE" badge. With iCloud Photos enabled, it will sync to iPhone automatically.
```

## Naming Convention

- Output files are placed in the **same directory** as the source video
- Base name = source video filename with the extension removed, spaces replaced with underscores
- Example: `911 touring 5s video.mp4` → `911_touring_5s_video.jpg` + `911_touring_5s_video.mov`

## Optional Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| Cover timestamp | `0` | Second in the video to extract the cover frame from (e.g. `1.5`) |
| Video duration | `3` seconds | Duration of the Live Photo motion portion |
| Start time | `0` | Second in the video to begin the clip from |

Use defaults when the user does not specify — do not proactively ask.

## Notes

- If `makelive` is not installed, guide the user to run: `pipx install makelive --python python3.13`
- Do not transfer via AirDrop — AirDrop may strip the pairing metadata
- The files must be imported through the Mac Photos app for Live Photo to be recognized correctly
