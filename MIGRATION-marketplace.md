> **2026-07-15 更新**：第 0/8 节里"重定制技能（feat/autopilot/worktree-dev）本轮不迁"的决策已被推翻。三者已 `git mv` 进 `plugins/hank-dev/skills/`，随第一个落地的 plugin `hank-dev` 一起发布，`{placeholder}` 模板原样保留，走的是第 8 节的「路 A」：项目侧要定制内容，靠 `.claude/skills/<name>/SKILL.md` 覆盖中心版本，不再假设"重定制技能就该留在项目本地"。

# 迁移 SOP：amazing-dev-skills → Claude Code Plugin Marketplace

> 目标：把本仓库从「copy-paste / symlink 技能库」改造成官方 **plugin marketplace**，实现
> **中心仓库管技能、各项目 `.claude/settings.json` 声明加载、改一次全项目即时拿到**。
> 本文只是方案，未动手改造。按节奏分批推即可。

---

## 0. 决策基线（本轮已拍板）

- 本轮**只迁通用技能**（无项目耦合），重定制技能（`feat` / `autopilot` / `worktree-dev` / `deploy` 等）**暂留项目本地**，等整套 marketplace 机制验证跑通再说。（⚠️ 此条已被 2026-07-15 更新推翻：`feat`/`autopilot`/`worktree-dev` 三者已迁进 `hank-dev` 插件，见顶部更新说明。「deploy」在本仓没有对应的同名 skill，属于当初的泛指占位，不用对应到具体文件。）
- 不推荐 symlink（前端现用的 `skills -> ../../../../.claude/skills`）与全局 `~/.claude/skills`：前者跨设备/相对路径脆弱，后者无版本/无更新/无按项目开关。marketplace 取代二者。

---

## 1. 技能分类（迁 vs 留）

判定标准：**SKILL.md 里有没有 `{placeholder}` / 项目专属路径 / 单仓约定**。

| 类型 | 信号 | 处理 |
|------|------|------|
| **通用**（迁中心） | 单 `SKILL.md`、无 placeholder、跨项目同一份就能用 | ✅ 进 marketplace |
| **重定制**（留本地） | 带 `SETUP.md` + `{placeholder}`、含项目专属内容（web-api/链上/Figma/pnpm…） | ⛔ 本轮不迁，留各项目 `.claude/skills/`（⚠️ `feat`/`autopilot`/`worktree-dev` 例外，已按顶部 2026-07-15 更新迁进 `hank-dev` 插件，走「路 A」：项目侧仍可用 `.claude/skills/<name>/SKILL.md` 覆盖中心模板） |

本仓现状速判（以是否含 `SETUP.md` 多文件为线索，迁移前逐个 `grep '{' SKILL.md` 复核）：

- **本轮迁中心（通用）**：`grill-me` `partial-commit` `weekly-sync` `today-summary` `daily-report` `daily-todo` `live-photo` `sentry` `mac-cleanup` `disk-cleanup` `finance-*` `prd-writing` `ui-walkthrough` `ui-design-plan` `patch-audit` `sync-tokens` `vercel-build-doctor` `pencil-impl` `pen2swift` `agent-handoff` `project-rules-initialization` 等
- **本轮留本地（重定制，带 SETUP.md）**：~~`feat` `autopilot` `worktree-dev`~~（已迁进 `hank-dev` 插件，见顶部更新）`parallel-worktree` `headless-web-deploy` `back-to-cn-proxy` `persona-distill` `video-to-html-pres`

> 分批建议：一个 plugin 按域聚合多个 skill（如 `dev-workflow`、`reporting`、`finance`、`media`），不要一 skill 一 plugin（项目 `enabledPlugins` 会很碎）。

---

## 2. 目标仓库结构

```
amazing-dev-skills/
├── .claude-plugin/
│   └── marketplace.json            # 唯一分发清单，列出所有 plugin
├── plugins/
│   ├── dev-workflow/               # plugin = 一组同域 skill
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/
│   │       ├── grill-me/SKILL.md
│   │       ├── partial-commit/SKILL.md
│   │       └── patch-audit/SKILL.md
│   ├── reporting/
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/{weekly-sync,today-summary,daily-report}/SKILL.md
│   └── media/
│       └── ...
└── README.md
```

> 现有顶层 `feat/` `grill-me/` 等目录：迁移期可保留（standalone 仍可被 copy），稳定后再决定是否收编进 `plugins/`。`marketplace.json` 的 `source` 用相对路径指向 `plugins/<name>`，**不要用 `../` 指向 plugin 目录外**（plugin 入 cache 时外部文件不复制）。

---

## 3. 配置文件模板

### 3.1 `.claude-plugin/marketplace.json`（中心仓库根）

