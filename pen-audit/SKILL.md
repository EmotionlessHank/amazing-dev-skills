---
name: pen-audit
description: Pencil 设计稿结构自审查门禁。用确定性 lint 检测绝对定位退化、文字溢出、组件越界、幽灵节点等"原则性错误"，输出可执行的体检报告。Triggers on "审稿"、"设计稿体检"、"pen audit"、"原型校对"、"lint 设计稿"、"检查设计稿"。
---

# Pencil 设计稿自审查（pen-audit）

把"原型图对不对"从**肉眼看截图**变成**机器可判的确定性 lint**。这是 `/pen2swift` 流水线的第①步门禁——设计稿不过 lint，不进 SwiftUI 落地。

## 适用文件

- 设计文件：`design/pen/health-ai.pen`
- 组件库节点：`r2f7P`（Component Library，53 件，台账见 `design/briefs/component-library.md`）
- 只用 `pencil` MCP 工具读 .pen，**禁止** Read/Grep .pen（加密文件）。

## 核心判断

健康屏 = **组件（ref）+ flexbox（vertical/horizontal）+ fill_container/fit_content + padding token**。
病屏 = **绝对定位（layout:none）+ 写死 x/y + 0 组件**。后者的溢出/错位/不一致是结构性必然，单屏人工校对追不完——必须重画，不能补丁。

## 执行步骤

### 1. 全量溢出扫描（确定性，一次拿全）
```
snapshot_layout(filePath, problemsOnly=true, maxDepth=14)
```
返回所有 `partially clipped` / `fully clipped` 节点。记录每个的 id / width / x / 所属屏。

### 2. 逐组结构读取
```
batch_get(filePath, parentId=<各 US 组>, readDepth=2)
```
对每屏 frame 检查 `layout` 与子节点是否含 `ref`。

### 3. 跑 5 条 Lint 规则

| # | 规则 | 检测方式 | 判定 |
|---|---|---|---|
| **L1** | 绝对定位退化 | 屏**内容帧**（非手机外框）`layout:"none"` 且子树 `ref` 占比 < 30% | 🔴 **REBUILD**（重画，不补丁） |
| **L2** | 溢出/裁切 | step 1 的 problemsOnly 非空 | 🟡 逐节点修 |
| **L3** | 文字不换行溢出 | `text` 节点无 `textGrowth`（默认 auto）且渲染宽 > 父容器宽 | 🟡 改 `textGrowth:"fixed-width"` + `width:"fill_container"` |
| **L4** | 组件越界 | 子节点（含 ref）宽度 > 父容器宽（如 StatusBar 390 塞进 375 屏） | 🟡 改 ref `width:"fill_container"` |
| **L5** | 幽灵节点 | 节点位于画布外（x≤-100 或 width=0/height=0）且 `fully clipped` | 🟡 删除死节点 |
| **L6** | chip/标签云不换行 | 数量不定的横向组（chip/tag/badge/filter）是**单行**且可能超宽（或已 clip） | 🟡 改多行 wrap 容器，命名标注 `*-wrap`（SwiftUI: FlowLayout）。见 [[feedback_ui_dynamic_wrap]] |

> L1 的 `ref` 占比阈值：交互内容屏 < 30% 即判病。纯展示/插画屏可豁免，但需在报告标注理由（"无声上限"原则：豁免必须显式记录）。

### 4. 输出体检报告

按组列表，每组给：画法（组件+flex / 绝对定位）· 判定（🟢/🟡/🔴）· 命中规则 · 节点清单。
**修复优先级铁律**：先 L1（重画）再 L3/L4/L5（批量机械修）。L1 病屏不要先修 L2/L3，重画后这些自动消失。

## 铁律校验（health app 专属，叠加在结构 lint 之上）

读组件实例时额外核对（违反直接 🔴）：
- `Lib/AllergenBanner` 只有 Hit / CannotConfirm / NoMatch 三态，**无 Safe 态**
- `Org/EDModeView` / ED 变体**不含任何 kcal 数字**
- `Lib/CrisisResourceCard` fill 固定 `$mint`，非红/非 warn
- `Org/ChatThread` 顶部 sticky AI 免责 banner 存在
- 含营养数据的组件必带 `Lib/SourceChip` 来源标签

## 重画规范（L1 命中时）

不是修坐标，是按 `design-hifi.md` 的 Component-First 重建：
1. 查 `r2f7P` 是否已有对应组件 → 缺则先补组件/状态
2. 屏用 `layout:"vertical"`，section 用 `fill_container` + 统一 `padding` token
3. 全程 `ref` 引用，禁止裸 rectangle+text 手摆
4. 重画后重跑本 skill，必须全绿才算完成

## 完成标准

- snapshot_layout problemsOnly 为空（或仅剩已显式豁免项）
- 无 L1 病屏
- 铁律校验通过
- 报告写入 `docs/impl/phase1/`（或当前 phase 目录）留痕
