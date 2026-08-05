# amazing-dev-skills 维护规则 / amazing-dev-skills maintenance rules

本文件规定维护此仓库时所有 agent 都必须遵守的发布纪律。
This file defines release discipline that every agent must follow when maintaining this repository.

## 下游同步核验 / Downstream synchronization check

每次更新并推送 `amazing-dev-skills` 后，必须核验下游已安装 artifact 的使用和版本状态，再宣布发布完成。
After every `amazing-dev-skills` update and push, verify the usage and version state of downstream installed artifacts before declaring the release complete.

1. 读取远程 `main` 中对应插件 manifest 的版本，作为期望版本。
2. 刷新本机 Git marketplace。
3. 运行 `codex plugin list --json`，找到每个受影响的 `pluginId`。
4. 核验其 `version`、Git `source`、`installed` 和 `enabled` 状态。
5. 对已知 Claude 项目，核验 marketplace、插件启用状态和 reload 后的技能可见性。

1. Read the affected plugin manifest version from remote `main` as the expected version.
2. Refresh the local Git marketplace.
3. Run `codex plugin list --json` and locate every affected `pluginId`.
4. Verify its `version`, Git `source`, `installed`, and `enabled` state.
5. For known Claude projects, verify the marketplace, plugin enablement, and skill visibility after reload.

Codex 核验命令 / Codex verification commands:

```bash
codex plugin marketplace upgrade amazing-dev-skills --json
codex plugin list --json
```

检查结果必须记录：

- 受影响的 `pluginId` 与下游安装位置
- 期望版本与实际版本
- marketplace 或本地来源
- 已安装和已启用状态

Record the following results:
