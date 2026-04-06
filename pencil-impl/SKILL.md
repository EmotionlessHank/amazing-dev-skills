---
name: pencil-impl
description: Pencil 设计稿像素级还原强制流程。当用户说 "/pencil-impl"、"还原设计"、"按设计实现"、"像素还原"、"设计还原"、"pen 还原" 时触发。将 .pen 设计文件通过 6 步 SOP 结构化还原为 Vue 代码，每步设门控，杜绝跳步导致的返工。
version: 1.0.0
---

# /pencil-impl — Pencil 设计稿像素级还原强制流程

将 .pen 设计文件通过结构化流程还原为 Vue 代码。每一步设门控，不完成不允许进入下一步。

**设计背景**：AI 跳过截图获取和视觉对比步骤是还原任务返工的首要根因。本 Skill 通过结构化流程消除跳步。

**核心原则**：.pen 文件内容加密，只能通过 Pencil MCP 工具读写，禁止用 Read/Grep 直接读取 .pen 文件。

---

## 输入

用户提供以下信息（缺少时主动询问）：

| 参数 | 必填 | 说明 |
|------|------|------|
| .pen 文件路径 | 是 | UIUX/ 目录下的设计文件（如 `UIUX/pricing-page.pen`） |
| 目标节点名称或 ID | 否 | 要还原的具体 Frame/组件（不提供则列出顶层节点供选择） |
| 目标文件路径 | 否 | 要修改/创建的 Vue 组件文件（可在 Step 1 后确定） |
| 实现范围 | 否 | 单组件 / 整页（默认单组件，整页则自动拆分） |

---

## 前置动作（强制）

开始还原前必须执行：

1. 读取 `.progress/rewind-docs/LESSONS.md`，找到与当前任务相关的章节
2. 读取 `.progress/dev-docs/research/RES-000-reusable-assets.md`，了解项目已有的可复用资产
3. 读取 `UIUX/README.md` 和 `UIUX/DESIGN-PRACTICES.md`，了解设计规范

---

## 整页拆分规则（强制）

如果用户给的节点是整个页面（而非单组件），**必须先拆分为组件列表**，逐个走完整 Cycle。

```
整页节点
  → 用 batch_get 识别子组件边界（readDepth: 2）
  → 拆分为 N 个独立组件/区块
  → 列出实现顺序（从上到下、从外到内）
  → 用户确认拆分方案
  → 逐个组件执行下方 6 步 Cycle
```

**禁止行为**：整页一次性实现完再截图对比。

---

## 6 步 Cycle（每个组件/区块执行一遍）

### Step 1: 节点确认 ⛔ 门控

```
操作:
  1. 调用 batch_get({
       filePath: "UIUX/xxx.pen",
       patterns: [{ name: "用户给的节点名" }],
       readDepth: 2,
       searchDepth: 3
     }) 查看节点层级
  2. 如果用户没指定节点，先不带 patterns 获取顶层节点列表供选择
  3. 确认节点是最外层容器（Page → 顶层 Frame，Card → 最外层 frame）
  4. 如果用户给的是子节点 → 主动往上找父容器并告知用户

门控条件: 必须确认节点粒度正确后才能继续
输出: "节点确认: {nodeId} — {节点名称}（{层级位置}）"
```

### Step 2: 获取设计数据 ⛔ 门控

```
操作:
  1. 调用 batch_get({
       filePath: "UIUX/xxx.pen",
       nodeIds: [确认的 nodeId],
       readDepth: 4,
       resolveVariables: true,
       resolveInstances: true
     }) 获取完整节点树（含变量解析和组件展开）

  2. 调用 snapshot_layout({
       filePath: "UIUX/xxx.pen",
       parentId: nodeId,
       maxDepth: 3
     }) 获取布局结构（尺寸、位置、间距）

  3. 调用 get_variables({
       filePath: "UIUX/xxx.pen"
     }) 获取设计变量（颜色、字体等 Token）

  4. 如果节点内容过多（readDepth: 4 返回 "..."），分层读取子节点

门控条件: 必须获取到完整的节点数据 + 布局数据 + 变量数据
输出: 保存返回的结构化数据，标记所有设计 Token 和颜色值
```

