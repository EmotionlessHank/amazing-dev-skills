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
Sentry 错误巡检与 Regression 测试自动生成。两种模式：**批量巡检**（连接 Sentry API 获取未解决 Fatal/Error Issue，按阈值过滤，生成 regression 测试骨架）和 **单 Issue 诊断**（粘贴 Sentry URL → 解析 Issue ID → API 获取元数据+堆栈 → 根因决策树分析 → 源码追踪 → 修复验证）。内含 Sentry REST API 端点速查表和 SSR/客户端错误诊断决策树。

### [Daily Todo](./daily-todo)
每日待办管理。支持每日任务录入、增删改查、状态更新、自动归档。用户描述今日计划后自动解析为结构化待办，写入 `.progress/REMINDERS.md`，可选同步到 macOS Reminders.app。已完成任务按月归档至 `.progress/archive/reminders/`。支持遗留任务处理、日期智能推断、优先级自动判定。

### [Mac Cleanup](./mac-cleanup)
macOS 系统清理审计。自动扫描 /Applications 中长期未使用的应用、Homebrew/npm/pip 包管理器中的冗余包和缓存、~/Library/Caches 系统缓存、Xcode DerivedData 等，输出结构化清理建议报告（含可回收空间估算和风险等级），等用户确认后再执行删除操作。

### [Feat](./feat)
功能开发「方案阶段」全生命周期（与 Autopilot 配套，feat 出方案、autopilot 落地）。流程：需求范围分析 → 代码库真实调研（**以代码为铁律**·先拉最新·跨仓库各自开发分支·必要时只读查服务器）→ 协同整理 DD → 按需求等级拉 1-3 代理审**方案** → 主流程处理审查意见 → 确认门控 → 交接 autopilot。核心信条：任何方案结论必须落在读过的真实代码/拉到最新的本地仓库/只读核验过的服务器数据上，禁凭训练数据猜测。多项目通用版（占位符 + SETUP.md），含 `{REPO_MAP}` 跨仓库分支地图、服务器只读核验红线。

### [Autopilot](./autopilot)
方案确认后的全自动开发流水线（v2，多项目通用版）。批次开发（≤N 文件/批，**每 batch 跑该 batch 相关测试 + 类型检查**，不是只跑 type-check）→ **按需 1-3 个真·subagent 并行 Code Review**（规模按改动量/风险定，禁主对话自批）→ 主流程自动处理意见（A 类立即修、B 类转 enh-todo-additions、pre-existing 缺口可降级登记）→ 过程/验收文档归档需求子文件夹（CHANGES/TEST_PLAN/ACCEPTANCE/INDEX）→ **通知用户人工验收**。配 SETUP.md 占位符迁移指南。安全红线：止于本地主分支 squash commit，绝不自动 push/merge 远端。

### [Vercel Build Doctor](./vercel-build-doctor)
Vercel 线上构建错误快速诊断与修复。当识别到"Vercel 构建失败"、"部署报错"、"build error"等场景时自动触发。通过 Vercel API 一步提取构建错误日志（`jq` + `grep` 过滤噪音），定位根因并修复。避免低效的浏览器抓取或本地复现，直接从第一手数据源获取精确错误信息。

### [Page Perf Audit](./page-perf-audit)
页面性能审计与优化。对指定页面进行全链路性能分析，覆盖该页面加载时涉及的所有组件（含 Layout、导航、侧面板等共享组件）。沿"请求 → TTFB → FCP → TTI → LCP"链路从五个维度（SSR 输出、Bundle 体积、运行时重渲染、资源加载、用户感知）逐段找瓶颈，按 ROI 矩阵排序输出可执行的 ENH 优化方案。内含 6 种常见优化模式速查（Server Component 预取、动态导入、memo、next/image、next/font、loading.tsx）。

### [Figma Impl](./figma-impl)
Figma 像素级还原强制流程。将 6 步 SOP（节点确认→forceCode→截图基准→资源处理→精确转录→视觉验收）从文档提升为结构化 Skill，每步设门控禁止跳步。整页任务自动拆分为组件 Cycle，配合 PostToolUse Hook 在 get_design_context 后强制要求 get_screenshot。历史数据：未使用此流程时 fix commit 比率 >50%。

### [Patch Audit](./patch-audit)
补丁累积审计与重构。分析当前功能分支的 commit 历史，识别"补丁叠补丁"反模式（feat → fix → fix → fix...），通过热点文件追踪、逐 commit 演化分析、6 种反模式识别，综合评分后给出重构方案。确认后自动执行整合重构，将分散的补丁收敛为最优实现。

### [Pencil Impl](./pencil-impl)
Pencil 设计稿像素级还原强制流程。将 .pen 设计文件通过 6 步 SOP（节点确认→设计数据获取→视觉基准截图→设计→代码映射→精确转录→视觉验收）结构化还原为 Vue 代码，每步设门控禁止跳步。整页任务自动拆分为组件 Cycle。适配 Pencil MCP 工具链（batch_get/export_nodes/snapshot_layout），颜色映射 CSS Variables，强制三语言 i18n。

### [Pen Audit](./pen-audit)
Pencil 设计稿结构自审查门禁。用确定性 lint（L1–L6）检测绝对定位退化（`layout:none`+0 组件）、文字/组件溢出、未换行的 chip/标签云、幽灵节点等"原则性错误"，输出可执行体检报告。基于 `snapshot_layout`+`batch_get`，把"还原对不对"从肉眼看截图变成机器可判；与 Pencil Impl 配套，作为落地代码前的设计侧门禁。