```json
{
  "name": "amazing-dev-skills",
  "owner": { "name": "Hank", "email": "zggdszft@gmail.com" },
  "plugins": [
    {
      "name": "dev-workflow",
      "source": "./plugins/dev-workflow",
      "description": "Grill, partial-commit, patch-audit and other dev-loop skills"
    },
    {
      "name": "reporting",
      "source": "./plugins/reporting",
      "description": "Weekly sync, daily/today summaries"
    }
  ]
}
```

> 省略 `version` 字段 → 每个 commit 自动作为新版本，内部工具最省心（不用手 bump）。

### 3.2 `plugins/<name>/.claude-plugin/plugin.json`

```json
{
  "name": "dev-workflow",
  "description": "Dev-loop skills",
  "author": { "name": "Hank" }
}
```

### 3.3 各项目 `.claude/settings.json`（声明加载）

```jsonc
{
  "extraKnownMarketplaces": {
    "amazing-dev-skills": {
      "source": { "source": "github", "repo": "EmotionlessHank/amazing-dev-skills" }
    }
  },
  "enabledPlugins": {
    "dev-workflow@amazing-dev-skills": true,
    "reporting@amazing-dev-skills": true
  }
}
```

- `extraKnownMarketplaces`：注册中心仓库（一次声明，所有项目复用）。
- `enabledPlugins`：**逐项目**开关——某项目用不到的 plugin 不开。
- 项目级 `.claude/skills/<同名>` **覆盖** 中心同名 skill（保留本地定制版的逃生口）。

---

## 4. 落地步骤

1. **建结构**：在本仓建 `.claude-plugin/marketplace.json` + `plugins/<域>/.claude-plugin/plugin.json`。
2. **搬通用 skill**：把第 1 节「迁中心」清单里的 skill 移到对应 `plugins/<域>/skills/`（先 `git mv` 一个最小集，如 `dev-workflow` 含 `grill-me`+`partial-commit` 验证）。
3. **commit + push** 中心仓库。
4. **选一个项目试点**（建议 oddfi-backend）：写 `.claude/settings.json` 的两段；删该项目里这些通用 skill 的本地副本/symlink。
5. **验证**（见第 5 节）。
6. 通过后逐项目铺开 `settings.json`，并把各项目本地的通用 skill 副本清掉（`feat`/`autopilot`/`worktree-dev` 已迁进 `hank-dev` 插件，各项目若有本地定制版仍按「路 A」保留 `.claude/skills/<name>/SKILL.md` 覆盖中心版本）。

---

## 5. 验证清单

```bash
# 试点项目内启动 claude 后：
/plugin marketplace add EmotionlessHank/amazing-dev-skills   # 首次注册（或 settings.json 已声明则信任项目时自动提示）
/plugin                                                       # 浏览/确认 plugin 已 enabled
# 触发一个迁过去的 skill 验证可用，例如：
#   说 "grill me" 看是否进 grill 流程
#   说 "weekly sync" 看是否触发
ls ~/.claude/plugins/cache/                                   # 确认缓存已拉取且各项目共享一份
```

判定通过 = ① plugin 列表里 enabled；② skill 关键词能触发；③ 缓存目录存在。

---

## 6. 日后更新流程（核心收益）

```bash
# 在中心仓库改 skill：
cd /Users/hang/work/amazing-dev-skills
# edit plugins/dev-workflow/skills/grill-me/SKILL.md
git add -A && git commit -m "feat: 改进 grill 提问策略" && git push origin main

# 各项目拿更新（手动一条，或启动时自动）：
/plugin marketplace update amazing-dev-skills
```

→ **项目代码零改动，所有 enabled 项目即时拿到新版本。** 这就是替代 copy-paste/symlink 的根本价值。

---

## 7. 回滚

- 项目侧：删 `.claude/settings.json` 里 `enabledPlugins` 对应项（或整段），技能即下线；需要的话恢复本地 `.claude/skills/` 副本。
- 中心侧：`git revert` 对应 commit 即可，下次 `marketplace update` 各项目回退。

---

## 8. 未来：重定制技能怎么收编

`feat`/`autopilot`/`worktree-dev` 已经落地，走的就是下面「路 A」，不再是未来时。「deploy」当初是泛指，本仓没有同名 skill，不用对号入座。这一节保留给还没收编的其他重定制技能参考：

- **路 A（中心骨架 + 项目薄覆盖）**：通用模板进 marketplace；项目级保留同名 skill 只写「项目专属变量/约定」，靠项目级覆盖中心。改造小。
- **路 B（config 单一真值源）**：定制点抽成项目 `.claude/skill-vars.md`，中心 skill 运行时读它填充。最彻底，成本最高。

> 注意官方机制只发**同一份** skill 给所有项目；重定制技能不解决「每项目不同内容」就别硬塞中心，否则会被抹平。
