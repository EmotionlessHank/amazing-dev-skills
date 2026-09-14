# figma-impl 装机说明

复制 `SKILL.md` 到 `<project>/.claude/skills/figma-impl/SKILL.md`，替换下面的占位符，
再在 `~/.claude/skills/figma-impl` 建一条软链接指过去（工作区级 skill 只在 cwd 恰好等于
该目录时加载，不建软链接就等于在仓库子目录里永远不触发，见 harness `omc-skill-deploy`）。

留着不替换的占位符等于技能没装好：那几节全是「写错了不报错、只会安静产出错东西」的坑。

| 占位符 | 填什么 | 例 |
| --- | --- | --- |
| `{SCOPE_ROOT}` | 这份技能只对哪一批仓库生效 | `~/work/acme/` |
| `{SKILL_HOME}` | 技能真身的绝对路径 | `~/work/acme/.claude/skills/figma-impl/` |
| `{STACK}` | 前端技术栈，用来翻译 MCP 返回的 React + Tailwind | `Nuxt 4 + Vue 3 + Tailwind 4 + shadcn` |
| `{ICON_SYSTEM}` | 项目的图标体系，以及哪个库不许引入 | `FontAwesome，走 components/FaIcon.vue；lucide 只在生成的原语内部` |
| `{COLOR_SYSTEM}` | 颜色从哪来、映射表在哪、已知的坑 | `语义 token 在全局样式表，另有一份组件到变量的映射表` |
| `{DEV_COMMAND}` | 起开发服务器 | `pnpm dev` |
| `{TYPECHECK_COMMAND}` | 类型检查 | `pnpm typecheck` |
| `{TOKEN_CHECK}` | 校验设计 token 没漂，没有就删掉这行 | `pnpm tokens:check` |
| `{SCREENSHOT_SETUP}` | 用什么浏览器、登录态怎么造、注意事项 | `headed 真 Chrome；用仓库自带的测试夹具造会话` |
| `{ARTIFACT_DIR}` | 基线图、实现图、拼图、节点清单落哪 | `workspace/progress/<task>/figma/` |

`{组件}` `{nodeId}` 这类小写或驼峰的是运行时动态量，不要替换。
