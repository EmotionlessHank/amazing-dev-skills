---
name: back-to-cn-proxy
description: 在一台「中国大陆 IP」的云服务器上部署回国代理（sing-box，Shadowsocks-2022 + Hysteria2），供 iPhone Shadowrocket 以中国 IP 访问小红书等国内 App。当用户说「部署回国代理 / 搭回国节点 / 新机器装 sing-box / 配回国 Shadowrocket / 换了回国服务器重新部署」时触发。也适用于其它「需要落地某地 IP」的单用户代理落地。
---

# 回国代理部署（sing-box SS-2022 + Hysteria2）

把一台云服务器变成 iPhone Shadowrocket 用的回国代理落地节点。**出口 = 服务器所在地 IP**，所以服务器必须在目标地区（回国 = 中国大陆，如上海）。

## 适用与边界
- 单用户自用代理落地。服务器在哪，出口 IP 就在哪。
- 回国看小红书：服务器选**中国大陆**地域；境外免费云（Oracle/GCP/AWS）给的是外国 IP，**不适用**。
- 带宽是体验关键：直播是突发流量，**固定 3Mbps 会撞墙吐字**；优先选高峰值带宽机型（如腾讯云轻量「锐驰型」200Mbps 不限流量）。

## 开始前需要的信息
1. 服务器**公网 IP**
2. SSH 能登（推荐复用 `~/.ssh/tencent-xhs-key`，登录用户通常 `ubuntu`）
3. **云控制台「防火墙/安全组」已放行**：`23456/TCP`、`23457/UDP`（22 通常默认开）
   —— 这步只能在控制台点，脚本管不到；不放行则客户端永远连不上。

## 部署步骤

### 1. 打通 SSH 并登记
```bash
# 配 ~/.ssh/config 别名（按需改 IP）；连通后在 ~/.ssh/SERVERS.md 登记该机
ssh <alias> 'whoami && curl -s https://ipinfo.io/json | grep -E "ip|city|country|org"'
```
确认出口 `country=CN` 且地域正确。

### 2. 跑部署脚本（装 sing-box + 配置 + 加固 + 自检）
```bash
ssh <alias> 'bash -s' < scripts/deploy-singbox.sh
# 可选：SS_PORT=23456 HY_PORT=23457 SNI=www.bing.com 通过 ssh 'ENV=.. bash -s' 传入
```
脚本做：GitHub 加速镜像下载 + 多镜像 SHA256 交叉校验 → 装 sing-box → 生成 SS-2022 密钥/Hy2 密码/自签证书 → 写 config.json → 权限+systemd 自启 → ufw+fail2ban → **端到端自检**。
结尾打印 `RESULT_SS_PW=` / `RESULT_HY_PW=` / `RESULT_EXIT_IP=` 等，**抓下来**喂给第 3 步。验证 `RESULT_SB_ACTIVE=active` 且 `RESULT_EXIT_IP` 是目标地区 IP。

### 3. 生成客户端物料（链接 + 二维码 + Shadowrocket 配置）
```bash
python3 scripts/gen-client.py --host <IP> \
  --ss-pw '<RESULT_SS_PW>' --hy-pw '<RESULT_HY_PW>' \
  --out-dir <项目>/clients --conf '<iCloud Shadowrocket 容器>/xiaohongshu-cn.conf'
# 仅当线路有硬带宽上限（如 3Mbps）才加 --download-bandwidth 3；带宽充足别加。
```
iCloud Shadowrocket 容器路径：`~/Library/Mobile Documents/iCloud~com~liguangming~Shadowrocket/Documents/`
（只新增 `.conf`，**绝不动**里面的 `.db`）。同时在项目 `clients/` 留一份备份。

### 4. 客户端导入与规则（关键）
- Shadowrocket 扫 `shadowsocks-qr.png`（首选）或 `hysteria2-qr.png`；或导入 `.conf`（含规则）。
- **必须用「规则」模式**：只让小红书域名（见 gen-client.py 的 `XHS_DOMAINS`）走代理，其余直连，否则全局绕中国又慢又费流量。
- `.conf` 解析器**不支持 SS-2022**，故 `.conf` 内只放 Hy2 + 规则；要 SS 用扫码。

### 5. 收尾
- 控制台开**自动续费** + 设**流量/带宽告警**（只能人工点）。
- 在 `~/.ssh/SERVERS.md` 与项目记忆里登记该机（IP、端口、用途、到期）。

## 调优 / 排障
- **直播卡顿、一句一句吐字** = 带宽撞墙。逐秒采样网卡 TX，若顶在带宽上限即是。解法：换高带宽机型 / 客户端降清晰度 / Hy2 加 `download-bandwidth`（仅硬限速线路有用）。
- **某网络连不上 Hy2** = 该网络封 UDP/QUIC，改用 SS（TCP）。
- **AirPlay 投屏**：投屏拉流在手机，Apple TV 不必装 Shadowrocket；`.conf` 已含本地网段+组播直连规则保发现。
- 升级 sing-box：改 `SB_VERSION` 重跑脚本即可（同样走加速镜像 + 校验）。
