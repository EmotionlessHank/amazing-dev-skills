---
name: worktree-dev
description: 强制 Worktree 隔离开发。当用户说 "/worktree-dev"、"worktree 开发"、"隔离开发"、"开个 worktree 做"、"wt dev" 时触发。自动执行：从主分支拉新分支 → 创建 worktree → 同步 env → 注入隔离上下文 → 全程锁定工作目录。解决"Agent 跳出 worktree 污染主工作区"和"忘记从主分支拉新分支"两大高频问题。
version: 2.0.0
---

# /worktree-dev — 强制 Worktree 隔离开发

> **多项目通用版。** `{占位符}` 为各项目定制点，迁移前先按 `SETUP.md` 替换。
> 与 feat/autopilot 配套：worktree-dev 负责**隔离环境搭建 + cwd 锁定**，feat 在其中出方案、autopilot 在其中开发。

**核心铁律：一旦进入 worktree，所有文件读写、git 操作、构建命令必须在 worktree 目录下执行，严禁跳回主工作区。**

---

## 阶段 0：初始化参数收集

### 0.1 收集必要信息

| 参数 | 来源 | 示例 |
|------|------|------|
| 功能名称 | 用户描述 | "lend 页面开发" |
| 分支名 | 自动推断（用户可覆盖） | `feat/lend-page` |
| 方案文档 | `{DOCS_ROOT}/{type}/` 匹配 | `{ID}` 子文件夹 |

**分支命名规范**（继承项目规则）：`feat/`（新功能）· `fix/`（修复）· `chore/`（配置/依赖）· `refactor/`（重构）。

### 0.2 前置检查

```bash
git fetch origin {MAIN_BRANCH}
git log HEAD..origin/{MAIN_BRANCH} --oneline   # 有落后则提醒用户先 pull
```

---

## 阶段 1：Worktree 创建

### 1.1 创建 Worktree（强制路径）

```bash
# ✅ 唯一合法路径：{WORKTREE_BASE}/<name>
git worktree add {WORKTREE_BASE}/<name> -b <branch-name> {MAIN_BRANCH}

# ❌ 禁止其它路径（/tmp、仓库外、随意目录）
```

> 若项目有封装脚本 `{WT_HELPER}`（一步建 worktree + 自动 symlink env/配置）→ 优先用它。

### 1.2 同步环境/运行时文件（symlink · 强制）

所有 `{ENV_FILES}`（及个人配置如本地权限白名单）必须用 **symlink** 而非 `cp`——复制件是静态快照，主工作区后续改 env（换 RPC、改 API Key）worktree 感知不到，排查环境问题时方向全错。

```bash
# 在主工作区根目录执行，每个 env 文件 symlink 回主工作区（路径深度按 {WORKTREE_BASE} 调整）
ln -sf {相对主工作区路径}/{ENV_FILE} {WORKTREE_BASE}/<name>/{ENV_FILE}
```

> **缺失后果**：env 文件缺失常**静默回落**到默认/错误环境（不报错），是最隐蔽的坑。逐个确认 symlink 指向有效文件。`{ENV_FILES}` 的具体清单 + 各自缺失后果见 `SETUP.md`。

### 1.3 安装依赖

```bash
{INSTALL}   # 在 worktree 目录下；若依赖用全局 store 硬链接（如 pnpm）会很快
```

### 1.4 输出创建确认

```
🌿 Worktree 已创建
📂 路径: {WORKTREE_BASE}/<name>
🔀 分支: <branch-name>（基于 {MAIN_BRANCH}）
📋 方案: <方案文档路径 | 无>
🔒 隔离模式: 已激活
⚠️ 从此刻起，所有操作锁定在 worktree 目录内。
```

---

## 阶段 2：隔离开发（核心约束）

### 2.0 Pre-batch Read 清单（强制 · 进入开发第一步）

**进入 worktree 后、动手 Edit/Write 之前**，必须先一次性把本批次涉及的全部文件并发 Read 完。

**为什么不能边 Edit 边补 Read**：
- Edit/Write/MultiEdit 有硬约束——必须先 Read 同一路径才能 Edit
- **路径精确匹配**：主工作区路径与 worktree 路径在工具看来是两个文件（`src/x.ts` ≠ `{WORKTREE_BASE}/X/src/x.ts`），主工作区那次 Read 不能让 worktree 的 Edit 通过
- 边 Edit-fail 边补 Read → 每个文件一轮"Edit 失败→Read→重试"，N 文件 = N 轮往返，节奏被反复打断

**正确做法**：① 列出本次计划改动的全部文件（含同目录批量、i18n 全语种、co-location 测试、相邻组件）→ ② **一条消息内并发 Read 整个清单** → ③ 连续 Edit。

