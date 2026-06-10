# autopilot — 迁移到新项目（SETUP）

把 `SKILL.md` 复制进目标项目的 skills 目录后，按下表把 `{占位符}` 替换为本项目实际值，再跑验证。

## 占位符替换清单

| 占位符 | 含义 | 示例（oddfi-frontend） |
|--------|------|----------------------|
| `{DOCS_ROOT}` | 需求/方案文档根目录 | `.progress` |
| `{type}` | 需求类型子目录集合 | `designs` / `enh` / `bug` / `ud` / `ad` |
| `{ID}` | 需求编号格式 | `DD-NNN` / `ENH-NNN` / `BUG-NNN` |
| `{RULES_DIR}` | 项目规则目录 | `.claude/rules/` |
| `{LESSONS}` | 经验教训文档（可选，无则删 §0.3） | `docs/LESSONS.md` |
| `{MAX_FILES_PER_BATCH}` | 单 batch 文件上限 | `3` |
| `{TYPECHECK}` | 类型检查命令 | `pnpm type-check` |
| `{LINT}` | lint 命令 | `pnpm lint` |
| `{TEST}` | 测试命令（支持传文件/目录跑子集） | `pnpm test` |
| `{BUILD}` | 构建命令 | `pnpm build` |
| `{GEN_ASSETS}` | 资产索引刷新命令（可选，无则删相关行） | `pnpm gen-assets` |
| `{QUALITY_SCANNER}` | 高频陷阱快扫代理（无则 2 代理用别的，或退化为 1） | `quality-scanner` |
| `{DESIGN_IMPL_SKILL}` | UI 像素还原流程（无 UI 任务则删 Step 1.5） | `/figma-impl` |
| `{PROJECT_CONVENTIONS}` | 注入 review 代理的关键约定 | 运行时输出英语 / decimal.ts / Design Token / testing.md |
| `{EXAMPLE_REQUIREMENT_FOLDER}` | 一个完整需求子文件夹样板路径 | `.progress/designs/DD-132-invest-page-redesign/` |
| `{SUBAGENT_TRANSCRIPT}` | subagent 落盘 transcript 路径（报告被吞时取回；无此机制则删该兜底句） | `<session>/subagents/agent-<id>.jsonl` |

> `{type}` 示例里的 `ud`/`ad` 是 oddfi 自有类型，新项目按需删减，保留通用的 designs/enh/bug 即可。

## 依赖的 review 代理

Phase 2 用到的 subagent 类型（项目需提供，或换等价物）：
- `code-reviewer`（必需）— 深度代码审查
- `{QUALITY_SCANNER}`（默认 2 代理时用）— 高频陷阱快扫
- `security-reviewer` / `test-engineer` / `performance-engineer`（3 代理时按域选）

**最低要求**：项目需有任意 1 个可并行 spawn、能把报告写到指定绝对路径的 review subagent。完全没有 → Phase 2 退化为主流程自查 + 交用户把关（牺牲「不能自批」原则，需在报告里声明）。

> 注：feat 用 plan-review 视角 agent（critic/architect/design-distiller），autopilot 用 code-review 视角 agent（code-reviewer/quality-scanner），**二者不复用**。

## 可选模块（按项目裁剪）

- 无 UI/设计稿流程 → 删 §0.4 UI 判定 + §1.2 Step 1.5
- 无经验教训文档 → 删 §0.3
- 无资产索引脚本 → 删 §1.3 的 `{GEN_ASSETS}` 行
- 不走 worktree → §4.2 收尾简化为分支内提交，删「同步文档回主工作区」
- **无测试基建**（早期原型/纯静态站）→ §1.2 Step 2 退化为仅 `{TYPECHECK}`，§1.3 删 `{TEST}`，并在 ACCEPTANCE.md 声明「本项目无自动化测试，全部走人工验收」
- 无输出 hook 吞报告问题 → 删 §2.2 第 6 点的 `{SUBAGENT_TRANSCRIPT}` 取回兜底句

## 验证

1. 占位符全部替换（`grep -n "{.*}" SKILL.md` 应只剩示意性的 `{ID}`/`{platform}` 等动态量，无未替换的配置占位）
2. 拿一个已有需求跑一遍：确认 Phase 1 每 batch 跑了相关测试、Phase 2 真的 spawn 了 1-3 个 subagent 并各自落了 REV 文件、Phase 4 产出三件套且在对话里抛了验收清单
3. 确认收尾**没有自动 push/merge 远端**
