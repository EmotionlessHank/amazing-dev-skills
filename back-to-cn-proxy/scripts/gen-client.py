#!/usr/bin/env python3
"""根据服务器部署结果生成客户端物料：ss:// / hysteria2:// 链接、二维码、Shadowrocket .conf。

用法示例：
  python3 gen-client.py --host 1.2.3.4 --ss-port 23456 --hy-port 23457 \
      --ss-pw 'xxx==' --hy-pw 'yyy' --sni www.bing.com \
      --out-dir ./clients --conf ./clients/xiaohongshu-cn.conf

仅当线路有「硬带宽上限」时才传 --download-bandwidth（Mbps）；带宽充足的机器不要传，
让 Hy2 用 BBR 自适应即可。
"""
import argparse, base64, shutil, subprocess, urllib.parse, sys
from pathlib import Path

# 小红书相关域名（走代理），其余直连
XHS_DOMAINS = ["xiaohongshu.com", "xhscdn.com", "xhs.cn", "fegine.com"]


def ss_link(host, port, pw, name):
    userinfo = f"2022-blake3-aes-128-gcm:{pw}"
    b64 = base64.urlsafe_b64encode(userinfo.encode()).decode().rstrip("=")
    return f"ss://{b64}@{host}:{port}#{urllib.parse.quote(name)}"


def hy2_link(host, port, pw, sni, name):
    return (f"hysteria2://{urllib.parse.quote(pw)}@{host}:{port}/"
            f"?insecure=1&sni={sni}#{urllib.parse.quote(name)}")


def shadowrocket_conf(host, hy_port, hy_pw, sni, bw):
    # 注意：Shadowrocket 的 .conf 解析器不支持 SS-2022 加密，只放 Hy2；SS 用扫码导入。
    bw_str = ""
    if bw:
        bw_str = f", download-bandwidth={bw}, upload-bandwidth={bw}"
    rules = "\n".join(f"DOMAIN-SUFFIX,{d},回国" for d in XHS_DOMAINS)
    return f"""[General]
bypass-system = true
dns-server = system
ipv6 = false

[Proxy]
小红书-Hy2 = hysteria2, {host}, {hy_port}, password={hy_pw}, sni={sni}, skip-cert-verify=true{bw_str}

[Proxy Group]
回国 = select, 小红书-Hy2

[Rule]
{rules}
# 本地网段 + 组播直连：保 AirPlay 投屏/设备发现不被代理
IP-CIDR,192.168.0.0/16,DIRECT,no-resolve
IP-CIDR,10.0.0.0/8,DIRECT,no-resolve
IP-CIDR,172.16.0.0/12,DIRECT,no-resolve
IP-CIDR,224.0.0.0/4,DIRECT,no-resolve
FINAL,DIRECT
"""


def make_qr(text, path):
    if not shutil.which("qrencode"):
        print(f"  [跳过二维码] 未装 qrencode：brew install qrencode", file=sys.stderr)
        return False
    subprocess.run(["qrencode", "-o", str(path), "-s", "10", "-m", "4", text], check=True)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--ss-port", type=int, default=23456)
    ap.add_argument("--hy-port", type=int, default=23457)
    ap.add_argument("--ss-pw", required=True)
    ap.add_argument("--hy-pw", required=True)
    ap.add_argument("--sni", default="www.bing.com")
    ap.add_argument("--prefix", default="小红书")
    ap.add_argument("--out-dir", default="./clients")
    ap.add_argument("--conf", default=None, help="Shadowrocket .conf 输出路径")
    ap.add_argument("--download-bandwidth", type=int, default=None,
                    help="仅硬限速线路传（Mbps）；带宽充足留空")
    a = ap.parse_args()

    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    ss = ss_link(a.host, a.ss_port, a.ss_pw, f"{a.prefix}-SS")
    hy = hy2_link(a.host, a.hy_port, a.hy_pw, a.sni, f"{a.prefix}-Hy2")

    print("【SS-2022 链接】\n" + ss + "\n")
    print("【Hysteria2 链接】\n" + hy + "\n")

    make_qr(ss, out / "shadowsocks-qr.png")
    make_qr(hy, out / "hysteria2-qr.png")

    conf_path = Path(a.conf) if a.conf else (out / "xiaohongshu-cn.conf")
    conf_path.parent.mkdir(parents=True, exist_ok=True)
    conf_path.write_text(shadowrocket_conf(a.host, a.hy_port, a.hy_pw, a.sni, a.download_bandwidth),
                         encoding="utf-8")
    print(f"已写入二维码与 Shadowrocket 配置：{out}/ , {conf_path}")


if __name__ == "__main__":
    main()
