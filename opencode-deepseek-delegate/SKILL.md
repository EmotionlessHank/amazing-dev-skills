---
name: opencode-deepseek-delegate
description: 把某个子任务通过 opencode CLI 委派给 DeepSeek 模型执行，拿回纯文本结果。当用户说"委派给 deepseek"、"用 opencode 跑一下"、"丢给 deepseek 处理"、"/team 里加个 deepseek 子任务"，或在 /team、/omc-teams 编排中需要把某个子任务派给 opencode+deepseek 时触发。
user_invocable: true
---

# opencode + DeepSeek 任务委派

## 背景

opencode（本机已装 v1.17.18，`~/.config/opencode/opencode.json`）已配置 DeepSeek 为 provider，并定义了一个专职 primary agent `deepseek-worker`（`mode: primary`，绑定 `deepseek/deepseek-v4-pro`）。这是唯一能被 `opencode run --agent` 直接选中的方式——`mode: subagent` 的 agent 只能被 opencode 内部的 primary agent 调用，CLI 外部选不到，选了会静默 fallback，容易误以为生效了。

**OMC 的 `/team`（Claude Code 原生隐式团队）和 `/omc-teams`（外部 CLI worker）里的 worker 类型是硬编码闭合枚举**（`claude/codex/gemini/antigravity/grok/cursor`，定义在 OMC marketplace 插件源码的 6+ 个文件里），没有把 opencode 加成第 7 种原生并行 worker——那需要 fork/patch 插件源码，且会被插件更新覆盖。目前的落地方式是**轻量封装**：某个 Claude 队友在自己的任务执行过程中，把特定子任务通过 Bash 委派给 opencode+deepseek，当作一次工具调用，再照常走 OMC 原生消息协议汇报结果，不改动 OMC 插件本身。

## 调用契约

```bash
opencode run --agent deepseek-worker --auto --format json "<具体子任务 prompt>" < /dev/null \
  | grep '^{' \
  | jq -r 'select(.type=="text") | .part.text'
```

**三个坑，缺一个都会导致挂起或结果被污染，必须原样带上：**

1. `< /dev/null`：`opencode run` 在非 TTY 后台环境下如果读不到 stdin EOF，会等交互式权限确认**无限挂起**（实测卡住 2 分钟以上，同时直连 DeepSeek API curl 1 秒内返回，问题确认在 opencode 本身而非网络/key）。
2. `--auto`：自动批准所有权限请求（含文件写、外部目录访问），不加则同样会挂起等确认。**这意味着 deepseek-worker 在被调用的 cwd 下拥有完整读写权限**——委派前确认 cwd 是安全的工作目录（项目目录/scratchpad），不要在 `$HOME` 或敏感目录下委派不受信任的 prompt。
3. `grep '^{' | jq -r 'select(.type=="text") | .part.text'`：`--format json` 输出是逐 event 的 JSONL 流（`step_start`/`text`/`step_finish`），偶尔前面会混入一行非 JSON 的 ANSI 提示（比如 agent 类型选错时的警告），`grep '^{'` 先过滤掉再喂给 jq，否则 jq 会 parse error 整体失败。多轮 `text` event 需要用 `jq -rs` 或按需拼接，单轮问答取最后一条即可。

## 何时用 / 何时不用

- 用于：明确、独立、能一次性把上下文塞进 prompt 说清楚的子任务（摘要、翻译、生成候选方案、跑一段独立分析），DeepSeek 定价远低于 Claude，适合"量大但单次不复杂"的子任务分流。
- 不用于：需要多轮工具调用、需要访问当前 Claude 会话上下文/文件树、需要参与 OMC 团队消息协议直接汇报 verdict 的 reviewer/critic 角色——`/omc-teams` 的 codex/gemini worker 有专门的 verdict-file contract（见 `cli-worker-contract.ts`），deepseek-worker 没有这层适配，只能靠调用方（Claude 队友）自己解析文本结果后转述。
- 实测开销参考：一个两行回复的极简 prompt 也要吃约 1.5-1.6 万 token（`build` 系 primary agent 默认工具集的系统提示词开销），单次成本约 $0.002-0.003（deepseek-v4-pro，命中 prompt cache 后更便宜）。子任务 prompt 越薄越好，别指望"几乎免费"。

## 在 /team 里怎么接

不要写成 `omc team N:opencode ...`（不支持，会被 Phase 1 校验拒绝）。而是在派给某个 Claude 队友的任务描述里显式包含委派指令，例如：

> 你负责实现 X。其中"生成 3 个候选文案"这一步，用 Bash 调用：
> `opencode run --agent deepseek-worker --auto --format json "生成 3 个 XX 候选文案" < /dev/null | grep '^{' | jq -r 'select(.type=="text") | .part.text'`
> 拿到结果后按你自己的判断筛选/整合，正常走 TaskUpdate 汇报。

队友本身仍是原生 Claude teammate，deepseek 只是它工具箱里的一次 Bash 调用，不是独立并行的 tmux pane。

## 扩展到真·原生 `omc team N:opencode`（未做，按需再评估）

若未来确实需要 opencode 作为独立并行 worker（而不是被某个 Claude 队友当工具调用），落地点是 OMC 插件源码的：
`model-contract.ts`（加 `opencode` 到 `CliAgentType` + `CONTRACTS`）、`cli-detection.ts`、`capabilities.ts`（`WorkerBackend`）、`cli-worker-contract.ts`（reviewer 角色的 verdict 契约）、`types.ts`、`runtime-v2.ts`、`tmux-session.ts`，加对应测试，重新 build `dist/`。因为改的是 `~/.claude/plugins/marketplaces/omc/` 下的第三方插件源码，marketplace 更新会覆盖这些改动，需要自己维护 patch/fork 才能长期存活。当前判断这个投入产出比不划算，先用轻量封装。
