# Changelog

## 0.2.12

- `goal-to-prod` 的开发步骤不再默认把复杂批次交给 opus：`oh-my-claudecode:executor` 默认不传 model，按 frontmatter 跑 sonnet，只有跨模块或架构级改动才传 opus，与全局子代理路由规则一致。
- `goal-to-prod` no longer sends complex build batches to opus by default: `oh-my-claudecode:executor` is dispatched without a model, so its frontmatter runs it on sonnet, and opus is passed only for cross-module or architectural changes, in line with the global subagent routing rule.

## 0.2.11

- 新增 `housing-research` skill：把租房调研做成可复现流水线。先把需求写成硬条件、软条件、偏好权重三层并复述确认；再用真实浏览器实时抓取房源，多代理并行补查楼盘年份与设施，逐套看照片核验地板、家具和面积，用 Jev 逐维度打分加代码按权重加权，输出结构化 md 报告和 PPT，并做独立验证。来自一次 South Yarra 实战（114 套候选筛到 58 套），附浏览器运行外壳和 Jev 调用封装、需求清单模板和踩坑清单：规则层级被读窄、「带家具」被理解成电器、现住楼被当成候选、挂牌下架、Google 评分未渲染、PPT 空白页。浏览器接管和重连授权的做法见 `revium-browser-test` 第 8 步。
- Added the `housing-research` skill, a repeatable rental research pipeline. It first writes the brief as hard requirements, soft penalties and preference weights and has the user confirm it, then reads live listings through a real browser, fans out agents for building facts, checks floors, furniture and floor area from the photos, scores each dimension with Jev while code applies the weights, and delivers a structured report and a slide deck, checked by an independent verifier. It comes from a South Yarra run (114 candidates down to 58) and ships a browser runner with tab cleanup, a Jev client, a requirements template and a pitfalls list: rules read too narrowly, furniture mistaken for appliances, the renter's own building treated as a candidate, withdrawn listings, unrendered Google ratings and blank slides. Browser takeover and reconnect steps live in step 8 of `revium-browser-test`.

## 0.2.10

