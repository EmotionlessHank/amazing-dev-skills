"""
token_auth.py — HMAC 派生 token 的最小鉴权片段（Flask 示例）

设计：token = HMAC(SECRET, 固定串)[:24]。
- 不存 token，只存 SECRET（服务器 .env，600）；token 由 SECRET 现算，可随时换 SECRET 吊销。
- 比对用 hmac.compare_digest 防时序侧信道。
- 数据路径用环境变量，避免多组件写死相对路径。
"""

import hashlib
import hmac
import os
import pathlib

SECRET = os.environ.get("APP_SECRET", "dev-change-me").encode()
DATA = pathlib.Path(os.environ.get("DATA_PATH", "data.json"))  # 多组件共享同一份


def expected_token() -> str:
    return hmac.new(SECRET, b"app-v1", hashlib.sha256).hexdigest()[:24]


def check(req):
    from flask import abort
    if not hmac.compare_digest(req.args.get("token", ""), expected_token()):
        abort(403)


# ---- Flask 用法 ----
# from flask import Flask, request, send_file
# app = Flask(__name__)
#
# @app.get("/healthz")          # 不鉴权，给探活/证书校验
# def health(): return "ok"
#
# @app.get("/d")                # 受保护页面
# def page():
#     check(request)
#     return send_file("index.html")
#
# if __name__ == "__main__":
#     import sys
#     if "--token" in sys.argv:  # 打印当前有效 token（生成链接用，别打印到对话）
#         print(expected_token()); sys.exit(0)
#     app.run(host="127.0.0.1", port=8848)   # 只监听 localhost
