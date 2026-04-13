---
allowed-tools: Bash(git *), Bash(pnpm type-check*), Bash(pnpm test*), Bash(pnpm lint*)
description: 部分提交 — 仅提交当前会话的修改，不影响其他 tab 的改动
---

# Partial Commit — 部分提交

仅提交当前会话产生的改动，排除其他并行 tab 的修改。

## Step 1: 提取初始脏文件

从本次对话开头的 `gitStatus:` 系统消息中，提取会话启动时已存在的脏文件列表（modified / untracked / deleted）。
记为 `INITIAL_DIRTY`。

如果 gitStatus 中 Status 为空（开局干净），则 `INITIAL_DIRTY = []`。

## Step 2: 获取当前状态

运行 `git status --porcelain` 和 `git diff --name-only`，获取当前所有脏文件。
记为 `CURRENT_DIRTY`。

## Step 3: 分类

回顾当前对话历史，检查哪些文件使用过 Write / Edit / Bash(sed/awk/cp/mv) 工具修改过。记为 `SESSION_EDITED`。

按以下规则将 CURRENT_DIRTY 中的每个文件分为三类：

| 条件 | 分类 | 标记 |
|------|------|------|
| 不在 INITIAL_DIRTY 中 | 本会话改动 | ✅ |
| 在 INITIAL_DIRTY 中 **且** 在 SESSION_EDITED 中 | 存疑文件 | ⚠️ |
| 在 INITIAL_DIRTY 中 **且不在** SESSION_EDITED 中 | 其他 tab 改动 | 🚫 |

## Step 4: 展示并确认

向用户展示分类结果：

```
✅ 本会话改动（将提交）:
  M  app/[locale]/not-found.tsx
  A  app/[locale]/[...rest]/page.tsx

⚠️ 存疑（会话前已脏 + 本会话也改过，请确认是否纳入）:
  M  components/ui/Button.tsx

🚫 其他 tab 改动（不提交）:
  M  components/referral/ReferralPage.tsx
```

等待用户确认最终提交范围。用户可以：
- 直接确认
- 要求加入/排除某些文件
- 取消提交

**未经用户确认，不得执行 git add / git commit。**

## Step 5: 提交

用户确认后：

1. 运行 `git diff -- <files>` 查看将提交的具体改动
2. 运行 `git log --oneline -5` 参考 commit message 风格
3. 仅 `git add <file1> <file2> ...` 逐个添加确认的文件（禁止 `git add -A` / `git add .`）
4. 生成 commit message 并提交

## 约束

- commit message 必须简体中文，禁止 Co-Authored-By
- 提交前运行 type-check 确认无类型错误（lint/test 由 pre-commit hook 自动执行）
- 如果 ✅ 和 ⚠️ 均为空（本会话无改动），直接告知用户"当前会话无新改动需要提交"，不执行任何 git 操作
