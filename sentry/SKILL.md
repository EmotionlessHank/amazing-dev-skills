---
name: sentry
description: Sentry 错误巡检与 Regression 测试生成。当用户说 "/sentry"、"检查 Sentry"、"Sentry 巡检"、"sentry scan"、"生成回归测试" 时触发。当用户粘贴 Sentry Issue URL 时，自动进入单 Issue 诊断模式（diagnose），从 URL 解析 Issue ID → API 获取元数据+堆栈 → 源码定位 → 根因分析 → 修复。连接 Sentry API 获取未解决的 Fatal/Error Issue，按阈值规则过滤，自动定位源文件并生成 regression 测试骨架，输出待 review 的测试列表。
version: 1.1.0
---

# /sentry — Sentry 错误巡检与 Regression 测试自动生成

连接 Sentry API，获取线上未解决的严重错误，自动生成 regression 测试骨架。
设计文档：DD-028 §7.2

---

## 前置条件检查

执行 Skill 前，先验证 Sentry 环境是否就绪：

```bash
# 优先从 .env.local 加载（Claude Code 的 shell 不会自动 export 这些变量）
if [ -f .env.local ]; then
  source <(grep -E '^SENTRY_(LOCAL_AUTH_TOKEN|ORG|PROJECT)=' .env.local)
fi

# 检查环境变量
echo "SENTRY_LOCAL_AUTH_TOKEN: ${SENTRY_LOCAL_AUTH_TOKEN:+SET}"
echo "SENTRY_ORG: ${SENTRY_ORG:-NOT_SET}"
echo "SENTRY_PROJECT: ${SENTRY_PROJECT:-NOT_SET}"
```

> **注意**：后续所有 curl 命令执行前，都需要先 `source` `.env.local` 中的 Sentry 变量（每次 Bash 调用是独立 shell）。

**如果环境变量未配置**：
1. 提示用户："Sentry 环境变量未配置，请先完成 DD-028 §3.1 Step 4 的配置"
2. 提供回退模式：询问用户是否手动输入错误信息（见「手动模式」章节）
3. 终止自动巡检流程

**如果环境变量已配置**：继续执行自动巡检。

---

## 阶段 1：获取 Sentry Issues

### 1.1 调用 Sentry API

Sentry Issues search 不支持原生 OR 语法，`level:fatal level:error` 会被解释为 AND（互斥，永远返回空）。
因此必须**分两次请求**，分别获取 Fatal 和 Error 级别的 Issue，然后按 `id` 合并去重。

```bash
source <(grep -E '^SENTRY_(LOCAL_AUTH_TOKEN|ORG|PROJECT)=' .env.local)

# 请求 1: 获取未解决的 Fatal 级别 Issues（最近 14 天）
# 注意: Sentry Issues API 的 statsPeriod 仅支持 '', '24h', '14d'，不支持 '7d'
FATAL_ISSUES=$(curl -s -H "Authorization: Bearer ${SENTRY_LOCAL_AUTH_TOKEN}" \
  "https://sentry.io/api/0/projects/${SENTRY_ORG}/${SENTRY_PROJECT}/issues/?query=is:unresolved+level:fatal&statsPeriod=14d&limit=20")

# 请求 2: 获取未解决的 Error 级别 Issues（最近 14 天）
ERROR_ISSUES=$(curl -s -H "Authorization: Bearer ${SENTRY_LOCAL_AUTH_TOKEN}" \
  "https://sentry.io/api/0/projects/${SENTRY_ORG}/${SENTRY_PROJECT}/issues/?query=is:unresolved+level:error&statsPeriod=14d&limit=20")

# 校验响应是否为 JSON 数组（防止 rate limit / auth 错误导致 jq 失败）
for VAR in FATAL_ISSUES ERROR_ISSUES; do
  echo "${!VAR}" | jq -e 'type == "array"' > /dev/null 2>&1 || { echo "ERROR: ${VAR} 不是数组，请检查 API 响应"; exit 1; }
done

# 合并去重（按 Issue id 去重）
echo "$FATAL_ISSUES" "$ERROR_ISSUES" | jq -s 'add | unique_by(.id)'
```

