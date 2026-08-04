# Changelog

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
