# 用 Jev 打分和决策

Jev 是 TypeSafe 的 System One 模型：给它状态和类型化问题，返回带概率的 Noul（是否）、Score（有序评分）、Choice（选一）。代码拥有流程，Jev 只提供语义判断。先读最新文档：`https://docs.typesafe.ai/llms.txt`，composite scoring 模式见 `https://docs.typesafe.ai/patterns/composite-scoring.md`。

## 调用

- `POST https://api.typesafe.ai/v1/systemone`，`Authorization: Bearer $TYPESAFE_API_KEY`（key 在环境变量里，不要打印）。body：`state`（任意 JSON）、`model: "jev-latest"`、`questions`（id 到问题的字典，同一状态下的问题放同一次请求，并行评估）。
- Noul：`instructions` 加 `criteria: {true, false}`，返回 `noul` 概率。没写 criteria 时判断会漂（一个明显带家具的单元只给 0.8）。
- Score：`criteria` 是 2 到 10 个有序等级的数组，每级写具体情形，返回概率加权的 `score` 和 `confidence`。
- Choice：`criteria` 是 选项到描述 的字典，返回 `choice` 和 `probabilities`。
- 429 和 529 要指数退避。一次请求约 2 到 3 秒，6 线程并发即可。参考实现：`scripts/jev.py`。

## 状态（每套房源一个对象）

`listing`（地址、租金、卧室、Bond、面积、家具文字、描述前 1800 字）、`building`（名称、竣工年份与可信度、类型、联合办公 / gym / 泳池各自的答案和出处、其他设施）、`location`（到车站和超市的步行分钟）、`google`（评分、评论数，空值就是 null）、`floors`（客厅、卧室、依据、置信度）、`photo_review`（照片里实际看到的家具、是否疑似布置、备注）。

## 问题与权重

权重合计 100，数值是助手设定的假设，要告诉用户：联合办公 20、Google 评分 15、新旧 15、gym 10、泳池 10、通勤 8、购物 7、地板 5、家具 5、性价比 5。每个维度是 5 级 Score，等级写具体情形和数字锚点（例如「到车站 3 分钟以内」「竣工 2019 年或之后」「评分 4.6 以上且评论 50 条以上」）。另有：

- 是否酒店式（Noul）。
- 家具：`furniture_level`（Score，电器和内嵌柜不算家具）加 `has_bed`、`has_sofa`、`has_dining_table`、`has_desk`（Noul）。
- 决策（Choice）：`must_view`、`worth_viewing`、`backup`、`reject`。

## 决策问题的教训

- 指令要把**硬条件和扣分项分开写**，否则 Jev 会把软条件当淘汰理由（第一版把「只有卧室是地毯」判成 reject，全市场一半房源被判淘汰）。
- 档位要写成可检验的条件（如 must_view：2012 年后建成、至少一项设施有一手确认、实际家具、无硬伤）；写得太宽，几乎全是「值得看」，没有区分度。
- 「未知是待核实，不是淘汰理由」要写进指令。

## 未知信息

Score 的 0 级定义为「没有或未知」，所以有证据的楼盘占便宜。因此每套给两个分：**保守分**（未知按最低）和**中性分**（未知的联合办公、gym、泳池、评分、年份按 2 分）。排名按保守分，中性分用来识别「靠未知项撑起来的」房源。原始答案一律存盘，改权重只重算加权，不重新调用 Jev。

## 地毯

地毯在代码里扣分：客厅或卧室满铺地毯每间 10 分，混合 5 分，总分不低于 0，同时 Jev 的地板维度也反映它。可移除的小块地毯不算地毯（代理判断地板材质时就按底下的硬地板）。

## 规则变化时的局部重问

用户纠正规则后，只重问受影响的问题，把新答案并进已有结果：

```python
q = {k: Q[k] for k in ['furniture_level', 'has_bed', 'has_sofa', 'has_dining_table', 'has_desk', 'decision']}
item['jev'].update(parse(ask(build_state(item), q)))
```

同一状态重问同一问题分数会有约 0.1 的波动，所以不要为小改动全量重跑。局部重问的完整例子在作者案件归档的 `run_update.py` 里，不随插件发布。

## 硬条件

在代码里执行，理由写进 `excluded` 列表并出现在报告里：现住楼、没有实际家具、挂牌已下架。用户指定的对照房源（被硬条件排除的）仍然打分、单列展示，不要悄悄丢掉。
