---
name: autopilot
description: 方案确认后的全自动开发流水线。当用户确认开发方案后（"确认"/"OK"/"开始"），或说 "/autopilot"、"自动开发"、"跑流水线"、"autopilot" 时触发。自动执行：批次开发（每 batch 合适测试验证）→ 按需 1-3 代理并行 Review → 主流程自动处理 Review 意见 → 过程/验收文档归档需求子文件夹 → 通知用户验收。在识别到「方案确认可以开发」的模式时应主动调用。
version: 2.0.0
---

# /autopilot — 全自动开发流水线

> **多项目通用版。** `{占位符}` 为各项目定制点，迁移到新项目前先按 `SETUP.md` 把占位符替换为本项目实际值。
> feat 出方案 → autopilot 落地：**批次开发（每 batch 合适测试）→ 按需 1-3 代理并行 Review → 主流程自动处理意见 → 文档归档 + 通知验收**。

模拟真实团队：产品确认 PRD → 工程师按批次实现并自测 → 1-3 名高级工程师并行 Review → 工程师处理意见 → 整理交付文档 → 交人类验收。

---

## 核心原则

1. **方案已确认才启动** — 本技能不负责方案设计，只执行已确认的方案（DD/ENH/BUG）
2. **全程无需人工介入** — 从第一行代码到 Review 意见处理完毕，中间不暂停
3. **每 batch 合适测试验证** — 每个 batch 跑该 batch 相关测试（co-location 单测 + 类型检查），不是只跑类型检查；全部 batch 结束跑全量门禁
4. **Review 用真·subagent，按需 1-3 个并行** — 不是主对话自切「Review 模式」自审（写代码上下文不能自批）；规模按改动量/风险定 1-3 个
5. **主流程自动处理 Review 意见** — Critical/Major 自动修，Minor/低 ROI 自动转延后清单
6. **过程 + 验收文档归档需求子文件夹** — 所有产物落 `{DOCS_ROOT}/{type}/{ID}/`（见 §文档归档规约）
7. **收尾通知用户验收** — 产出验收清单并在对话显式抛给用户人工验收
8. **绝不自动 Push/Merge 远端** — 止于本地主分支 squash commit，由用户决定推送
9. **严格遵循项目规范** — 项目 `{RULES_DIR}` / 约定（Batch ≤N 文件、经验教训前置、worktree 默认、Review 分级修复）全部生效

---

## 文档归档规约（强制）

所有 autopilot 产物归入**需求子文件夹** `{DOCS_ROOT}/{type}/{ID}/`，**禁止平铺**。

```
{DOCS_ROOT}/{designs|enh|bug|...}/{ID}/
├── INDEX.md                  目录索引（产物清单 + 阶段时间线 + 关键 commit）
├── {DD|ENH|BUG}.md           方案文档（autopilot 启动前已存在）
├── reviews/                  审查报告（plan-review 来自 feat / code-review 来自本技能）
│   ├── REV-plan-v1-A-{agent}.md   （feat 阶段方案审查）
│   ├── REV-code-v1-A-{agent}.md   （autopilot 代码审查）
│   └── REV-code-v1-B-{agent}.md   （v2 = 二次审查，不覆盖 v1）
├── CHANGES.md                Phase 4：commit 清单 + 新增/修改/删除文件
├── TEST_PLAN.md              Phase 4：AI 已自动测试项（类型/单测/全量/构建/review）
├── ACCEPTANCE.md             Phase 4：必须人工验收清单（浏览器/联调/边界）
└── enh-todo-additions.md     Phase 3：B 类延迟项
```

> 多平台任务（如 PC + 移动端）可拆 `TEST_PLAN-{platform}.md` / `ACCEPTANCE-{platform}.md`。
> 历史已平铺的旧需求保持原样；新任务一律走子文件夹。
> ⚠️ 若 `{DOCS_ROOT}` 被 gitignore，worktree 收尾必须 `cp` 回主工作区（见 §收尾）。
> 参考样板：`{EXAMPLE_REQUIREMENT_FOLDER}`。

---

## Phase 0: 启动检查

### 0.1 方案文档 + 需求子文件夹定位

