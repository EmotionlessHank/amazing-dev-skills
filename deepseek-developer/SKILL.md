---
name: deepseek-developer
description: 受限 DeepSeek 外部补丁生成器。仅在用户明确指派时，向隔离的外部模型发送经扫描的公开代码片段，并把通过 allowlist 校验的 unified diff 交给 Codex 审查和应用。它不是 Codex 原生 agent，不会直接写入工作树、提交或运行命令。
---

# DeepSeek 外部补丁生成器

本技能只把已经明确、低风险、可公开外发的局部任务交给 DeepSeek。DeepSeek 只生成文本补丁，Codex 主模型保留代码读取、文件写入、测试、审查和最终决策权。不得将其当作 native subagent 使用，也不得调用 `spawn_agent` 代替本流程。

## 授权与边界

只有用户在本次会话明确说“委派给 DeepSeek”“用 DeepSeek 生成补丁”或点名本技能时才能调用。每次调用都要在命令行内显式设置 `HANK_DEEPSEEK_OUTBOUND_APPROVED=1`，不能写入 shell 配置、项目 `.env` 或任何长期配置。调用前向用户说明本次任务、外发的是哪些绝对路径、外发内容类别和实际模型提供方。

允许：纯函数实现、局部单元测试、无外部依赖的 bug 修复、仅限 allowlist 内的局部重构、公开文档草稿。

禁止：身份认证、授权、支付、加密、安全修复、秘密管理、生产或部署、基础设施、数据库迁移、第三方依赖安装或升级、访问控制、个人数据、客户数据、未公开产品策略、需要读取全仓或 Git 历史的任务。

如果无法把任务缩至上述范围，留在 Codex 主模型内完成。

## 调用流程

1. 先建立隔离 worktree，并把可改文件缩至精确 allowlist。只允许修改已存在的普通文件，第一版不允许新增、删除、重命名文件。
2. 只读取 allowlist 文件，人工检查其内容不含凭据、个人资料、生产配置、日志、数据库导出或未公开业务数据。
3. 只把任务与验收标准写进临时任务说明文件，不得手工拼接源码。不要发送仓库、目录树、环境变量、Git 历史、`.env`、凭据或未在 allowlist 中的内容。
4. 调用 `scripts/validate_outbound.py`，由它读取精确 allowlist 并确定性生成最终请求文件。任何拒绝都停止外发。
5. 调用 `/Users/hang/.agents/skills/opencode-deepseek-delegate/scripts/run-deepseek-delegate.py`。它会创建临时 `HOME`，禁用工具、插件、MCP 和外部目录访问，完成后删除临时目录。
6. 要求模型只返回 unified diff，不要 Markdown、解释、命令或新增文件。将原始输出直接管道给 `scripts/validate_patch.py`。任何拒绝都不得应用补丁。
7. 主模型逐行审查已验证 diff 的语义后，再通过 `apply_patch` 应用到隔离 worktree。绝不对外部输出直接运行 `git apply` 或 `apply_patch`。
8. 运行目标测试和静态检查，再由主模型进行独立审查。验证通过后才可合并或提交。

## 校验命令模板

将 `{worktree}`、`{task_file}`、`{request_file}` 和每个 `{absolute_allowed_file}` 替换为本次实际值。任务说明只含任务与验收标准，最终请求文件只能由校验器生成。

```sh
python3 /Users/hang/.codex/skills/deepseek-developer/scripts/validate_outbound.py \
  --worktree "{worktree}" \
  --task-file "{task_file}" \
  --output "{request_file}" \
  --allow "{absolute_allowed_file}"
```

```sh
HANK_DEEPSEEK_OUTBOUND_APPROVED=1 python3 /Users/hang/.agents/skills/opencode-deepseek-delegate/scripts/run-deepseek-delegate.py \
  --prompt-file "{request_file}" \
  | python3 /Users/hang/.codex/skills/deepseek-developer/scripts/validate_patch.py \
      --worktree "{worktree}" \
      --allow "{absolute_allowed_file}"
```

不要把上述临时请求文件、模型原始输出或任何审批环境变量提交进仓库。