| 任务类型 | 必读清单 |
|---------|---------|
| 改 1 个组件 | 该文件 + 它的测试 + 同目录被引用的子组件 |
| 改 i18n 文案 | 全部语种 message 文件一次读完 |
| 改 hook 行为 | hook 文件 + 测试 + 调用方组件（最多 3-5 个） |
| 改基础设施 | 待改文件 + 1 个同类参考文件（风格对齐） |

> 协同 hook（可选）：`{EDIT_READ_PREREQ_HOOK}` 在检测到 "File has not been read yet" 时强提醒批量 Read。

### 2.0.1 工作目录锁定（最高优先级规则）

进入 worktree 后，以下行为全部禁止，无例外：

| 禁止 | 说明 |
|------|------|
| ❌ `cd {REPO_ROOT}` 切回主工作区 | — |
| ❌ Read/Edit/Write 主工作区路径 | — |
| ❌ 在主工作区执行 git commit/push/merge | — |
| ❌ 在主工作区执行 build/test/dev | — |

**唯一合法例外（只读）**：读 `{DOCS_ROOT}/` 下文档（方案/todo/lessons）、读 `{RULES}`（项目规则）。

### 2.1 路径守卫（每次工具调用前自检）

```
合法读写前缀：{REPO_ROOT}/{WORKTREE_BASE}/<name>/
只读前缀：{REPO_ROOT}/{DOCS_ROOT}/ · {REPO_ROOT}/{RULES}
其他一切主工作区路径 → 🚫 BLOCK
```

### 2.2 批次开发

沿用 `/feat` → `/autopilot` 的批次规则：每批 ≤ `{MAX_FILES_PER_BATCH}` 文件，每批完成后在 worktree 内验证：

```bash
cd {WORKTREE_BASE}/<name> && {TYPECHECK} && {TEST}
```

### 2.3 批次播报（含 worktree 上下文）

```
📦 Batch N/M 完成
📂 Worktree: {WORKTREE_BASE}/<name> | 🔀 <branch-name>
修改文件: <worktree-相对路径>...
验证: type-check ✅ | test ✅
🔒 隔离状态：正常（未触碰主工作区）
```

---

## 阶段 3：提交与收尾

### 3.1 在 worktree 内提交

```bash
cd {WORKTREE_BASE}/<name>
git add <具体文件> && git commit -m "<commit message>"
```

commit message 继承项目规范（`{COMMIT_CONVENTION}`，如语言/禁止 AI 署名）。

### 3.2 最终验证

```bash
cd {WORKTREE_BASE}/<name> && {TYPECHECK} && {LINT} && {TEST} && {BUILD}
```

### 3.3 完成播报 + 收尾指引

```
✅ Worktree 开发完成
📂 {WORKTREE_BASE}/<name> | 🔀 <branch-name> | 📝 <commit 数>
🔒 隔离状态：全程未触碰主工作区 ✅

💡 下一步（默认由 AI 收尾 / 或用户手动，按项目约定）：
  1. 同步 {DOCS_ROOT} 文档回主工作区（若 gitignore 不随 merge 流回）
  2. 回主工作区 squash 合并: git merge --squash <branch-name> → commit
  3. 清理: git worktree remove {WORKTREE_BASE}/<name> + git branch -d <branch-name>
```

> **合并回主分支 + push 远端是用户权责**——AI 默认止于本地主分支 squash commit，不自动 push（除非项目约定 AI 可收尾合并；push 一律由用户决定）。

---

## 异常处理

| 场景 | 处理 |
|------|------|
| worktree 路径已存在 | 提示用户：复用还是删除重建 |
| `{ENV_FILES}` symlink 缺失/指向不存在文件 | 检查全部 env symlink 指向主工作区，补全后重启 dev server |
| 依赖安装失败 | 检查运行时版本，输出错误日志 |
| Agent 意外切回主工作区 | 立即停止，声明违规，切回 worktree 继续 |
| type-check 有遗留错误 | 标"遗留错误"，与本次无关则继续 |
| 用户要求"顺手改一下主工作区的 XX" | 🚫 拒绝，建议另开会话在主工作区处理 |

---

## Agent 委派场景

主 Agent 通过 `Agent tool` 委派 subagent 做 worktree 开发时，prompt 必须含：

```
⚠️ 隔离约束（最高优先级）：
- 工作目录锁定: {REPO_ROOT}/{WORKTREE_BASE}/<name>/
- 所有 Read/Edit/Write/Bash 必须在此目录下
- 禁止读写主工作区 {REPO_ROOT}/ 下的非 {DOCS_ROOT}/ 文件
- 禁止在主工作区执行任何 git/构建命令
```

---

> 迁移到新项目：见同目录 `SETUP.md`。
