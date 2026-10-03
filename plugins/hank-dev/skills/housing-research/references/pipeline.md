# 流水线细节

数据目录建议：`<案件>/data/`（脚本里的 `D`），照片 `candidates/<地址>-<房源号>/photos/`。所有取数脚本都写成可续跑：一套一个 JSON，已存在就跳过。

## 1 取数（浏览器，单驱动）

搜索页，限定区域、户型、价格：

```
https://www.realestate.com.au/rent/between-0-1000-in-<区1>%3B+<区2>.../list-<页>?maxBeds=2&minBeds=1&keywords=furnished&includeSurrounding=false
```

- 区写成 `south+yarra,+vic+3141`，多个区用 `%3B+` 连接。`includeSurrounding=false` 才不会混入周边区（否则 2118 套，关掉后 63 套）。
- `keywords=furnished` 会把 `unfurnished` 也命中，所以详情页必须再判。`furnished=true` 参数无效。
- 链接正则：`/property-[a-z+-]+-vic-[a-z+]+-\d+$`。推广位会混入 CBD、Carlton 的房源，靠离现住地址的距离过滤。
- 每页 25 套，翻页间隔 3 到 6 秒。

详情页读取字段：标题（地址、类型）、`$N per week`、`Bond $N`、`Available ...`、卧室卫浴车位（取第一个含 `bedroom` 的 `aria-label`）、`Rental information` 到 `Bedrooms & bathrooms` 之间的文字、`Property features`、`Property highlights` 到 `Property features` 之间的描述、`inspections` 段落（看房时间）、`Building size`、nbn 类型。图片清单不要点界面，读页面内嵌的 `templatedUrl`（见浏览器 skill 的踩坑表）。

地址被隐藏或描述为空的页面单独标记，重读一次；仍然空就剔除并在报告里说明。

## 2 文字筛选

代码判断：价格、卧室数（studio 即 0 房，剔除）、离现住地址（Nominatim 地理编码，超过约 2.2 km 剔除）。Jev 判断：是否带实际家具、地板文字。地理编码 1.1 秒一次，用缓存。

## 3 楼盘补查（5 个并行代理，只用网页）

按楼分组（每组约 10 栋）。让每个代理输出：楼名、开发商、竣工年份（附来源，标是否一手）、类型、联合办公 / gym / 泳池各 yes、no、unknown 并附原文出处、其他设施、典型地板、置信度。规则：一手来源（开发商或楼盘官网）优先于聚合站；Domain 对抓取返回 403，别指望；不知道就写 unknown。同时让一个代理专查用户指定的几栋楼，另一个查酒店式公寓运营商官网（价格、最短租期、账单）。

## 4 照片核验（并行看图代理）

1. 下载图库：`curl -A "Mozilla/5.0" https://i2.au.reastatic.net/800x600/<hash>/image.jpg`，返回 302 说明不是 jpg（户型图是 png），改 `.png`。用 `bash -c` 跑循环。
2. 每套拼一张编号联系表（PIL，6 列，缩略 320x240，左上角黑底白字编号）。
3. 7 个代理各看约 9 套：客厅和卧室地板（carpet、timber、timber_look、tile、mixed、unknown）、各房间代表照片编号、垃圾图（中介广告、二维码、户型图）、是否别的单元的图。缩略图看不清时必须打开原图。
4. 另 7 个代理逐项记录家具：床、沙发、餐桌、书桌、电视各 yes、no、unknown 并附照片编号，是否布置图或别的单元，读户型图上印的面积。「实际家具」不含洗碗机、冰箱、内嵌衣柜。
5. 代理输出会有矛盾和不确定，保留 confidence 和 evidence 字段，进卡片。

## 5 Google 评分和位置

- Google Maps：`https://www.google.com/maps/search/<楼名 地址>?hl=en`。只接受结果名称与楼名匹配、类别为住宅类的结果；没有楼名的老楼搜地址只会落到楼里的商铺，记「无楼级评分」。页面空白是没渲染，不是没评分。评论数普遍很少，只能当弱证据。
- 位置：Nominatim 按名称定位火车站和超市，步行时间 = 直线距离 x 1.3 / 80 米每分钟，写明是估算（误差约 200 米，街道级定位会把同街的两栋定到同一点）。Overpass 常超时，不要依赖。

## 7 复核挂牌

交付当天对入围前 30 名逐个打开链接：标题含 `Real Estate, Property and Homes For Sale`（跳回首页）或读不到价格就是已下架，剔除并在报告里记录。2026-10-02 当天就有 2 套下架。

## 8 目录与索引

案件目录里放：报告、`data/`、`scripts/`、`candidates/`、README（材料清单、风险）。领域 `INDEX.md` 和顶层索引同步一行。
