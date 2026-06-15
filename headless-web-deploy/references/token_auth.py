"""
token_auth.py — Minimal HMAC-derived token auth snippet (Flask example)

Design: token = HMAC(SECRET, fixed-string)[:24].
- The token is never stored — only the SECRET is (in server .env, chmod 600).
  The token is derived on demand from SECRET and can be revoked by rotating SECRET.
- Comparison uses hmac.compare_digest to prevent timing side-channel attacks.
- Data path comes from an environment variable to avoid multiple components hardcoding relative paths.
"""

import hashlib
import hmac
import os
import pathlib

SECRET = os.environ.get("APP_SECRET", "dev-change-me").encode()
DATA = pathlib.Path(os.environ.get("DATA_PATH", "data.json"))  # shared across components


def expected_token() -> str:
    return hmac.new(SECRET, b"app-v1", hashlib.sha256).hexdigest()[:24]


def check(req):
    from flask import abort
    if not hmac.compare_digest(req.args.get("token", ""), expected_token()):
        abort(403)


# ---- Flask usage ----
# from flask import Flask, request, send_file
# app = Flask(__name__)
#
# @app.get("/healthz")          # no auth — for health checks / ACME validation
# def health(): return "ok"
#
# @app.get("/d")                # protected route
# def page():
#     check(request)
#     return send_file("index.html")
#
# if __name__ == "__main__":
#     import sys
#     if "--token" in sys.argv:  # print current valid token (for link generation — never print to conversation)
#         print(expected_token()); sys.exit(0)
#     app.run(host="127.0.0.1", port=8848)   # listen on localhost only
