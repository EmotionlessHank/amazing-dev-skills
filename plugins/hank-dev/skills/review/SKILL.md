---
name: review
description: 多代理 code review，按 diff 复杂度自动判定编排规模，强制包含一次 DeepSeek 独立复核。Triggers on "/hank-dev:review", "hank-dev review", "多代理 review", "team review 一下这个改动". 小改动走单 Claude reviewer + 1 次 DeepSeek 独立复核；跨模块/大改动自动升级到 omc /team 多维度评审（correctness/security/simplification/test-coverage）并由其中一名队友携带 DeepSeek 委派子任务，findings 过对抗式验证后合并输出。
version: 1.0.0
---

# hank-dev:review：规模自适应多代理 Review（强制含 DeepSeek 独立视角）

审查对象：默认当前分支相对 main 的 diff；用户也可以指定 PR 号或具体 commit range。

**硬性约束：无论走轻量模式还是团队模式，DeepSeek 独立复核都是必选项，不能因为改动小就跳过。** 如果 `opencode run --agent deepseek-worker` 调用失败（超时/报错/opencode 未装），必须在最终报告里显式标注"DeepSeek 复核缺失，原因：xxx"，不能静默略过当作没有这一项。

**环境依赖**：DeepSeek 复核用的 bash 命令是自包含的，不依赖 `opencode-deepseek-delegate` 这个 skill 是否被加载（该 skill 只是这段调用契约最初的出处，供参考背景），但依赖本机已装 `opencode` CLI 且配置好 `deepseek-worker` primary agent。如果在没有这套本地环境的机器上跑这个技能（比如别人装了 `hank-dev` 插件但没配 opencode），会命中上面的失败分支，如实标注缺失即可，不是 bug。

---

## Step 1：复杂度判定（决定走轻量还是团队模式）

```bash
git diff --stat main...HEAD    # 或指定的 commit range / PR diff
```

取两个信号：
- `F` = 改动文件数
- `L` = 改动行数（新增+删除）
- 是否跨多个顶层目录/模块（例如同时改了 `frontend/` 和 `backend/`，或改了 3 个以上互不相关的顶层包）

判定规则（默认阈值，可按项目实际调整，不是死数字；起点定得宽松一些，避免常规 2-3 文件的 feature 分支就被拉去团队模式）：
- **轻量模式**：`F <= 3` 且 `L <= 250` 且改动集中在同一个模块/目录
- **团队模式**：超过以上任一阈值，或跨多个不相关模块，或用户显式要求

用户可以用参数强制指定，跳过自动判定：
- `/hank-dev:review quick` 强制轻量模式
- `/hank-dev:review team` 强制团队模式

---

## Step 2A：轻量模式流程

1. 用 Agent 工具拉一个 Claude reviewer（正确性 + 简化/复用双视角，参考 `/code-review` 的检查清单），审查完整 diff。
2. **并行**触发一次 DeepSeek 独立复核：把 diff 摘要（或完整 diff，视 token 预算）作为子任务 prompt，照抄 `opencode-deepseek-delegate` 技能里的调用契约，三个坑必须原样带上：

   ```bash
   opencode run --agent deepseek-worker --auto --format json "审查以下 diff，指出潜在 bug、边界条件遗漏、可复用性/简化空间：<diff内容或摘要>" < /dev/null \
     | grep '^{' \
     | jq -r 'select(.type=="text") | .part.text'
   ```

3. 合并两份结果：去重（同一个文件同一行的相同问题只保留一条，标注"Claude+DeepSeek 双方一致"提高置信度），保留双方独有的发现并标注来源。
4. 用 ReportFindings 输出，按严重程度排序。

---

## Step 2B：团队模式流程（跨模块/大改动）

1. 用 Workflow 工具（如果当前环境没有 Workflow 工具，改用 `/oh-my-claudecode:team` 或直接并行拉多个 Agent 达到同样的分维度效果）按维度拆分审查任务，典型维度（按实际 diff 内容增减，不是固定死 3-5 个）：
   - 正确性（correctness）
   - 安全（security，涉及鉴权/输入校验/密钥处理时必须有这一维度）
   - 简化/复用/效率
   - 测试覆盖

2. **DeepSeek 的接入方式**：deepseek-worker 不能作为独立的 team 成员（tmux pane），OMC 的 `/team` 和 `/omc-teams` worker 类型是硬编码闭合枚举，没有 opencode 这一类。正确做法是：固定指派其中一名 Claude 队友，在它的任务描述里显式包含 DeepSeek 委派子任务（用上面 Step 2A 第 2 步同样的调用契约），该队友拿到 DeepSeek 的文本结果后，按自己的判断筛选整合，连同自己那个维度的发现一起，正常走 TaskUpdate 汇报。DeepSeek 的产出算作这名队友那个维度下的一组独立发现，不要单独建一个"DeepSeek 维度"当作平行的 team 成员对待。

3. 对抗式验证只用在高价值 finding 上，避免 agent 调用数量失控：只对 Critical/High 级别的 finding 逐条并行拉 2-3 个 skeptic agent 尝试推翻，多数判定"无法推翻"才保留（参考 code-review ultra 模式的验证方式）；Medium/Low 级别直接按置信度展示，不额外验证。单次 review 的验证轮次总数建议设一个上限（比如最多验证 15 条 Critical/High finding），超出的按严重程度排序只展示不验证，并在报告里注明"因数量上限，以下 N 条未做对抗验证"。

4. 用 ReportFindings 汇总所有存活 finding，按严重程度排序，并在报告开头注明触发团队模式的原因（例如 "F=8 文件，L=420 行，跨 frontend/backend 两个模块"）。

---

## 输出格式

统一走 ReportFindings 工具输出，对齐 `/code-review` 的阅读习惯，方便复用同一套 review 阅读方式；如果当前环境没有 ReportFindings 工具，退化为一份按严重程度排序的 markdown 列表，字段保持一致（文件、行号、一句话结论、来源）。每条 finding 额外标注来源（`Claude` / `DeepSeek` / `Claude+DeepSeek 一致`）。支持 `--fix` 参数：把置信度高、确认属实的 finding 直接应用到工作区，其余留给用户自行判断。
