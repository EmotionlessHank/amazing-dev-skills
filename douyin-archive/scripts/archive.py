#!/usr/bin/env python3
"""抖音单视频归档器（被 douyin-dl.sh 调用）。

流程：调 DouK /douyin/detail 取数据 → 下载 mp4 → ffmpeg 抽音频 →
mlx-whisper 转写出「字幕(srt) + 口播文字稿(txt)」→ 写 meta.md → 刷新 INDEX.md。

用法：archive.py <video_id> <cookie> <proxy> <archive_root> <whisper_model> [folder_name]
"""
import sys
import os
import re
import json
import subprocess
import urllib.request

API = "http://127.0.0.1:5555/douyin/detail"


def fetch_detail(vid: str, cookie: str, proxy: str) -> dict:
    # 关键：去掉尾部的 "; " 等空白，否则 httpx/h11 报 Illegal header value
    cookie = cookie.strip().rstrip(";").strip()
    body = json.dumps({"detail_id": vid, "cookie": cookie, "proxy": proxy}).encode()
    req = urllib.request.Request(
        API, data=body, headers={"Content-Type": "application/json"}
    )
    resp = json.load(urllib.request.urlopen(req, timeout=180))
    data = resp.get("data") or {}
    if not isinstance(data, dict) or not data:
        raise SystemExit(f"获取作品数据失败：{resp.get('message')}")
    return data


def download_video(url, dst: str, cookie: str, socks: str):
    if isinstance(url, list):
        url = url[0]
    cmd = [
        "curl", "-sL", "--max-time", "600", "--socks5-hostname", socks,
        "-H", "Referer: https://www.douyin.com/",
        "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "-b", cookie, "-o", dst, url,
    ]
    subprocess.run(cmd, check=True)
    # 校验确实是媒体文件
    out = subprocess.run(["file", dst], capture_output=True, text=True).stdout
    if "ISO Media" not in out and "MP4" not in out:
        raise SystemExit(f"下载结果不是有效视频：{out.strip()}")


def srt_time(t: float) -> str:
    h = int(t // 3600); m = int((t % 3600) // 60); s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def transcribe(wav: str, model: str, folder: str):
    import mlx_whisper
    r = mlx_whisper.transcribe(
        wav, path_or_hf_repo=model, language="zh",
        initial_prompt="以下是普通话视频的口播内容。",
    )
    # 口播文字稿（纯文本）
    with open(os.path.join(folder, "transcript.txt"), "w") as f:
        f.write(r["text"].strip() + "\n")
    # 字幕（带时间轴 srt）
    with open(os.path.join(folder, "subtitle.srt"), "w") as f:
        for i, seg in enumerate(r.get("segments", []), 1):
            f.write(f"{i}\n{srt_time(seg['start'])} --> {srt_time(seg['end'])}\n"
                    f"{seg['text'].strip()}\n\n")
    return r["text"].strip()


def write_meta(folder: str, d: dict, vid: str):
    tags = re.findall(r"#([^\s#]+)", d.get("desc", ""))
    with open(os.path.join(folder, "meta.md"), "w") as f:
        f.write(f"# {d.get('nickname','?')} · {first_title(d.get('desc',''))}\n\n")
        f.write(f"- 视频ID：`{vid}`\n")
        f.write(f"- 作者：{d.get('nickname','')}（@{d.get('unique_id','')}）\n")
        f.write(f"- 发布时间：{d.get('create_time','')}\n")
        f.write(f"- 时长：{d.get('duration','')}\n")
        f.write(f"- 链接：{d.get('share_url','')}\n")
        f.write(f"- 数据：👍{d.get('digg_count','')} 💬{d.get('comment_count','')} "
                f"⭐{d.get('collect_count','')} ↗{d.get('share_count','')}\n")
        if tags:
            f.write(f"- 标签：{' '.join('#'+t for t in tags)}\n")
        f.write(f"\n## 文案（作者描述）\n\n{d.get('desc','')}\n")
    return tags


def first_title(desc: str, n: int = 24) -> str:
    line = re.sub(r"#[^\s#]+", "", desc).strip().split("\n")[0]
    return (line[:n] + "…") if len(line) > n else line or "(无标题)"


def update_index(root: str, vid: str, d: dict, folder_name: str, tags):
    idx = os.path.join(root, "INDEX.md")
    header = (
        "# 抖音视频归档检索地图\n\n"
        "> 每行一个视频。检索：`grep` 本表找方向，再 `grep -r 关键词 <文件夹>/transcript.txt` 钻内容。\n\n"
        "| 发布日期 | 作者 | 标题 | 标签 | 视频ID | 文件夹 |\n"
        "|---|---|---|---|---|---|\n"
    )
    if not os.path.exists(idx):
        open(idx, "w").write(header)
    body = open(idx).read()
    if vid in body:  # 幂等：已存在则不重复追加
        return
    date = (d.get("create_time", "") or "")[:10]
    row = (f"| {date} | {d.get('nickname','')} | {first_title(d.get('desc',''))} "
           f"| {' '.join('#'+t for t in tags)} | `{vid}` | `{folder_name}/` |\n")
    open(idx, "a").write(row)


def main():
    vid, cookie, proxy, root, model = sys.argv[1:6]
    cookie = cookie.strip().rstrip(";").strip()  # 去尾部空白，防 Illegal header value
    folder_name = sys.argv[6] if len(sys.argv) > 6 else None
    socks = proxy.replace("socks5://", "")

    print("→ 取作品数据…")
    d = fetch_detail(vid, cookie, proxy)
    date = (d.get("create_time", "") or "0000-00-00")[:10]
    folder_name = folder_name or f"{date}_{vid}"
    folder = os.path.join(root, folder_name)
    os.makedirs(folder, exist_ok=True)
    print(f"→ 归档目录：{folder}")

    print("→ 下载视频…")
    download_video(d["downloads"], os.path.join(folder, "video.mp4"), cookie, socks)

    print("→ 写元数据/文案…")
    tags = write_meta(folder, d, vid)

    print("→ 抽音频…")
    wav = os.path.join(folder, ".audio.wav")
    subprocess.run(
        ["ffmpeg", "-y", "-i", os.path.join(folder, "video.mp4"),
         "-vn", "-ac", "1", "-ar", "16000", wav],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    print(f"→ Whisper 转写（{model}，首次会下模型）…")
    text = transcribe(wav, model, folder)
    os.remove(wav)

    update_index(root, vid, d, folder_name, tags)
    print(f"✅ 完成：{folder}")
    print(f"   作者：{d.get('nickname')} | 时长：{d.get('duration')} | 文字稿 {len(text)} 字")


if __name__ == "__main__":
    main()