### Step 3: 获取视觉基准 ⛔ 阻断门控（最关键）

```
操作:
  调用 export_nodes({
    filePath: "UIUX/xxx.pen",
    nodeIds: [nodeId],
    outputDir: ".screenshots",
    format: "png",
    scale: 2
  }) 导出设计截图

  或调用 get_screenshot({
    filePath: "UIUX/xxx.pen",
    nodeId: nodeId
  }) 获取内联截图

门控条件: 截图必须成功获取
  - 导出截图路径: .screenshots/{nodeId}.png
  - 失败时: 重试一次，仍失败则暂停并告知用户

输出: "视觉基准已获取: .screenshots/{nodeId}.png"

⛔ 此步是硬阻断: 没有视觉基准就开始实现 = 盲写代码，禁止继续。
```

### Step 4: 设计 → 代码映射分析

```
操作:
  1. 分析 Step 2 获取的设计数据，建立映射关系：

  A. 颜色映射:
     - 设计变量（$xxx）→ 匹配项目 CSS Variable（var(--color-xxx)）
     - 硬编码颜色值 → 检查 base.scss 中是否有对应变量
     - 找不到对应变量 → 使用裸值 + /* @design-hardcoded */ 注释

  B. 组件映射:
     - 设计系统组件（ref 节点）→ 匹配项目已有 Vue 组件
     - Button → Element Plus ElButton 或自定义按钮组件
     - Card/Badge/Input → 检查 app/components/ 下对应组件
     - 无对应组件 → 标记需要新建

  C. 图标映射:
     - 设计中的 icon_font 节点 → 对应 Phosphor 图标或自定义 SVG
     - 品牌/定制图标 → 用 export_nodes 导出 SVG，抽成 components/icons/XxxIcon.vue
     - 无法判断的图标 → 列出描述，询问用户

  D. 文本映射:
     - 检查文本内容是否需要 i18n 处理
     - 硬编码文案 → 需要加入 en.json / ja.json / zh-TW.json

输出: 映射清单（每项标注: 已有组件/需新建/待确认）
```

### Step 5: 实现代码

```
操作:
  1. 精确像素值转录（保留设计数据的精确值）:
     - 设计标注 gap: 32 → 写 gap-[32px]，禁止 gap-8
     - 设计标注 padding: 40 → 写 p-[40px]，禁止 p-10
     - 设计标注 borderRadius: [16,16,0,0] → 写 rounded-t-[16px]，禁止 rounded-t-2xl
     唯一例外: tailwind.config.ts 中已有精确匹配的 Design Token

  2. 颜色处理:
     - 有对应 CSS Variable → 使用 var(--color-xxx) 或 Tailwind class
     - 硬编码色值 → 写裸值 + /* @design-hardcoded */ 注释
     - 禁止自行创建新 CSS Variable

  3. 效果类属性（透明度/模糊/阴影/渐变）:
     - 先 grep 项目中同类效果的已有实现
     - 以项目已有参数为基准适配，不直接复制设计值
     - 必须结合实际渲染环境判断

  4. Vue 组件规范:
     - 使用 Composition API（<script setup>）
     - 组件命名 PascalCase
     - i18n 使用 const { t } = useI18n()，禁止 $t
     - 路由使用 NuxtLink / navigateTo()
     - API 调用通过 app/api/ 模块

  5. 文件修改限制: 单次不超过 3 个文件

输出: 实现完成的代码
```

### Step 6: 视觉验收 ⛔ 交付门控

