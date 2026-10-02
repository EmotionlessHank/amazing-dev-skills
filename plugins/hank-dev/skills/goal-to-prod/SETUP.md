# goal-to-prod，迁移到新项目（SETUP）

把 `SKILL.md` 和 `jev-ask.sh` 一起复制到目标项目的 `.claude/skills/goal-to-prod/`（`jev-ask.sh` 是随项目复制的脚本，保持可执行，`chmod +x`），按下表替换 `SKILL.md` 里所有 `{占位符}`，再跑验证步骤。项目级同名 skill 会覆盖插件里的中心版本。
本技能的前提是用户明确授权「自动决策、不要我介入」；它和 `feat`、`autopilot` 的占位符各自独立，但 `{DOCS_ROOT}` 建议与 `feat` 保持一致。

## 占位符替换表

| 占位符 | 含义 | 示例（two-of-us） |
|--------|------|-------------------|
| `{DOCS_ROOT}` | 需求目录根，每个需求一个 `fNNN-<kebab>/` 子目录 | `docs/features` |
| `{CHECK}` | 提交前必须全绿的检查命令 | `pnpm check` |
| `{DEPLOY}` | 部署命令（构建后执行） | `npx wrangler deploy` |
| `{SMOKE}` | 线上冒烟清单：URL 加预期状态码 | 首页 200；`/api/me` 未登录 401；`POST /api/runner/claim` 无令牌 401 |
| `{GH_ACCOUNT_MAP}` | gh 多账号登记文件路径；没有多账号就把 §2.1 第 4 条整行删掉 | `~/.config/gh/ACCOUNTS.md` |
| `{DEFAULT_GH_ACCOUNT}` | 命令链结束后切回的默认 gh 账号；删掉上一行时这个占位符也一并删掉或改成「保持当前账号」 | `hank-dong-revium` |
| `{ROLLBACK}` | 部署后判定要回滚时执行的命令 | `npx wrangler rollback <上一版本> --name two-of-us` |
| `{QUEUE_CHECK}` | 部署前只读检查排队任务的命令（可选，没有队列就删 §2.6 第 1 条和 §3 第 6 条里的相关句） | `wrangler d1 execute two-of-us --remote --command "SELECT ..."` |

另外两处属于项目事实，替换时顺手核对：§2.1 第 3 条的自动化工作流名称（two-of-us 是 `.github/workflows/auto-fix.yml`，只处理带 `feedback` 标签的 issue），其余不再有未参数化的项目命令。

## jev-ask.sh

脚本复制进项目后原样使用，不需要改代码。密钥的真实来源由两个环境变量决定：

| 环境变量 | 默认值 | 作用 |
|----------|--------|------|
| `JEV_KEY_VAR` | `TYPESAFE_API_KEY` | 存放密钥的变量名；该变量没有值时，脚本从下面的文件里找同名的 `NAME=value` 一行 |
| `JEV_KEY_FILE` | `<git 根>/.dev.vars` | 备用密钥文件路径 |

项目里密钥不叫 `TYPESAFE_API_KEY`，或密钥文件不在仓库根，就设这两个变量（写进 shell 配置或调用环境），不要去改脚本。密钥经 curl 的标准输入配置传入，不出现在进程列表里。非 git 目录且没有环境变量时，脚本直接报「no 变量名」。

```bash
.claude/skills/goal-to-prod/jev-ask.sh --dry <request.json>                          # 只校验 JSON 形状，不联网
.claude/skills/goal-to-prod/jev-ask.sh <research/jev 目录> <名字前缀> <request.json>   # 真问，请求与回答原文存档
```

同一个名字前缀已有成功存档，或另一个进程正在用它时，脚本拒绝（退出码 2），再问要换名字（`c1`、`c2`）。存档只在成功时留下：回答先写临时文件，HTTP 200 且 `answers` 非空才改成正式名字；curl 失败、HTTP 非 200、`answers` 为空都视为「没有回答」，退出码 4，请求副本和临时回答一并删掉，同一个名字可以直接重试。request.json 的形状在真问前也会校验，坏请求（退出码 1）不会留下任何文件。真问需要网络和密钥。

最小 request.json 示例（`model` 必须是 `jev-latest`，`type` 只用 `choice`，criteria 是对象且至少两个字符串值）：

```json
{
  "model": "jev-latest",
  "state": {
    "setup": "事实写全，JEV 只读文字，看不到图和代码。",
    "review_summary": "已做的检查和剩余风险。"
  },
  "questions": {
    "q1": {
      "type": "choice",
      "question": "能不能开始开发？",
      "criteria": { "go": "方案准出，开始开发", "hold": "先补方案再说" }
    }
  }
}
```

题面保持中性，不暗示答案；criteria 的具体字段以 TypeSafe 的 System One 文档为准，上面只用于通过 `--dry` 的形状校验。

## 验证

0. 占位符残留检查：`grep -oE '\{[A-Z_]+\}' SKILL.md | sort -u`，不应有任何输出（全大写占位符必须全部替换或随所在行删除）。`<id>`、`fNNN`、`<kebab>` 是运行时变量，不属于占位符。
1. `jev-ask.sh` 可执行：`ls -l .claude/skills/goal-to-prod/jev-ask.sh`，权限位带 `x`。
2. 在项目里存上面的示例为 任意路径（比如 scratchpad 里的 `sample-request.json`），运行 `jev-ask.sh --dry` 应输出 `shape ok`。
3. 有密钥时，选一道无害的题真问一次，确认回答原文落到 `{DOCS_ROOT}/<id>/research/jev/`，终端打印选项和概率。
4. 用一个小需求端到端演练，确认每道准出都有 `research/decisions.md` 记录，评审是独立子代理，PR 正文没有 AI 署名，部署后冒烟逐项对上 `{SMOKE}`。
