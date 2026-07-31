# Git Hook Gate

## English

This repository uses versioned Git hooks to protect `main`.

Install them after cloning:

```bash
bash scripts/setup-git-hooks.sh
```

Rules:

1. Commit messages must be English.
2. Changed Markdown documentation must be bilingual. Each changed `.md` or `.mdx` file must contain both Chinese and English text.
3. Pushes to `main` must run an AI review command. Configure `AMAZING_DEV_SKILLS_AI_REVIEW_CMD` to a single local executable path that accepts one patch-file path, writes a review report to stdout, and exits nonzero when the review fails. Use a wrapper script when the review command needs arguments.
4. Commit messages must not contain AI authorship signatures such as `Co-Authored-By: Codex`, `Co-Authored-By: Claude Code`, `Codex-Session:`, or `Generated with ChatGPT`.
5. Deleting remote `main` is blocked by the pre-push hook.

Example:

```bash
export AMAZING_DEV_SKILLS_AI_REVIEW_CMD=/absolute/path/to/your-ai-review-runner
git push origin main
```

The hook saves AI review artifacts under `.git/ai-review/`. These artifacts are local and are not committed.

Note: GitHub does not execute client-side Git hooks during web merges. If GitHub itself must reject merges, configure branch protection and required status checks in the repository settings as the server-side enforcement layer.

## 中文

本仓库使用版本化 Git hook 保护 `main`。

克隆后安装：

```bash
bash scripts/setup-git-hooks.sh
```

规则：

1. commit message 必须使用英文。
2. 被修改的 Markdown 文档必须是中英文双语。每个被修改的 `.md` 或 `.mdx` 文件都必须同时包含中文和英文文本。
3. 推送到 `main` 前必须运行 AI 审查命令。请把 `AMAZING_DEV_SKILLS_AI_REVIEW_CMD` 配置为单个本地可执行文件路径，该文件接收一个 patch 文件路径，把审查报告写到 stdout，并在审查失败时返回非零退出码。审查命令需要参数时，请使用 wrapper script。
4. commit message 不允许包含 AI 作者署名，例如 `Co-Authored-By: Codex`、`Co-Authored-By: Claude Code`、`Codex-Session:` 或 `Generated with ChatGPT`。
5. pre-push hook 会阻止删除远端 `main`。

示例：

```bash
export AMAZING_DEV_SKILLS_AI_REVIEW_CMD=/absolute/path/to/your-ai-review-runner
git push origin main
```

hook 会把 AI 审查产物保存到 `.git/ai-review/`。这些产物只保存在本地，不进入提交。

注意：GitHub 网页合并不会执行开发者本机的 client-side Git hooks。如果需要 GitHub 直接拒绝合并，请在仓库设置里配置 branch protection 和 required status checks，作为服务端准入层。
