---
name: headless-web-deploy
description: 把一个小型 Web 应用（Flask/FastAPI/Node/静态站）部署到无域名的无头服务器（AWS Lightsail / EC2 / VPS），用 Caddy + sslip.io 自动签 Let's Encrypt 证书、systemd 常驻、HMAC token 鉴权，最终给一条可在手机/Telegram 内置浏览器打开的 HTTPS 链接。当用户说「部署到服务器」「上线网页」「sslip.io」「Caddy 反代」「免域名 HTTPS」「驾驶舱/看板上服务器」时触发。
version: 1.0.0
author: Hank
triggers:
  - 部署网页到服务器
  - web 应用上线
  - 免域名 https 部署
  - sslip.io
  - caddy 反代
  - 部署驾驶舱
  - /headless-web-deploy
---

# headless-web-deploy — 无域名 Web 应用一键上线

把本地跑通的小型 Web 应用部署到无头服务器，对外只暴露一条 **带 token 的 HTTPS 链接**，手机/Telegram 内置浏览器可直接打开。

## 适用场景

- 个人项目，**没有/不想用域名**，要能 HTTPS（Telegram、iOS Safari 拒绝自签证书，必须有效证书）。
- 服务器无头（Lightsail / EC2 / VPS），有 `ssh` 别名直连 + `sudo`。
- 应用是单进程 HTTP 服务（Flask/FastAPI/Express/静态），监听 localhost 某端口即可。
- 数据敏感（财务/私人）→ 不能裸奔公网 → 用 URL token 兜底（无 token → 403）。

## 架构（确定方案，照搬即可）

```
手机/TG 内置浏览器
   │ HTTPS  https://<ip-用连字符>.sslip.io/<path>?token=…
   ▼
[云防火墙 :80 :443]            ← 唯一公网暴露，多数云厂商要在控制台单独开
   ▼
Caddy（系统服务，自动 Let's Encrypt，sslip.io 域）
   │ reverse_proxy 127.0.0.1:<APP_PORT>
   ▼
App（systemd user 服务，仅监听 127.0.0.1）── 读写 ── 数据文件/DB
```

**为什么这么分**：Caddy 要绑特权端口 80/443 + 管证书 → 系统服务最稳；App 不碰特权端口 → systemd **user** 服务，免 root、隔离。sslip.io 把 IP 编进域名（`52-77-48-244.sslip.io` 解析回 `52.77.48.244`），**免域名、免费、URL 固定**。

## 三条铁律（信源审计后的取舍）

1. **「免费 + 免开端口 + 固定 URL」不可能三角，只能选两个**：
   - sslip.io + Caddy = 免费 + 固定 URL，**要开端口**（本方案）。
   - Cloudflare Tunnel = 免开端口 + 固定 URL，**需自有域名**。
   - trycloudflare 临时隧道 = 免费 + 免开端口，**URL 每次变**。
2. **Telegram/iOS 拒自签证书** → 必须 Let's Encrypt 等公信 CA（Caddy 自动搞定，别手搓自签）。
3. **敏感数据靠 token 不靠锁 IP**：手机 IP 漂移、ACME 校验 IP 不固定，锁源 IP 会同时锁死用户和签证书。安全=token 鉴权 + 仅暴露 80/443 + 应用只监听 localhost。

## 执行流程

> 先读 `references/RUNBOOK.template.md` 拿可照抄的命令；按你的应用填变量。分两阶段，Phase A 全内部可回滚，Phase B 才碰公网。

### 变量先确认
`SSH`（ssh 别名）、`APP_DIR`、`APP_PORT`、`RUN_CMD`（启动命令）、`DOMAIN=<ip 连字符>.sslip.io`、是否要 token 鉴权、数据文件路径。

### Phase A — 服务器内部署（不开端口）
1. 建目录骨架；**逐文件 scp**（禁 `scp -r` 整目录覆盖，会清掉服务器上你本地没有的文件）。
2. 装运行时（Python 注意 `python3-venv` 常缺，见踩坑）；建 venv / `npm ci`。
3. **服务器现生成密钥**：`openssl rand -hex 32` → `.env`（`chmod 600`），**永不进 git / 不打印到对话**。
4. 写 systemd **user** unit（`references/app.service.template`），`enable --now`，**只监听 127.0.0.1**。
5. 本地验证：`curl 127.0.0.1:<PORT>/healthz`、无 token→403、带 token→200。

### Phase B — 开端口 + Caddy HTTPS（碰公网，先跟用户确认）
0. 🔴 **让用户在云控制台开 80 + 443 TCP**（云防火墙独立于 OS ufw；Source 选 **Any IPv4**，别选 Custom IP）。Agent 一般无云厂商凭据，这步交用户。
1. 装 Caddy（apt 官方源，见 RUNBOOK）。
2. 写 `/etc/caddy/Caddyfile`（`references/Caddyfile.template`）→ `reload caddy`。
3. 等 ACME 签发（~10s），查 `journalctl -u caddy | grep "certificate obtained"`；Mac 侧 `curl https://$DOMAIN/healthz` 期望 200 + TLS verify=0。
4. 生成带 token 完整链接（**服务器侧生成、不打印 token 到对话**，通过 IM 直接发用户）。

### 收尾
- 回滚表（每个组件怎么撤）写进交付文档。
- 若是 **Hermes skill 配套**：改 skill 后必须 `hermes gateway restart`（运行期不热更新）。

## 实测踩坑（照此避坑）

- **`python3-venv` 缺**：Ubuntu 22.04 默认无 `ensurepip`，`python3 -m venv` 失败 → 先 `sudo apt-get install -y python3.10-venv`（版本号对应 `python3 --version`）。
- **云防火墙 ≠ OS 防火墙**：`ufw` 可能 inactive 也连不上——Lightsail/EC2 的**云安全组/防火墙**要在控制台单独开 80/443。开完 `nc -vz <ip> 443`：`Connection refused`=端口通但没服务（正常，起 Caddy 后变通）；`timed out`=云防火墙还没开。
- **Source IP 别填 Custom**：默认想锁 IP 反而锁死手机 + ACME 校验，选 **Any IPv4**。
- **scp 逐文件**：`scp -r 整目录` / `rsync --delete` 会清空服务器上本地缺失的文件，只更新要改的。
- **app 要认环境变量指定数据路径**（如 `BTC_STATE`）：多个组件共享同一份数据文件时，别让某个组件写死相对路径。
- **token 是访问凭据**：生成、注入、验证全在服务器侧做，只回报 HTTP 状态码；完整链接通过 IM 私发用户，不落聊天记录/日志/git。

## 参考文件（references/）

- `RUNBOOK.template.md` — 可照抄的逐步命令（含回滚表）。
- `Caddyfile.template` — sslip.io 反代最小配置。
- `app.service.template` — systemd user 服务模板。
- `token_auth.py` — HMAC 派生 token 的最小鉴权片段（Flask）。

## 安全红线

- 密钥服务器现生成、`600`、不进 git/对话/日志。
- 应用只监听 `127.0.0.1`，公网只走 Caddy 的 80/443。
- 碰公网（开端口）前显式跟用户确认——不可逆的对外暴露。
