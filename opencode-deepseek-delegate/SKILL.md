---
name: opencode-deepseek-delegate
description: 把一个不需要读取本地文件的纯文本子任务通过 opencode CLI 委派给 DeepSeek，并返回纯文本结果。触发词包括“委派给 deepseek”“用 opencode 跑一下”“丢给 deepseek 处理”和“在 team 里加一个 deepseek 子任务”。
user_invocable: true
---

# opencode 与 DeepSeek 纯文本委派

## 适用边界

本 Skill 只处理能在 prompt 中一次说清的纯文本任务，例如摘要、翻译、候选方案和独立分析。它不允许读取调用者项目目录，也不参与 OMC 团队消息协议。

DeepSeek 是外部模型服务。prompt 包含本地源码、私有数据、个人信息或商业内容时，调用前必须取得用户对本次外发的明确授权。普通本地任务授权不能推导为外发授权。

## 最小权限契约

每次调用都通过同目录的 `scripts/run-deepseek-delegate.py` 新建空临时目录，并在该目录运行 OpenCode。任务只通过 prompt 输入。

```bash
skill_root="<根据当前 SKILL.md 绝对路径解析的 Skill 根目录>"
HANK_DEEPSEEK_OUTBOUND_APPROVED=1 \
  "$skill_root/scripts/run-deepseek-delegate.py" "$task_prompt"
```

环境变量只表示用户已经明确授权本次外发，不能跨轮次复用。runner 从进入委派流程起执行 120 秒整体超时，并捕获标准输出、标准错误和退出码。prompt 通过标准输入传递，不进入进程参数。禁止添加任何自动审批参数。默认拒绝全部工具，外部目录再次显式拒绝，因此模型只能使用 prompt 中的文本。runner 使用隔离的 HOME 与 XDG 目录，禁用 Claude 兼容规则和默认插件，只把 DeepSeek provider、模型与最小权限配置传入子进程。

临时目录清理前必须确认路径由本次 `mktemp` 返回，且路径位于 `${TMPDIR:-/tmp}` 下。不得在 `$HOME`、项目根目录或其他已有目录中运行委派。

## 结果判定

`--format json` 返回 JSONL。runner 逐行解析并汇总 text 事件。任何非 JSON 输出都会失败关闭，不能静默丢弃。

以下任一情况都判为失败：

1. 进程退出码非 0。
2. 整体超时。
3. 输出包含 permission denied。
4. 输出或标准错误提示 agent fallback。
5. 出现 error 事件。
6. JSONL 解析失败。
7. 没有 text 事件或文本只包含空白。
8. 文本只表示拒绝执行，没有实际结果。
9. 出现任何意外工具调用事件。

失败时必须向上游报告“DeepSeek 委派缺失”和具体类别，不能把失败文本当作模型结论。

## 在团队流程中的使用

DeepSeek 不是 OMC 的原生 worker。当前执行 Agent 可以在自己的任务内部执行上述纯文本委派，再筛选结果并按原团队协议汇报。不要写成 `omc team N:opencode`。

若任务需要读取 diff 或代码文件，改用 Hank Dev review 的单文件审查 profile。不得给本 Skill 增加项目读取权限。