- 新增 `goal-to-prod` skill，由 two-of-us 项目里的本地版移植并通用化：用户给出明确目标并授权「自动决策」后，自动走完 plan、开发、评审循环、PR、部署、线上冒烟、回写 issue，全程不打扰用户。核心是交叉决策规则：任何需要「选一个」的节点（方案准出、评审意见接受还是推迟、代码准出、部署后保留还是回滚）都写成措辞中性的 Choice 题，由 JEV 和一个全新上下文的独立模型各自作答，互相看不到对方的答案；两方一致就采用，不一致先补事实再换新名字重问，仍不一致就选更可逆的那个；JEV 概率差小于 0.2 记为弱信号，只能跟有明确理由的模型或选更可逆项，不得写成「JEV 放行」；禁止为了想要的答案重问同一题。请求与回答原文随 `jev-ask.sh` 存档，决策表逐行记依据。项目特有的命令和路径换成 `{DOCS_ROOT}`、`{CHECK}`、`{DEPLOY}`、`{SMOKE}`、`{GH_ACCOUNT_MAP}`、`{DEFAULT_GH_ACCOUNT}`、`{ROLLBACK}`、`{QUEUE_CHECK}`，由 `SETUP.md` 说明如何替换；`jev-ask.sh` 随项目复制，密钥变量名和密钥文件由环境变量 `JEV_KEY_VAR`（默认 `TYPESAFE_API_KEY`）和 `JEV_KEY_FILE`（默认 `<git 根>/.dev.vars`）决定，密钥经 curl 标准输入传入而不进命令行参数，存档只在成功时留下：回答先写临时文件，HTTP 200 且 `answers` 非空才改成正式名字，curl 失败、非 200 或空 `answers` 都以退出码 4 结束并删掉请求副本和临时回答，同名可重试；名字用原子方式认领，已有成功存档或另一个进程正在用就拒绝覆盖，并附 `--dry` 形状校验，真问前同样校验。`autopilot` 的额度路由有脚本时照其规则走，没有路由脚本的 Claude Code 环境里跳过。F007 实跑里测出并写进「已知的坑」的五件事：执行者报告的「全绿」必须由主流程重跑，新增测试必须对旧代码跑一遍确认真会失败；变异评审会临时改文件，不能和别的评审共用同一个工作目录，否则其他评审看到被反复改动的脏工作区，结论一度混乱，要串行或用 worktree、`git archive` 副本；JEV 的弱信号如实记录，不升级成放行；题面里写进「还没人看过」之类的倾向会让 JEV 偏向 hold；一个 issue 要的功能可能早已上线，动手前先核对线上和已合并 PR。
- Added the `goal-to-prod` skill, ported from the local version in the two-of-us project and generalised: once the user gives a clear goal and authorises autonomous decisions, it runs plan, build, review loop, PR, deploy, live smoke test and issue write-back end to end without interrupting the user. The core is the cross-decision rule: every point that needs a pick (plan exit, accepting or deferring a review finding, code exit, keep or roll back after deploy) is written as a neutrally worded choice question and answered independently by JEV and a fresh-context model that cannot see each other's answer. Agreement is adopted; disagreement first adds facts and re-asks under a new name; if it still splits, the more reversible option wins. A JEV probability gap under 0.2 is recorded as a weak signal and may only follow a model that gave a clear reason or fall back to the more reversible option, never be written up as "JEV approved"; re-asking the same question to get a wanted answer is forbidden. Requests and raw responses are archived by `jev-ask.sh`, and the decision table records the basis of each row. Project-specific commands and paths become `{DOCS_ROOT}`, `{CHECK}`, `{DEPLOY}`, `{SMOKE}`, `{GH_ACCOUNT_MAP}`, `{DEFAULT_GH_ACCOUNT}`, `{ROLLBACK}` and `{QUEUE_CHECK}`, explained in `SETUP.md`; `jev-ask.sh` is copied into the project, takes the key variable name and key file from the `JEV_KEY_VAR` (default `TYPESAFE_API_KEY`) and `JEV_KEY_FILE` (default `<git root>/.dev.vars`) environment variables, passes the key to curl on stdin so it never appears in argv, archives only on success (the reply goes to a temp file and is renamed once HTTP 200 and a non-empty `answers` object are confirmed; a curl failure, non-200 or empty answers exits 4 and removes the copied request and temp reply so the same name can be retried), claims the name atomically so a used name or a concurrent run is refused, and ships with a `--dry` shape check that the real call runs too. Where the `autopilot` quota router script exists its rules apply; in a Claude Code environment without the router script the step is skipped. Five pitfalls measured in the F007 dry run are recorded: an executor's "all green" claim must be re-run by the main flow and a new test must be run against the old code to prove it fails; a mutation review edits files temporarily and must not share a working directory with other reviewers, who otherwise see a repeatedly changing dirty tree and reach muddled conclusions, so run it serially or on a worktree or `git archive` copy; weak JEV signals are recorded as weak and never promoted to approval; wording such as "not yet read by the owner" in a question tilts JEV towards hold; and a requested issue may already be shipped, so check the live bundle and merged PRs before starting.

## 0.2.9

- 新增 `demo-video` skill，改编自 Damien Tanner 的同名 gist：先跟人敲定三到六幕的分镜与旁白脚本，再截图、配音、用 ffmpeg 把每张截图按对应音轨时长渲染成一幕并拼接成 MP4，让审查者看着改动跑起来而不是从 diff 里脑补。相对上游去掉了两处项目耦合，`api/.dev.vars` 的 key 路径和写死的私有 R2 桶，并把默认 TTS 从需要 API key 的 Inworld 换成 macOS 内置的 `say`，托管 TTS 降级为可选。上传成片改成必须用户明确要求才执行，理由是那等于把用户应用的录像发布到公开 URL。写入一条实测的静默失败：`say -o` 在 agent 沙箱里退出码为 0、stderr 为空，却写出一个结构合法的 4096 字节 AIFF，音频负载全零，成片除了没声音一切正常，整条流水线没有一环会抱怨；因此技能强制要求用 ffprobe 断言每个音频文件的 duration，`N/A` 或大小卡在 4096 字节就停下来改由用户在沙箱外生成。另记录相关行为：传入本机未安装的声音名会让 `say` 挂死而不是报错。视频链路本身以三幕合成音轨验证过，产出 6.05 秒的 h264/aac 1280x720 成片。
- Added the `demo-video` skill, adapted from Damien Tanner's gist of the same name: agree a three to six scene storyboard and narration script with the user first, then capture screenshots, generate voice audio, render each still for the length of its audio track with ffmpeg, and concatenate the scenes into an MP4, so a reviewer watches the change run instead of reconstructing it from a diff. Two upstream project couplings are removed, the `api/.dev.vars` key path and a hardcoded private R2 bucket, and the default TTS moves from Inworld, which needs an API key, to the macOS built-in `say`, with hosted TTS demoted to optional. Uploading the finished video now requires an explicit request, because it publishes a recording of the user's application to a public URL. One measured silent failure is documented: inside the agent sandbox `say -o` exits 0 with empty stderr while writing a structurally valid 4096-byte AIFF whose audio payload is all zeroes, so the video is correct except for being silent and no stage of the pipeline complains. The skill therefore requires an ffprobe assertion on every audio file's duration, stopping on `N/A` or a size near 4096 bytes and handing TTS back to the user outside the sandbox. A related behaviour is recorded: passing a voice name that is not installed makes `say` hang rather than error. The video chain itself was verified with three synthetic-audio scenes producing a 6.05s h264/aac 1280x720 file.

