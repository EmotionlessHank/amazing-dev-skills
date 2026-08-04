# 计划审查 v1

结论：通过修订后执行。

- 发现 Claude YAML frontmatter 描述含未引用冒号，严格校验会失败。已将三个 workflow 的 description 改为 YAML 安全引用。
- 要求双端 manifest 使用同一递增 SemVer，CHANGELOG 需记录版本，并对 pre push 接入发布门禁。已落实。
- 要求隔离 `personal` 插件，避免同名插件遮蔽 Git marketplace 验收。已使用临时 marketplace 名称完成本地安装验证并清理。
- 要求明确无法在未推送前验证 Git marketplace 的双版本升级。已保留在人工验收中。
