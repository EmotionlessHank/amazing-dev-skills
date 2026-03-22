---
name: autopilot
description: DD/ENH 方案确认后的全自动开发流水线。当用户确认开发方案后（"确认"/"OK"/"开始"），或说 "/autopilot"、"自动开发"、"跑流水线"、"autopilot" 时触发。自动执行完整 Pipeline：批次开发 → 自动 Review → 自动修复 → 最终报告交付用户。Claude Code 应在识别到「多轮打磨方案后用户确认可以开发」的模式时主动调用此技能。
version: 1.0.0
---

# /autopilot — 全自动开发流水线

DD/ENH 方案经人类确认后，自动执行：**批次开发 → Code Review → Review 修复 → 最终交付**。

模拟真实团队工作流：产品确认 PRD → 工程师拆分实现 → 高级工程师 Review → 工程师修复 → 交付合并。

---

## 核心原则

1. **方案已确认才启动** — 本技能不负责方案设计，只负责执行已确认的方案
2. **全程无需人工介入** — 从第一行代码到 Review 修复完毕，中间不暂停等待用户
3. **绝不自动 Push/Merge** — 最终结果呈报用户，由用户决定 git 操作
4. **严格遵循项目规范** — CLAUDE.md 所有约定（Batch ≤3 文件、LESSONS 前置、Review 分级修复）全部生效

---

## 触发条件

### 被动触发（Claude 主动识别）

当 Claude 在对话中识别到以下**任一**模式时，**应主动调用此技能**：

| 模式 | 识别信号 |
|------|---------|
| 生成 DD/ENH 后用户确认开发 | Claude 生成了 DD 或 ENH 文档，用户回复"确认"/"OK"/"开始"/"可以开发"/"go"/"开始实施" |
| 用户指向已有方案要求实施 | "按照 DD-NNN 开发"、"实施这个方案"、"把 DD 落地"、"按这个 ENH 来" |
| 对话中存在开发方案且用户要求自动执行 | 用户说"自动开发"、"你来跑完"、"后面自动搞定" |

**关键**：不要求"多轮打磨"。即使 DD/ENH 是一轮生成、用户直接确认，也应触发。判断核心是：**存在开发方案文档（DD/ENH）+ 用户确认要开始编码实现**。

**识别后行为**：
1. 声明即将启动 autopilot 流水线
2. 简要列出即将执行的步骤（一句话概括每步）
3. 等待用户最终确认（"确认启动"或类似指令）
4. 确认后开始全自动执行

> **注意**：普通的"OK"/"确认"（如确认修改一个文件、确认一个问题的回答）不应触发。判断依据：对话上下文中是否存在 DD/ENH 开发方案文档，且用户的确认意图是「开始编码实现」。

### 主动触发

用户直接说：`/autopilot`、"自动开发"、"跑流水线"、"autopilot"、"全自动"。

主动触发时需要以下输入：
- DD/ENH 文档路径（必需 — 若上下文中已有则自动识别）
- 功能分支名（若已在正确分支则自动识别）

---

## Phase 0: 启动检查

### 0.1 方案文档定位

从对话上下文或用户输入中确定方案文档：

```
检查顺序：
1. 对话中明确提到的 DD-NNN / ENH-NNN 路径
2. 当前分支名推断（feat/xxx → DD-NNN-xxx.md）
3. 最近修改的 DD/ENH 文件
```

读取方案文档，提取：
- **实施计划**（§4 实施计划 中的子任务列表 / Phase 列表 / Batch 列表）
- **组件拆分**（哪些文件需要创建或修改）
- **技术决策**（关键实现选择）

**无实施计划 → BLOCK**：方案文档必须包含可执行的实施计划（子任务或 Phase），否则提示用户补充。

### 0.2 分支检查

```bash
git branch --show-current
```

| 当前分支 | 行为 |
|---------|------|
| `main` | **BLOCK** — 提示用户创建 `feat/` 或 `fix/` 分支 |
| `feat/*` / `fix/*` / `refactor/*` / `chore/*` | 通过，记录分支名 |
| 其他 | 警告，询问是否在正确分支 |

### 0.3 LESSONS.md 关联

读取 `.progress/rewind-docs/LESSONS.md`，根据方案涉及的技术领域自动匹配相关章节（规则同 feat skill §0.3）。

输出关键陷阱提醒，**不等待用户确认，直接继续**。

### 0.4 工作区状态

```bash
git status --porcelain
```

若有未提交的改动 → 警告并询问用户是否先 stash 或 commit。

### 0.5 启动播报

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 Autopilot 流水线启动
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
方案: {DD-NNN / ENH-NNN 标题}
分支: {branch_name}
实施计划: {N} 个 Batch / Phase

