---
name: douyin-archive
description: 下载抖音视频并归档成可检索语料（视频 + 字幕srt + 口播文字稿txt + 元数据）。当用户说 "/下抖音"、"下抖音"、"抖音存档"、"抖音视频归档"、"下载抖音视频"、"抖音转文字稿/字幕" 并给出抖音链接或视频ID时触发。
user_invocable: true
---

# douyin-archive — 抖音视频归档为可检索语料

一条命令把抖音视频抓成**结构化、可全文检索的本地语料**：每视频一文件夹（视频 + 带时间轴字幕 + 口播文字稿 + 元数据）+ 根目录 INDEX 检索地图。用于后续「文字稿快速检索 + LLM 凝练」。

## 触发条件

用户给出抖音视频链接（`douyin.com/video/...`、含 `modal_id=` 的主页/收藏夹链接、`v.douyin.com` 短链）或纯数字视频ID，要求下载 / 存档 / 转文字稿。

## 为什么不用 yt-dlp（实测结论）

- **yt-dlp 下不了抖音**：a_bogus 反爬签名变更，解析器长期失修（cookie / 浏览器指纹 / 中国 IP 全试无效）→ 改用 [TikTokDownloader/DouK](https://github.com/JoeanAmier/TikTokDownloader) 的 Web API 模式（自己算 a_bogus）。
- **抖音无字幕轨**：画面字幕是硬字幕。口播文字稿走 `ffmpeg 抽音频 → whisper ASR`。
- **海外 IP 被风控**：抖音接口对非中国 IP 返回空 → 必须经中国大陆出口代理（`ssh -D` 隧道）。

## 前置依赖

```bash
brew install ffmpeg sqlite
python3 -m venv {ARCHIVE_ROOT}/.tools/venv
{ARCHIVE_ROOT}/.tools/venv/bin/pip install -U "yt-dlp[default,curl-cffi]" mlx-whisper   # 非 Apple Silicon 换 faster-whisper
git clone --depth 1 https://github.com/JoeanAmier/TikTokDownloader.git {ARCHIVE_ROOT}/.tools/TikTokDownloader
{ARCHIVE_ROOT}/.tools/venv/bin/pip install -r {ARCHIVE_ROOT}/.tools/TikTokDownloader/requirements.txt
```
> clone 第三方仓后**先排雷再装**：查无 install 钩子、无 `curl …|sh` 远程执行。

另需：中国大陆出口 SSH 别名（填进脚本 `CN_PROXY_SSH_ALIAS`）、浏览器登录过抖音（cookie 从浏览器读，首次弹钥匙串点「允许」单次，勿「始终允许」）。

## 安装

1. 复制 `scripts/douyin-dl.sh` → `{ARCHIVE_ROOT}/douyin-dl.sh`，`scripts/archive.py` → `{ARCHIVE_ROOT}/.tools/archive.py`。
2. 改 `douyin-dl.sh` 顶部配置：`ARCHIVE_ROOT`、`CN_PROXY_SSH_ALIAS`（至少这两个）。
3. `chmod +x {ARCHIVE_ROOT}/douyin-dl.sh`。

## 执行

```bash
{ARCHIVE_ROOT}/douyin-dl.sh '<抖音链接或ID>' [自定义文件夹名]
```
脚本自动：建中国出口隧道 → 启 DouK API → 读浏览器 cookie → 取数据 → 下视频 → 抽音频 → Whisper 转写 → 写 meta → 刷 INDEX.md。完成后向用户汇报产物路径。

## 产物结构

```
{ARCHIVE_ROOT}/INDEX.md                    # 检索地图(日期|作者|标题|标签|ID|文件夹)
{ARCHIVE_ROOT}/<发布日期>_<视频ID>/
├── video.mp4          # 原片
├── subtitle.srt       # 字幕(带时间轴)
├── transcript.txt     # 口播文字稿(纯文本)
└── meta.md            # 作者/文案/标签/数据/链接
```
检索：`grep` INDEX.md 找方向 → `grep -r 关键词 {ARCHIVE_ROOT}/*/transcript.txt` 钻内容 → 喂 LLM 凝练。

## 排错（按频率）

- **cookie 字段过少 / 取数据失败**：浏览器没登录抖音；或 cookie 串尾部带 `; ` 空格 → h11 报 `Illegal header value`（脚本已 strip，自写调用务必 `.strip().rstrip(";")`）。
- **出口非 CN**：抖音返回空。确认 `ssh <别名>` 通、`curl --socks5-hostname` 出口是 CN。
- **`unbound variable` 带乱码**：macOS bash 3.2 把全角符号并进变量名 → 紧贴中文的 `$VAR` 写成 `${VAR}`。
- **DouK 菜单卡首次提示**：脚本已 sqlite 幂等种入 `Disclaimer=1`/`Language=zh_CN`。
