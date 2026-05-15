# Design System Selection Guide

Source: https://github.com/VoltAgent/awesome-design-md/tree/main/design-md

## Selection Decision Tree

```
1. 检查 memory/creator-styles.json
   → creator 已知? → 直接用存储的 design_style，跳到步骤 4
   → 未知? → 继续步骤 2

2. 分析视频主题关键词
   → 匹配 theme_keywords 表
   → 有命中? → 用对应 style
   → 无命中? → 继续步骤 3

3. 主动判断：
   → 读取视频标题 + 前30s字幕
   → 判断情绪基调：严肃/活泼/技术/情感/娱乐
   → 参考下方选择矩阵选出最匹配的风格
   → 向用户确认（"我判断应该用 ElevenLabs 风格，因为…，你确认吗？"）

4. 从 VoltAgent repo 获取对应 DESIGN.md token
   → URL: https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/{style}/DESIGN.md
   → 提取: colors / typography / spacing / component tokens
   → 如网络受限，使用 memory/creator-styles.json 中的内置 token

5. 更新 memory/creator-styles.json（新 creator 或新主题）
```

## 风格选择矩阵

| 视频情绪/主题    | 推荐风格     | 原因                          |
|----------------|-------------|-------------------------------|
| 金融·财富·人生  | elevenlabs  | 暗黑电影感，权威感，适合严肃内容 |
| AI·科技·未来    | minimax     | 霓虹粗体，冲击力强              |
| 开发·工具·SaaS  | cursor      | 代码感，克制精准                |
| 音乐·娱乐·创作  | spotify     | 绿色活力，封面主导              |
| 极简·产品·发布  | vercel      | 纯粹黑白，无噪音                |
| 设计·创意·视觉  | figma       | 彩色活泼，专业设计感            |
| 健康·生活·情感  | claude      | 暖棕色调，柔和亲切              |

## ElevenLabs Token（内置，无需网络）

```css
/* 已在本 session 验证可用 */
--bg:       #0c0a09;   /* canvas-deep */
--elev:     #1c1917;   /* surface-dark-elevated */
--soft:     #a8a29e;   /* on-dark-soft */
--muted:    #777169;
--mint:     #a7e5d3;   /* gradient-mint */
--peach:    #f4c5a8;   /* gradient-peach */
--lavender: #c8b8e0;   /* gradient-lavender */
--sky:      #a8c8e8;   /* gradient-sky */
--rose:     #e8b8c4;   /* gradient-rose */
--font-d:   'Noto Serif SC', 'Times New Roman', serif;  /* Waldenburg fallback */
--font-b:   'Noto Sans SC', system-ui, sans-serif;
/* display: weight 300, letter-spacing -1.92px, line-height 1.05 */
/* pill: border-radius 9999px */
/* no neon, no saturated CTA, atmospheric photography aesthetic */
```

## 文件命名规则

```
序号-creator-标题.html
序号-creator-标题.vtt

序号: 三位数字，按 creator 维度递增（memory 中记录）
creator: 小写，去空格（孙哥→sunge，李笑来→lxl）
标题: 视频标题精简版，中文保留，去特殊符号，空格用连字符

示例:
  001-sunge-财务目标从100万到一个亿.html
  001-sunge-财务目标从100万到一个亿.vtt
  002-sunge-如何选择人生第一份工作.html
  001-lxl-时间的朋友.html
```
