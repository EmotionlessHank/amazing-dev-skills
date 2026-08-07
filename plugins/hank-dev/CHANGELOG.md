# Changelog

## 0.2.6

- `feat` 现在要求每个 Batch 记录 reasoning effort、工程依据、Spark 资格、依赖、文件所有权和运行时资源。`autopilot` 使用最新 `/usage` 快照和实时模型目录执行 Terra、Luna、Spark 配额门禁。
- 新增默认拒绝的纯函数路由器与 27 项行为测试。CLI 可信时间和独立额度周期阻止旧快照与旧授权重放，真实 Git 根目录、common directory、分支和路径身份校验阻止跨仓与别名绕过。唯一 `dispatch_wave()` 入口只为 `ALLOW` 决策生成原生 Agent 启动清单，混合 Spark 波次保持部分阻塞语义。
- `feat` now records reasoning effort, engineering evidence, Spark eligibility, dependencies, file ownership, and runtime resources for every Batch. `autopilot` applies Terra, Luna, and Spark quota gates from a fresh `/usage` snapshot and live model catalog.
- Added a default-deny pure router with 27 behavior tests. CLI-generated trusted time and an independent quota-period argument block replay of old snapshots and approvals. Real Git root, common-directory, branch, and path identity checks block cross-repository and alias bypasses. The sole `dispatch_wave()` entry generates native Agent launch manifests only for `ALLOW` decisions while preserving partial-block semantics for mixed Spark waves.

## 0.2.5

- `feat` 的 Phase 3.1 现明确绑定 Codex 原生结构化提问，每轮只处理一个决策组，提供 2 到 3 个互斥选项、推荐项与理由，等待回复后将结论记录到 DD。流程图也展示了原生提问、等待回答和写入 DD 的路径。
- Phase 3.1 of `feat` now explicitly binds to Codex native structured questions: each round handles one decision group with 2 to 3 mutually exclusive choices, a recommendation, and rationale, then waits and records the conclusion in the DD. The flowchart now shows the native question, answer wait, and DD-recording path.

## 0.2.4

- 英文与中文双语覆盖到 `mermaid-skill`，并补充 `README` 目录项与 `SKILL.md`、各 `reference/*.md` 的中英文用途说明，明确本地 `mmdc` 优先、Kroki 需用户授权。
- Updated the `mermaid-skill` documentation set with bilingual coverage for the catalog entry, skill prompt file, and reference guides, with explicit local-first `mmdc` priority and user-approved Kroki usage.

## 0.2.3

- Git tree 发布校验在带 `--base` 时不读取工作树，并对必填 metadata 和每个 skill 目录的 `SKILL.md` 完整校验。

## 0.2.2

- 发布门禁改为直接验证待推送 Git tree 的 metadata、skills 和脚本权限，避免工作树内容掩盖提交内容。
- 版本号采用严格的稳定 SemVer 格式，拒绝带前导零的版本段。
- 修正 review workflow 对 DeepSeek 独立复核的条件说明。

## 0.2.1

- 修复三个核心 workflow skill 的 YAML frontmatter，确保 Claude 严格校验和 runtime metadata 加载通过。
- 主分支推送时校验发布内容已同步提高双端版本，并要求 changelog 存在对应版本。

## 0.2.0

- 同一 `hank-dev` 插件目录同时支持 Claude Code 与 Codex 官方 metadata。
- 新增 Codex Git marketplace 入口和双分发一致性校验。
- 文档明确 marketplace refresh 与已安装 plugin artifact 更新是两个独立步骤。
