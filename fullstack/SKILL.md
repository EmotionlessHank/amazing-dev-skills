---
name: fullstack
description: 全栈（前端 + 后端 + 端到端联调）需求一处触发、自动 loop 编排。当用户说 "/fullstack"、"全栈开发"、"跨仓开发"、"前后端一起做"、"端到端联调方案"、"fullstack" 时触发。以 autopilot 为基座，新增单仓 autopilot 没有的能力：契约 SoT 优先门 · 双端 Batch 映射 · 整合双仓门禁 · e2e 测试驱动 gate（三态归因）· 双 track 学习回写。主仓（{MAIN_REPO}）= 总设计 + 契约 SoT；驱动双仓同会话开发。来源 harness：fullstack-orchestration。
---

# /fullstack — 全栈需求编排（契约优先 → 双仓并行 → e2e 测试驱动）

> **本项目定制版**（{MAIN_REPO} 主仓 + {BACKEND_REPO} 后端仓）。通用模板见 harness `fullstack-orchestration`。
> **一句话**：feat/autopilot 是「单仓视角」；`/fullstack` 把「前端 + 后端 + 端到端联调」三轨拧成**一处触发、自动 loop**，主仓作总设计、契约（`{CONTRACT_SOT_FILE}`）作双端唯一真相源。

---

## 何时用 /fullstack（vs /feat + /autopilot）

| 场景 | 用 |
|------|-----|
| 纯前端改动（UI / 端上逻辑 / 不碰契约） | `/feat` → `/autopilot`（单仓，本技能过重） |
| 纯后端改动（内部重构、不改契约） | 后端仓 `/feat` → 后端 dev loop |
| **改动跨前后端契约**（新增/改路由、payload、事件、错误码、safety 约定） | **`/fullstack`** |
| **新功能需要两端协同 + 端到端联调** | **`/fullstack`** |

判据：**只要这次改动会动到 `{CONTRACT_SOT_FILE}`（两端共享契约），就走 /fullstack**。

---

## 仓库地图与角色

| 仓 | 路径 | 角色 | 工具链/门禁 |
|---|---|---|---|
| 主仓 | `{MAIN_REPO}` | **总设计 + 契约 SoT**（`{CONTRACT_SOT_FILE}`）+ FE 实现 | {FE_GATE} |
| 后端仓 | `{BACKEND_REPO}` | 据契约实现服务端；自有 DD 生命周期 + 门禁 | {BE_GATE} + smoke |

> 契约冲突仲裁：`{CONTRACT_SOT_FILE}`（主仓）> 后端落地事实笔记。**改协议必先改主仓 `{CONTRACT_SOT_FILE}`**，后端据此实现。

---

## 五阶段（一处触发，自动 loop）

```
/fullstack [DD-NNN | 需求描述]

Phase 0  契约 SoT 优先 (contract-first)
Phase 1  三轨方案分解 (前端总设计驱动) + 确认门控
Phase 2  双仓并行开发 (autopilot ×2，契约优先解耦)
Phase 3  端到端联调 (测试驱动 gate · 三态归因)
Phase 4  三轨交付 + 跨仓对账 + 全栈开发总结
```

---

### Phase 0 — 契约 SoT 优先（contract-first）

**目的**：双端动手前，先在主仓把跨端契约定稿——这是「前端仓作总设计」的落地，FE/BE 都从契约 derive，杜绝两端各写各的。

1. **调研**（代码铁律，复用 /feat 调研阶段）：拉两仓最新；读服务端真实实现（路由 / safety / envelope）+ 客户端现状，**禁凭训练数据**。
2. **更新契约**：在 `{CONTRACT_SOT_FILE}` 写清本次跨端变更——新增/改的 **payload 字段 / 事件 / 工具 / 错误码 / safety 约定 / 限速**。每条标版本。
3. **产出契约变更点清单**：列「字段/事件 × 前端责任 × 后端责任 × e2e 断言点」，写入 hub `INDEX.md`。
4. **门禁 ⛔**：契约定稿（变更点清单完整、版本标注无歧义）才进 Phase 1。**契约未定不许分轨**。

> 红线：契约是双端唯一真相源。本阶段只改文档（`{CONTRACT_SOT_FILE}`），不写代码。

---

### Phase 1 — 三轨方案分解（前端总设计驱动）+ 确认门控

在主仓 `docs/designs/DD-NNN-<topic>/` 建**全栈 hub**，分解三轨方案。复用 /feat 的 DD 模板 + grill + plan review。

