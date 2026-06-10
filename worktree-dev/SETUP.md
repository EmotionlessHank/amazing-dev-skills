# worktree-dev — 迁移到新项目（SETUP）

把 `SKILL.md` 复制进目标项目 skills 目录后，按下表替换 `{占位符}`，再跑验证。
与 `feat`/`autopilot` 配套（worktree-dev 搭隔离环境 → feat 出方案 → autopilot 开发），占位符尽量与它们一致。

## 占位符替换清单

| 占位符 | 含义 | 示例（oddfi-frontend） |
|--------|------|----------------------|
| `{REPO_ROOT}` | 主工作区绝对路径 | `/Users/hang/work/oddfi-frontend` |
| `{MAIN_BRANCH}` | 主分支 | `main` |
| `{WORKTREE_BASE}` | worktree 统一存放目录（相对主工作区） | `.claude/worktrees` |
| `{WT_HELPER}` | 一步建 worktree + symlink 的封装脚本（可选，无则删该提示） | `bin/wt-add.sh`（`pnpm wt <name> <branch>`） |
| `{ENV_FILES}` | 需 symlink 的 env/个人配置文件清单（见下方） | 见下方 |
| `{ENV_FILE}` | `{ENV_FILES}` 中单个文件（§1.2 symlink 命令模板变量，按清单逐个实例化） | `.env.local` |
| `{INSTALL}` | 依赖安装命令 | `pnpm install` |
| `{TYPECHECK}` / `{LINT}` / `{TEST}` / `{BUILD}` | 验证命令 | `pnpm type-check` / `pnpm lint` / `pnpm test` / `pnpm build` |
| `{DOCS_ROOT}` | 需求/方案文档根（只读例外，与 feat/autopilot 同名） | `.progress` |
| `{type}` / `{ID}` | 需求类型 / 编号 | `designs` / `DD-NNN` |
| `{RULES}` | 项目规则只读路径 | `CLAUDE.md` + `.claude/rules/` |
| `{MAX_FILES_PER_BATCH}` | 单批文件上限 | `3` |
| `{COMMIT_CONVENTION}` | commit 规范 | 简体中文 + 禁止 Co-Authored-By |
| `{EDIT_READ_PREREQ_HOOK}` | "先 Read 再 Edit" 协同 hook（可选） | `.claude/hooks/edit-read-prereq.sh` |

## {ENV_FILES} — 需 symlink 的文件清单（关键定制点）

列出本项目所有「主工作区有、但 gitignore 不入库、worktree 必须有」的文件，及各自缺失后果。oddfi 实例：

| 文件 | 作用 | 缺失后果 |
|------|------|---------|
| `.env.local` | 默认环境变量 | Route Handler 代理 500 |
| `.env.dev.local` | dev 环境（独立端口） | 静默回落默认 env |
| `.env.testnet.local` | testnet 环境 | **静默走 mainnet**，连错链 |
| `.claude/settings.local.json` | 个人 Bash/MCP 权限白名单 | 每次操作被重新询问权限 |
| `.claude/skills/` | 工作流 skill 资源（symlink 共享不复制） | 个人 skill 不可用 |

> 换项目：把你项目里所有 gitignore 但 worktree 必需的文件列进来。symlink 不是 cp（cp 是静态快照，主工作区改了 worktree 感知不到）。
> ⚠️ symlink 相对路径深度 = `{WORKTREE_BASE}` 嵌套层数 + 文件层数，逐个核对 `ln -sf` 的 `../` 数量。

## 验证

0. 占位符残留自检：`grep -oE '\{[A-Za-z_]+\}' SKILL.md | sort -u`，确认只剩运行时动态量（`{ID}` `{type}` `<name>` 等示意量），无未替换的配置占位
1. 跑一遍：建一个 worktree → 确认 `{ENV_FILES}` 全部 symlink 成功且指向有效文件、`{INSTALL}` 成功、cwd 锁定生效（尝试读主工作区非 `{DOCS_ROOT}` 文件应被自觉拒绝）
2. 确认收尾**没有自动 push 远端**（合并/推送是用户权责，除非项目明确约定 AI 可收尾合并到本地主分支）