```
操作:
  1. 在浏览器中打开实现结果（开发服务器应已运行）
  2. 截图当前实现:
     - 使用 chrome-devtools take_screenshot 或 playwright browser_take_screenshot
     - 截图存放: .screenshots/impl-{component}-current.png
  3. 与 Step 3 的设计基准截图逐项对比:

  对比清单:
  □ 整体布局结构（元素排列/层级关系）
  □ 间距（padding/margin/gap）
  □ 颜色（文字色/背景色/边框色）
  □ 圆角（border-radius）
  □ 字号/字重（font-size/font-weight）
  □ 图标（正确性/尺寸/颜色）
  □ 特效（阴影/模糊/渐变）

  4. 偏差处理:
     - 发现偏差 → 当场修复 → 重新截图 → 再对比
     - 单个组件最多 3 轮修正，超过 3 轮暂停并报告给用户
     - 无偏差 → 进入交付

门控条件: 实现截图与设计基准截图无可见偏差
输出:
  "视觉验收通过: {component_name}
   设计基准: .screenshots/{nodeId}.png
   实现结果: .screenshots/impl-{component}-current.png"
```

---

## Cycle 完成后

```
1. 清理截图:
   - 验收通过的截图可删除（节省空间）
   - 或保留到整个任务完成后统一清理

2. 如果是整页拆分模式:
   - 标记当前组件为完成
   - 输出进度: "完成 {M}/{N} 个组件"
   - 自动进入下一个组件的 Cycle

3. 如果是单组件模式:
   - 直接完成
```

---

## 整体任务完成播报

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pencil 设计还原完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
组件数: {N} 个
修改文件: {files list}
修正轮数: {total rounds}（目标 <= 1 轮/组件）
跳过步骤: 0（强制流程保障）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 可选参数

| 参数 | 说明 |
|------|------|
| `--desktop-only` | 仅实现桌面端，跳过移动端适配 |
| `--mobile-only` | 仅实现移动端 |
| `--skip-effects` | 跳过效果类属性（阴影/模糊/渐变），后续单独处理 |
| `--skip-i18n` | 跳过 i18n 处理，仅实现默认语言 |
| `--dry-run` | 仅执行 Step 1-4（分析+映射），不写代码 |

---

## 异常处理

| 场景 | 处理方式 |
|------|---------|
| batch_get 返回 "..." 子节点 | 增大 readDepth 或按子节点 ID 分段读取 |
| export_nodes / get_screenshot 失败 | 重试一次；仍失败则要求用户确认 Pencil 编辑器是否运行 |
| 节点 ID 无效 | 用 batch_get 的 patterns 搜索节点名称重新定位 |
| 实现截图与设计差异过大 | 3 轮修正后仍不匹配 → 暂停，输出差异清单，等用户指示 |
| 浏览器未启动 | 提示用户启动开发服务器（npm run dev）和浏览器 |
| 效果类属性环境不匹配 | 优先使用项目已有同类效果的参数，标注适配原因 |
| 设计变量无对应 CSS Variable | 使用裸值 + 注释标记，不自行创建新变量 |

---

## 与项目基建的协同

| 基建 | 协同方式 |
|------|---------|
| `UIUX/design-system.pen` | 组件复用、颜色/字体 Token 来源 |
| `app/assets/css/base.scss` | CSS Variable 对照表 |
| `UIUX/DESIGN-PRACTICES.md` | Pencil 操作规范参照 |
| `/review` Skill | 实现完成后可触发 Code Review |
| `/quality-scan` Skill | 实现完成后可检查代码规范 |
| `CLAUDE.md` | 架构约定和代码规范的权威来源 |

---

## 反模式警告

以下行为会导致大量返工，本 Skill 通过门控结构性禁止：

| 反模式 | 后果 | 本 Skill 如何阻止 |
|--------|------|------------------|
| 不截图就实现 | 盲写代码，偏差累积 | Step 3 硬阻断 |
| 整页实现完才对比 | 偏差难以定位 | 整页强制拆分为组件 Cycle |
| 用 Tailwind 语义 class 近似 | 间距/圆角普遍偏差 | Step 5 精确像素值转录规则 |
| 硬编码颜色值 | 主题不一致 | Step 4 颜色映射 + Step 5 CSS Variable 规则 |
| 用 Read/Grep 读 .pen 文件 | 内容加密，读到乱码 | 全流程强制使用 Pencil MCP 工具 |
| 跳过 i18n | 文案只有一种语言 | Step 4 文本映射检查 |
| 效果属性直接复制设计值 | 实际环境渲染不一致 | Step 5 环境适配流程 |