**产物结构**（主仓 hub + 同步后端仓）：
```
docs/designs/DD-NNN-<topic>/                  (主仓 = 总设计)
├── INDEX.md            全栈总索引（三轨 + 契约变更点 + 双端 Batch 映射 + e2e 场景 + 进度）
├── DD.md               FE track（前端方案，/feat 产出）
├── DD-backend.md       BE track（服务端方案：契约变更→文件/批次/后端单测）
├── DD-e2e.md           E2E track（契约一致性 + live 联调场景 + 测试驱动顺序）
├── HANDOFF-backend-<topic>.md   跨仓执行包/审计痕迹（A2A 范式，Phase 2 产出/回写）
└── reviews/ · 三轨各自三件套
        ↓ BE-DD 同步
{BACKEND_REPO}/docs/designs/DD-00X-<topic>/   (后端仓自有 DD 生命周期)
```

**双端 Batch 映射表**（hub INDEX.md 核心）：每个里程碑同步点标 `FE Batch i ↔ BE Batch x ↔ 契约片段 ↔ e2e 场景`，确保两端按契约片段对齐推进（不是各拆各的）。

**E2E track 测试驱动（关键）**：**先定 e2e 验收场景**（契约一致性双向断言 + live 联调路径），再让两端建到让它们绿。每场景标「自动（模拟器+服务端）vs 人工（真机/话术核对）」。

**并行 plan review**（复用 /feat review 阶段，按风险拉代理）：FE 方案 review + BE 方案 review + e2e 场景设计/critic，各自一份 `reviews/REV-plan-v1-*`。

**门禁 ⛔ 确认门控**（强制交互式 `AskUserQuestion`，同 /feat）：播报三轨摘要（契约变更点数 / 三轨 Batch 数 / e2e 场景数 / review 结论）+ 每个待决项一题 + 「是否开始」一题，附推荐。收到确认才进 Phase 2。

---

### Phase 2 — 双仓并行开发（autopilot ×2，契约优先解耦）

两端按 Phase 1 的 Batch 映射并行开发。**两侧先对 contract fixture / mock 编码 → 契约优先使两端解耦并行**（不必互等）。

- **FE 轨**：复用 `/worktree-dev` 搭隔离（`feat/<topic>` 分支 + worktree）→ `/autopilot` 按 `DD.md` §4 批次（每 batch ≤3 文件 + **{FE_GATE} 门禁**）。
- **BE 轨**：在 `{BACKEND_REPO}` 搭 worktree（`feat/<topic>` 从 main）→ **后端 dev loop**（同 autopilot 节奏，每 batch ≤3 文件 + **{BE_GATE} 门禁** + 新单测）。后端轨由**子代理 cd 进后端仓执行**，保 cwd 隔离纪律（主 loop 不漂出主仓工作区）。
- **整合双仓门禁**：里程碑同步点要求 **FE 门禁绿 ∧ BE 门禁绿** 才算该 milestone 过（防「前端绿 + 后端红」半成品）。
- **A2A handoff 文档**：即便同会话自动驱动，仍产出/回写 `HANDOFF-backend-<topic>.md`（问题证据 / 改动事实 / 验收清单 / 回执）作审计 + 可恢复痕迹。

**门禁 ⛔**：两侧各自单仓门禁绿 + 双端 Batch 映射全部完成 → 进 Phase 3。

---

### Phase 3 — 端到端联调（测试驱动 gate · 三态归因）

让 Phase 1 先定的 e2e 验收场景真正绿。复用 harness `live-acceptance-smoke`（探针→bug 类映射 + 自验优先）。

1. **部署 BE**：`{BACKEND_REPO}` `{DEPLOY_CMD}` → 跑后端 smoke（确定性门禁 + 真上游流）。
2. **跑 e2e**：
   - **契约一致性双向断言**：客户端出境 payload ↔ 服务端 schema 解析 ↔ 服务端响应 ↔ 客户端解码，逐字段对齐（防漂移）。
   - **live 联调**：客户端 `{LIVE_TEST_FLAG}` 真后端端到端测试覆盖 Phase 1 场景。
3. **三态归因**（e2e 红时）：定位是 **① FE bug / ② BE bug / ③ 契约漂移**（两端实现都对但契约文档没对齐）→ 回对应轨修 → 重跑 loop。契约漂移 → 回 Phase 0 改 `{CONTRACT_SOT_FILE}` 两端同步。
4. **门禁 ⛔**：e2e 场景全绿（能自动的自动判；真机/模型话术核对入 ACCEPTANCE B 段）才进 Phase 4。

