---
name: worktree-dev
description: 强制 Worktree 隔离开发。当用户说 "/worktree-dev"、"worktree 开发"、"隔离开发"、"开个 worktree 做"、"wt dev" 时触发。自动执行：从 main 拉新分支 → 创建 worktree → 同步 env → 注入隔离上下文 → 全程锁定工作目录。解决"Agent 跳出 worktree 污染主工作区"和"忘记从 main 拉新分支"两大高频问题。
version: 1.0.0
---

# /worktree-dev — 强制 Worktree 隔离开发

**核心铁律：一旦进入 worktree，所有文件读写、git 操作、构建命令必须在 worktree 目录下执行，严禁跳回主工作区。**

---

## 阶段 0：初始化参数收集

### 0.1 收集必要信息

从用户描述中提取：

| 参数 | 来源 | 示例 |
|------|------|------|
| 功能名称 | 用户描述 | "lend 页面开发" |
| 分支名 | 自动推断（用户可覆盖） | `feat/lend-page` |
| DD 文档 | `.progress/designs/` 匹配 | `DD-048-lend.md` |

**分支命名规范**（继承项目规则）：

| 前缀 | 用途 |
|------|------|
| `feat/` | 新功能 |
| `fix/` | Bug 修复 |
| `chore/` | 配置/依赖 |
| `refactor/` | 重构 |

### 0.2 前置检查

```bash
# 确认 main 分支是最新的
git fetch origin main
git log HEAD..origin/main --oneline  # 有落后则提醒用户先 pull
```

---

## 阶段 1：Worktree 创建

### 1.1 创建 Worktree（强制路径）

```bash
# ✅ 唯一合法路径：.claude/worktrees/<name>
git worktree add .claude/worktrees/<name> -b <branch-name> main

# ❌ 以下路径全部禁止
# git worktree add .worktrees/<name>         ← 禁止
# git worktree add worktrees/<name>          ← 禁止
# git worktree add /tmp/<name>               ← 禁止
```

### 1.2 同步环境文件

```bash
# .env.local 不入库，worktree 必须手动同步
cp .env.local .claude/worktrees/<name>/.env.local
```

### 1.3 安装依赖

```bash
cd .claude/worktrees/<name> && pnpm install
```

### 1.4 输出创建确认

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌿 Worktree 已创建
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 路径: .claude/worktrees/<name>
🔀 分支: <branch-name>（基于 main）
📋 DD: <DD 文档路径 | 无>
🔒 隔离模式: 已激活

⚠️ 从此刻起，所有操作锁定在 worktree 目录内。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 阶段 2：隔离开发（核心约束）

### 2.0 工作目录锁定（最高优先级规则）

**进入 worktree 后，以下行为全部禁止，无任何例外：**

| 禁止行为 | 说明 |
|---------|------|
| ❌ `cd /Users/hang/work/oddfi-frontend` | 禁止切回主工作区 |
| ❌ 读写主工作区文件 | 禁止 Read/Edit/Write 主工作区路径 |
| ❌ 在主工作区执行 git 命令 | 禁止在主工作区 commit/push/merge |
| ❌ 在主工作区执行 build/test | 禁止在主工作区 pnpm dev/build/test |

**唯一合法例外**：

| 允许行为 | 说明 |
|---------|------|
| ✅ 读取 `.progress/` 下的文档 | DD 文档、todo、lessons 等只读参考 |
| ✅ 读取 `CLAUDE.md` / `rules/` | 项目规则只读参考 |

### 2.1 路径守卫（每次工具调用前自检）

Agent 在执行任何文件操作前，必须验证路径：

```
合法路径前缀：/Users/hang/work/oddfi-frontend/.claude/worktrees/<name>/
只读路径前缀：/Users/hang/work/oddfi-frontend/.progress/
只读路径前缀：/Users/hang/work/oddfi-frontend/CLAUDE.md
只读路径前缀：/Users/hang/work/oddfi-frontend/.claude/rules/

其他一切主工作区路径 → 🚫 BLOCK
```

### 2.2 批次开发

沿用 `/feat` 技能的批次规则：

- 每批 ≤ 3 个文件
- 每批完成后验证：

```bash
cd .claude/worktrees/<name> && pnpm type-check && pnpm test
```

### 2.3 批次播报（含 worktree 上下文）

每批完成后输出：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 Batch N/M 完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 Worktree: .claude/worktrees/<name>
🔀 分支: <branch-name>

修改文件：
  ✅ <worktree-相对路径>/file1.tsx
  ✅ <worktree-相对路径>/file2.ts

验证：type-check ✅ | test ✅
🔒 隔离状态：正常（未触碰主工作区）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 阶段 3：提交与收尾

### 3.1 在 worktree 内提交

```bash
cd .claude/worktrees/<name>
git add <具体文件>
git commit -m "<中文 commit message>"
```

**commit message 规范**（继承项目规则）：
- 必须简体中文
- 禁止 Co-Authored-By 行

### 3.2 最终验证

```bash
cd .claude/worktrees/<name>
pnpm type-check && pnpm test
```

### 3.3 完成播报

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Worktree 开发完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 Worktree: .claude/worktrees/<name>
🔀 分支: <branch-name>
📋 DD: <DD 文档路径>
📝 Commits: <commit 数量>
🔒 隔离状态：全程未触碰主工作区 ✅

💡 下一步（由用户在主工作区手动执行）：
  1. 回到主工作区: cd /Users/hang/work/oddfi-frontend
  2. 合并: git merge --squash <branch-name>
  3. 提交: git commit -m "<squash commit message>"
  4. 清理: git worktree remove .claude/worktrees/<name>
  5. 删分支: git branch -d <branch-name>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**禁止 Agent 自行执行合并/清理** — 合并回 main 是用户的权责。

---

## 异常处理

| 场景 | 处理方式 |
|------|---------|
| worktree 路径已存在 | 提示用户：是复用还是删除重建 |
| `.env.local` 不存在 | 警告用户补全，Route Handler 代理会 500 |
| pnpm install 失败 | 检查 Node/pnpm 版本，输出错误日志 |
| Agent 意外切回主工作区 | 立即停止操作，声明违规，切回 worktree 继续 |
| type-check 有遗留错误 | 标注"遗留错误"，与本次改动无关则继续 |
| 用户要求"顺手改一下主工作区的 XX" | 🚫 拒绝，建议用户在主工作区另开会话处理 |

---

## Agent 委派场景

当主 Agent 通过 `Agent tool` 委派 subagent 执行 worktree 开发时，prompt 必须包含：

```
⚠️ 隔离约束（最高优先级）：
- 工作目录锁定: /Users/hang/work/oddfi-frontend/.claude/worktrees/<name>/
- 所有 Read/Edit/Write/Bash 操作必须在此目录下
- 禁止读写主工作区 /Users/hang/work/oddfi-frontend/ 下的非 .progress/ 文件
- 禁止在主工作区执行任何 git/pnpm 命令
```
