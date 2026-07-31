#!/usr/bin/env python3
import json
import os
import pwd
import stat
import sys
import urllib.parse
import urllib.request

TELEGRAM_LIMIT = 4096


def default_env_path():
    return os.environ.get("WORKTREE_CLEANUP_RELAY_ENV", os.path.expanduser("~/.hermes/.env"))


def load_env(path):
    st = os.stat(path)
    owner = pwd.getpwuid(st.st_uid).pw_name
    expected_owner = os.environ.get("WORKTREE_CLEANUP_RELAY_ENV_OWNER", owner)
    mode = stat.S_IMODE(st.st_mode)
    if owner != expected_owner or mode != 0o600:
        raise RuntimeError("relay .env owner or mode is invalid")
    values = {}
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def send_message(text, env_path=None):
    env_path = env_path or default_env_path()
    if not text.strip():
        raise RuntimeError("refusing to send an empty message")
    if len(text.encode("utf-8")) > TELEGRAM_LIMIT:
        raise RuntimeError("refusing to send an oversized message")
    values = load_env(env_path)
    token = values.get("TELEGRAM_BOT_TOKEN")
    chat_id = values.get("TELEGRAM_HOME_CHANNEL")
    if not token or not chat_id:
        raise RuntimeError("relay .env is missing Telegram configuration")
    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read()
        status_code = getattr(response, "status", response.getcode())
    if status_code != 200:
        raise RuntimeError("Telegram HTTP status failed")
    try:
        parsed = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Telegram response is not JSON") from exc
    if parsed.get("ok") is not True:
        raise RuntimeError("Telegram API returned failure")
    return True


def main():
    text = sys.stdin.read()
    try:
        send_message(text)
    except Exception as exc:
        print(f"send failed: {exc}", file=sys.stderr)
        return 1
    print("send succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