> **注意**：使用 `jq` 而非 `python3 -m json.tool`。macOS 12.3+ 不再预装 Python，`jq` 更轻量且开发者通常已安装。

### 1.2 解析 Issue 列表

从 API 响应中提取每个 Issue 的关键字段：

| 字段 | 用途 |
|------|------|
| `id` | Sentry Issue ID（用于测试命名 `SENTRY-{id}`） |
| `title` | 错误标题（用于测试描述） |
| `level` | 严重级别（fatal / error） |
| `count` | 出现次数 |
| `culprit` | 出错的文件/函数路径 |
| `metadata.type` | 异常类型（TypeError / ReferenceError 等） |
| `metadata.value` | 异常信息 |
| `firstSeen` / `lastSeen` | 首次/最后出现时间 |

### 1.3 获取 Issue 详情（堆栈）

对每个需要处理的 Issue，获取最新事件的堆栈：

```bash
source <(grep -E '^SENTRY_(LOCAL_AUTH_TOKEN|ORG|PROJECT)=' .env.local)
curl -s -H "Authorization: Bearer ${SENTRY_LOCAL_AUTH_TOKEN}" \
  "https://sentry.io/api/0/issues/{issue_id}/events/latest/" \
  | jq '.'
```

从事件中提取：
- 堆栈帧（`exception.values[0].stacktrace.frames`）
- 定位到项目内的源文件和行号（过滤掉 `node_modules` 帧）
- 提取 tag `domain`（如有：balance / betting / odds）

---

## 阶段 2：阈值过滤

### 2.0 前置：第三方代码检测

在进入阈值判定前，先检查每个 Issue 的堆栈是否包含**项目内代码帧**：

```
对每个 Issue:
  Step A: 错误消息关键词检测
    检查 exception.values[0].value 是否包含以下关键词:
      - "tronlinkParams"    （TronLink 注入的 Proxy 属性）
      - "ethereum"           （MetaMask / 其他 EVM 钱包注入）
      - "solana"             （Phantom 等 Solana 钱包注入）
    如果命中任一关键词 → 标记为 SKIP

  Step B: 堆栈帧路径检测
    获取最新事件的 stacktrace frames
    过滤出 inApp == true 的帧
    再排除以下路径的帧（即使 inApp 标记为 true）:
      - injected/           （浏览器扩展注入脚本）
      - extensions/          （浏览器扩展）
      - chrome-extension://
      - moz-extension://
    如果过滤后剩余 0 个项目帧 → 标记为 SKIP

  SKIP 的 Issue:
    → 输出提示："[SKIP] #{id} — 第三方扩展错误（{关键词或路径}），非我方代码"
    → 跳过后续阈值判定
    → 建议用户在 Sentry 上执行 "Delete and discard future events"
```

> **背景**：Web3 项目用户常装钱包扩展（TronLink、MetaMask、Phantom 等），这些扩展向页面注入 JS 并可能触发 TypeError/Proxy 错误。这类错误我方无法修复，不应进入 regression 测试流程。
>
> **双重防线**：`instrumentation-client.ts` 的 `beforeSend` 在客户端拦截（阻止上报），此处在 `/sentry` Skill 端再次过滤（防止漏网之鱼进入测试流程）。遇到新的钱包扩展关键词时，同步更新两处。

### 2.1 阈值判定

按 DD-028 §7.4 的规则过滤，决定每个 Issue 的处理方式：

```
对每个 Issue（已通过第三方代码检测的）:
  │
  ├─ tag domain IN [balance, betting] ?
  │   → YES: 标记为 MUST_TEST（资金相关，零容忍）
  │
  ├─ level = fatal ?
  │   → YES: 标记为 MUST_TEST（页面崩溃，零容忍）
  │
  ├─ level = error AND 频率 >= 3 次/小时 ?
  │   → YES: 标记为 MUST_TEST（普通错误，频次触发）
  │   频率计算: count / ((lastSeen - firstSeen) 的小时数)
  │   若 firstSeen == lastSeen（仅出现 1 次），频率视为 0
  │
  └─ 其他
      → 标记为 SKIP（不进入飞轮）
```