---

### Phase 4 — 三轨交付 + 跨仓对账 + 全栈开发总结

1. **三轨三件套**：FE（CHANGES/TEST_PLAN/ACCEPTANCE）+ BE（同，落后端仓 DD）+ E2E（ACCEPTANCE：联调结果 + 真机/人工项）。
2. **跨仓对账**：`{CONTRACT_SOT_FILE}` ↔ 服务端实现 ↔ 客户端实现 三方逐字段核验无漂移；后端落地事实笔记追记。
3. **全栈开发总结**（autopilot 总结模板 + 扩展）：一句话 / 三轨交付物表 / 架构决策 / 铁律守护 / **双端改动摘要 + 契约对账结果 + e2e 场景结果** / review 处理 / **诚实披露**（前向兼容/范围收窄/延后/真机待验）/ 状态 + 下一步。
4. **ship 双仓**：各自 `/ship`（pre-push 门禁 + 多账号感知），**后端推送 + 部署后再跑线上 smoke**。
5. **双 track 学习回写**：`/learning-sync`（FE track + BE track，DD 标 Implemented 时）。
6. 刷索引：两仓 `bash bin/update-designs-index.sh` + 主仓进度脚本。

---

## 多代理编排（自由安排）

| 阶段 | 并行代理 |
|---|---|
| Phase 0 调研 | 主仓现状 + 后端真实实现 + 契约对账（并行 Explore） |
| Phase 1 review | FE 方案 critic/architect/security + BE 方案 critic + e2e 场景设计（并行） |
| Phase 2 开发 | FE autopilot（前端 worktree）+ BE dev loop（后端仓子代理）+ 各自 code review |
| Phase 3 联调 | 契约一致性断言 + live 场景 + 三态归因（并行验证代理） |

> 写与审分离：每轨开发后独立 subagent review，禁主对话自批（同 autopilot 红线）。

---

## 红线（继承 feat/autopilot/worktree-dev + 新增）

1. **契约 SoT 优先** — 跨端改动必先改主仓 `{CONTRACT_SOT_FILE}`，两端从契约 derive；契约未定不分轨。
2. **代码为铁律** — 两仓结论必有真实代码/数据支撑，禁训练数据假设。
3. **整合双仓门禁** — 里程碑要 FE 绿 ∧ BE 绿；禁「一端绿就过」。
4. **e2e 测试驱动** — 验收场景先定、两端建到让它们绿；契约漂移单独归因。
5. **cwd 隔离纪律** — FE 在前端 worktree、BE 由子代理 cd 进后端仓；主 loop 不漂出主仓工作区（只读例外：`docs/`）。
6. **确认门控前禁编码** — Phase 1 确认门控（交互式）收到确认才进 Phase 2。
7. **项目铁律不可绕过** — 引用本项目核心红线（如安全/隐私约定），两端双层防御。
8. **绝不自动 merge/push** — 交付后 `/ship` 各仓由门禁守绿；多账号切换 + 切回。
9. **A2A handoff 留痕** — 跨仓改动产出 `HANDOFF-*.md`（审计 + 可恢复）。

---

## 异常处理

| 场景 | 处理 |
|------|------|
| 改动不碰契约 | 退回 `/feat`+`/autopilot`（单仓），本技能过重 |
| 后端 `pull --ff-only` 失败 | 不 reset/merge，告诉用户去后端仓处理 |
| 契约漂移（e2e 红但两端实现都"对"） | 回 Phase 0 改 `{CONTRACT_SOT_FILE}`，两端同步，重跑 e2e |
| 一端门禁红 | 该 milestone 不过，回对应轨修，不进 Phase 3 |
| 需写服务器/部署线上 | 部署走 `{DEPLOY_CMD}`（后端仓既有脚本）；写库/改线上配置停手交用户 |
| 真机/话术核对 | 入 ACCEPTANCE B 段，不外包能自动化的 |

---

> 来源 harness：`fullstack-orchestration`（横切 prd-dd-lifecycle + live-acceptance-smoke + infra-config-sot；新增 contract-first / dual-batch-mapping / e2e-tdd / cross-repo-coordination）。迁移/再同步见同名 harness 的 SETUP.md。
