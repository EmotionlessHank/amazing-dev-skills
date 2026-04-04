---
name: figma-impl
description: Figma 像素级还原强制流程。当用户说 "/figma-impl"、"还原 Figma"、"按 Figma 实现"、"像素还原"、"Figma 适配" 时触发。将 LESSONS §14 的 6 步 SOP 从文档变成结构化流程，每步设门控，杜绝跳步导致的返工。
version: 1.0.0
---

# /figma-impl — Figma 像素级还原强制流程

将 LESSONS §14 的 6 步 SOP 从"建议文档"提升为"强制流程"。每一步设门控，不完成不允许进入下一步。

**设计背景**：历史数据显示 Figma 还原任务的 fix commit 比率 >50%（swap-figma 50%, betslip 78%），根因是 AI 跳过截图获取和视觉对比步骤。本 Skill 通过结构化流程消除跳步。

---

## 输入

用户提供以下信息（缺少时主动询问）：

| 参数 | 必填 | 说明 |
|------|------|------|
| Figma 节点 ID 或链接 | 是 | 要还原的设计稿节点 |
| 目标文件路径 | 否 | 要修改/创建的组件文件（可在 Step 1 后确定） |
| 实现范围 | 否 | 单组件 / 整页（默认单组件，整页则自动拆分） |

---

## 整页拆分规则（强制）

如果用户给的节点是整个页面（而非单组件），**必须先拆分为组件列表**，逐个走完整 Cycle。

```
整页节点
  → 用 get_metadata 识别子组件边界
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
  1. 调用 get_metadata({nodeId}) 查看节点层级
  2. 确认节点是最外层容器（Modal → overlay 层，Card → 最外层 frame）
  3. 如果用户给的是子节点 → 主动往上找父容器并告知用户

门控条件: 必须确认节点粒度正确后才能继续
输出: "节点确认: {nodeId} — {节点名称}（{层级位置}）"
```

### Step 2: 获取设计数据 ⛔ 门控

```
操作:
  调用 get_design_context({
    nodeId: "...",
    forceCode: true,
    clientLanguages: "typescript,css",
    clientFrameworks: "react,next.js,tailwindcss",
    artifactType: "COMPONENT_WITHIN_A_WEB_PAGE_OR_APP_SCREEN"
  })

门控条件: 必须传 forceCode: true（Hook 也会检查）
输出: 保存返回的结构化代码，标记所有 localhost 资源 URL
```

### Step 3: 获取视觉基准 ⛔ 阻断门控（最关键）

```
操作:
  调用 get_screenshot({nodeId}) 获取 Figma 截图

门控条件: 截图必须成功获取并保存
  - 截图存放: .screenshots/figma-{nodeId}-baseline.png
  - 失败时: 重试一次，仍失败则暂停并告知用户

输出: "视觉基准已获取: .screenshots/figma-{nodeId}-baseline.png"

⛔ 此步是硬阻断: 没有视觉基准就开始实现 = 盲写代码，禁止继续。
```

### Step 4: 资源处理

```
操作:
  1. 扫描 Step 2 返回代码中的所有 http://localhost:3845/assets/ URL
  2. 按以下规则分类处理:

  A. 通用 UI 图标（菜单/箭头/搜索/关闭/设置等）:
     → 禁止下载 SVG
     → 从 @phosphor-icons/react 找对应图标（必须加 Icon 后缀）
     → Phosphor 找不到 → 立即告知用户，等待指示

  B. 品牌/自定义图标（Logo/代币/赛事特有图标等）:
     → curl 下载到 public/ 对应子目录
     → 自定义 SVG 图标抽成 components/icons/XxxIcon.tsx

  C. 无法判断的图标:
     → 列出图标截图/描述，询问用户属于 A 还是 B

输出: 资源处理清单（每项标注: Phosphor/下载/待确认）
```

### Step 5: 实现代码

```
操作:
  1. 转录 MCP 精确像素值（禁止替换为 Tailwind 语义 class）:
     - gap-[32px] → 写 gap-[32px]，禁止 gap-8
     - p-[40px] → 写 p-[40px]，禁止 p-10
     - rounded-bl-[16px] → 写 rounded-bl-[16px]，禁止 rounded-l-2xl
     唯一例外: tailwind.config.ts 中已有精确匹配的 Design Token

  2. 颜色处理:
     - 有 var(--xxx) 的 → 使用对应 Design Token
     - 裸 hex/rgba（Figma 硬编码）→ 写裸值 + @figma-hardcoded 注释
     - 禁止自行创建新 Token

  3. 效果类属性（透明度/模糊/阴影/渐变）:
     - 先 grep 项目中同类效果的已有实现
     - 以项目已有参数为基准适配，不直接复制 Figma 值
     - 必须结合实际渲染环境判断

  4. 文件修改限制: 单次不超过 3 个文件

输出: 实现完成的代码（已通过 PostToolUse type-check hook）
```

