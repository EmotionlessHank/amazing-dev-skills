# RUNBOOK 模板 — 无域名 Web 应用上线

> 把 `<尖括号>` 变量替成你的值。命令在本机执行（`ssh <SSH>` 直连服务器）。
> 变量：`SSH`=ssh 别名、`APP_DIR=~/apps/<app>`、`PORT=<localhost端口>`、`DOMAIN=<ip连字符>.sslip.io`、`SRC=<本地源目录>`、`DATA=~/.local/share/<app>/data`（可选共享数据）。

## Phase A — 服务器内（不开端口，可回滚）

### A1 目录 + 逐文件上传（禁 scp -r 整目录）
```bash
ssh <SSH> 'mkdir -p ~/apps/<app> ~/.config/systemd/user'
scp "<SRC>/app.py" "<SRC>/"*.html "<SRC>/"*.py  <SSH>:'~/apps/<app>/'
```

### A2 运行时 + 依赖
```bash
# Python：先补 venv 包（Ubuntu 常缺），再建 venv
ssh <SSH> 'sudo apt-get install -y python3-venv || sudo apt-get install -y python3.$(python3 -c "import sys;print(sys.version_info.minor)")-venv'
ssh <SSH> 'cd ~/apps/<app> && python3 -m venv .venv && .venv/bin/pip -q install --upgrade pip <你的依赖>'
# Node：scp 后 `npm ci --omit=dev`
```

### A3 生成密钥（服务器现生成，不进 git/对话）
```bash
ssh <SSH> 'umask 077; printf "APP_SECRET=%s\nDATA_PATH=%s\n" "$(openssl rand -hex 32)" "$HOME/<DATA>" > ~/apps/<app>/.env; chmod 600 ~/apps/<app>/.env; stat -c %a ~/apps/<app>/.env'
```

### A4 systemd user 服务（仅 localhost）
```bash
# 用 references/app.service.template，scp 到 ~/.config/systemd/user/<app>.service 后：
ssh <SSH> 'systemctl --user daemon-reload && systemctl --user enable --now <app> && sleep 2 && systemctl --user --no-pager status <app> | head -6'
```

### A5 本地验证
```bash
ssh <SSH> 'curl -s 127.0.0.1:<PORT>/healthz; echo'
ssh <SSH> 'curl -s -o /dev/null -w "no-token:%{http_code}\n" 127.0.0.1:<PORT>/<protected>'   # 期望 403
ssh <SSH> 'T=$(set -a;. ~/apps/<app>/.env;set +a; cd ~/apps/<app> && .venv/bin/python app.py --token); curl -s -o /dev/null -w "token:%{http_code}\n" "127.0.0.1:<PORT>/<protected>?token=$T"'  # 期望 200
```

## Phase B — 开端口 + Caddy（碰公网，先跟用户确认）

### B0 🔴 用户在云控制台开 80 + 443 TCP（Source=Any IPv4）
开后验证：`nc -vz <公网IP> 443`（refused=通但无服务，正常；timed out=没开）。

### B1 装 Caddy（apt 官方源）
```bash
ssh <SSH> 'sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl && \
 curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg && \
 curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt | sudo tee /etc/apt/sources.list.d/caddy-stable.list && \
 sudo apt-get update && sudo apt-get install -y caddy && caddy version'
```

### B2 Caddyfile 反代（见 references/Caddyfile.template）
```bash
ssh <SSH> 'sudo tee /etc/caddy/Caddyfile >/dev/null' <<CADDY
<DOMAIN> {
	encode zstd gzip
	reverse_proxy 127.0.0.1:<PORT>
}
CADDY
ssh <SSH> 'sudo systemctl reload caddy || sudo systemctl restart caddy'
```

### B3 验证证书 + HTTPS
```bash
sleep 8
ssh <SSH> 'sudo journalctl -u caddy --no-pager --since "2 min ago" | grep -iE "certificate obtained|error" | tail'
curl -s -o /dev/null -w "%{http_code} verify=%{ssl_verify_result}\n" https://<DOMAIN>/healthz   # 期望 200 verify=0
```

### B4 生成带 token 链接（服务器侧，不打印 token）
```bash
ssh <SSH> 'T=$(set -a;. ~/apps/<app>/.env;set +a; cd ~/apps/<app> && .venv/bin/python app.py --token); echo "链接: https://<DOMAIN>/<path>?token=$T"'
# 该链接通过 IM 私发用户，不落聊天/日志/git
```

## 回滚表
| 组件 | 回滚 |
|------|------|
| App | `systemctl --user disable --now <app>; rm ~/.config/systemd/user/<app>.service; systemctl --user daemon-reload` |
| Caddy | `sudo systemctl disable --now caddy`（或 `apt-get remove -y caddy`）|
| 端口 | 云控制台删 80/443 规则 |
| 数据 | 备份 `<DATA>`；应用每次写前留 `.bak` |
