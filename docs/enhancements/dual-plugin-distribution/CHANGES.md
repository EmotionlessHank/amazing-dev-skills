# 变更记录

## 提交

- `11f91af`：新增 Codex manifest、repo scoped marketplace 与结构校验。
- `139767c`：修复 Claude 严格校验，补齐文档与主分支发布门禁。
- `265dde5`：将发布版本提升到 0.2.1。
- `3bd1ff0`：记录本地 Codex 安装验收与远端 Git marketplace 验收边界。
- `543804f`：将发布版本和 changelog 校验改为读取目标 Git tree。
- `ad57ad3`：完整验证目标 Git tree，严格校验 SemVer，并发布 0.2.2。
- `3ace521`：发布门禁不再读取工作树，并发布 0.2.3。

## 交付

- 双平台 metadata：Claude `.claude-plugin`，Codex `.codex-plugin` 与 `.agents/plugins`。
- 共享插件根：`plugins/hank-dev/skills/` 和 `plugins/hank-dev/scripts/`。
- 发布保障：JSON 结构、版本同步、changelog、目标 Git tree、可执行脚本权限。
- 最终版本：0.2.3。
- 文档：两端首次安装、升级、缓存更新与回滚步骤。
