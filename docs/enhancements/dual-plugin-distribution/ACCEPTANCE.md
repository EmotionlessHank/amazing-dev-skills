# 人工验收

- 2026-08-04，GitHub `main` 已推送至 `39ebb51`。Claude Code 已执行 marketplace update 与 plugin update，`hank-dev@amazing-dev-skills` 从旧提交更新为 0.2.3，保持 enabled。重启 Claude 会话后生效。
- 2026-08-04，Codex 已从 GitHub marketplace 安装 `hank-dev@amazing-dev-skills` 0.2.3，Git source 为 `https://github.com/EmotionlessHank/amazing-dev-skills.git`。5 个 skills 和 3 个可执行脚本均已验证，marketplace upgrade 无错误。新开 Codex session 后使用新插件。
- 已保留 `hank-dev@personal` 0.1.12+codex.e6b3e8e 作为本地回退基线，未修改其来源或启用状态。
- 下次修改并发布更高 patch 版本后，执行 marketplace upgrade，确认是否需要 remove、add 才 materialize 新 artifact，并将真实结果回填文档。
- 在 Claude Code 项目重启后，确认 `hank-dev` 已启用且 `/hank-dev:feat` 可触发。
- 若发布需要回滚，使用更高 patch 版本发布修复内容，分别按 Claude refresh、plugin update、reload 和 Codex upgrade、remove、add、新 session 验证。