```
检查顺序：
1. 对话中明确提到的 {ID 编号} 路径
2. 当前分支名推断（feat/xxx → designs/{ID}/，fix/xxx → bug/{ID}/）
3. 最近修改的方案文件
```

**交接优先级**：若由 feat 交接而来（上文已有确认门控播报的 DD 路径）→ **直接复用该路径**，跳过下方三级推断；仅独立 `/autopilot` 入口才走推断。

锁定需求子文件夹 `{DOCS_ROOT}/{type}/{ID}/`。读方案文档，提取：实施计划（Batch/Phase 列表）、组件拆分（改哪些文件）、关键技术决策。

**无实施计划 → BLOCK**：方案必须含可执行实施计划，否则提示用户补充。

### 0.2 分支检查

| 当前分支 | 行为 |
|---------|------|
| 主分支（main/master） | **BLOCK** — 提示创建功能分支或走 worktree |
| `feat/*`/`fix/*`/`refactor/*`/`chore/*` | 通过，记录分支名 + worktree 绝对路径 |

### 0.3 经验教训关联（若项目有 `{LESSONS}`）

读 `{LESSONS}`，按方案技术领域匹配相关章节，输出关键陷阱提醒，**不等待确认直接继续**。

### 0.4 工作区状态 + 任务类型

`git status --porcelain` 检查未提交改动。识别任务类型：含设计稿节点 ID / "设计稿/还原" 关键词 / JSX 渲染 → **UI 任务**（Phase 1 增设计稿驱动实现 + 视觉验收，见 `{DESIGN_IMPL_SKILL}`）；否则标准任务。

### 0.5 启动播报

```
🚀 Autopilot 流水线启动
方案: {ID 标题} | 分支: {branch} | 类型: {UI/标准}
需求文件夹: {DOCS_ROOT}/{type}/{ID}/
Pipeline:
  Phase 1: 批次开发 → {N} Batch（每 batch 合适测试验证）
  Phase 2: 按需 {1-3} 代理并行 Review → reviews/REV-v1-*.md
  Phase 3: 主流程自动处理意见（A 类修 / B 类转 enh-todo-additions）
  Phase 4: 归档 CHANGES/TEST_PLAN/ACCEPTANCE/INDEX → 通知验收
```

---

## Phase 1: 批次开发

### 1.1 Batch 拆分

从实施计划提取 Batch，每个 Batch：**≤ {MAX_FILES_PER_BATCH} 文件**、逻辑完整最小单元（可独立通过类型检查）、有依赖严格按序。粒度过大自动细分。

### 1.2 单 Batch 执行

**Step 1 编码**：按方案设计编码，遵守项目代码规范，参考经验教训避坑。
**Step 1.5 设计稿驱动（仅 UI 任务）**：用 `{DESIGN_IMPL_SKILL}` 流程取设计数据 → 按精确值编码 → 逐组件视觉验收；委派 subagent 必须传设计节点 ID。

**Step 2 合适测试验证（每 batch 必做）** — 不是只跑类型检查，按本 batch 改动性质跑相应测试：

```bash
{TYPECHECK}                          # 必跑
{TEST} {本 batch 涉及的测试文件/目录}   # 跑改动相关 co-location 单测
```

| 本 batch 改动 | 跑什么 |
|--------------|--------|
| 纯函数 / 工具库 | 对应 co-location 单测（P0 必含） |
| 全局状态 / store | 对应 store 测试 |
| hook 逻辑 | 对应 hook 测试（hooks 改动应含测试） |
| 组件渲染/交互 | 组件目录内组件测试 |
| 类型契约 / API 层 | 受影响的集成测试 |
| 纯样式 / 文案 | 跳过单测，标 `visual-fix`/`copy-fix`，类型检查即可 |

无对应测试但改了核心逻辑 → 先补失败测试（红）再修（绿），或显式标「pre-existing gap，登记 enh-todo」。类型/测试失败 → **立即修**，不跳下一 Batch。

**Step 3 提交**：`git commit`，message 用项目语言规范，禁止 AI 署名。
**Step 4 Batch 播报**：列改动文件 + 验证结果 + commit。

### 1.3 全部 Batch 完成后（全量门禁）

```bash
{TYPECHECK} && {LINT} && {TEST} && {BUILD}
```

- 新建过受 `{GEN_ASSETS}` 索引的文件 → 先跑 `{GEN_ASSETS}` 刷新（否则 pre-commit hook 拦截）
- 任一失败 → 修根因，禁止 `--no-verify`/`SKIP_*` 绕过；修复作为**独立 commit 追加**（不 amend 历史 batch），squash 时统一压平
- 删除过文件 → grep 确认无残留 import + 索引同步

---

## Phase 2: 按需 1-3 代理并行 Review

**核心：用真·subagent 审查，不是主对话自切「Review 模式」自审**（写代码上下文不能自批）。review 代理是独立 subagent，并行跑，各自落一份 REV 报告。

### 2.1 按需定代理数（1-3，规模/风险驱动）

| 代理数 | 适用 | 组合 |
|-------|------|------|
| **1** | 小改动（≤~5 文件、低风险、机械式如契约迁移/文案/配置） | `code-reviewer` |
| **2**（默认） | 标准功能/多文件/有业务逻辑 | `code-reviewer`（深审）+ `{QUALITY_SCANNER}`（高频陷阱快扫；无此 agent 时第二个用 `test-engineer` 或通用 reviewer 替代） |
| **3** | 大型/安全敏感/资金·认证·支付/跨多模块 | 上述 + 第三个按域：`security-reviewer` 或 `test-engineer` 或 `performance-engineer` |

拿不准选 2。

### 2.2 并行委派（Agent tool，一条消息多个 Agent 调用）

每个 review 代理 prompt **必须显式注入**（subagent 不继承主对话上下文）：

1. **工作目录**（worktree 绝对路径）+ 待审 commit 范围
2. **任务背景**：方案文档路径 + 需求摘要
3. **必读上下文**：项目关键约定（`{PROJECT_CONVENTIONS}`：如运行时输出语言、精度计算、设计 Token、测试规范）；UI 任务额外传设计节点 ID
4. **审查重点**：按改动域列，最高风险排前
5. **输出落位**：完整 REV 报告写到子文件夹绝对路径 `{DOCS_ROOT}/{type}/{ID}/reviews/REV-code-v1-{A|B|C}-{agent}.md`，按项目 review 规范（🚨Critical/⚠️Major/ℹ️Minor + 每问题 `[级别/触发场景/影响范围/修复ROI]` 4 栏 + 测试覆盖审查节 + Deletion Test 节）
6. **最终消息只回**：N Crit/M Major/K Minor + 总评 + 报告绝对路径（**不贴全文**，防上下文截断/输出 hook 丢报告；若报告被吞，按 `{SUBAGENT_TRANSCRIPT}` 从 subagent 落盘 transcript 提取最长 assistant text 块取回）

> 多 agent review **必须各自一份文件**（REV-code-v1-A/-B/-C），禁止合并。
> **版本约定**：首次 `v1`；代码经修改后需二次审查时由人类指令触发，新建 `v2` 文件不覆盖 v1。

### 2.3 汇总结论

收齐后主流程读各 REV，合并去重，综合判定 🟢 Ship It / 🟡 Needs Changes / 🔴 Major Rework + Crit/Major/Minor 计数。

---

## Phase 3: 主流程自动处理 Review 意见（分级修复）

### 3.1 Triage

| 类别 | 覆盖 | 处理 |
|------|------|------|
| **A 类（立即修）** | Critical、Major Bug、阻断逻辑、严重性能、违反架构、测试缺失（核心逻辑无对应测试） | 立即改代码 |
| **B 类（延后）** | Minor、重构建议、低 ROI、风险过高的非紧急、pre-existing 缺口 | 转子文件夹 `enh-todo-additions.md` |

> **降级判断**：某 Major 若 pre-existing 且本次行为保持、风险低，可降级 B 类登记，但须在 REV 回写 + 最终报告**显式说明降级理由**。

### 3.2 A 类修复