Pipeline:
  Phase 1: 批次开发 → {N} 个 Batch
  Phase 2: 自动 Code Review
  Phase 3: Review 修复（A 类立即修 / B 类转 enh-todo）
  Phase 4: 最终报告

⚙️ 开始执行...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phase 1: 批次开发

### 1.1 Batch 拆分

从方案文档的实施计划中提取 Batch/Phase/子任务列表。每个 Batch 遵循：

- **≤ 3 个文件**修改（CLAUDE.md §一 文件修改限制）
- 每个 Batch 是一个**逻辑完整的最小单元**（可独立通过 type-check）
- Batch 之间有依赖时，严格按序执行

若方案文档的 Phase 粒度过大（单 Phase > 3 文件），自动细分为多个 Batch：

```
DD Phase 1（5 文件）→ Batch 1（3 文件）+ Batch 2（2 文件）
```

### 1.2 单 Batch 执行流程

对每个 Batch，按以下步骤执行：

**Step 1: 编码实现**
- 按方案文档的设计进行编码
- 遵守 CLAUDE.md 所有代码规范（Design Token、decimal.ts、触控热区等）
- 参考 LESSONS.md 关联章节避免已知陷阱

**Step 2: 验证**
```bash
pnpm type-check
```

- type-check 通过 → 继续
- type-check 失败 → **立即修复**，不跳到下一 Batch
- 若失败是遗留错误（非本次引入）→ 标注"遗留错误"并继续

**Step 3: 提交**
```bash
git add {修改的文件}
git commit -m "{commit message}"
```

Commit message 规范：
- 简体中文
- 格式：`feat(scope): 描述` 或 `fix(scope): 描述`
- 禁止 `Co-Authored-By`

**Step 4: Batch 播报**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 Batch {N}/{M} 完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
修改文件:
  ✅ path/to/file1.tsx（新增/修改）
  ✅ path/to/file2.ts（新增/修改）

验证: type-check ✅
提交: {commit hash} {commit message}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 1.3 全部 Batch 完成后

```bash
pnpm type-check && pnpm test
```

输出阶段性总结：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Phase 1 完成 — 批次开发
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
完成 Batch: {M}/{M}
修改文件: {N} 个
提交数: {M} 笔
type-check: ✅
test: ✅ / ⚠️ {失败数}

→ 进入 Phase 2: 自动 Code Review
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phase 2: 自动 Code Review

### 2.1 角色切换声明

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 已进入 Review Agent 模式
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 2.2 Review 上下文加载（CLAUDE.md §16.1 强制）

按顺序读取：
1. `.progress/review-docs/REVIEW.md`（历史审查覆盖范围）
2. `CLAUDE.md`（架构约定、设计系统、代码规范）
3. `package.json`（实际依赖版本）
4. `tsconfig.json`（TS 严格度）

### 2.3 获取 Diff

```bash
git diff main...HEAD
```

### 2.4 执行审查

严格按照 `.progress/prompts/qa-review.md` 结构审查：

1. **Critical** — 阻断上线（Bug、安全漏洞、Hydration 失败等）
2. **Major** — 合并前必须修复（逻辑错误、缺失边界、性能问题）
3. **Minor** — 下个 PR 优化（命名、结构、可读性）
4. **Best Practices Checklist** — 逐项验证
5. **Action List** — Top 5 by ROI

附加 §17.5 测试覆盖审查章节。

### 2.5 输出 REV 报告

报告写入 `.progress/review-docs/`：

```
命名: REV-{DD编号或分支名}-v1-{ShortDesc}.md
示例: REV-DD026-v1-mock-betting-flow.md
```

### 2.6 Review 完成声明

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Phase 2 完成 — Code Review
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
报告: .progress/review-docs/{REV-file}
判定: 🟢 Ship It / 🟡 Needs Changes / 🔴 Major Rework
Critical: {N} | Major: {N} | Minor: {N}

Review Agent 模式结束
→ 进入 Phase 3: Review 修复
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phase 3: Review 修复（CLAUDE.md §16.3 分级修复）

### 3.1 Triage 分类

通读 REV 报告中的行动清单，分为两类：

| 类别 | 覆盖范围 | 处理方式 |
|------|---------|---------|
| **A 类（立即修复）** | Critical、Major 级别的 Bug、阻断逻辑错误、严重性能问题、违反架构规则 | 立即修改代码 |
| **B 类（延迟处理）** | Minor、重构建议、低 ROI 代码洁癖、当前修改风险过高的非紧急优化 | 转移至 enh-todo.md |

### 3.2 A 类修复

- 直接修改业务代码
- 若涉及 > 3 文件，拆分为多个 sub-batch 分批执行
- 每个 sub-batch 执行后 `pnpm type-check`
- 所有 A 类修复完成后统一提交：

```bash
git add {修改的文件}
git commit -m "fix: Review A 类问题修复"
```

### 3.3 B 类转移

