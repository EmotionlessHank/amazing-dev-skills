---
name: pen2swift
description: Pencil 设计稿 → SwiftUI 高保真落地全链路。门禁(pen-audit)→导出参考→生成 SwiftUI→XcodeBuild 截图→visual-verdict 比对→快照测试，闭环还原设计稿。Triggers on "落地 SwiftUI"、"pen2swift"、"设计稿转代码"、"还原设计稿到代码"、"实现这屏"。
---

# Pencil → SwiftUI 高保真落地（pen2swift）

把「还原设计稿」变成**闭环视觉比对**而非肉眼复刻。`pen-audit` 是第①步门禁，本 skill 是完整流水线。

## 适用栈
SwiftUI · iOS 17.4+ · 设计文件 `design/pen/health-ai.pen` · token 见 `docs/DESIGN_SYSTEM.md` · XcodeBuildMCP（`.mcp.json` 已配 `xcodebuild`）

## 流水线（每屏）

### ① 设计门禁 — `/pen-audit`
落地前设计稿必须先过 audit（L1–L6 全绿）。**绝对定位/溢出/未换行的设计稿不进 SwiftUI**——否则把 bug 翻译成代码。

### ② 导出参考真值
- `export_nodes` 屏幕节点 → `design/exports/vN/<screen>.png`（像素参考，不靠肉眼）
- `get_variables` → token 数值（间距/色/字号），落地的标尺

### ③ 生成 SwiftUI（token 驱动，非肉眼复刻）
- **token 映射**（见下表），全部走 `DesignSystem` 常量，禁硬编码
- **chip/标签云** → `Layout` 协议自定义 `FlowLayout`（无内置 wrap；`ViewThatFits` 不换行）。chip 配 `.fixedSize()` 防内部截断。见 [[feedback_ui_dynamic_wrap]]
- **任意动态文本** → `.lineLimit` + `.minimumScaleFactor(0.7)` 或 `.fixedSize(horizontal:false,vertical:true)`
- **组件对应**：Pencil 的 `Lib/*`/`Org/*` 各对应一个 SwiftUI View；component-first 的 ref 关系映射成 View 复用
- **铁律入 UI**（见下方清单）

### ④ 构建 + 截图（XcodeBuildMCP）
真机/模拟器渲染图，**最坏矩阵**：最大 Dynamic Type（`.accessibility5`）× 最长 locale（de）

### ⑤ 比对裁决 — `visual-verdict`
SwiftUI 截图 vs ② 的参考 PNG，结构化差异清单（非"差不多得了"）。差异 → 回 ③ 迭代

### ⑥ 快照测试闸（CI 回归）
`pointfreeco/swift-snapshot-testing`：每组件在 `[默认, .accessibility5] × [en, de]` 矩阵打快照，diff 即回归。把"溢出/截断"钉死在 CI

### ⑦ 迭代至 visual-verdict 通过 + 快照绿

## token → SwiftUI 映射

| Pencil 变量 | 值 | SwiftUI |
|---|---|---|
| `$primary` | #FF6B6B | `Color.primaryCoral`（CTA/强调）|
| `$primarySoft` | #FFE8E8 | 选中态底 |
| `$danger` | #FF3B30 | **仅**破坏性操作（删除/Clear All）|
| `$warn`/`$warnSoft` | #F5A623/#FFF3DC | 过敏告警**唯一**色 |
| `$surface`/`$surface2` | #FFF/#F2F2F0 | 卡片/次级容器 |
| `$ink`/`$inkMuted`/`$inkSubtle` | #1A1A1A/#6B6B6B/#9A9A95 | 文字三级 |
| `$radiusChip`/`$radiusCard` | 10/16 | `cornerRadius` |

## 铁律在 UI 层（不可绕过）
- 过敏 Banner **永不绿色/"safe"**，只 may contain / cannot confirm（warn-amber）
- ED 模式 View **完全移除 kcal 数字**（非灰掉）
- 危机卡用 `$mint` 暖绿，非红/非 warn
- AI 免责 banner 会话级 sticky，结构的一部分不可删
- 含营养数据的 View 必带来源标签（SourceChip/SourceBadge）
- 营养数字不由 LLM 直出（拆食材→USDA→求和）

## 完成标准
- `/pen-audit` 全绿（设计侧）
- visual-verdict 通过（实现 vs 参考）
- 最坏矩阵（AX5 × de）无溢出/截断
- 快照测试绿
- 无硬编码颜色/间距（全 token）