- 直接改；> `{MAX_FILES_PER_BATCH}` 文件拆 sub-batch，每 sub-batch 跑相关测试 + 类型检查；统一提交（与开发 commit 分开便于追溯）
- **串行执行**：A 类修复由主流程串行做，不并行 spawn 修复 agent（避免多 agent 改同一文件冲突）
- **升级出口**：某 A 类根因超出本方案范围（如 pre-existing 架构缺陷）/ 同一错误修 N 次未果 → 不强行改、不静默降级，暂停呈报用户（连 §异常表）。「降级 B」只适用 pre-existing + 低风险，**不是 Critical 的逃生通道**

### 3.3 B 类转移

写 `{DOCS_ROOT}/{type}/{ID}/enh-todo-additions.md`，格式含触发场景 + 降级理由便于人类决策。

### 3.4 REV 回写

每份 REV 底部追加「Dev Agent 修复记录」：A 类勾 `[x]` + 改法；降级 B 类标 `⏭️` + 理由；修复 commit + 复测结论。

### 3.5 修复后验证

`{TYPECHECK} && {LINT} && {TEST}` 确认无新增失败。

---

## Phase 4: 文档归档 + 通知用户验收

### 4.1 产出交付文档（写需求子文件夹）

| 文件 | 内容 |
|------|------|
| `CHANGES.md` | commit 清单 + 新增/修改/删除文件分类 + 「未改动（确认）」 |
| `TEST_PLAN.md` | AI 已自动测试项（类型/lint/全量 test/构建/每 batch 单测/review）+ 重点契约断言覆盖表 |
| `ACCEPTANCE.md` | 必须人工验收项（浏览器交互、联调、跨端、未自动验收声明）；多端拆 `-{platform}` |
| `INDEX.md` | 产物清单 + 时间线 + 关键 commit + review 结论 |

### 4.2 收尾（worktree 默认路径）

1. **同步文档回主工作区**：若 `{DOCS_ROOT}` gitignore → `cp -r` 子文件夹回主工作区（先 diff 避免覆盖更权威版）
2. **Squash 合本地主分支**：`git merge --squash {分支}` → commit（pre-commit hook 再跑门禁）。**不 push**
3. **清理 worktree**：`git worktree remove` + `git branch -D`
4. **跟进项**：用户随口提的跨团队依赖/发版协调等记入项目提醒文件

### 4.3 最终报告 + 通知验收

输出总结（开发/review/验证统计 + 文档路径），并**从 ACCEPTANCE.md 摘 3-6 条最关键验收项直接列在对话里**，附完整清单路径。UI 改动必附「未做浏览器自动验收，请人工核对 hover/入场/边界态」提醒。

后续 push/merge 远端由用户决定。

---

## 异常处理

| 场景 | 处理 |
|------|------|
| 方案无实施计划 | BLOCK — 提示补充 |
| 在主分支 | BLOCK — 提示功能分支/worktree |
| 类型检查同一错误修 N 次仍失败 | 暂停，报告详情，请求用户介入 |
| 测试失败但非本次引入 | 标「遗留失败」，继续 |
| Review 合并判定 🔴 Major Rework | 暂停，呈报用户，建议重设计 |
| 单 Batch 需超 `{MAX_FILES_PER_BATCH}` 文件 | 自动拆 sub-batch |
| A 类修复引入新问题 | 回滚该修复，标需用户介入，继续其他 A 类 |
| 中途用户发消息 / 喊停整条流水线 | 暂停，保留已 commit 分支不删 worktree，呈报当前进度，交用户决定续/弃 |

---

## 安全红线

1. **绝不自动 push / merge 远端** — 止于本地主分支 squash commit
2. **Review 必须独立 subagent** — 禁主对话自批
3. **绝不改业务代码 + 需求文档以外的非代码文件**（如全局配置、密钥、env）
4. **绝不跳过门禁失败** — 类型/lint/test/构建必须通过，禁绕过，修根因
5. **Major Rework 必须暂停** — 红灯交用户决策
6. **破坏性/外发操作前确认** — 生产部署、跨团队契约（如前后端发版时序）先核证据再说明，不盲目执行

---

> 迁移到新项目：见同目录 `SETUP.md` 的占位符替换清单 + 验证步骤。
