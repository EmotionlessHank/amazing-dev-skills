---
name: dsh-deepseek-delegate
description: 把一个不需要读取本地文件的纯文本子任务通过 dsh CLI 委派给 DeepSeek，并返回纯文本结果。触发词包括"委派给 deepseek""用 dsh 跑一下""丢给 deepseek 处理"和"在 team 里加一个 deepseek 子任务"。
version: 1.0.0
---

# dsh 与 DeepSeek 纯文本委派

<!-- HANK_DELEGATE_SECURITY_CONTRACT_V1 -->

## 个人技能库镶镜副本

本插件内的脚本共享路径是 `plugins/hank-dev/scripts/run-dsh-delegate.py`（跟 `review` 一致，不在各技能自己的目录下）。但 `deepseek-developer` 技能硬编码引用的是个人技能库路径 `/Users/hang/.agents/skills/dsh-deepseek-delegate/scripts/run-dsh-delegate.py`——这是一份**自包含的手动镜像**，把脚本复制进了该技能自己的 `scripts/` 子目录，故意不跟插件内的共享脚本布局一致。原因：`deepseek-developer` 需要一个不经过 plugin marketplace 机制、稳定不变的绝对路径。改动 `scripts/run-dsh-delegate.py` 后，必须手动把文件同步复制到 `~/.agents/skills/dsh-deepseek-delegate/scripts/run-dsh-delegate.py` 和 `~/.claude/skills/dsh-deepseek-delegate/scripts/run-dsh-delegate.py`，否则两处会漂移。

## 适用边界

本 Skill 只处理能在 prompt 中一次说清的纯文本任务，例如摘要、翻译、候选方案和独立分析。它不允许读取调用者项目目录，也不参与 OMC 团队消息协议。

DeepSeek 是外部模型服务。prompt 包含本地源码、私有数据、个人信息或商业内容时，调用前必须取得用户对本次外发的明确授权。普通本地任务授权不能推导为外发授权。

## 最小权限契约

每次调用都通过同目录的 `scripts/run-dsh-delegate.py` 新建空临时目录，把任务文本写入其中的 `task.md`，再在该目录运行 `dsh --profile headless`。

```bash
skill_root="<根据当前 SKILL.md 绝对路径解析的 Skill 根目录>"
HANK_DEEPSEEK_OUTBOUND_APPROVED=1 \
  "$skill_root/scripts/run-dsh-delegate.py" "$task_prompt"
```

大段任务文本（例如需要整段粘贴的请求文件）改用 `--prompt-file`：

```bash
HANK_DEEPSEEK_OUTBOUND_APPROVED=1 \
  "$skill_root/scripts/run-dsh-delegate.py" --prompt-file "$request_file"
```

环境变量只表示用户已经明确授权本次外发，不能跨轮次复用。runner 从进入委派流程起执行 120 秒整体超时，并捕获标准输出、标准错误和退出码。禁止添加任何自动审批参数。

runner 以 `DSH_PERMISSION_MODE=read-only` 调用 `dsh --profile headless`：该模式下写入与执行会被沙箱拒绝且无审批通道可逃逸。读取权限是按整个工作目录授予的——工作目录（临时隔离目录）里只放了 `task.md` 和两个全新的隔离 `home`/`DSH_HOME` 子目录，模型能读到的本地内容仅限于此。这与旧版基于 OpenCode 单文件权限对象的"零工具"设计不同：dsh 没有等价的逐文件读取白名单，只有整目录粒度的读/写开关，因此这里授予的是"只能读这一个临时目录"，不是"完全不能用任何工具"，是已知并接受的取舍。runner 使用隔离的 HOME 与全新的 `DSH_HOME`，只显式传入 `DEEPSEEK_API_KEY`，不继承其余环境变量。runner 启动前用 `shutil.which("dsh")` 解析出绝对路径再调用，不依赖子进程环境里的 `PATH` 按裸命令名查找，防止 `PATH` 被篡改后执行非预期程序并拿到 `DEEPSEEK_API_KEY`。

临时目录清理前必须确认路径由本次 `mkdtemp` 返回，且路径位于 `${TMPDIR:-/tmp}` 下。不得在 `$HOME`、项目根目录或其他已有目录中运行委派。

## 结果判定

runner 直接解析 `dsh --profile headless` 的纯文本输出（不是 JSONL 事件流）。以下任一情况都判为失败：

1. 非零退出码或超时。
2. 标准错误非空（成功的 dsh 调用应该没有任何 stderr 输出；出现任何内容都按不确定状态失败关闭，不去猜测其含义）。
3. 输出为空。
4. 文本只表示拒绝执行，没有实际结果。

失败时必须向上游报告"DeepSeek 委派缺失"和具体类别，不能把失败文本当作模型结论。

## 在团队流程中的使用

DeepSeek 不是 OMC 的原生 worker。当前执行 Agent 可以在自己的任务内部执行上述纯文本委派，再筛选结果并按原团队协议汇报。不要写成 `omc team N:dsh`。

若任务需要读取 diff 或代码文件，改用 `hank-dev:review` 的 DeepSeek 单文件审查 profile（`scripts/run-deepseek-review.py`）。不得给本 Skill 增加项目读取权限。
