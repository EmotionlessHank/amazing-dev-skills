# ENH dual plugin distribution

## 1. 背景与范围

`hank-dev` 目前只通过 Claude 的 metadata 发布，Codex 实际加载的是独立本地副本 `/Users/hang/plugins/hank-dev`。这使中心仓库发布后，Codex 不会自动取得更新。

本需求让 `/Users/hang/work/.worktrees/amazing-dev-skills-dual-plugin-distribution/plugins/hank-dev/` 成为唯一共享内容根，同时支持 Claude Code 和 Codex 的官方插件分发。

本次范围：

- 保留 Claude marketplace 与 manifest
- 增加 Codex plugin manifest 与 repo scoped marketplace
- 用无依赖校验锁定两套 metadata 与共享 skills 的一致性
- 写明两端首次安装、升级、当前会话刷新、回滚步骤
- 用本机 Codex CLI 验证 Git marketplace 的发现、安装和更新

不在本次范围：

- 删除现有 `hank-dev@personal`
- 改写任何 skill 的业务流程
- 加入 MCP、认证、hooks 或新第三方依赖

## 2. 调研证据

### Codex 官方

- OpenAI 官方要求插件根有 `.codex-plugin/plugin.json`，并把 skills 保留在同一插件根的 `skills/` 下。
  https://developers.openai.com/plugins/build/plugins#create-a-plugin-manually
- OpenAI 官方建议 repo scoped marketplace 使用 `.agents/plugins/marketplace.json`，每个条目以相对 marketplace 根的 `./plugins/...` 路径引用插件目录。
  https://developers.openai.com/plugins/build/plugins#build-your-own-curated-plugin-list
- Codex CLI 的 Git marketplace 更新命令是 `codex plugin marketplace upgrade <name>`。
  https://learn.chatgpt.com/docs/developer-commands#codex-plugin-marketplace

### Claude 官方

- Claude marketplace 位于仓库根 `.claude-plugin/marketplace.json`，其中 plugin entry 的 source 指向插件根。
  https://code.claude.com/docs/en/plugin-marketplaces
- Claude plugin manifest 位于插件根 `.claude-plugin/plugin.json`，skills 必须在插件根 `skills/` 内。安装会缓存插件目录，所以不可依赖插件根以外的相对路径。
  https://code.claude.com/docs/en/plugins
- 公开发布的 Claude plugin 应在 manifest 维护 SemVer，并在升级后刷新当前会话。
  https://code.claude.com/docs/en/plugins-reference

### 开源实践与信源审计

- `duyet/codex-claude-plugins` 使用每个插件子目录同时放置 `.claude-plugin/plugin.json` 与 `.codex-plugin/plugin.json`，根目录同时维护两套 marketplace，并用脚本校验共有字段与路径。核验时未 archived，最近 push 为 2026-07-24，5 位贡献者，作者账号创建于 2013 年，未命中刷量判据。其 license 为 null，因此只采用结构与测试思想，不复制代码。
  https://github.com/duyet/codex-claude-plugins
- `obra/superpowers` 也采用双 manifest 与双 marketplace，并对 Codex marketplace 写了回归测试。核验时未 archived、MIT、最近 push 为 2026-08-03、38 位贡献者。其高 star 仅作为发现线索，不作为可靠性结论。一个未关闭 issue 报告缓存可能丢失可执行脚本权限，因此本方案加入安装后可执行位检查。
  https://github.com/obra/superpowers/issues/2040

⚠️ 信源污染警告：没有采用任何插件目录站或 README 镜像站作为独立证据。开源案例仅提供结构交叉验证，结论以 Codex 和 Claude 官方文档为准。

## 3. 设计决策

### 3.1 一套内容根，两套 metadata

共享内容仅放在 `/Users/hang/work/.worktrees/amazing-dev-skills-dual-plugin-distribution/plugins/hank-dev/skills/` 和 `/Users/hang/work/.worktrees/amazing-dev-skills-dual-plugin-distribution/plugins/hank-dev/scripts/`。

同一插件根新增 `.codex-plugin/plugin.json`，保留现有 `.claude-plugin/plugin.json`。两个 manifest 的 name 固定为 `hank-dev`。这样 Claude 与 Codex 均加载同一批 skill 文件，不需要同步副本。

### 3.2 分发目录按平台隔离

保留 `/Users/hang/work/.worktrees/amazing-dev-skills-dual-plugin-distribution/.claude-plugin/marketplace.json` 供 Claude 使用。

新增 `/Users/hang/work/.worktrees/amazing-dev-skills-dual-plugin-distribution/.agents/plugins/marketplace.json` 供 Codex 使用。两者均指向 `./plugins/hank-dev`。Codex entry 使用官方的 local source.path、installation policy、authentication policy 与 category 字段。

### 3.3 版本与更新

Codex manifest 使用 SemVer。Claude manifest 同样加入同一 SemVer，版本只出现在各自 manifest，不在 marketplace entry 重复维护。