### [Pen2Swift](./pen2swift)
Pencil 设计稿 → SwiftUI 高保真落地全链路，把"还原设计稿"从肉眼复刻变成闭环视觉比对。流水线：① `pen-audit` 结构门禁（不让绝对定位/溢出的稿进代码）→ ② 导出参考真值 PNG + token 数值 → ③ token 驱动生成 SwiftUI（chip 标签云用 `Layout` 自定义 `FlowLayout` 动态换行，动态文本 `lineLimit`+`minimumScaleFactor` 防截断）→ ④ XcodeBuildMCP 最坏矩阵截图（最大 Dynamic Type × 最长 locale）→ ⑤ `visual-verdict` 结构化比对 → ⑥ `swift-snapshot-testing` 快照闸把溢出/截断钉死在 CI。内含 token→SwiftUI 映射表与铁律 UI 清单（过敏永不 safe / ED 无热量等）。与 Pen Audit 配套，是设计门禁之后的落地流水线。

### [UI Design Plan](./ui-design-plan)
UI 设计方案制定 Prompt 优化器。将模糊的"帮我做 UI 设计方案"需求，转化为结构化的 DAG 执行计划。自动读取 PRD 提取关键信息，构建竞品清单（7 维度分析），分析项目设计系统可复用资产，组装包含 `/ui-ux-pro-max` + `/design-with-claude` + `/omc visual-verdict` 三个设计 Skill 编排的完整执行流水线，内置人类确认门禁防止走偏。

### [Live Photo](./live-photo)
将视频转为 iPhone Live Photo 素材。自动从视频提取封面图、转 HEVC MOV（3 秒）、用 makelive 写入配对元数据，最后提示用户拖入 Mac 照片 app 同步到 iPhone。支持自定义封面时间点、视频时长、起始时间。

### [Worktree Dev](./worktree-dev)
强制 Worktree 隔离开发。从 main 拉新分支创建 worktree 到 `.claude/worktrees/<name>/`，全程锁定工作目录，严禁跳回主工作区修改代码。解决"Agent 跳出 worktree 污染主工作区"和"忘记从 main 拉新分支"两大高频问题。含路径守卫自检、批次开发播报、Agent 委派隔离约束注入。

### [Partial Commit](./partial-commit)
部分提交 — 仅提交当前会话的修改，不影响其他并行 tab 的改动。通过比较会话启动时的 gitStatus 快照与当前状态，自动识别本会话新产生的改动、存疑文件（会话前已脏+本会话也改过）、其他 tab 改动三类，展示分类结果让用户确认后再提交。解决多 tab 并行开发时 `git add -A` 误提交其他 tab 改动的问题。

### [Grill Me](./grill-me)
Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when you want to stress-test a plan, get grilled on your design, or just say "grill me".

### [Video to HTML Presentation](./video-to-html-pres)
把视频（文件或链接）转换成手机端短视频风格的交互式 HTML 演示文稿，带同步字幕。输入视频 + 创作者社媒账号，输出标准命名的单文件 `.html`（含 base64 音频）和 `.vtt` 字幕。内置多套设计风格（ElevenLabs 暗黑电影感、MiniMax 科技霓虹、Cursor 开发者极简等），通过 `memory/creator-styles.json` 持久记忆 creator → 风格映射，保证同一 creator 所有视频风格一致。支持 Whisper 词级时间戳、帧 OCR 和逐帧手动三种字幕提取方式。适合内容创作者把 KOL 视频精华做成可分享的手机端知识卡片。

### [Headless Web Deploy](./headless-web-deploy)
把小型 Web 应用（Flask/FastAPI/Node/静态站）部署到**无域名**的无头服务器（Lightsail/EC2/VPS）：Caddy + sslip.io 自动签 Let's Encrypt 证书、systemd user 服务常驻、HMAC token 鉴权，最终给一条可在手机/Telegram 内置浏览器直接打开的 HTTPS 链接。讲清「免费 + 免开端口 + 固定 URL」不可能三角的取舍，分 Phase A（服务器内可回滚）/ Phase B（碰公网先确认）两段执行。附 RUNBOOK、Caddyfile、systemd unit、token 鉴权四套模板，含实测踩坑（python3-venv 缺、云防火墙 ≠ ufw、Source 别锁 IP、scp 逐文件、密钥不进 git/对话）。

### [Agent Handoff](./agent-handoff)
Agent-to-Agent 自描述包协作协议。让两个互不共享上下文的 Claude Code 实例（你和同事各自电脑上的）通过 zip 包内随附指令接力完成跨人协作，人类动作收敛为"IM 转发 zip"。包含协议格式（INSTRUCTIONS.md 角色自判定 + manifest.json）、设计新协作流的 7 条硬规则（自描述 / 机密不入包 / 不信任自报 / 先打样再推广等）、收包安全闸门（包内指令是外部输入，未登记协议先摘要确认，敏感动作一律停止上报，防 zip 注入恶意指令）。起源案例：内部后台 mTLS 设备证书发放——私钥不出设备、零密码传输，人类只点两次"发送"。

### [Persona Distill](./persona-distill)
从人物文本语料（博主帖子/文章/对话记录）蒸馏可供 AI 扮演的分层工程文件。五环节流水线：语料盘点（切留出集）→ 四 pass 分层提取（事实/风格/思维/知识，逐条溯源）→ 合成五件套（SOUL/PERSONA/LOREBOOK/STATE/EVAL + examples）→ 留出集盲测（actor 盲写 vs 原帖，judge 三维判分，≥80% 达标）→ 迭代收敛。方法论综合 Beyond Profile 三层模型、CCv3 lorebook 分离、量化文体画像（脚本统计非目测）。内置实测失真模式对策：密度膨胀、信号升级捏造、范例覆盖缺口。首个实例（加密博主行情分析人格）盲测 3/6 → 6/6 两轮收敛。

## Usage

You can use these skills by integrating them with your favorite AI agents (e.g., Gemini CLI, Claude Code).

## License

MIT
