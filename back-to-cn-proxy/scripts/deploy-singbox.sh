#!/usr/bin/env bash
# China-egress proxy one-command deployment: sing-box (Shadowsocks-2022 + Hysteria2)
# Run on the target server as a sudoer non-root user (typically ubuntu).
# Usage:  ssh <server> 'bash -s' < deploy-singbox.sh
# Optional env vars: SS_PORT(23456) HY_PORT(23457) SB_VERSION(1.13.13) SNI(www.bing.com)
# Prints RESULT_* machine-readable fields at the end for gen-client.py to consume.
set -euo pipefail

SS_PORT="${SS_PORT:-23456}"
HY_PORT="${HY_PORT:-23457}"
SB_VERSION="${SB_VERSION:-1.13.13}"
SNI="${SNI:-www.bing.com}"
MIRRORS=("https://ghfast.top/" "https://gh-proxy.com/")
log(){ echo "[deploy] $*" >&2; }

# 1. Detect architecture
case "$(uname -m)" in
  x86_64) A=amd64;; aarch64) A=arm64;; *) echo "Unsupported architecture: $(uname -m)"; exit 1;; esac

# 2. Download sing-box (direct GitHub access is slow from China; use acceleration mirrors;
#    cross-validate SHA256 across multiple mirrors to detect tampering)
URL="https://github.com/SagerNet/sing-box/releases/download/v${SB_VERSION}/sing-box_${SB_VERSION}_linux_${A}.deb"
cd /tmp; rm -f sb_*.deb
i=0; for m in "${MIRRORS[@]}"; do i=$((i+1)); curl -fsL --connect-timeout 10 --max-time 180 -o "sb_${i}.deb" "${m}${URL}" || true; done
mapfile -t files < <(ls /tmp/sb_*.deb 2>/dev/null || true)
[ "${#files[@]}" -ge 1 ] || { echo "All mirrors failed to download"; exit 1; }
mapfile -t hashes < <(sha256sum "${files[@]}" | awk '{print $1}' | sort -u)
if [ "${#files[@]}" -ge 2 ] && [ "${#hashes[@]}" -ne 1 ]; then echo "Mirror SHA256 mismatch — possible tampering, aborting"; exit 1; fi
[ "${#files[@]}" -ge 2 ] && log "Dual-mirror SHA256 match: ${hashes[0]}" || log "Only one mirror available (no cross-validation): ${hashes[0]}"

# 3. Install
sudo dpkg -i "${files[0]}" >/dev/null
rm -f /tmp/sb_*.deb
log "Installed $(sing-box version | head -1)"

# 4. Generate keys and self-signed cert (idempotent: keep cert if it already exists)
sudo mkdir -p /etc/sing-box
SS_PW="$(openssl rand -base64 16)"
HY_PW="$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)"
if [ ! -f /etc/sing-box/cert.pem ]; then
  openssl ecparam -genkey -name prime256v1 -out /tmp/k.pem 2>/dev/null
  openssl req -new -x509 -days 3650 -key /tmp/k.pem -out /tmp/c.pem -subj "/CN=${SNI}" 2>/dev/null
  sudo mv /tmp/k.pem /etc/sing-box/key.pem; sudo mv /tmp/c.pem /etc/sing-box/cert.pem
fi

# 5. Write config (full direct egress = server's own IP location)
sudo tee /etc/sing-box/config.json >/dev/null <<EOF
{
  "log": { "level": "warn", "timestamp": true },
  "inbounds": [
    { "type": "shadowsocks", "tag": "ss-in", "listen": "::", "listen_port": ${SS_PORT},
      "method": "2022-blake3-aes-128-gcm", "password": "${SS_PW}" },
    { "type": "hysteria2", "tag": "hy2-in", "listen": "::", "listen_port": ${HY_PORT},
      "users": [ { "password": "${HY_PW}" } ],
      "tls": { "enabled": true, "alpn": ["h3"],
        "certificate_path": "/etc/sing-box/cert.pem", "key_path": "/etc/sing-box/key.pem" } }
  ],
  "outbounds": [ { "type": "direct", "tag": "direct" } ]
}
EOF
sudo sing-box check -c /etc/sing-box/config.json

# 6. Permissions + enable on boot + start
sudo chown -R sing-box:sing-box /etc/sing-box
sudo chmod 750 /etc/sing-box
sudo chmod 640 /etc/sing-box/key.pem /etc/sing-box/cert.pem /etc/sing-box/config.json
sudo systemctl enable sing-box >/dev/null 2>&1
sudo systemctl restart sing-box

# 7. Host firewall ufw (allow port 22 first to avoid lockout) + fail2ban
sudo ufw allow 22/tcp >/dev/null
sudo ufw allow "${SS_PORT}"/tcp >/dev/null
sudo ufw allow "${SS_PORT}"/udp >/dev/null
sudo ufw allow "${HY_PORT}"/udp >/dev/null
sudo ufw --force enable >/dev/null
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y fail2ban >/dev/null 2>&1 || true
printf '[sshd]\nenabled = true\nbackend = systemd\nmaxretry = 5\nbantime = 1h\nfindtime = 10m\n' | sudo tee /etc/fail2ban/jail.local >/dev/null
sudo systemctl enable --now fail2ban >/dev/null 2>&1 || true
sudo systemctl restart fail2ban >/dev/null 2>&1 || true

# 8. End-to-end self-test (spin up a local client via SS, verify the encrypted forward chain)
EXIT_IP="failed"
cat > /tmp/_tc.json <<EOF
{ "inbounds":[{"type":"mixed","listen":"127.0.0.1","listen_port":11080}],
  "outbounds":[{"type":"shadowsocks","server":"127.0.0.1","server_port":${SS_PORT},
    "method":"2022-blake3-aes-128-gcm","password":"${SS_PW}"}] }
EOF
sing-box run -c /tmp/_tc.json >/dev/null 2>&1 & TCPID=$!
sleep 2
EXIT_IP="$(curl -s --max-time 12 -x http://127.0.0.1:11080 https://ipinfo.io/ip || echo failed)"
kill "$TCPID" 2>/dev/null || true; rm -f /tmp/_tc.json

# 9. Print machine-readable results
echo "RESULT_SS_PORT=${SS_PORT}"
echo "RESULT_HY_PORT=${HY_PORT}"
echo "RESULT_SS_PW=${SS_PW}"
echo "RESULT_HY_PW=${HY_PW}"
echo "RESULT_SNI=${SNI}"
echo "RESULT_SB_ACTIVE=$(systemctl is-active sing-box)"
echo "RESULT_EXIT_IP=${EXIT_IP}"
