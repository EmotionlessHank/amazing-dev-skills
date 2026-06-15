---
name: back-to-cn-proxy
description: Deploy a China-egress proxy (sing-box, Shadowsocks-2022 + Hysteria2) on a cloud server with a mainland China IP, for use with iPhone Shadowrocket to access Chinese apps like Xiaohongshu with a Chinese IP. Triggers when the user says "deploy a China proxy / set up a China-exit node / install sing-box on a new machine / configure Shadowrocket for China / re-deploy after switching China servers". Also applicable to any single-user proxy where the egress must land in a specific region.
---

# China-Egress Proxy Deployment (sing-box SS-2022 + Hysteria2)

Turns a cloud server into a China-egress landing node for iPhone Shadowrocket. **The egress IP = the server's location IP**, so the server must be in the target region (China-egress = mainland China, e.g., Shanghai).

## Scope and Constraints
- Single-user personal proxy egress. Egress IP follows the server's location.
- To access Xiaohongshu from abroad: choose a **mainland China** region. Overseas free-tier clouds (Oracle/GCP/AWS) provide foreign IPs and **are not suitable**.
- Bandwidth is critical for the experience: live streams are bursty traffic — **a 3 Mbps cap will cause choppy, word-by-word playback**. Prefer high-peak-bandwidth instance types (e.g., Tencent Cloud Lighthouse "Sprint" type: 200 Mbps unlimited traffic).

## Information Required Before Starting
1. Server **public IP**
2. SSH access (recommended: reuse `~/.ssh/tencent-xhs-key`; login user is typically `ubuntu`)
3. **Cloud console firewall/security group has already opened**: `23456/TCP`, `23457/UDP` (port 22 is usually open by default)
   — This step can only be done in the console; the script cannot manage it. Without these rules, clients will never connect.

## Deployment Steps

### 1. Establish SSH and Register the Host
```bash
# Add a ~/.ssh/config alias (update IP as needed); after confirming connectivity, register the machine in ~/.ssh/SERVERS.md
ssh <alias> 'whoami && curl -s https://ipinfo.io/json | grep -E "ip|city|country|org"'
```
Confirm that the egress shows `country=CN` and the correct region.

### 2. Run the Deployment Script (installs sing-box + config + hardening + self-test)
```bash
ssh <alias> 'bash -s' < scripts/deploy-singbox.sh
# Optional: pass env vars via ssh 'ENV=.. bash -s': SS_PORT=23456 HY_PORT=23457 SNI=www.bing.com
```
The script: downloads via GitHub acceleration mirrors with multi-mirror SHA256 cross-validation → installs sing-box → generates SS-2022 key / Hy2 password / self-signed cert → writes config.json → sets permissions + systemd auto-start → ufw + fail2ban → **end-to-end self-test**.
At the end it prints `RESULT_SS_PW=` / `RESULT_HY_PW=` / `RESULT_EXIT_IP=` etc. — **capture these** to feed into step 3. Verify `RESULT_SB_ACTIVE=active` and `RESULT_EXIT_IP` is a target-region IP.

### 3. Generate Client Materials (links + QR codes + Shadowrocket config)
```bash
python3 scripts/gen-client.py --host <IP> \
  --ss-pw '<RESULT_SS_PW>' --hy-pw '<RESULT_HY_PW>' \
  --out-dir <project>/clients --conf '<iCloud Shadowrocket container>/xiaohongshu-cn.conf'
# Only add --download-bandwidth 3 if the line has a hard bandwidth cap (e.g., 3 Mbps); omit if bandwidth is adequate.
```
iCloud Shadowrocket container path: `~/Library/Mobile Documents/iCloud~com~liguangming~Shadowrocket/Documents/`
(Only add the new `.conf` file — **never touch** the `.db` files inside.) Keep a backup copy in the project's `clients/` directory.

### 4. Client Import and Rules (Critical)
- In Shadowrocket, scan `shadowsocks-qr.png` (preferred) or `hysteria2-qr.png`; or import the `.conf` (which includes rules).
- **Must use "Rule" mode**: only route Xiaohongshu domains (see `XHS_DOMAINS` in gen-client.py) through the proxy; everything else goes direct — otherwise all traffic routes through China, which is slow and wastes data.
- The `.conf` parser **does not support SS-2022**, so the `.conf` only includes Hy2 + rules; use QR code scanning for SS.

### 5. Wrap-Up
- Enable **auto-renewal** in the console + set **traffic/bandwidth alerts** (manual console steps only).
- Register the machine in `~/.ssh/SERVERS.md` and in project memory (IP, ports, purpose, expiry).

## Tuning / Troubleshooting
- **Live stream choppy, word-by-word playback** = bandwidth cap hit. Sample the NIC TX per second; if it's pegged at the cap, that's the cause. Fix: switch to a higher-bandwidth instance type / lower stream quality on the client / add `download-bandwidth` to Hy2 (only useful on hard-capped lines).
- **Hy2 unreachable on certain networks** = that network blocks UDP/QUIC. Switch to SS (TCP).
- **AirPlay screen mirroring**: streaming is pulled on the iPhone — Apple TV doesn't need Shadowrocket. The `.conf` already includes local subnet + multicast direct rules to preserve device discovery.
- Upgrading sing-box: change `SB_VERSION` and re-run the script (same acceleration mirrors + validation).
