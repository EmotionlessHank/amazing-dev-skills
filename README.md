# Amazing Dev Skills

A curated list of practical AI Agent skills for enhancing productivity across development workflows, inspired by [awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills).

This repository serves as a personal collection of organized skills, version-controlled for continuous iteration and improvement.

## Skills Included

### [Project Rules Initialization](./project-rules-initialization)
A skill to initialize project rules, setup progress folders, generate common rules, synchronize agent rules, setup multi-agent workflow files, and create standard directory structures.

### [PRD Writing](./prd-writing)
Write production-grade Product Requirements Documents following a proven PM methodology. Covers 6 core writing patterns: "Display + Rules" dual-column, phase-based drill-down, table-driven comparison, independent edge case sections, domain education, and analytics tracking specs. Optimized for Web3/fintech and general product domains.

### [Daily Report](./daily-report)
一键生成每日开发日报。自动扫描当日所有分支（含 worktree）的 git 提交记录，按功能模块分组，生成大厂风格结构化日报表格，归档至 `.progress/daily-reports/`。支持指定日期回溯，方便飞书文档归档与产品经理跟进。

### [Finance Analyze](./finance-analyze)
分析银行账单 PDF，自动分类交易、生成分类汇总与 Excel 报告，对比上期数据标出异常变化，更新财务上下文并输出关键发现摘要。

### [Finance Health](./finance-health)
执行家庭财务健康检查。计算现金流、应急储备覆盖月数、目标资金充足率，输出综合评分和改进建议的健康报告卡。

### [Finance Update](./finance-update)
通过自然语言更新财务上下文信息。自动判断修改对应的 YAML 文件（收入、支出、目标、汇率、家庭信息），支持目标状态流转。

### [Finance Forecast](./finance-forecast)
基于当前收入支出数据和假设参数，预测未来 6-12 个月的现金流走势，标注风险节点（余额触及安全线、储备耗尽时间等）。

### [Finance Summary](./finance-summary)
一页式家庭财务概况速览。展示账户余额、月度支出、进行中目标、汇率、海外储备跑道等关键信息，并标注过期数据提醒更新。

### [Weekly Sync](./weekly-sync)
生成面向产品经理的周工作同步报告。自动扫描上周及本周所有分支的 git 提交记录，按业务维度归纳，输出 Lark 友好的无序列表格式，可直接复制发送。

### [Sync Tokens](./sync-tokens)
同步 Figma Design Token 到项目代码。接收 Figma 导出的 JSON 文件路径，自动复制到 `tokens/figma/`、运行同步脚本生成 CSS 变量和 TS 常量、展示 diff。无参数调用时提醒提供文件路径。

### [Parallel Worktree](./parallel-worktree)
并行 Worktree 开发编排。自动执行任务分解、文件所有权冲突检查、worktree 创建、聚焦上下文注入、合并指引。借鉴 Anthropic 16 并行 Agent 构建 C 编译器的工程模式，解决"任务拆分不当导致合并冲突"和"Agent 缺乏聚焦上下文导致越界修改"两大核心问题。附带 Anthropic CCC 模式参考文档。

### [Sentry](./sentry)
Sentry 错误巡检与 Regression 测试自动生成。连接 Sentry API 获取线上未解决的 Fatal/Error Issue，按阈值规则（资金零容忍、Fatal 零容忍、Error ≥3次/小时）过滤，自动定位源文件并生成 co-location regression 测试骨架。支持手动模式回退（Sentry 未接入时手动描述错误）。四阶段流程：获取 → 过滤 → 生成 → 验证。

### [Daily Todo](./daily-todo)
每日待办管理。支持每日任务录入、增删改查、状态更新、自动归档。用户描述今日计划后自动解析为结构化待办，写入 `.progress/REMINDERS.md`，可选同步到 macOS Reminders.app。已完成任务按月归档至 `.progress/archive/reminders/`。支持遗留任务处理、日期智能推断、优先级自动判定。

### [Mac Cleanup](./mac-cleanup)
macOS 系统清理审计。自动扫描 /Applications 中长期未使用的应用、Homebrew/npm/pip 包管理器中的冗余包和缓存、~/Library/Caches 系统缓存、Xcode DerivedData 等，输出结构化清理建议报告（含可回收空间估算和风险等级），等用户确认后再执行删除操作。

## Usage

You can use these skills by integrating them with your favorite AI agents (e.g., Gemini CLI, Claude Code).

## License

MIT