### Step 6: 视觉验收 ⛔ 交付门控

```
操作:
  1. 在浏览器中打开实现结果
  2. 截图当前实现: browser_take_screenshot 或 chrome-devtools take_screenshot
     - 截图存放: .screenshots/impl-{component}-current.png
  3. 与 Step 3 的 Figma 基准截图逐项对比:

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

门控条件: 实现截图与 Figma 基准截图无可见偏差
输出:
  "✅ 视觉验收通过: {component_name}
   Figma 基准: .screenshots/figma-{nodeId}-baseline.png
   实现结果: .screenshots/impl-{component}-current.png"
```

---

## Cycle 完成后

```
1. 清理截图:
   - 验收通过的截图可删除（节省空间）
   - 或保留到整个任务完成后统一清理

2. 如果是整页拆分模式:
   - 标记当前组件为 ✅
   - 输出进度: "完成 {M}/{N} 个组件"
   - 自动进入下一个组件的 Cycle

3. 如果是单组件模式:
   - 直接完成
```

---

## 整体任务完成播报

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Figma 还原完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
组件数: {N} 个
修改文件: {files list}
修正轮数: {total rounds}（目标 ≤ 1 轮/组件）
跳过步骤: 0（强制流程保障）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 可选参数

| 参数 | 说明 |
|------|------|
| `--pc-only` | 仅实现 PC 端（≥768px），跳过 H5 适配 |
| `--h5-only` | 仅实现 H5 端（<768px），跳过 PC |
| `--skip-effects` | 跳过效果类属性（阴影/模糊/渐变），后续单独处理 |
| `--dry-run` | 仅执行 Step 1-4（分析+资源），不写代码 |

---

## 异常处理

| 场景 | 处理方式 |
|------|---------|
| get_design_context 返回截断 | 检查是否传了 forceCode: true；仍截断则拆分子节点分段获取 |
| get_screenshot 失败 | 重试一次；仍失败则要求用户手动提供截图 |
| Figma 节点 ID 无效 | 要求用户确认节点 ID，提供 get_metadata 辅助定位 |
| 实现截图与 Figma 差异过大 | 3 轮修正后仍不匹配 → 暂停，输出差异清单，等用户指示 |
| 浏览器未启动 | 提示用户启动开发服务器（pnpm dev）和浏览器 |
| 效果类属性环境不匹配 | 优先使用项目已有同类效果的参数，标注适配原因 |

---

## 与其他基建的协同

| 基建 | 协同方式 |
|------|---------|
| `figma-checkpoint.sh` Hook | Hook 在 get_design_context 后提醒截图；本 Skill 在流程中强制执行 |
| `type-check.sh` Hook | Step 5 写代码后自动触发类型检查 |
| `/patch-audit` Skill | 实现完成后可用 patch-audit 检查是否有补丁累积 |
| `/quality-scan` Skill | 实现完成后可用 quality-scan 检查代码规范 |
| LESSONS §14 | 本 Skill 是 §14 的可执行化身，规则来源一致 |

---

## 反模式警告（历史教训）

以下行为在历史 session 中导致了 50%+ 的返工率，本 Skill 通过门控结构性禁止：

| 反模式 | 历史后果 | 本 Skill 如何阻止 |
|--------|---------|------------------|
| 不截图就实现 | swap-figma 10 个 fix commit | Step 3 硬阻断 |
| 整页实现完才对比 | 偏差累积难以定位 | 整页强制拆分为组件 Cycle |
| 用 Tailwind 语义 class 近似 | 间距/圆角普遍偏差 | Step 5 转录规则 |
| 忽略 localhost 资源 URL | 组件缺图标/图片 | Step 4 强制处理 |
| 效果类属性直接复制 Figma 值 | 毛玻璃/阴影在实际环境不可见 | Step 5 环境适配流程 |
| 用 Phosphor 替代自定义图标 | 用户反复纠正 | Step 4 分类规则 + 不确定时询问 |
