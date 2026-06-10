# feat — 迁移到新项目（SETUP）

把 `SKILL.md` 复制进目标项目的 skills 目录后，按下表替换 `{占位符}`，再跑验证。
与 `autopilot` 配套使用（feat 出方案 → autopilot 开发），两者占位符尽量保持一致。

## 占位符替换清单

| 占位符 | 含义 | 示例（oddfi-frontend） |
|--------|------|----------------------|
| `{DOCS_ROOT}` | 需求/方案文档根目录 | `.progress` |
| `{type}` / `{ID}` | 需求类型 / 编号格式 | `designs`·`bug` / `DD-NNN`·`BUG-NNN` |
| `{LESSONS}` | 经验教训文档（可选，无则删 §0.3） | `docs/LESSONS.md` |
| `{WORKTREE_SKILL}` | worktree 隔离开发流程（无则改成「建功能分支」） | `/worktree-dev` |
| `{SMALL_FILE_THRESHOLD}` | 小功能文件数阈值（可跳 DD） | `2` |
| `{MAX_FILES_PER_BATCH}` | 单 batch 文件上限 | `3` |
| `{DESIGN_IMPL_SKILL}` | UI 像素还原流程（无 UI 则删 §2.5 + 相关行） | `/figma-impl` |
| `{REPO_MAP}` | 跨仓库地图（路径 + 各自开发分支） | 见下方 |
| `{REPO_PATH}` | {REPO_MAP} 中某仓库本地路径（命令模板变量，按表逐仓实例化，不在 SKILL 逐项替换） | `~/work/oddfi-backend` |
| `{DEV_BRANCH}` | {REPO_MAP} 中该仓库的开发活跃分支（命令模板变量） | `dev`（后端）/ `main`（合约） |
| `{SSH_INVENTORY}` | SSH 服务器清单文件（含别名→用途） | `~/.ssh/SERVERS.md` |
| `{SERVER_ALIAS}` | 服务器别名（多台见 {SSH_INVENTORY}） | `oddfi-backend` / `oddfi-dev` |

> `{SMALL_FILE_THRESHOLD}`（跳 DD 门槛）与 `{MAX_FILES_PER_BATCH}`（批次切分上限）语义不同、可不等值，别误填成同值。

## {REPO_MAP} — 跨仓库地图（关键定制点）

各仓库**开发分支可能不同**，必须在此明确，§2.1 据此拉取。oddfi 实例：

| 仓库 | 路径 | 开发分支 | API 全景入口 |
|------|------|---------|-------------|
| 后端 | `~/work/oddfi-backend` | **dev**（后端在 dev 迭代） | 子服务 handler/model |
| 合约 | `~/work/oddfi-ODD` | **main** | `docs/development/api.md` |
| 前端（本仓） | `~/work/oddfi-frontend` | **main** | — |

空白模板（换项目时直接填）：

| 仓库 | 路径 | 开发分支 | API 全景入口 |
|------|------|---------|-------------|
| `{...}` | `{...}` | `{...}` | `{...}` |

> 换项目时：列出本项目所有相关仓库 + 各自「开发活跃分支」（这是最易错的定制点——拉错分支 = 调研到旧代码）。
> **不确定某仓库的开发活跃分支** → 跑 `git -C <path> branch -r --sort=-committerdate | head -3` 看最近活跃分支，或问该仓库 owner。

## 可选模块（按项目裁剪）

- 无其它仓库（纯单仓项目）→ 删 §2.1/§2.2 跨仓库部分，保留「读本仓真实代码」
- 无服务器/无需运行时核验 → 删 §2.3
- 无 UI/设计稿 → 删 §0 UI 判定 + §2.5 + `{DESIGN_IMPL_SKILL}` 引用
- 无经验教训文档 → 删 §0.3

## 依赖的 plan-review 代理

阶段 4 用到的 subagent（项目需提供或换等价物）：
- `critic`（中/大需求）— 方案漏洞/边界/可行性
- `design-distiller`（中需求可选）— 磨平方案软边界
- `architect`（大需求）— 架构/可逆性
- `security-reviewer` / `document-specialist`（大需求按域）

无对应 agent → 降为 1 个通用 review agent，或主对话先自查再请用户把关。

## 验证

0. 占位符残留自检：`grep -oE '\{[A-Za-z_|]+\}' SKILL.md | sort -u`，确认只剩**运行时动态量**白名单（`{ID}` `{type}` `{platform}` `{agent}` `{N}` `{K}` `{M}` `{REPO_PATH}` `{DEV_BRANCH}` `{DD|ENH|BUG}`），无未替换的**配置占位**
1. 占位符全部替换，`{REPO_MAP}` 已填本项目真实仓库 + 开发分支
2. 拿一个涉及跨仓库的需求跑一遍：确认 §2.1 真的切对分支拉了最新、§2 的 DD §Research 里有「真实代码路径行号 / commit / curl HTTP 码」证据、阶段 4 真的 spawn 了对应数量 plan-review 代理
3. 确认服务器操作**全程只读**、确认门控前**没有编码**
