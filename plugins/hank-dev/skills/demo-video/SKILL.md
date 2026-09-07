---
name: demo-video
description: 把一个功能或 PR 录成带旁白的演示视频：浏览器截图 + TTS 配音 + ffmpeg 合成 MP4，让审查者看着改动跑起来而不是从 diff 里脑补。触发词包括 "/hank-dev:demo-video"、"录个 demo"、"把这个 PR 录成视频"、"demo video" 和 "演示视频"。
version: 1.0.0
---

# hank-dev:demo-video

产出一个 MP4：每一幕是一张运行中应用的截图，按对应旁白的时长停留。改编自 Damien Tanner 的 `demo-video` gist，原版硬编码了他自己项目的 `api/.dev.vars` 路径和私有 R2 桶，这一版去掉了项目耦合，默认走零 API key 的本地 TTS。

Adapted from Damien Tanner's `demo-video` gist. The upstream version hardcodes his own project layout and pushes to his own R2 bucket; this version removes both couplings and defaults to local TTS with no API key.

## 适用范围 / Scope

通用开发工具，不绑定任何客户或仓库，任何能在本地跑起来的项目都可以用。输出是用户应用的录像，未经明确要求不得上传到任何地方。

Generic developer tool, not tied to any client or repository. The output is a recording of the user's application, so never upload it anywhere unless explicitly asked.

## 前置检查 / Prerequisites

逐项确认，缺什么就报什么，不要猜：

```bash
command -v ffmpeg
command -v say
say -v '?' | grep -E 'en_(AU|US|GB)'
```

截图后端按以下顺序选择：本次会话已连接的浏览器 MCP（Playwright、Chrome DevTools）优先；其次 `npx agent-browser`（vercel-labs，免安装）；项目本身已依赖 Playwright 时用 `npx playwright`。未经询问不得安装任何浏览器自动化栈。

Pick a screenshot backend in this order: a browser MCP already connected in the session, then `npx agent-browser`, then `npx playwright` if the project already depends on it. Never install a browser automation stack without asking.

## 已知失败：`say` 在 agent 沙箱里静默失败

实测于 macOS 25.4，2026-09-07。`say -o out.aiff "text"` 在 Claude Code 的 Bash 沙箱里**退出码为 0，stderr 为空，写出一个结构合法的 4096 字节 AIFF，音频负载全是零**。语音合成守护进程在沙箱内不可达，而 `say` 不报告这件事。成片除了没有声音以外一切正常，整条流水线没有任何一环会抱怨。

另有一个相关行为：传入一个本机未安装的声音名（例如上游写的 `Ava`）会让 `say` 挂死而不是报错。

Verified on macOS 25.4: inside the agent sandbox, `say -o` exits 0 with empty stderr while writing a structurally valid 4096-byte AIFF whose audio payload is all zeroes. The resulting video is correct except that it is silent, and nothing in the pipeline complains. Separately, passing an uninstalled voice name makes `say` hang rather than error.

两条后果：绝不信任 `say` 的退出码，必须走下面 Step 3 的断言；断言失败时请用户在沙箱外自己跑 TTS（在输入框敲 `! say -v Karen -o tmp/video/scene1.aiff "..."`），或改用托管 TTS API，不要带着死音频继续走 ffmpeg。

## 流程 / Process

### Step 1：先敲定脚本，再录任何东西

把分镜和旁白写成文本给用户过目，确认之后才开始截图。每一幕是一张截图加一到两句旁白，三到六幕是有用的区间。这一步搞错整段渲染都要重做。

```
scene1  初始状态    "Here is the booking list before the change."
scene2  触发功能    "Clicking Reschedule now opens the inline picker."
scene3  结果        "The slot updates without a full page reload."
```

### Step 2：截图

启动应用，逐幕驱动浏览器，PNG 存到项目根的 `tmp/video/`，按幕序命名（`scene1_landing.png`）。全程使用同一个 viewport，尺寸不一致会让 concat 失败或者输出黑边。