### 输出过滤结果

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Sentry 巡检结果
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 统计: 共 {N} 个未解决 Issue，{M} 个需要生成测试

🔴 MUST_TEST（需生成 regression 测试）:
  1. SENTRY-{id}: {title}
     级别: {level} | 出现: {count} 次 | 文件: {culprit}
     原因: {资金相关 / 页面崩溃 / 频次超阈值}

  2. SENTRY-{id}: {title}
     ...

🚫 SKIP（第三方代码，非我方可控）:
  - SENTRY-{id}: {title}（来源: {injected.js / chrome-extension 等}）
  ...

⏭️ SKIP（未达阈值）:
  - SENTRY-{id}: {title}（{level}, {count} 次 — 未达阈值）
  ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

如果 MUST_TEST 数量为 0，输出 "当前无需处理的 Sentry Issue" 并结束。

---

## 阶段 3：生成 Regression 测试

对每个 MUST_TEST Issue：

### 3.1 定位测试文件

根据源文件路径确定测试文件位置（co-location 模式）：

```
源文件: lib/decimal.ts       → 测试文件: lib/decimal.test.ts
源文件: stores/tradeStore.ts → 测试文件: stores/tradeStore.test.ts
源文件: hooks/useWallet.ts   → 测试文件: hooks/useWallet.test.ts
```

- 如果测试文件已存在 → 追加新的 `it()` 到对应 `describe` 块末尾
- 如果测试文件不存在 → 创建新文件，包含基本 import 和 describe 结构

### 3.2 生成测试骨架

**命名规范**（DD-028 §3.2.2）：

```typescript
it('regression: SENTRY-{id} — {error description in English}', () => {
  // Sentry Issue: https://sentry.io/organizations/{org}/issues/{id}/
  // Error: {exception type}: {exception message}
  // File: {source file}:{line number}
  // First seen: {date}, Count: {count}
  //
  // TODO: implement assertion
})
```

**智能生成规则**：

根据源文件和错误类型，尝试生成具体的测试逻辑（而非仅 TODO）：

| 错误模式 | 自动生成内容 |
|---------|------------|
| `lib/decimal.ts` 相关 | 直接 import 函数，基于错误信息推断输入值，生成 `expect().toBe()` |
| `TypeError: Cannot read properties of undefined` | 生成空值/undefined 输入测试 |
| `RangeError` / `DecimalError` | 生成边界值测试 |
| 其他 | 生成 TODO 骨架，留给用户填充 |

### 3.3 检查是否可生成 ESLint 规则

如果错误模式可用 AST selector 匹配，建议新增 ESLint 规则：

```
发现: SENTRY-456 — 代码中直接使用 Math.random() 生成赔率
建议: 添加 ESLint 规则:
  {
    "selector": "CallExpression[callee.object.name='Math'][callee.property.name='random']",
    "message": "Do not use Math.random() for odds calculation"
  }
```

仅作为建议输出，不自动写入 .eslintrc.json。

### 3.4 输出生成结果

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 Regression 测试生成结果
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ 已生成 {N} 个 regression 测试:

  1. SENTRY-{id} → lib/decimal.test.ts
     it('regression: SENTRY-{id} — ...')
     状态: 已生成完整断言 / TODO 需手动补充

  2. SENTRY-{id} → hooks/useWallet.test.ts
     it('regression: SENTRY-{id} — ...')
     状态: TODO 需手动补充

💡 建议 ESLint 规则: {N} 条（见上方详情）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 3.5 等待用户确认

输出以上测试清单后，**暂停执行**，询问用户：

> "以上 {N} 个 regression 测试已生成，是否确认写入对应的 .test.ts 文件？"

- 用户确认 → 写入文件，继续阶段 4
- 用户要求修改 → 根据反馈调整后重新输出
- 用户取消 → 终止 Skill

> 此门控与 CLAUDE.md §一「方案确认后再开发」的核心协议一致。

---

## 阶段 4：验证与收尾

### 4.1 运行测试

```bash
pnpm test --run
```

- 全绿 → 提示 "所有测试通过，可以 commit"
- 有 TODO 测试 → 提示 "有 N 个测试需要补充断言逻辑"
- 有失败 → 定位失败原因并修复

