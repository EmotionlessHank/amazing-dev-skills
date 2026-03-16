---
name: daily-report
description: 一键生成每日开发日报。当用户说 "/daily-report"、"日报"、"今日总结"、"生成日报"、"daily report" 时触发。自动扫描当日所有分支（含 worktree）的 git 提交记录，按大厂日报格式输出，并归档至 .progress/daily-reports/。
version: 1.0.0
---

# /daily-report — 每日开发日报生成

自动扫描当天所有开发活动，生成结构化日报，归档至项目 `.progress/daily-reports/` 目录。

---

## 触发条件

用户说出以下任意关键词：
- `/daily-report`
- `日报`、`今日总结`、`生成日报`、`每日总结`
- `daily report`、`daily summary`

---

## 执行步骤

### Step 1：数据采集

并行执行以下 git 命令，收集当天所有开发活动：

```bash
# 1. 获取今天日期
DATE=$(date +%Y-%m-%d)

# 2. 所有分支今日 commit（含 worktree）
git log --all --since="${DATE}T00:00:00" --format="%h %s (%D)" --date=short

# 3. 活跃 worktree 列表
git worktree list

# 4. 各功能分支与 main 的 diff stat
git diff --stat main...<branch> | tail -3
```

对每个活跃 worktree，进入目录执行相同的 `git log` 命令。

### Step 2：数据分析

将采集到的 commit 按以下维度分组：

1. **按分支归类**：每个功能分支独立列出
2. **识别状态**：
   - 分支已合入 main → `✅ 已合入 main`
   - 分支有 commit 但未合并 → `🔵 开发完成，待合并` 或 `🟡 开发中`
   - 分支有 Review 修复 commit → 统计 Review 轮次
3. **统计汇总**：总 commit 数、总代码行变更、涉及文件数

### Step 3：生成日报

按以下模板输出日报内容：

```markdown
# Oddfi 前端日报 | {YYYY-MM-DD}

## 今日进展

| # | 功能模块 | 状态 | 说明 |
|---|---------|------|------|
| 1 | {模块名} | {状态标记} | {一句话说明} |
| 2 | ... | ... | ... |

## 关键数据

- Commit：{N} 个 | 新增/修改代码：~{N} 行 | 涉及文件：{N} 个
- Code Review：{N} 轮（{版本}），{修复要点}
（若当天无 Review 活动，省略此行）

## 提交明细

### {分支名} → {合并状态}

| Commit | 说明 |
|--------|------|
| `{hash}` | {commit message} |

（每个活跃分支一个子表格）

## 明日计划

- {基于当天 🟡 进行中的任务，推断明日优先项}
- {基于 🔵 待合并的分支，建议合并}
- {其他合理建议}

---

> 状态标记：✅ 已完成 🔵 待合并 🟡 进行中 🔴 阻塞
```

### Step 4：归档

1. 将日报写入 `.progress/daily-reports/{YYYY-MM-DD}.md`
2. 更新 `.progress/daily-reports/INDEX.md` 索引表，追加当日条目
3. 在对话中输出完整日报内容，方便用户直接复制到飞书

---

## 模板字段规则

| 字段 | 规则 |
|------|------|
| 功能模块名 | 从 commit message 的 scope 提取（如 `feat(wallet)` → 钱包连接弹窗），相同 scope 合并为一行 |
| 状态标记 | ✅ 已合入 main / 🔵 待合并 / 🟡 进行中 / 🔴 阻塞 |
| 说明 | 不超过 30 字，聚焦"做了什么"而非"怎么做" |
| 关键数据 | 从 `git diff --stat` 和 `git log --oneline` 汇总 |
| 明日计划 | 基于当天未完成项推断，不超过 3 条 |

---

## 边界情况

| 场景 | 处理 |
|------|------|
| 当天无 commit | 输出"今日无代码提交记录"，跳过归档 |
| worktree 已删除但分支仍在 | 通过 `git log --all` 仍可获取，正常列出 |
| 跨天开发（0 点前后） | 以 `--since` 当天 00:00 为准，不回溯 |
| 同一分支多人提交 | 按 author 过滤，仅统计当前用户 |
| 用户指定日期 | 支持 `/daily-report 2026-03-15` 格式，修改 DATE 变量 |

---

## 输出规范

- 对话中输出完整日报 markdown，方便直接复制
- 归档文件路径在输出末尾提示：`📁 已归档至 .progress/daily-reports/{date}.md`