## 0.2.8

- `review` 新增 Step 5 消融实验：逐个移除改动中的元素，重跑仓库自己的检查，记录相对基线新增的失败。移除后什么都不坏的元素必须逐条给出结论，要么它不承重、删掉，要么检查漏了它存在的场景、补检查。首次实跑的改动里，十一个元素有六个移除后零失败，其中包括整个删掉路由滚动重置，因为覆盖它的断言导航到的是短页面，浏览器本来就会把滚动偏移夹回零，有没有那段代码都通过。移除后什么都不坏有三种解释而不是两种，第三种是「和别的元素互为冗余，且这份冗余是有意的」，专门堵单元素消融的盲区：两道纵深防御的守卫各自拆掉都全绿，各自被判可删，一起删就出洞。冗余必须说得出安全、容错或降级的理由才算有意，说不出就是偶然重复，留一个删一个。删除候选要凑成一组再拆一次，接受删除后重设基线，全部落定后整跑一次。另外只有全绿基线才允许判「删除」，基线里已经红的检查给不出信号，被它覆盖的元素只能记「未验证」。消融在临时 worktree 里跑，不带 `--fix` 时全程只读，三种判读只进报告不落改动。并写明两条先决条件：跑检查等于执行待审 diff 里的代码，来源不可信就跳过或进容器；以及未提交的改动不会自动进 worktree，要显式导出补丁应用过去再比对一致。测试和注释都不进删除式消融：删掉本次新增的测试不会让任何检查失败，会被误判成可删，测试要靠改坏它覆盖的生产代码来反证；注释改问「没有这句话读代码的人会误判什么」，并对照仓库自身注释密度基线。
- `review` gains Step 5, an ablation pass: remove one element of the change at a time, re-run the repo's own checks, and record which of them newly fail against a recorded baseline. An element whose removal breaks nothing gets an explicit per-element verdict, either it is not load-bearing and goes, or the checks are missing the case it exists for and a check gets added. On the first change this ran against, six of eleven elements failed nothing, including deleting the router scroll reset outright, because the assertion covering it navigated to a short page where the browser clamps the scroll offset to zero on its own and it passed either way. Breaking nothing has three readings rather than two; the third is that the element is deliberately redundant with another, which closes the blind spot of single-element ablation: two defence-in-depth guards each pass when removed alone, each is marked deletable, and removing both opens a hole. Redundancy counts as deliberate only when a safety, fault-tolerance, or fallback reason can be stated; otherwise it is accidental duplication and one copy goes. Deletion candidates are ablated together as a group, the baseline is reset after each accepted deletion, and the full checks run once over the accumulated result. A "delete" verdict requires a green baseline, since a check that is already failing gives no signal and anything covered only by it can only be recorded as unverified. The ablation runs in a throwaway worktree, and without `--fix` the whole step stays read-only: the three verdicts reach the report and never the working tree. Two preconditions are stated: running the checks executes the diff's own code, so an untrusted diff is skipped or containerised rather than run locally; and uncommitted work does not follow a worktree, so the full change is exported as a patch, applied to the copy, and verified against the review input first. Tests and comments are both excluded from deletion-style ablation: removing a test the change just added fails nothing, because a test catches future regressions rather than failing correct code, so it would be misread as deletable; a test is instead proved load-bearing by breaking the production code it covers. Comments get the different question of what a reader would get wrong without them, measured against the repo's own comment density.

## 0.2.7

