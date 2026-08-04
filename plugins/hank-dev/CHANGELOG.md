# Changelog

## 0.2.1

- 修复三个核心 workflow skill 的 YAML frontmatter，确保 Claude 严格校验和 runtime metadata 加载通过。
- 主分支推送时校验发布内容已同步提高双端版本，并要求 changelog 存在对应版本。

## 0.2.0

- 同一 `hank-dev` 插件目录同时支持 Claude Code 与 Codex 官方 metadata。
- 新增 Codex Git marketplace 入口和双分发一致性校验。
- 文档明确 marketplace refresh 与已安装 plugin artifact 更新是两个独立步骤。
