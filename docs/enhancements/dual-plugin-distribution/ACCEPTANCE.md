# 人工验收

- 推送到 GitHub 后，在 Codex 新 session 执行 Git marketplace add、plugin add，确认 `hank-dev@amazing-dev-skills` 显示 0.2.1。
- 修改并发布更高 patch 版本后，执行 marketplace upgrade，确认是否需要 remove、add 才 materialize 新 artifact，并将真实结果回填文档。
- 在 Claude Code 项目执行 marketplace update、plugin update、reload，确认 `hank-dev` 已启用且 `/hank-dev:feat` 可触发。
- 若发布需要回滚，使用更高 patch 版本发布修复内容，分别按 Claude refresh、plugin update、reload 和 Codex upgrade、remove、add、新 session 验证。