### 4.2 更新 LESSONS.md

对 Fatal 级别的 Issue，在 `.progress/rewind-docs/LESSONS.md` 追加条目：

```markdown
### §{N}: {错误类别}

**Sentry Issue**: SENTRY-{id}
**根因**: {分析}
**修复**: {方案}
**防护**: regression 测试 in {test file}
```

### 4.3 关闭 Sentry Issue

测试通过后提示：
> "建议在 Sentry Dashboard 中将 SENTRY-{id} 标记为 Resolved。下次该错误再出现时 Sentry 会自动 reopen 并告警。"

---

## 手动模式（Sentry 未配置时的回退）

当 Sentry 环境变量未配置，或用户手动描述错误时：

```
/sentry manual
```

提示用户输入：
1. 错误描述（一句话）
2. 涉及的文件/函数（如知道）
3. 严重程度（fatal / error / warning）

然后跳过阶段 1-2，直接进入阶段 3 生成测试骨架。

测试命名使用 `MANUAL-{date}` 替代 `SENTRY-{id}`：

```typescript
it('regression: MANUAL-20260320 — {description}', () => {
  // Reported manually
  // TODO: implement assertion
})
```

---

## 单 Issue 诊断模式（Diagnose）

### 触发条件

用户粘贴 Sentry Issue URL（如 `https://oddfi.sentry.io/issues/7364402444/...`），或说"定位这个 Sentry 错误"、"诊断这个 issue"。

### Step 1: URL 解析

从 URL 中提取关键参数：

```
https://{org}.sentry.io/issues/{issue_id}/?environment={env}&project={project_id}
                                            ↑                  ↑
                                            可选过滤           项目 ID
```

提取：`issue_id`（必须）、`org`（从子域名，备用从 .env.local）

### Step 2: 加载认证

```bash
source <(grep -E '^SENTRY_(LOCAL_AUTH_TOKEN|ORG|PROJECT)=' .env.local)
```

优先使用 `SENTRY_LOCAL_AUTH_TOKEN`（Personal Token，有 issue 读取权限）。
`SENTRY_AUTH_TOKEN`（Org Token）通常仅有 source map 上传权限，查 issue 会 403。

### Step 3: 获取 Issue 元数据

```bash
curl -s -H "Authorization: Bearer ${SENTRY_LOCAL_AUTH_TOKEN}" \
  "https://sentry.io/api/0/organizations/${SENTRY_ORG}/issues/${ISSUE_ID}/" \
  | jq '{
    id, title, level, status,
    substatus, priority, count, userCount,
    firstSeen, lastSeen,
    culprit,
    type: .metadata.type,
    value: .metadata.value,
    filename: .metadata.filename,
    platform,
    release: .firstRelease.shortVersion
  }'
```

**关键字段速查**：

| 字段 | 诊断价值 |
|------|---------|
| `title` | 错误一句话概括 |
| `culprit` | 出错的路由/函数（如 `GET /zh/markets`） |
| `metadata.filename` | 出错的源文件路径 |
| `platform` | `node` = SSR 端 / `javascript` = 客户端 — **决定修复方向** |
| `count` / `userCount` | 频次和影响用户数 |
| `substatus` | `new` / `regressed` / `escalating` — 判断是新问题还是回归 |
| `priority` | Sentry 自动评级（high/medium/low） |

### Step 4: 获取最新事件（完整堆栈）

```bash
curl -s -H "Authorization: Bearer ${SENTRY_LOCAL_AUTH_TOKEN}" \
  "https://sentry.io/api/0/organizations/${SENTRY_ORG}/issues/${ISSUE_ID}/events/latest/" \
  | jq '.'
```

**从事件中提取三类信息**：

#### 4a. 堆栈帧（从底到顶读）

```
entries[0].data.values[0].stacktrace.frames[]
```

- `inApp: true` 的帧 = 项目代码（重点关注）
- `inApp: false` 的帧 = node_modules（追踪依赖调用链）
- 从最底层帧（触发点）向上追溯到项目代码帧 = **根因定位路径**

#### 4b. Tags（环境上下文）

```
tags[] → { key, value }
```

