# hank-dev 插件

个人开发流水线插件，通过 `hank-dev:<skill>` 方式调用。发布在 amazing-dev-skills 这个 marketplace 仓库里，同时支持 Claude Code 与 Codex，二者共享本插件目录中的 skills 与 scripts。

## 技能清单

| 技能 | 调用方式 | 说明 |
|------|----------|------|
| feat | `/hank-dev:feat` | 功能规划阶段：需求分析、代码调研、grill 澄清、DD 方案撰写、多代理评审、确认后交给 autopilot |
| autopilot | `/hank-dev:autopilot` | 方案确认后的全自动开发：分批开发、并行代码评审、交付文档、验收通知 |
| worktree-dev | `/hank-dev:worktree-dev` | 强制 worktree 隔离开发：建分支、建 worktree、同步环境、锁定工作目录 |
| resume-tailor | `/hank-dev:resume-tailor` | 简历/JD 定制流程：master CV 打磨、按 JD 定制、ATS/HR 双代理独立审查、diff 复核、归档 |
| review | `/hank-dev:review` | 多代理 review：按 diff 规模自动判定单代理还是 team 编排。只有本次明确授权且敏感信息扫描通过时才执行独立 DeepSeek 复核，否则报告缺失原因。 |

`feat` / `autopilot` / `worktree-dev` 仍带 `{placeholder}`，是多项目模板，需要按各自的 `SETUP.md` 在项目侧覆盖定制内容（见下面「关于模板占位符」）。

## 配额感知路由

Autopilot 的开发模型由用量快照和额度门禁决定，不由任务复杂度直接决定。周剩余大于或等于 25%，且当天 25% 可支配目标能覆盖每个 worker 5% 的波次预留时，使用 Terra。周剩余 10% 至 24%，或 Terra 日额度预留不足时，必须取得本次运行的 Luna 授权。周剩余低于 10% 时，只在实时模型目录确认 Spark 可用、用户明确授权且 Batch 通过安全门禁后使用 Spark。

Autopilot selects the development model through usage and quota gates, not task complexity. Terra is admitted at 25% or more weekly remaining when the daily 25% target covers a 5% reserve per worker. Luna requires run-scoped approval from 10% through 24%, or when Terra daily reserve is insufficient. Below 10%, Spark requires live-catalog availability, explicit approval, and Batch safety eligibility.

没有官方机器可读用量时，只接受用户在本次运行提供的 `/usage` 快照。插件不读取浏览器会话、Cookie 或非公开账户接口。每个波次都重新计算 `daily_headroom = 25% - today_used_percent`，快照缺失、周期不匹配或过期时默认拒绝。

Without official machine-readable usage, the plugin accepts only a `/usage` snapshot supplied during the current run. It does not inspect browser sessions, cookies, or private account endpoints. Every wave recalculates `daily_headroom = 25% - today_used_percent` and denies by default for a missing, mismatched, or stale snapshot.

纯函数判定器位于 `scripts/autopilot_quota_router.py`，只返回 `ALLOW`、`AWAITING_APPROVAL` 或 `PARTIAL_BLOCKED`。生产 CLI 使用系统 UTC 时间，并从独立参数读取当前额度周期，不信任路由 JSON 内伪造的运行时字段，防止旧快照或旧授权重放。`dispatch_wave()` 是唯一 worker 调度入口，CLI 只为 `ALLOW` 决策输出 `launch_results`。混合 Spark 波次可输出合格 Batch，但顶层保持 `PARTIAL_BLOCKED`，禁止完整门禁和交付。主流程只能把该清单交给 Codex 原生 Agent 工具。并行波次默认不超过 3 个 worker，CLI 会校验真实 Git 根目录、common directory 和分支，要求 linked worktree 属于同一协调仓库，消解符号链接与 macOS 路径别名，并把文件所有权规范成仓库相对路径后检查隔离冲突。