按 CLAUDE.md §16.3 规则，将 B 类问题写入 `.progress/tasks/enh-todo.md`：

| 关键词 | 归入主题 |
|--------|---------|
| `<img>`、`next/image`、Image | T1: next/image 迁移 |
| hex、颜色、Token、硬编码色 | T2: Design Token |
| Deposit、ProxyWallet | T3: Deposit 流程 |
| 重复、提取、hook、utils | T4: 工具函数 |
| UI、UX、skeleton、Toast | T5: UI/UX 细节 |
| config、lint、a11y | T6: 工程配置 |

写入格式：`- [ ] [P:low] {问题描述} (来源: REV-xxx-v1)`

### 3.4 REV 报告状态回写

- 已修复的 A 类：`[x]`
- B 类：追加 `→ 已转移至 enh-todo.md`
- 底部追加修复记录节

### 3.5 最终验证

```bash
pnpm type-check && pnpm test
```

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Phase 3 完成 — Review 修复
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A 类修复: {N} 个（已提交）
B 类转移: {N} 个（→ enh-todo.md）
type-check: ✅
test: ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phase 4: 最终交付报告

### 4.1 生成总结报告

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏁 Autopilot 流水线完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 方案: {DD/ENH 编号 + 标题}
🔀 分支: {branch_name}

📦 开发阶段:
   Batch 数: {M}
   修改文件: {N} 个
   新增文件: {X} 个

🔍 Review 结果:
   判定: {Ship It / Needs Changes}
   Critical: {N} → 已全部修复
   Major: {N} → 已全部修复
   Minor: {N} → 已转移 enh-todo.md
   报告: {REV 文件路径}

📝 Commit 历史:
   {hash1} {message1}
   {hash2} {message2}
   ...
   {hashN} fix: Review A 类问题修复

✅ 验证: type-check ✅ | test ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏸️ 等待你的指示
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

以下操作需要你来决定:

  1. 查看 diff:    git diff main...HEAD
  2. 查看 Review:  cat {REV 文件路径}
  3. 提交分支:     git push origin {branch_name}
  4. 合并主线:     git checkout main && git merge --squash {branch_name}
  5. 继续修改:     告诉我需要调整的部分

⛔ Autopilot 不会自动执行任何 push/merge 操作。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 4.2 todo.md 更新

读取 `.progress/tasks/todo.md`，将当前任务标记为已完成（若能找到对应条目）。

### 4.3 Worktree 上下文播报

若当前在 Worktree 中开发，附加 CLAUDE.md 要求的上下文播报：

```
📋 DD 进度: {DD 路径} — 已完成全部 Phase
📂 工作目录: {当前路径}
🔀 分支/提交: {分支名}
   - {各 commit 列表}
```

---

## 异常处理

| 场景 | 处理方式 |
|------|---------|
| 方案文档无实施计划 | BLOCK — 提示用户在 DD 中补充 §4 实施计划 |
| 当前在 main 分支 | BLOCK — 提示创建功能分支 |
| type-check 持续失败（同一错误修复 3 次仍失败） | 暂停 Pipeline，报告错误详情，请求用户介入 |
| test 失败但非本次引入 | 标注"遗留测试失败"，继续 Pipeline |
| Review 判定为 Major Rework（🔴） | 暂停 Pipeline，将 Review 报告呈报用户，建议重新设计方案 |
| 单 Batch 改动需超 3 文件 | 自动拆分为 sub-batch，每批 ≤ 3 文件 |
| A 类修复引入新问题 | 回滚该修复，标记为需用户介入，继续处理其他 A 类问题 |
| 中途用户发消息 | 暂停 Pipeline，响应用户，用户确认后继续 |

---

## 与现有 Skill 的关系

| Skill | 关系 |
|-------|------|
| `feat` | feat 覆盖「前半程」（分支检查 → DD 创建 → 确认门控），autopilot 接管「后半程」（确认后 → 开发 → Review → 修复）。两者互补，不重复。 |
| `quality-scan` | autopilot Phase 2 的 Review 已包含质量检查。但用户可在 Pipeline 完成后额外运行 quality-scan 做二次验证。 |
| `enh-review` | autopilot Phase 3 的 B 类问题会写入 enh-todo.md。后续可运行 enh-review 做增强项维护。 |
| `parallel-worktree` | 并行场景下，每个 worktree 中的 Agent 可独立触发 autopilot。 |

---

## 安全红线

1. **绝不自动 git push** — 推送是敏感操作，必须用户手动执行
2. **绝不自动 git merge** — 合并策略由用户决定（squash merge、rebase 等）
3. **绝不修改 .progress/ 以外的非代码文件** — 如 CLAUDE.md、rules.md、.env.local
4. **绝不跳过 type-check 失败** — 构建必须通过
5. **Major Rework 必须暂停** — Review 判定为红灯时不强行修复，交由用户决策
