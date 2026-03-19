---
name: parallel-worktree
description: 并行 Worktree 开发编排。当用户说 "/parallel"、"并行开发"、"开 worktree"、"并行任务"、"parallel dev"、"拆分并行" 时触发。自动执行：任务分解 → 文件所有权检查 → worktree 创建 → 聚焦上下文注入 → 合并指引。解决"任务拆分不当导致合并冲突"和"Agent 缺乏聚焦上下文导致越界修改"两大核心问题。
version: 1.0.0
---

# /parallel — 并行 Worktree 开发编排

当用户需要多任务并行开发时，按以下阶段顺序执行。核心原则：**按文件所有权隔离任务，让每个 Agent 只看到自己该做的事。**

---

## 阶段 0：并行可行性评估

### 0.1 收集任务列表

从用户描述中提取所有待执行任务。若不明确，读取 `.progress/tasks/todo.md` 获取活跃工作项。

### 0.2 文件所有权分析

对每个任务，推断其涉及的文件范围：

```
任务 → 路由目录 + 组件目录 + 类型文件 + Mock Handler
```

项目的天然隔离边界：

| 路由 | 组件目录 | 独立性 |
|------|---------|--------|
| `app/markets/` | `components/market/` | 高 |
| `app/stake/` | `components/stake/` | 高 |
| `app/swap/` | `components/swap/` | 高 |
| `app/trade/` | `components/trade/` | 高 |
| `app/invite/` | `components/invite/` | 高 |

共享文件（冲突热点）：

| 文件 | 冲突风险 | 处理策略 |
|------|---------|---------|
| `tailwind.config.ts` | 高 | 基础设施分支独占 |
| `lib/api.ts` | 中 | 新增 endpoint 通常不冲突 |
| `types/*.ts` | 低 | 各自新增类型定义 |
| `mocks/handlers/index.ts` | 低 | 仅追加 import |

### 0.3 可行性判定

检查以下条件，全部满足才推荐并行：

- [ ] 任务间文件所有权重叠 ≤ 2 个文件
- [ ] 重叠文件均为"追加型"（如 types/、handlers/index.ts），非"修改型"
- [ ] 并行任务数 ≤ 3（1 人团队认知上限）
- [ ] 每个任务有明确的 DD 文档或需求描述

**不满足时**：向用户说明原因，建议串行执行或调整任务拆分。

### 0.4 输出并行计划

```
📋 并行任务分解
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🅰️ Worktree A: {分支名}
   任务: {任务描述}
   文件范围: {目录列表}
   DD: {DD 文档路径}

🅱️ Worktree B: {分支名}
   任务: {任务描述}
   文件范围: {目录列表}
   DD: {DD 文档路径}

⚠️ 共享文件: {列表}
   → 处理策略: {说明}

📐 合并顺序: A → B（B 需 rebase）
✅ 文件冲突风险: {低/中/高}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

等待用户确认后进入下一阶段。

---

## 阶段 1：Worktree 创建与环境初始化

### 1.1 创建 Worktree

为每个并行任务执行：

```bash
git worktree add .worktrees/{name} -b {branch-name}
cd .worktrees/{name} && pnpm install
```

分支命名遵循项目规范：`feat/`、`fix/`、`refactor/`、`chore/`。

### 1.2 注入聚焦上下文

在每个 worktree 根目录生成 `WORKTREE_CONTEXT.md`：

```markdown
# Worktree 任务上下文

## 当前任务
{分支名} — {任务描述}

## DD 文档
{DD 文档路径，无则标注"无需 DD"}

## 文件所有权（只允许修改以下文件）
{文件/目录列表}

## 禁止修改（其他 worktree 负责）
{其他 worktree 的文件范围}

## 当前进度
{初始为"尚未开始"}
```

### 1.3 输出启动指引

为用户生成可直接复制的终端命令：

```
🚀 启动并行开发
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

终端 1:
  cd .worktrees/{name-a}
  claude
  > 读取 WORKTREE_CONTEXT.md，按 DD 文档开始开发

终端 2:
  cd .worktrees/{name-b}
  claude
  > 读取 WORKTREE_CONTEXT.md，按 DD 文档开始开发

或使用 Claude 原生方式:
  终端 1: claude --worktree {name-a}
  终端 2: claude --worktree {name-b}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 阶段 2：合并指引（所有 worktree 完成后）

当用户表示所有并行任务已完成，输出合并操作指引：

### 2.1 合并前检查

```bash
# 在每个 worktree 中确认测试通过
cd .worktrees/{name} && pnpm type-check && pnpm test
```

### 2.2 按序合并

```bash
# 回到主目录
cd /Users/hang/work/oddfi-frontend

# 合并第一个分支（冲突风险最低的先合）
git merge --squash {branch-a}
git commit -m "{commit message}"

# 第二个分支 rebase 后合并
cd .worktrees/{name-b}
git rebase main
cd /Users/hang/work/oddfi-frontend
git merge --squash {branch-b}
git commit -m "{commit message}"

# 最终验证
pnpm type-check && pnpm test && pnpm build
```

### 2.3 清理

```bash
git worktree remove .worktrees/{name-a}
git worktree remove .worktrees/{name-b}
git branch -d {branch-a}
git branch -d {branch-b}
```

---

## 异常处理

| 场景 | 处理方式 |
|------|---------|
| 文件所有权冲突严重 | 建议串行，不强行并行 |
| 合并时出现冲突 | 展示冲突文件，辅助用户手动解决 |
| 某个 worktree 任务膨胀 | 暂停该 worktree，重新评估任务范围 |
| Agent 修改了越界文件 | 提醒用户回退越界改动，从 WORKTREE_CONTEXT.md 重申边界 |
| 磁盘空间不足 | 清理已完成的 worktree 和 node_modules |

---

## 附加资源

### 参考文档

- **`.progress/dev-docs/parallel-worktree-sop.md`** — 完整 SOP 文档（含决策公式、模式速查、注意事项）
- **`.progress/dev-docs/research/worktree-parallel-dev-research.md`** — 行业调研报告（含 Anthropic C 编译器案例、大神工作流）

### 并行模式速查

| 模式 | 描述 | 适用场景 |
|------|------|---------|
| 分治并行 | 按文件所有权拆分，各开 worktree | 多个独立页面/模块 |
| 竞争式实现 | 同一需求两个 worktree 各做一版 | 方案选型 |
| 基础设施 + 业务 | 基础改动 + 业务功能并行 | 重构期间不阻塞业务 |
