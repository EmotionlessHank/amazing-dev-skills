# RUNBOOK Template — Domain-Free Web App Deployment

> Replace `<angle-bracket>` variables with your actual values. Commands run on your local machine (connecting to the server via `ssh <SSH>`).
> Variables: `SSH`=ssh alias, `APP_DIR=~/apps/<app>`, `PORT=<localhost port>`, `DOMAIN=<ip-with-hyphens>.sslip.io`, `SRC=<local source dir>`, `DATA=~/.local/share/<app>/data` (optional shared data).

## Phase A — Server-Side Only (ports closed, fully reversible)

### A1 Directory + File-by-File Upload (never scp -r whole directories)
```bash
ssh <SSH> 'mkdir -p ~/apps/<app> ~/.config/systemd/user'
scp "<SRC>/app.py" "<SRC>/"*.html "<SRC>/"*.py  <SSH>:'~/apps/<app>/'
```

### A2 Runtime + Dependencies
```bash
# Python: install venv package first (often missing on Ubuntu), then create venv
ssh <SSH> 'sudo apt-get install -y python3-venv || sudo apt-get install -y python3.$(python3 -c "import sys;print(sys.version_info.minor)")-venv'
ssh <SSH> 'cd ~/apps/<app> && python3 -m venv .venv && .venv/bin/pip -q install --upgrade pip <your dependencies>'
# Node: after scp, run `npm ci --omit=dev`
```

### A3 Generate Secrets (server-side only — never in git/conversation)
```bash
ssh <SSH> 'umask 077; printf "APP_SECRET=%s\nDATA_PATH=%s\n" "$(openssl rand -hex 32)" "$HOME/<DATA>" > ~/apps/<app>/.env; chmod 600 ~/apps/<app>/.env; stat -c %a ~/apps/<app>/.env'
```

### A4 systemd User Service (localhost only)
```bash
# Use references/app.service.template, scp it to ~/.config/systemd/user/<app>.service, then:
ssh <SSH> 'systemctl --user daemon-reload && systemctl --user enable --now <app> && sleep 2 && systemctl --user --no-pager status <app> | head -6'
```

### A5 Local Verification
```bash
ssh <SSH> 'curl -s 127.0.0.1:<PORT>/healthz; echo'
ssh <SSH> 'curl -s -o /dev/null -w "no-token:%{http_code}\n" 127.0.0.1:<PORT>/<protected>'   # expect 403
ssh <SSH> 'T=$(set -a;. ~/apps/<app>/.env;set +a; cd ~/apps/<app> && .venv/bin/python app.py --token); curl -s -o /dev/null -w "token:%{http_code}\n" "127.0.0.1:<PORT>/<protected>?token=$T"'  # expect 200
```

## Phase B — Open Ports + Caddy (touches public internet — confirm with user first)

### B0 🔴 User opens ports 80 + 443 TCP in cloud console (Source=Any IPv4)
Verify after opening: `nc -vz <public IP> 443` (refused=reachable but no service yet, normal; timed out=still not open).

### B1 Install Caddy (official apt source)
```bash
ssh <SSH> 'sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl && \
 curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg && \
 curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt | sudo tee /etc/apt/sources.list.d/caddy-stable.list && \
 sudo apt-get update && sudo apt-get install -y caddy && caddy version'
```

### B2 Caddyfile Reverse Proxy (see references/Caddyfile.template)
```bash
ssh <SSH> 'sudo tee /etc/caddy/Caddyfile >/dev/null' <<CADDY
<DOMAIN> {
	encode zstd gzip
	reverse_proxy 127.0.0.1:<PORT>
}
CADDY
ssh <SSH> 'sudo systemctl reload caddy || sudo systemctl restart caddy'
```

### B3 Verify Certificate + HTTPS
```bash
sleep 8
ssh <SSH> 'sudo journalctl -u caddy --no-pager --since "2 min ago" | grep -iE "certificate obtained|error" | tail'
curl -s -o /dev/null -w "%{http_code} verify=%{ssl_verify_result}\n" https://<DOMAIN>/healthz   # expect 200 verify=0
```

### B4 Generate Link with Token (server-side — do not print token to conversation)
```bash
ssh <SSH> 'T=$(set -a;. ~/apps/<app>/.env;set +a; cd ~/apps/<app> && .venv/bin/python app.py --token); echo "Link: https://<DOMAIN>/<path>?token=$T"'
# Send this link to the user via IM — never let it appear in chat/logs/git
```

## Rollback Table
| Component | Rollback |
|------|------|
| App | `systemctl --user disable --now <app>; rm ~/.config/systemd/user/<app>.service; systemctl --user daemon-reload` |
| Caddy | `sudo systemctl disable --now caddy` (or `apt-get remove -y caddy`) |
| Ports | Delete the 80/443 rules in the cloud console |
| Data | Back up `<DATA>`; application leaves a `.bak` before each write |
