---
name: headless-web-deploy
description: Deploy a small web application (Flask/FastAPI/Node/static site) to a headless server without a domain (AWS Lightsail / EC2 / VPS), using Caddy + sslip.io for automatic Let's Encrypt certificates, systemd persistence, and HMAC token authentication — delivering a single HTTPS link openable in a phone browser or Telegram's in-app browser. Triggers when the user says "deploy to server", "publish a web page", "sslip.io", "Caddy reverse proxy", "domain-free HTTPS", or "dashboard on server".
version: 1.0.0
author: Hank
triggers:
  - deploy web app to server
  - publish web application
  - domain-free https deployment
  - sslip.io
  - caddy reverse proxy
  - deploy dashboard
  - /headless-web-deploy
---

# headless-web-deploy — Domain-Free Web App One-Command Deployment

Deploy a locally working small web application to a headless server, exposing only a single **HTTPS link with a token** to the outside world — directly openable in a phone browser or Telegram's in-app browser.

## Use Cases

- Personal project, **no domain / don't want one**, but needs HTTPS (Telegram and iOS Safari reject self-signed certificates — a valid CA-signed cert is required).
- Headless server (Lightsail / EC2 / VPS) with an `ssh` alias and `sudo` access.
- Application is a single-process HTTP service (Flask/FastAPI/Express/static), listening on localhost at some port.
- Data is sensitive (financial/personal) → cannot expose bare to the internet → URL token as the security layer (no token → 403).

## Architecture (established approach — copy as-is)

```
Phone / Telegram in-app browser
   │ HTTPS  https://<ip-with-hyphens>.sslip.io/<path>?token=…
   ▼
[Cloud firewall :80 :443]            ← only public exposure; most cloud providers require this to be opened in the console
   ▼
Caddy (system service, auto Let's Encrypt, sslip.io domain)
   │ reverse_proxy 127.0.0.1:<APP_PORT>
   ▼
App (systemd user service, listens on 127.0.0.1 only) ── read/write ── data files/DB
```

**Why this split**: Caddy needs privileged ports 80/443 + certificate management → system service is most stable; the app doesn't touch privileged ports → systemd **user** service, no root required, isolated. sslip.io encodes the IP into a domain name (`52-77-48-244.sslip.io` resolves to `52.77.48.244`) — **no domain, free, fixed URL**.

## Three Iron Rules (trade-offs after source audit)

1. **"Free + no port exposure + fixed URL" is an impossible triangle — pick two**:
   - sslip.io + Caddy = free + fixed URL, **requires open ports** (this approach).
   - Cloudflare Tunnel = no open ports + fixed URL, **requires your own domain**.
   - trycloudflare temporary tunnel = free + no open ports, **URL changes every time**.
2. **Telegram/iOS rejects self-signed certificates** → must use Let's Encrypt or another public CA (Caddy handles this automatically — don't hand-roll a self-signed cert).
3. **Sensitive data: secure with tokens, not IP locking**: mobile IPs roam, ACME validation IPs vary — locking source IPs will simultaneously lock out users and block certificate issuance. Security = token auth + expose only 80/443 + app listens on localhost only.

## Execution Flow

> Read `references/RUNBOOK.template.md` first for copy-pasteable commands; fill in variables for your application. Two phases: Phase A is fully internal and reversible; Phase B touches the public internet.

### Confirm Variables First
`SSH` (ssh alias), `APP_DIR`, `APP_PORT`, `RUN_CMD` (start command), `DOMAIN=<ip-with-hyphens>.sslip.io`, whether token auth is needed, data file paths.

### Phase A — Server-Side Deployment (ports closed)
1. Create directory skeleton; **scp files individually** (never `scp -r` whole directories — it will wipe files on the server that don't exist locally).
2. Install runtime (Python: `python3-venv` is often missing — see gotchas); create venv / `npm ci`.
3. **Generate secrets on the server**: `openssl rand -hex 32` → `.env` (`chmod 600`). **Never put secrets in git / never print to the conversation**.
4. Write systemd **user** unit (`references/app.service.template`), `enable --now`, **listen on 127.0.0.1 only**.
5. Local verification: `curl 127.0.0.1:<PORT>/healthz`, no token → 403, with token → 200.

### Phase B — Open Ports + Caddy HTTPS (touches public internet — confirm with user first)
0. 🔴 **Have the user open ports 80 + 443 TCP in the cloud console** (cloud firewall is separate from OS ufw; set Source to **Any IPv4**, not a Custom IP). Agent generally has no cloud provider credentials — delegate this step to the user.
1. Install Caddy (from official apt source, see RUNBOOK).
2. Write `/etc/caddy/Caddyfile` (`references/Caddyfile.template`) → `reload caddy`.
3. Wait for ACME certificate issuance (~10s), check `journalctl -u caddy | grep "certificate obtained"`; from Mac: `curl https://$DOMAIN/healthz` expecting 200 + TLS verify=0.
4. Generate the full link with token (**generate on server side — do not print the token to the conversation**; send to user directly via IM).

### Wrap-Up
- Write a rollback table (how to undo each component) into the delivery document.
- If this is a **Hermes skill integration**: after modifying the skill, run `hermes gateway restart` (runtime does not hot-reload).

## Tested Gotchas (follow these to avoid pain)

- **`python3-venv` missing**: Ubuntu 22.04 doesn't ship `ensurepip` by default; `python3 -m venv` will fail → first run `sudo apt-get install -y python3.10-venv` (match the version number to `python3 --version`).
- **Cloud firewall ≠ OS firewall**: `ufw` may be inactive and you still can't connect — Lightsail/EC2's **cloud security group / firewall** must be opened separately in the console. After opening, `nc -vz <ip> 443`: `Connection refused` = port is reachable but no service yet (normal, will change once Caddy starts); `timed out` = cloud firewall still not open.
- **Don't set Source IP to Custom**: trying to lock the IP will lock out your phone + ACME validation. Use **Any IPv4**.
- **scp file by file**: `scp -r whole-directory` / `rsync --delete` will delete files on the server that don't exist locally. Only update what needs changing.
- **App must read data paths from environment variables** (e.g., `BTC_STATE`): when multiple components share the same data file, don't let any component hardcode a relative path.
- **Token is an access credential**: generate, inject, and validate entirely on the server side; only report back the HTTP status code. Send the full link to the user via IM — never let it appear in chat history / logs / git.

## Reference Files (references/)

- `RUNBOOK.template.md` — step-by-step copy-pasteable commands (with rollback table).
- `Caddyfile.template` — minimal sslip.io reverse proxy config.
- `app.service.template` — systemd user service template.
- `token_auth.py` — minimal HMAC-derived token auth snippet (Flask).

## Security Red Lines

- Secrets generated on the server, `chmod 600`, never in git/conversation/logs.
- Application listens on `127.0.0.1` only; public internet sees only Caddy's 80/443.
- Explicitly confirm with the user before touching the public internet (opening ports) — this exposure is irreversible.
