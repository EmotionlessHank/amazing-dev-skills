# 装到新项目（Fullstack-Orchestration 迁移指南）

> 前置：本实践横切 [[prd-dd-lifecycle]]（需求文件夹生命周期 + 确认门控 + 三件套）、[[live-acceptance-smoke]]（Phase 3 真环境冒烟）、[[infra-config-sot]]（部署配置单一真相）。**主仓应先装好 prd-dd-lifecycle**（`/feat` + `docs/designs/` + 索引脚本），本实践在其之上叠加跨仓三轨编排。

## 占位符（先填好，下文 templates 全用这套）

| 占位符 | 含义 | 示例 |
|---|---|---|
| `{MAIN_REPO}` | 主仓（总设计 + 契约 SoT + 客户端实现） | `~/work/myapp-ios` |
| `{BACKEND_REPO}` | 后端仓（据契约实现服务端，自有 DD 生命周期 + 门禁） | `~/work/myapp-backend` |
| `{CONTRACT_SOT_FILE}` | 跨端契约的单一真相源文件（主仓内） | `docs/API_CONTRACT.md` |
| `{FE_GATE}` | 前端单仓门禁命令 | `xcodegen → swiftlint --strict → xcodebuild test` |
| `{BE_GATE}` | 后端单仓门禁命令 | `npm run typecheck && npm run build && npm test` |
| `{DEPLOY_CMD}` | 后端部署命令（Phase 3 前置） | `bash infra/deploy.sh` |
| `{LIVE_TEST_FLAG}` | 触发客户端真后端 e2e 的开关 | `TEST_RUNNER_RELAY_LIVE_TEST=1` |

## 步骤

1. **建 skill 文件**：复制 `templates/fullstack-skill-template.md` → `{MAIN_REPO}/.claude/skills/fullstack/SKILL.md`，把全部占位符替换成本项目值。skill 的触发关键词、五阶段、红线照搬；仅替换仓库地图与门禁命令。

2. **定契约 SoT 文件位置**：确认 `{CONTRACT_SOT_FILE}` 在主仓存在且是**双端共享的接口契约**（payload 字段 / 事件 / 错误码 / safety 约定 / 限速）。后端仓**不重定义契约**，只留一份「落地事实」笔记（如 `RELAY_INTEGRATION.md`）追记实现细节。在主仓文档地图里把它标为「改协议先改这里，后端据此实现」。

3. **主仓 hub DD 结构**：主仓的 `docs/designs/` 已由 prd-dd-lifecycle 提供。本实践扩展为「全栈 hub」——一个 DD 文件夹下分三轨：
   - `INDEX.md`（用 `templates/fullstack-hub-INDEX-template.md`：三轨 + 契约变更点 + 双端 Batch 映射 + e2e 场景 + 进度）
   - `DD.md`（FE track，沿用 /feat 的 DD 模板）
   - `DD-backend.md`（BE track，契约变更 → 文件 / 批次 / 后端单测）
   - `DD-e2e.md`（E2E track，用 `templates/e2e-track-DD-template.md`）

4. **后端仓 DD 生命周期对接**：`{BACKEND_REPO}` 应**自有一套 prd-dd-lifecycle**（独立的 `docs/designs/` + 自己的 `/feat` + 门禁）。主仓 hub 的 BE track 与后端仓的 DD 双向引用：主仓 `DD-backend.md` 写契约责任与批次，后端仓 `docs/designs/DD-NNN/` 落具体实现与三件套。后端轨**由子代理 cd 进后端仓执行**，保 cwd 隔离（主 loop 不漂出主仓工作区）。

5. **整合双仓门禁**：定义里程碑同步点的过关条件 = `{FE_GATE}` 绿 ∧ `{BE_GATE}` 绿。两端各自的单仓门禁照旧（前端 pre-push / 后端 CI），本实践只在 hub Batch 映射表里把同步点标成「需双绿」，并要求 Phase 2 milestone 不满足双绿就不进 Phase 3。

6. **贴 CLAUDE.md 片段**：把 `templates/claude-md-snippet.md` 内容贴进 `{MAIN_REPO}/CLAUDE.md` 工作流小节，替换占位符。注册 `/fullstack` 的触发判据（动到 `{CONTRACT_SOT_FILE}` 就走）+ 跨仓角色 + 红线引用。

7. **验证**（见下）。

## 验证

- **契约门真生效**：给一个跨端需求，确认 AI 在 Phase 0 只改 `{CONTRACT_SOT_FILE}`（不写任何代码），且产出「字段 × FE 责任 × BE 责任 × e2e 断言点」变更点清单后才进 Phase 1。
- **双端映射成表**：hub `INDEX.md` 出现 `FE Batch i ↔ BE Batch x ↔ 契约片段 ↔ e2e 场景` 的映射表，而非两端各拆各的。
- **整合门禁挡半成品**：人为让一端门禁红，确认该 milestone 不过、不进 Phase 3。
- **e2e 测试驱动**：确认 e2e 验收场景在 Phase 1 就定下（不是 Phase 3 临时补），且 Phase 3 红时 AI 显式做三态归因（FE / BE / 契约漂移）而非笼统「联调失败」。
- **cwd 隔离**：后端轨由子代理在 `{BACKEND_REPO}` 内执行，主 loop 全程不写主仓工作区之外的文件（只读 `docs/` 例外）。

## 设计原则（为什么这么做）

- **为什么契约优先**：跨端最贵的事故是「两端各自实现都对、但对不上」。把契约定稿提前到动手之前，就把这个事故从联调期（已写大量代码、改起来贵）提前成立项期（只改一份文档）。契约作双端唯一真相源后，两端可对 fixture 解耦并行，不必互等。
- **为什么测试驱动 e2e**：端到端是两端实现 × 契约三者的交点，事后人工点一遍既不可复现也无法归因。先定验收场景 → 两端建到让它们绿，使「联调通过」有确定性定义；红时三态归因把黑盒失败拆成可定位的责任轨。
- **为什么主仓作总设计**：跨仓需求需要一个「总设计 + 契约真相源」的锚点，否则两个仓平级各自为政必然漂移。让客户端主仓承担总设计（它最接近产品需求与用户场景），后端仓据契约实现——主从清晰，契约冲突有唯一仲裁方。