The pure router lives in `scripts/autopilot_quota_router.py` and returns only `ALLOW`, `AWAITING_APPROVAL`, or `PARTIAL_BLOCKED`. The production CLI uses the system UTC clock and a separate current-period argument, ignoring forged runtime fields in route JSON to prevent replay. `dispatch_wave()` is the sole worker dispatch entry, and the CLI emits `launch_results` only for `ALLOW` decisions. A mixed Spark wave may emit eligible Batches while remaining top-level `PARTIAL_BLOCKED`, which blocks the full gate and delivery. The main flow may pass only that manifest to the Codex native Agent tool. A parallel wave has at most 3 workers after real Git root, common-directory and branch checks, linked-worktree repository identity enforcement, symbolic-link and macOS path resolution, repository-relative ownership normalization, and structured runtime-resource conflict checks.

---

## 在 Claude Code 项目里安装

**方式一，直接写配置文件（推荐，一步到位）**：写入目标项目的 `.claude/settings.json`（或 `.claude/settings.local.json`，只想自己本地生效不想提交进项目仓库就用这个）：

```jsonc
{
  "extraKnownMarketplaces": {
    "amazing-dev-skills": {
      "source": { "source": "github", "repo": "EmotionlessHank/amazing-dev-skills" }
    }
  },
  "enabledPlugins": {
    "hank-dev@amazing-dev-skills": true
  }
}
```

写完跑 `/reload-plugins`，确认输出里插件数、技能数有增加，就说明生效了。

**方式二，交互式命令（实测跑通的真实步骤，注意中间那个坑）**：

```bash
/plugin marketplace add EmotionlessHank/amazing-dev-skills   # 只是注册 marketplace，不会自动启用插件！
/plugin                                                       # 打开插件菜单，手动把 hank-dev 切到 enabled，这一步不能省
/reload-plugins                                               # 不是 /reload-skills，命令名是 /reload-plugins
```

**踩过的坑**：`/plugin marketplace add` 执行成功只代表 marketplace 注册上了，`hank-dev` 这个插件默认是**未启用**状态，这时候直接敲 `/hank-dev:feat` 只会得到 "No commands match"。必须在 `/plugin` 菜单里手动启用一次（或者用方式一直接在 settings.json 里写 `enabledPlugins`），再 `/reload-plugins`，技能才会真正出现。

启用成功后，`/reload-plugins` 的输出会报告插件数、技能数等增量（比如 "Reloaded: 4 plugins · 6 skills · ..."），从这个数字变化就能确认 `hank-dev` 真的被吃进去了。技能要用完整的冒号形式触发，比如 `/hank-dev:feat`、`/hank-dev:review`，裸的 `/hank-dev` 不对应任何命令。

---

## 关于模板占位符

`feat` / `autopilot` / `worktree-dev` 发的是通用模板，`{placeholder}` 不会自动替换，插件缓存里的文件也没法直接改。如果某个项目已经有本地定制版（比如 oddfi-backend、health-ai-agent 之前手工替换过占位符的版本），继续在该项目 `.claude/skills/feat/SKILL.md`（同名同路径）保留本地版本即可，项目级同名 skill 会覆盖插件里的中心版本，两者互不冲突。

全新项目、还没有本地定制版的，插件启用后拿到的是带 `{placeholder}` 的原始模板，不能直接用。要替换占位符，必须在该项目里新建 `.claude/skills/<name>/SKILL.md`（复制插件里对应技能的 `SKILL.md` 内容过去），照 `SETUP.md` 的替换表填好占位符，这份项目级文件才会覆盖插件里的中心版本生效；不要以为改一下就能就地生效。

`resume-tailor` 和 `review` 没有占位符，是通用即用版本。

---

## Claude Code 增量更新流程

在这个仓库里改一个技能，改完直接影响所有启用了 `hank-dev` 的项目，不需要逐项目改代码：

```bash
cd /Users/hang/work/amazing-dev-skills
# 编辑 plugins/hank-dev/skills/<name>/SKILL.md
git add -A && git commit -m "..." && git push origin main
```

各项目侧拿更新：

```bash
/plugin marketplace update amazing-dev-skills
```

发布版本由 `.claude-plugin/plugin.json` 与 `.codex-plugin/plugin.json` 共同维护，二者必须使用同一 SemVer。发布后先刷新 marketplace，再更新已安装 plugin，最后 reload 当前会话。