- `review` 的 DeepSeek 复核改用 `dsh --profile headless` 调用，不再经过 OpenCode/OpenRouter。沙箱从单文件读取白名单变为 `DSH_PERMISSION_MODE=read-only`（工作目录整体粒度、写入与执行被拒绝），已用真实调用验证。安全契约标记升级到 V3。
- `review`'s DeepSeek pass now calls `dsh --profile headless` directly instead of going through OpenCode/OpenRouter. The sandbox moved from a single-file read allowlist to `DSH_PERMISSION_MODE=read-only` (workspace-directory granularity; writes and exec are denied), verified against the real binary. Security contract marker bumped to V3.
- 新增 `dsh-deepseek-delegate` skill，取代已移除的 `opencode-deepseek-delegate`：同样的纯文本委派契约（无项目文件访问、显式外发授权、失败关闭），改用 `dsh` 而非 `opencode`，并支持 `--prompt-file` 传入大段任务文本。
- Added the `dsh-deepseek-delegate` skill, replacing the removed `opencode-deepseek-delegate`: same pure-text delegation contract (no project file access, explicit outbound consent, fail-closed), built on `dsh` instead of `opencode`, with `--prompt-file` support for longer task text.

## 0.2.6

- `feat` 现在要求每个 Batch 记录 reasoning effort、工程依据、Spark 资格、依赖、文件所有权和运行时资源。`autopilot` 使用最新 `/usage` 快照和实时模型目录执行 Terra、Luna、Spark 配额门禁。
- 新增默认拒绝的纯函数路由器与 27 项行为测试。CLI 可信时间和独立额度周期阻止旧快照与旧授权重放，真实 Git 根目录、common directory、分支和路径身份校验阻止跨仓与别名绕过。唯一 `dispatch_wave()` 入口只为 `ALLOW` 决策生成原生 Agent 启动清单，混合 Spark 波次保持部分阻塞语义。
- `feat` now records reasoning effort, engineering evidence, Spark eligibility, dependencies, file ownership, and runtime resources for every Batch. `autopilot` applies Terra, Luna, and Spark quota gates from a fresh `/usage` snapshot and live model catalog.
- Added a default-deny pure router with 27 behavior tests. CLI-generated trusted time and an independent quota-period argument block replay of old snapshots and approvals. Real Git root, common-directory, branch, and path identity checks block cross-repository and alias bypasses. The sole `dispatch_wave()` entry generates native Agent launch manifests only for `ALLOW` decisions while preserving partial-block semantics for mixed Spark waves.

## 0.2.5

- `feat` 的 Phase 3.1 现明确绑定 Codex 原生结构化提问，每轮只处理一个决策组，提供 2 到 3 个互斥选项、推荐项与理由，等待回复后将结论记录到 DD。流程图也展示了原生提问、等待回答和写入 DD 的路径。
- Phase 3.1 of `feat` now explicitly binds to Codex native structured questions: each round handles one decision group with 2 to 3 mutually exclusive choices, a recommendation, and rationale, then waits and records the conclusion in the DD. The flowchart now shows the native question, answer wait, and DD-recording path.

## 0.2.4

- 英文与中文双语覆盖到 `mermaid-skill`，并补充 `README` 目录项与 `SKILL.md`、各 `reference/*.md` 的中英文用途说明，明确本地 `mmdc` 优先、Kroki 需用户授权。
- Updated the `mermaid-skill` documentation set with bilingual coverage for the catalog entry, skill prompt file, and reference guides, with explicit local-first `mmdc` priority and user-approved Kroki usage.

## 0.2.3

- Git tree 发布校验在带 `--base` 时不读取工作树，并对必填 metadata 和每个 skill 目录的 `SKILL.md` 完整校验。

## 0.2.2

- 发布门禁改为直接验证待推送 Git tree 的 metadata、skills 和脚本权限，避免工作树内容掩盖提交内容。
- 版本号采用严格的稳定 SemVer 格式，拒绝带前导零的版本段。
- 修正 review workflow 对 DeepSeek 独立复核的条件说明。

## 0.2.1

- 修复三个核心 workflow skill 的 YAML frontmatter，确保 Claude 严格校验和 runtime metadata 加载通过。
- 主分支推送时校验发布内容已同步提高双端版本，并要求 changelog 存在对应版本。

## 0.2.0

- 同一 `hank-dev` 插件目录同时支持 Claude Code 与 Codex 官方 metadata。
- 新增 Codex Git marketplace 入口和双分发一致性校验。
- 文档明确 marketplace refresh 与已安装 plugin artifact 更新是两个独立步骤。