发布后，Claude 使用官方 marketplace update、plugin update 与 reload 流程。Codex 的 marketplace upgrade 只刷新 Git marketplace，不承诺更新已安装 artifact。因此发布验收先执行 upgrade，再测试同名 add 的行为；若它不重装，则采用 remove、add、新开 session 的官方确定性流程。文档只记录经本机验证的命令。

### 3.4 防漂移校验

新增 Python 标准库脚本，读取 JSON 而非 grep 文本，断言：

- 两个 manifest 的 name、version 一致
- Codex manifest 的 skills 为 `./skills/`
- Claude manifest 列出的每一个 skills 目录都存在
- 两个 marketplace 都有 `hank-dev` entry，且 source 路径为 `./plugins/hank-dev`
- 共享 skills 目录中的每个直接子目录都有 `SKILL.md`
- 安装包中现有可执行 scripts 保留 executable bit

校验脚本加入现有本地验证命令，不引入依赖。

## 4. 实施批次

### Batch 1，metadata 与一致性校验

1. 新增 `/Users/hang/work/.worktrees/amazing-dev-skills-dual-plugin-distribution/plugins/hank-dev/.codex-plugin/plugin.json`
2. 新增 `/Users/hang/work/.worktrees/amazing-dev-skills-dual-plugin-distribution/.agents/plugins/marketplace.json`
3. 更新 Claude manifest 为同一版本号
4. 新增 `/Users/hang/work/.worktrees/amazing-dev-skills-dual-plugin-distribution/plugins/hank-dev/scripts/validate-distribution.py`
5. 运行 manifest 校验及既有 review security 校验

### Batch 2，文档与安装验收

1. 更新 `/Users/hang/work/.worktrees/amazing-dev-skills-dual-plugin-distribution/README.md`
2. 更新 `/Users/hang/work/.worktrees/amazing-dev-skills-dual-plugin-distribution/plugins/hank-dev/README.md`
3. 新增 `CHANGELOG.md`，记录首个双平台版本
4. 用 Codex CLI 添加临时 Git marketplace，安装 plugin，升级 marketplace，记录真实结果
5. 在可用时运行 Claude 官方 validate，缺少 Claude CLI 时明确记录验证缺口

## 5. 测试决策

| 层级 | 断言 |
| --- | --- |
| 静态结构 | 两个 marketplace 与 manifest 均可被 JSON 解析，所有路径和 skills 可达 |
| 版本一致性 | 两端 manifest name 与 version 相同 |
| 安全回归 | `validate-review-security.sh` 保持通过，安装后可执行 scripts 的权限可验证 |
| Codex 冒烟 | Git marketplace 可被 CLI 添加，plugin 可列出或安装，upgrade 后 artifact 的版本与 source 可验证 |
| Claude 冒烟 | CLI 存在时执行严格 validate，否则保留为人工命令与缺口 |

## 6. 风险矩阵

| 风险 | 触发场景 | 影响 | 缓解 |
| --- | --- | --- | --- |
| 两端 metadata 漂移 | 只改一端版本或 skills 指向 | 一端加载旧内容或失效 | JSON 一致性校验和 release checklist |
| 缓存路径依赖 | skill 引用插件根外文件 | 安装后运行失败 | 共享内容限定在插件根内 |
| 本地 personal 插件遮蔽测试 | 同名 plugin 同时启用 | 误认为 Git 版本已生效 | 保留 personal 作为回滚，使用独立 marketplace 标识和 CLI source 验证 |
| CLI 行为差异 | Codex update 不自动 materialize 已安装副本 | 更新未生效 | 以真实 CLI 输出决定是否需要重新 add，并写入文档 |

## 7. 回滚

Git marketplace 验收失败时，删除 Codex Git 安装与 marketplace。现有 `hank-dev@personal` 保持不变，因此回滚不影响当前工作流。

## 8. 确认记录

用户于 2026-08-04 明确确认：先完成方案，再使用 autopilot 执行，并要求采用业界最佳实践、Codex 官方文档和 Claude 官方文档。

## 9. 计划审查处理记录

计划审查发现 Claude 严格校验失败、版本未升级会阻断缓存更新、回滚流程不完整、直接安装会污染 personal plugin 的风险。

- 已修复三个 skill 的 YAML frontmatter，并为 Claude marketplace 补齐 description。
- 已实现基于 Git base 的发布版本门禁，并接入 `/Users/hang/work/.worktrees/amazing-dev-skills-dual-plugin-distribution/.githooks/pre-push`。
- 已将 changelog 放在 `/Users/hang/work/.worktrees/amazing-dev-skills-dual-plugin-distribution/plugins/hank-dev/CHANGELOG.md`，实际发布版本为 0.2.1。
- 已通过独立名称的临时 Codex marketplace 安装 0.2.0，验证 5 个 skills 与 3 个可执行 scripts 后删除测试 plugin 与 marketplace。`hank-dev@personal` 保持原版本、来源和启用状态。
- 已补充 Claude 与 Codex 的客户端回滚流程。发布错误只能通过更高 patch 版本修复，不复用或降低版本号。
