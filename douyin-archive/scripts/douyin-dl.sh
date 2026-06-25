#!/usr/bin/env bash
# douyin-dl.sh — 抖音视频归档器
# 一条命令：下载视频 + 字幕(srt) + 口播文字稿(txt) + 文案/元数据，归到独立文件夹，刷新检索地图。
#
# 用法：
#   ./douyin-dl.sh <抖音视频链接或ID> [自定义文件夹名]
# 示例：
#   ./douyin-dl.sh 'https://www.douyin.com/video/7627721752642194724'
#   ./douyin-dl.sh 'https://www.douyin.com/user/self?modal_id=7627721752642194724'
#   ./douyin-dl.sh 7627721752642194724
set -euo pipefail

# ===================== 配置（定制点）=====================
ARCHIVE_ROOT="{ARCHIVE_ROOT}"      # 归档根目录
PROXY_SSH_ALIAS="{CN_PROXY_SSH_ALIAS}"               # 中国出口 SSH 别名（见 ~/.ssh/config）
SOCKS_PORT=1090                                 # 本地 SOCKS5 端口
API_PORT=5555                                   # DouK Web API 端口
WHISPER_MODEL="mlx-community/whisper-large-v3-turbo"
BROWSER="chrome"                               # cookie 来源浏览器（首次会弹钥匙串，点"允许"）
# =========================================================

TOOLS="$ARCHIVE_ROOT/.tools"
VENV="$TOOLS/venv"
DOUK="$TOOLS/TikTokDownloader"
PY="$VENV/bin/python"
YTDLP="$VENV/bin/yt-dlp"

log(){ printf '\033[1;36m[douyin-dl]\033[0m %s\n' "$*" >&2; }
die(){ printf '\033[1;31m[douyin-dl][ERROR]\033[0m %s\n' "$*" >&2; exit 1; }

[ $# -ge 1 ] || die "用法: $0 <抖音视频链接或ID> [自定义文件夹名]"
[ -x "$PY" ] || die "venv 缺失：${VENV}（见 .tools 重建说明）"

# ---- 解析 video id ----
RAW="$1"
extract_id(){
  local s="$1"
  [[ "$s" =~ modal_id=([0-9]+) ]] && { echo "${BASH_REMATCH[1]}"; return; }
  [[ "$s" =~ /video/([0-9]+) ]]   && { echo "${BASH_REMATCH[1]}"; return; }
  [[ "$s" =~ ^[0-9]+$ ]]          && { echo "$s"; return; }
  if [[ "$s" =~ v\.douyin\.com ]]; then  # 分享短链：跟随重定向
    local loc; loc=$(curl -sIL --max-time 20 "$s" | grep -i '^location:' | tail -1 || true)
    [[ "$loc" =~ /video/([0-9]+) ]] && { echo "${BASH_REMATCH[1]}"; return; }
    [[ "$loc" =~ modal_id=([0-9]+) ]] && { echo "${BASH_REMATCH[1]}"; return; }
  fi
  return 1
}
VID=$(extract_id "$RAW") || die "无法解析视频ID：$RAW"
log "视频ID: $VID"

# ---- 1. 中国出口隧道 ----
if pgrep -f "ssh -D $SOCKS_PORT " >/dev/null; then
  log "隧道已在 (SOCKS5 :$SOCKS_PORT)"
else
  log "建立中国出口隧道（${PROXY_SSH_ALIAS}）…"
  ssh -D "$SOCKS_PORT" -N -f -o ExitOnForwardFailure=yes -o ConnectTimeout=15 "$PROXY_SSH_ALIAS" \
    || die "SSH 隧道失败（检查 ~/.ssh/config 的 ${PROXY_SSH_ALIAS}）"
  sleep 2
fi
EXIT_CC=$(curl -s --max-time 15 --socks5-hostname "127.0.0.1:$SOCKS_PORT" https://ipinfo.io/country 2>/dev/null || true)
[ "$EXIT_CC" = "CN" ] && log "出口IP确认：中国 🇨🇳" || log "⚠️ 出口IP=${EXIT_CC}（非CN，抖音可能拒绝；检查代理）"

# ---- 2. DouK Web API 服务 ----
if lsof -iTCP:$API_PORT -sTCP:LISTEN -P -n >/dev/null 2>&1; then
  log "DouK API 已在 :$API_PORT"
else
  log "启动 DouK Web API…"
  # 幂等种入免责声明/语言，跳过首次交互提示
  sqlite3 "$DOUK/Volume/DouK-Downloader.db" \
    "INSERT OR REPLACE INTO config_data VALUES('Disclaimer',1);
     INSERT OR REPLACE INTO option_data VALUES('Language','zh_CN');" 2>/dev/null || true
  ( cd "$DOUK" && printf '7\n' | "$PY" main.py >/tmp/douk-server.log 2>&1 & )
  for i in $(seq 1 30); do
    lsof -iTCP:$API_PORT -sTCP:LISTEN -P -n >/dev/null 2>&1 && break
    sleep 1
  done
  lsof -iTCP:$API_PORT -sTCP:LISTEN -P -n >/dev/null 2>&1 \
    || die "DouK API 启动超时（见 /tmp/douk-server.log）"
  log "DouK API 就绪"
fi

# ---- 3. 取 cookie（从浏览器，首次弹钥匙串点"允许"）----
log "读取浏览器 cookie（${BROWSER}）…"
CK_TXT="$TOOLS/.dy-cookies.txt"
"$YTDLP" --cookies-from-browser "$BROWSER" --cookies "$CK_TXT" --skip-download \
  "https://www.douyin.com/" >/dev/null 2>&1 || true
COOKIE=$(grep -iE "douyin" "$CK_TXT" | grep -v '^#' | awk -F'\t' 'NF==7 && $6!="" {printf "%s=%s; ", $6,$7}')
N=$(printf '%s' "$COOKIE" | tr ';' '\n' | grep -c '=' || true)
[ "$N" -ge 5 ] || die "cookie 字段过少($N)，浏览器是否登录/访问过抖音？"
log "cookie 字段数：$N"

# ---- 4. 归档（取数据→下视频→转写→写 meta→刷 INDEX）----
shift || true
"$PY" "$TOOLS/archive.py" "$VID" "$COOKIE" "socks5://127.0.0.1:$SOCKS_PORT" \
  "$ARCHIVE_ROOT" "$WHISPER_MODEL" "${1:-}"

log "归档完成。检索地图：$ARCHIVE_ROOT/INDEX.md"
