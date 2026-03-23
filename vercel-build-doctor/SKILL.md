---
name: vercel-build-doctor
description: Vercel 线上构建错误诊断。当用户提到 Vercel/线上构建失败、部署报错、build error 时自动触发。通过 Vercel CLI/API 一步获取错误日志，定位根因并修复。
triggers:
  - vercel 构建失败
  - 线上构建报错
  - 部署失败
  - build error
  - vercel error
  - /vercel-doctor
---

# Vercel Build Doctor

线上构建错误的快速诊断与修复技能。

## 触发场景识别

以下信号表明需要启动此技能：
- 用户提到"Vercel 构建失败"、"线上报错"、"部署失败"
- 用户发送 Vercel 部署链接（含 `vercel.com` URL）
- 用户说"build error"、"构建挂了"

## 执行流程

### Step 1：获取部署 ID

从用户提供的信息中提取部署 ID。如果用户提供的是 Vercel URL，从中解析；如果没有，用 `vercel ls` 找到最近的 Error 部署：

```bash
vercel ls 2>&1 | head -15
```

找到状态为 `● Error` 的部署 URL。

### Step 2：一步提取构建错误

使用以下命令直接提取错误信息（**核心命令，一步到位**）：

```bash
DPL_ID="<deployment_id_or_url>" && \
TOKEN=$(python3 -c "import json; print(json.load(open('/Users/hang/Library/Application Support/com.vercel.cli/auth.json')).get('token',''))") && \
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.vercel.com/v2/deployments/${DPL_ID}/events?builds=1&limit=2000&direction=forward" \
  | jq -r '.[].payload.text' \
  | grep -iEB2 -A2 'error:|fail|ELIFECYCLE' \
  | grep -v 'sourcemap'
```

**参数说明**：
| 参数 | 作用 |
|------|------|
| `events?builds=1` | 只返回构建日志（排除运行时日志） |
| `limit=2000` | 拉足够多的日志行避免截断 |
| `direction=forward` | 按时间正序，错误在末尾 |
| `jq -r '.[].payload.text'` | 提取纯文本日志行 |
| `grep -iEB2 -A2` | 错误行前后各 2 行上下文 |
| `grep -v 'sourcemap'` | 去除 Sentry sourcemap 噪音 |

如果 `jq` 不可用，备选方案：

```bash
curl -s ... | python3 -c "
import sys, json
for e in json.load(sys.stdin):
    t = e.get('payload',{}).get('text','')
    if t and any(k in t.lower() for k in ['error', 'fail', 'elifecycle']):
        if 'sourcemap' not in t.lower():
            print(t)
"
```

### Step 3：诊断与修复

根据提取到的错误类型，执行对应修复：

| 错误类型 | 修复动作 |
|---------|---------|
| ESLint error（如 `no-unused-vars`） | 定位文件行号，直接修复代码 |
| Type error | 读取报错文件，修复类型问题 |
| Module not found | 检查 import 路径和依赖 |
| Build timeout | 检查是否有死循环或重型计算 |

修复后：
1. 本地验证 `pnpm lint && pnpm build`
2. 提交并推送
3. 用 `vercel ls` 确认新部署状态

## 注意事项

- **优先用 CLI/API 获取第一手数据**，不要用 WebFetch 抓 Vercel 网页（需登录，拿不到）
- **不要本地 build 复现**，直接从 Vercel 拿日志更快更准
- Vercel auth token 存储路径：`/Users/hang/Library/Application Support/com.vercel.cli/auth.json`
- 如果 `vercel` CLI 未登录或 link 失败，提示用户执行 `vercel login` 和 `vercel link --yes --scope <scope>`