### Step 3：生成旁白音频并断言

```bash
say -v Karen -o tmp/video/scene1.aiff "Here is the booking list before the change."
```

`Karen` 是 en_AU，`Samantha` 是 en_US，`Daniel` 是 en_GB。逐条串行生成，一幕一条命令。

生成完必须断言每个文件都是真音频：

```bash
for f in tmp/video/scene*.aiff; do
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
  s=$(stat -f%z "$f")
  echo "$f duration=${d:-NONE} bytes=$s"
done
```

duration 为 `N/A`，或者大小卡在 4096 字节附近，就是静音输出，按上一节处理，不要继续。

### 可选：托管 TTS

只在用户有 key 且主动要求时使用。key 从项目自己的 env 文件读取，绝不打印。Inworld 的两个上游坑值得保留：并发请求会被拒绝并报成误导性的 `SESSION_TOKEN_INVALID`，所以要用 `&&` 串行；单次请求上限 2000 字符。返回文件只有几个字节说明是 API 报错，用 `| head -c 500` 读原始响应。

```bash
curl -s -X POST "https://api.inworld.ai/tts/v1/voice" \
  -H "Authorization: Basic ${INWORLD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"text":"...","voiceId":"<voice>","modelId":"inworld-tts-1.5-max",
       "audioConfig":{"audioEncoding":"MP3","sampleRateHertz":22050}}' \
  | jq -r '.audioContent' | base64 --decode > tmp/video/scene1.mp3
```

### Step 4：渲染交给子代理

截图和通过断言的音频都就位后，把 ffmpeg 工作交给后台子代理，否则 ffmpeg 的输出会灌满主上下文。把文件名和下面的命令一起给它。

单幕：

```bash
ffmpeg -loop 1 -i tmp/video/scene1_landing.png -i tmp/video/scene1.aiff \
  -c:v libx264 -tune stillimage -c:a aac -ar 22050 -b:a 128k \
  -pix_fmt yuv420p -shortest -y tmp/video/scene1.mp4
```

截图像素为奇数时补 `-vf "scale=trunc(iw/2)*2:trunc(ih/2)*2"`，libx264 配 yuv420p 不接受奇数尺寸。

拼接：

```bash
cd tmp/video
printf "file 'scene1.mp4'\nfile 'scene2.mp4'\nfile 'scene3.mp4'\n" > concat.txt
ffmpeg -f concat -safe 0 -i concat.txt -c copy -y demo.mp4
```

流复制只在所有片段编码和分辨率一致时成立，拼出坏文件就改成重编码。

### Step 5：交付

```bash
open tmp/video/demo.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 tmp/video/demo.mp4
```

报告路径和时长。`tmp/video/` 没被忽略的话补进 `.gitignore`。

## 分享（仅在被要求时）

上游默认把成片推到 Cloudflare R2 公开桶，不要这么做，那等于把用户应用的录像发布到公开 URL。用户要分享链接时先确认目标桶：

```bash
npx wrangler r2 object put "<bucket>/$(git branch --show-current).mp4" \
  --file tmp/video/demo.mp4 --content-type "video/mp4" --remote
```

## 反模式 / Anti-patterns

- 信任 `say` 的退出码。它会一边报成功一边写静音。
- 给 `say` 传未安装的声音名。挂死而不是报错。
- 旁白脚本没确认就开始截图。渲染白做。
- 对托管 TTS 并发调用。静默且标签误导的失败。
- 各幕 viewport 尺寸不一致。拼接损坏或输出黑边。
- 未经询问上传成片。

## 验证记录 / Verified

ffmpeg 8.0.1 on macOS 25.4，2026-09-07：三幕合成音轨渲染并拼接，产出 6.05 秒的 h264/aac 1280x720 MP4。视频链路本身可靠，只有 `say` 那一步带上面的沙箱警告。

Three synthetic scenes rendered and concatenated into a 6.05s h264/aac 1280x720 MP4. The video chain is sound; only the `say` step carries the sandbox caveat above.
