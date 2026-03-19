---
name: sentry
description: Sentry 错误巡检与 Regression 测试生成。当用户说 "/sentry"、"检查 Sentry"、"Sentry 巡检"、"sentry scan"、"生成回归测试" 时触发。连接 Sentry API 获取未解决的 Fatal/Error Issue，按阈值规则过滤，自动定位源文件并生成 regression 测试骨架，输出待 review 的测试列表。
version: 1.0.0
---

# /sentry — Sentry 错误巡检与 Regression 测试自动生成

连接 Sentry API，获取线上未解决的严重错误，自动生成 regression 测试骨架。
设计文档：DD-028 §7.2

---

## 前置条件检查

执行 Skill 前，先验证 Sentry 环境是否就绪：

```bash
# 检查环境变量
echo "SENTRY_AUTH_TOKEN: ${SENTRY_AUTH_TOKEN:+SET}"
echo "SENTRY_ORG: ${SENTRY_ORG:-NOT_SET}"
echo "SENTRY_PROJECT: ${SENTRY_PROJECT:-NOT_SET}"
```

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
# 请求 1: 获取未解决的 Fatal 级别 Issues（最近 7 天）
FATAL_ISSUES=$(curl -s -H "Authorization: Bearer ${SENTRY_AUTH_TOKEN}" \
  "https://sentry.io/api/0/projects/${SENTRY_ORG}/${SENTRY_PROJECT}/issues/?query=is:unresolved+level:fatal&statsPeriod=7d&limit=20")

# 请求 2: 获取未解决的 Error 级别 Issues（最近 7 天）
ERROR_ISSUES=$(curl -s -H "Authorization: Bearer ${SENTRY_AUTH_TOKEN}" \
  "https://sentry.io/api/0/projects/${SENTRY_ORG}/${SENTRY_PROJECT}/issues/?query=is:unresolved+level:error&statsPeriod=7d&limit=20")

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
curl -s -H "Authorization: Bearer ${SENTRY_AUTH_TOKEN}" \
  "https://sentry.io/api/0/issues/{issue_id}/events/latest/" \
  | jq '.'
```

从事件中提取：
- 堆栈帧（`exception.values[0].stacktrace.frames`）
- 定位到项目内的源文件和行号（过滤掉 `node_modules` 帧）
- 提取 tag `domain`（如有：balance / betting / odds）

---

## 阶段 2：阈值过滤

按 DD-028 §7.4 的规则过滤，决定每个 Issue 的处理方式：

```
对每个 Issue:
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

⏭️ SKIP（不处理）:
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

## 与其他 Skill 的集成

| Skill | 集成方式 |
|-------|---------|
| `/preflight` | Check 7 检查是否有未处理的 Sentry Issue（见 preflight 更新） |
| `/quality-scan` | 共享 LESSONS.md 作为检查规则源 |
| `/feat` | 开发前自动提示相关模块是否有未解决的 Sentry Issue |