关键 tag：
- `runtime` → `node` 说明在 SSR 阶段触发
- `transaction` → 触发的路由（如 `GET /zh/markets`）
- `browser` / `os` → 客户端环境（仅客户端错误有用）
- `mechanism` → `auto.node.onunhandledrejection` / `onerror` 等

#### 4c. Contexts（运行环境详情）

```
contexts.runtime → { name, version }   // node v24.13.0 = Vercel SSR
contexts.cloud_resource → { cloud.provider, cloud.region }
```

### Step 5: 根因分析决策树

```
1. platform == "node" ?
   ├─ YES → SSR 端错误
   │   ├─ 错误涉及浏览器 API（indexedDB/localStorage/window/document）?
   │   │   → 模块顶层代码在 SSR 执行了浏览器专属 API
   │   │   → 修复: typeof window 守卫 / dynamic import / 延迟初始化
   │   │
   │   ├─ 错误来自 node_modules 依赖?
   │   │   → 依赖未做 SSR 兼容
   │   │   → 修复: next/dynamic + ssr:false / 条件导入
   │   │
   │   └─ 错误来自项目 API Route / Server Component?
   │       → 检查数据获取逻辑
   │
   └─ NO → 客户端错误
       ├─ 堆栈全是 node_modules 帧?（钱包扩展/第三方注入）
       │   → SKIP，建议 Sentry "Delete and discard"
       │
       └─ 有项目代码帧?
           → 正常 Bug，定位源文件修复
```

### Step 6: 源码追踪

从堆栈的**项目代码帧**出发，在本地代码中定位：

```bash
# 1. 找到堆栈中的项目文件
# 堆栈显示: lib/connectors.ts → 去项目中读取该文件

# 2. 追踪导入链（谁导入了这个模块，导致它在 SSR 被执行）
grep -r "from.*connectors" --include="*.ts" --include="*.tsx" | grep -v node_modules

# 3. 确认 'use client' 边界是否正确
# 检查导入链上的每个文件是否有 'use client' 标记
```

### Step 7: 修复 → 验证 → 提交

1. **最小化修复**：只改出问题的文件，不扩大范围
2. **类型检查**：`pnpm tsc --noEmit`
3. **构建验证**：`pnpm build`（确认编译通过）
4. **测试**：`pnpm test`（确认无回归）
5. **提交**：commit message 中注明 `Sentry: ODDFI-FRONTEND-{N}`

### 输出格式

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Sentry Issue 诊断报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Issue: ODDFI-FRONTEND-{N} (#{issue_id})
错误: {exception type}: {exception message}
路由: {culprit}
环境: {platform} / {runtime} / {cloud provider}
频次: {count} 次 ({firstSeen} ~ {lastSeen})
优先级: {priority}

📍 调用链:
  {项目文件} → {中间依赖} → {触发点（最底层帧）}

🔬 根因:
  {一句话描述根因}

🛠️ 修复:
  文件: {修改的文件}
  方案: {修复方案简述}
  Commit: {commit hash}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Sentry API 端点速查

| 用途 | 端点 | 说明 |
|------|------|------|
| Issue 元数据 | `GET /api/0/organizations/{org}/issues/{id}/` | 标题、级别、频次 |
| 最新事件 | `GET /api/0/organizations/{org}/issues/{id}/events/latest/` | 堆栈、tags、contexts |
| 事件列表 | `GET /api/0/organizations/{org}/issues/{id}/events/` | 所有事件（分页） |
| Issue 列表 | `GET /api/0/projects/{org}/{project}/issues/` | 批量查询（巡检模式用） |

> **注意**：`sentry-cli issues` 子命令仅支持 `list/mute/resolve`，不支持查看单个 Issue 详情。
> 单 Issue 诊断必须用 REST API（curl）。

---

## 与其他 Skill 的集成

| Skill | 集成方式 |
|-------|---------|
| `/preflight` | Check 7 检查是否有未处理的 Sentry Issue（见 preflight 更新） |
| `/quality-scan` | 共享 LESSONS.md 作为检查规则源 |
| `/feat` | 开发前自动提示相关模块是否有未解决的 Sentry Issue |