```bash
/plugin marketplace update amazing-dev-skills
/plugin update hank-dev@amazing-dev-skills
/reload-plugins
```

## 在 Codex 里安装和更新

Codex 使用仓库根的 `.agents/plugins/marketplace.json` 与本插件的 `.codex-plugin/plugin.json`。首次安装：

```bash
codex plugin marketplace add EmotionlessHank/amazing-dev-skills --ref main
codex plugin add hank-dev@amazing-dev-skills
codex plugin list --json
```

日常更新先刷新 Git marketplace：

```bash
codex plugin marketplace upgrade amazing-dev-skills --json
codex plugin list --json
```

`marketplace upgrade` 只承诺刷新 Git marketplace，不承诺自动更新已经安装的 plugin artifact。若 `codex plugin list --json` 显示版本或 source 未更新，执行：

```bash
codex plugin remove hank-dev@amazing-dev-skills
codex plugin add hank-dev@amazing-dev-skills
```

随后新开 Codex session。不要编辑 `/Users/hang/.codex/plugins/cache/`，缓存由 Codex 管理。

---

## 新增一个技能到插件里

**关键点：Claude Code 不会自动扫描 `skills/` 目录，必须手动把新技能路径加进 `plugin.json` 的 `skills` 数组，否则技能不会被加载。**（这是本插件搭建时踩过的一个坑：第一版 `plugin.json` 忘了写 `skills` 数组，五个技能一个都不会生效。）

步骤：

1. 建目录 `plugins/hank-dev/skills/<new-skill-name>/SKILL.md`（多项目模板另加 `SETUP.md`）
2. 编辑 `plugins/hank-dev/.claude-plugin/plugin.json`，在 `skills` 数组里加一行 `"./skills/<new-skill-name>/"`
3. 在本文件顶部的技能清单表格加一行
4. commit + push
5. 修改两个 manifest 的相同版本号，运行 `python3 plugins/hank-dev/scripts/validate-distribution.py`
6. 在 Claude 或 Codex 的正式安装路径中验证新技能可见

---

## 验证清单

新增/修改技能后，在任意一个已启用 `hank-dev` 的项目里过一遍：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s plugins/hank-dev/tests -v
python3 plugins/hank-dev/scripts/validate-distribution.py
```

```bash
/plugin marketplace update amazing-dev-skills
/plugin update hank-dev@amazing-dev-skills
/plugin
/reload-plugins
```

判定通过：① `/plugin` 列表里 `hank-dev` 明确显示 enabled（只跑过 `marketplace add` 但没手动启用过的话，这里会是灰的/未启用，容易误以为已经装好）；② `/reload-plugins` 的输出里插件数/技能数有相应增量；③ 用完整冒号形式（如 `/hank-dev:review`）或触发关键词能进对应技能的流程，裸的 `/hank-dev` 不会有反应属于正常；④ 需要占位符的技能（feat/autopilot/worktree-dev）在这个项目要么有本地覆盖版本，要么已经按 `SETUP.md` 替换过占位符。

---

## 回滚

- 项目侧：删 `.claude/settings.json` 里 `enabledPlugins` 对应项，技能即下线。
- Claude 中心侧：`git revert` 对应 commit，各项目刷新 marketplace、更新 plugin、reload 后回退。
- Codex 中心侧：`git revert` 对应 commit，各项目刷新 marketplace，必要时 remove、add plugin 后新开 session 回退。
- Claude 项目侧：在 `/plugin` 中禁用或卸载 `hank-dev@amazing-dev-skills`，然后 `/reload-plugins`。如不再使用该 marketplace，再移除 marketplace 配置。
- Codex 项目侧：执行 `codex plugin remove hank-dev@amazing-dev-skills`，如不再使用该 marketplace，再执行 `codex plugin marketplace remove amazing-dev-skills`，随后新开 session。
- 删除 Git 分发 plugin 或 marketplace 不会删除独立的 `hank-dev@personal`，它仍可作为本地回滚基线。

更底层的 marketplace 迁移背景见仓库根目录的 `MIGRATION-marketplace.md`。
