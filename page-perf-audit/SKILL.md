# /page-perf-audit — 页面性能审计与优化

对指定页面进行全链路性能分析，覆盖该页面加载时涉及的**所有组件**（含 Layout、导航、侧面板等共享组件），输出可执行的优化方案。

---

## 触发方式

用户说出以下任一：
- `/page-perf-audit`、"优化 XX 页面"、"XX 页面性能审计"、"分析 XX 页面加载速度"
- 需提供目标页面路由（如 `/markets`、`/swap`、`/trade`）

---

## 心智模型

所有优化基于一条核心链路——**用户从点击到看到内容经历了什么**：

```
请求发出 → 服务器处理（TTFB）
  → HTML 到达 → 解析 HTML + 下载阻塞资源（CSS/字体）
    → 首次渲染（FCP — 用户第一眼看到东西）
      → JS 下载 → React hydration（TTI — 页面可交互）
        → 图片/异步数据加载完成（LCP — 最大内容渲染）
```

**审计就是沿这条链路逐段找瓶颈，对每个瓶颈评估 ROI，按优先级输出方案。**

---

## Phase 0: 确定审计范围

### 0.1 识别完整组件树

不只审计页面路由文件本身，而是**用户视觉上看到的一切**：

```bash
# 从路由文件向上追溯所有 Layout
app/[locale]/layout.tsx          # 根布局（TopNav、MobileTabBar、Providers）
app/[locale]/{page}/layout.tsx   # 页面级布局（如 Markets 的 BetSlip 面板）
app/[locale]/{page}/page.tsx     # 页面本身
```

列出组件清单时，按视觉区域划分：

| 区域 | 示例 |
|------|------|
| 全局导航 | TopNav, MobileTabBar |
| 全局 Provider | Providers (Web3, Query, i18n) |
| 页面级布局 | 侧面板、右栏、浮窗按钮 |
| 页面核心内容 | 列表、卡片、图表、表单 |
| 弹窗/抽屉 | Modal、Sheet、Settings |

### 0.2 读取所有相关文件

**必须实际读取代码**，不能凭猜测分析。按以下顺序读取：

1. 页面路由文件 (`page.tsx`)
2. 页面 Layout 文件 (`layout.tsx`)
3. 根 Layout (`app/[locale]/layout.tsx`)
4. `providers.tsx`
5. 页面内引用的所有组件（递归追踪 import）
6. 相关 hooks、stores、API 函数

---

## Phase 1: 五维度分析

沿着加载链路，从五个维度逐一审查：

### 维度一：服务器返回了什么？（TTFB → FCP）

**目标**：HTML 到达时用户能看到内容吗？

**检查清单**：

- [ ] **SSR 输出验证**：页面是 Server Component 还是 Client Component？
  - `'use client'` 在 page.tsx 顶部 → SSR 不渲染页面内容
  - async Server Component + 数据预取 → SSR 输出真实数据

- [ ] **数据获取位置**：数据在哪里获取？
  - 服务端 prefetch（`prefetchQuery` / `fetch` with `revalidate`）→ 好
  - 客户端 useQuery / useEffect → 必须等 JS 加载后才开始获取 → 瀑布流

- [ ] **Provider 阻塞**：是否有 `mounted` 守卫、`typeof window` 检查等导致 SSR 输出为空？

- [ ] **缓存策略**：Route Handler 或 fetch 是否设置了合理的 `Cache-Control` / `revalidate`？

**判断标准**：
```
能 SSR → 应该 SSR（数据不依赖用户状态的页面）
不能 SSR → 确认原因是否合理（钱包状态、用户私有数据）
```

### 维度二：浏览器下载了多少 JS？（Bundle 体积）

**目标**：首屏关键路径上是否加载了不需要的 JS？

**检查清单**：

- [ ] **构建分析**：`next build` 输出中，该路由的 First Load JS 是多少？
  - < 200KB → 良好
  - 200-300KB → 可优化
  - \> 300KB → 需重点关注

- [ ] **未使用依赖**：`package.json` 中有没有声明了但代码中 0 处 import 的依赖？
  - `grep -r "from 'xxx'" src/` 搜索确认

- [ ] **可延迟加载的组件**：判断标准——**这个组件是首屏渲染的关键路径吗？**
  - 弹窗/Modal → 用户主动触发才出现 → `dynamic({ ssr: false })`
  - 设置面板 → 条件渲染 → `dynamic({ ssr: false })`
  - 侧面板（如 BetSlip）→ 首屏显示"空状态" → 可延迟
  - 图表组件 → 大体积库 → 必须 `dynamic({ ssr: false })`

- [ ] **大体积第三方库**：
  - 图表库（lightweight-charts ~90KB, recharts ~200KB）
  - 动画库（framer-motion ~150KB）
  - Web3 库（wagmi+viem ~80KB, rainbowkit ~40KB）
  - 图标库（phosphor-icons, lucide-react）
  - 是否在首屏就需要？不需要就延迟加载

### 维度三：渲染过程中有没有浪费？（运行时重渲染）

**目标**：React 是否在做无用功？

**memo 判断流程**：
```
1. 被列表渲染吗？（× N 实例）
   → 是 → 高概率需要 memo

2. 父组件会频繁重渲染吗？（轮询、WebSocket 推送、全局状态变化）
   → 是 → 高概率需要 memo

3. 组件渲染成本高吗？（DOM 节点多？子组件多？）
   → 是 → 更需要 memo

4. Props 经常变化吗？
   → 每次都变 → memo 无用，不加
   → 大部分时候不变 → 加 memo 有收益
```

**检查清单**：

- [ ] **列表组件是否有 memo**：逐个检查列表项组件（MatchRow、TokenRow 等）
- [ ] **Zustand 选择器粒度**：是否整个 store 订阅（`const {...} = useStore()`）还是精确选择器（`useStore(s => s.field)`）
- [ ] **useMemo / useCallback 合理性**：衍生数据计算是否有缓存？事件回调是否稳定？
- [ ] **Context 传播范围**：Provider value 变化时，是否导致无关组件重渲染？

### 维度四：资源加载策略（图片、字体、CSS）

**目标**：非 JS 资源是否高效加载？

**图片检查**：
- [ ] 是否使用 `next/image` 而非原生 `<img>`？
  - `next/image` 自动：WebP/AVIF 转换、lazy loading、响应式 srcset、CDN 缓存
  - 首屏关键图片加 `priority`（如 hero banner、logo）
  - 列表中的图片用默认 lazy loading

- [ ] `next.config` 的 `remotePatterns` 是否配置了所有外部图片域名？

**字体检查**：
- [ ] 是否有 Google Fonts `@import` 或 `<link>` 外部请求？
  - 有 → 用 `next/font/google` 替代（构建时下载，同域分发）
- [ ] 本地字体是否用 woff2 格式 + `font-display: swap`？

**CSS 检查**：
- [ ] 是否有大体积的第三方 CSS（如 RainbowKit styles）在首屏加载？
- [ ] Tailwind purge/content 配置是否正确（不打包无用样式）？

### 维度五：用户体验感知（骨架屏、过渡、CLS）

**目标**：加载过程中用户看到什么？

- [ ] **loading.tsx 是否存在**：路由切换时是否有骨架屏而非白屏？
- [ ] **骨架屏匹配度**：骨架屏布局是否与真实内容一致（避免 CLS）？
- [ ] **数据加载态**：isLoading 时显示 Skeleton 而非 Spinner？
- [ ] **图片占位**：是否预留宽高避免加载后内容跳动？

---

## Phase 2: 生成优化方案

### 2.1 汇总发现

按维度整理发现项，每项标注：

```
[维度] 发现描述
  影响指标: FCP / LCP / TTI / Bundle / CLS
  严重程度: Critical / Major / Minor
  修复方案: 具体操作
  工作量: 时间估算
  收益: 性能指标预期变化
```

### 2.2 ROI 排序

用 2×2 矩阵排优先级：

```
              收益高               收益低
           ┌─────────────────┬─────────────────┐
工作量小   │  S 级（立即做）    │ 随手做           │
           │ 如: 删未用依赖    │ 如: 加 memo      │
           │     移除阻塞守卫  │     加 loading   │
           ├─────────────────┼─────────────────┤
工作量大   │  A 级（规划做）    │ 不做             │
           │ 如: SSR 改造     │ 如: 深度组件拆分   │
           │     图片全局迁移  │                  │
           └─────────────────┴─────────────────┘
```

### 2.3 输出格式

生成 ENH 文档（`.progress/dev-docs/ENH/ENH-NNN-{page}-perf.md`），包含：

1. **现状基线**（测量数据）
2. **发现清单**（按维度分类）
3. **优化方案**（按 ROI 排序的 Batch 列表）
4. **预期效果**（优化后指标预估）
5. **不做什么**（明确边界）

---

## Phase 3: 基线测量（可选，用户要求时执行）

如果用户要求量化数据，执行以下测量：

### 3.1 SSR 输出验证

```bash
# 1. 生产构建
pnpm build

# 2. 启动生产服务器
PORT=3999 pnpm start

# 3. 获取 access cookie（如有邀请码保护）
curl -c cookies.txt -X POST http://localhost:3999/api/auth/verify \
  -H "Content-Type: application/json" -d '{"code":"..."}'

# 4. 检查 HTML 内容
curl -b cookies.txt -o page.html http://localhost:3999/{route}

# 5. 分析 HTML：去掉 <script> 后还有多少可见内容？
python3 -c "
import re
html = open('page.html').read()
body = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL).group(1)
no_scripts = re.sub(r'<script[^>]*>.*?</script>', '', body, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', ' ', no_scripts).strip()
print(f'Body (no scripts): {len(no_scripts)} bytes')
print(f'Text content: {len(text)} chars')
"
```

### 3.2 浏览器端 Web Vitals

使用 Playwright 导航到页面，通过 Performance API 采集：

```javascript
// 在 browser_evaluate 中执行
const nav = performance.getEntriesByType('navigation')[0];
const fcp = performance.getEntriesByType('paint')
  .find(p => p.name === 'first-contentful-paint');
return {
  ttfb: nav.responseStart - nav.startTime,
  fcp: fcp?.startTime,
  domComplete: nav.domComplete - nav.startTime,
  transferSize: nav.transferSize,
  decodedBodySize: nav.decodedBodySize,
};
```

### 3.3 Bundle 体积

从 `next build` 输出中提取目标路由的 First Load JS 数值。

### 3.4 TTFB 多轮测试

```bash
for i in 1 2 3 4 5; do
  curl -b cookies.txt -o /dev/null -w "R$i: %{time_starttransfer}s\n" \
    http://localhost:3999/{route}
done
```

---

## 常见优化模式速查

### 模式 A: Client → Server Component + prefetchQuery

**适用场景**: 页面数据不依赖用户状态（公开的列表、详情页）

```tsx
// Before: page.tsx ('use client' + useQuery)
// After:
export default async function Page({ params }) {
  const qc = new QueryClient();
  await qc.prefetchQuery({ queryKey, queryFn });
  return (
    <HydrationBoundary state={dehydrate(qc)}>
      <PageClient />  // 'use client'，useQuery 命中预取缓存
    </HydrationBoundary>
  );
}
```

### 模式 B: 非首屏组件动态导入

**适用场景**: 弹窗、侧面板、设置面板、图表

```tsx
const Modal = dynamic(() => import('./Modal'), { ssr: false });
const Chart = dynamic(() => import('./Chart'), {
  ssr: false,
  loading: () => <ChartSkeleton />
});
```

### 模式 C: 列表项 memo 包裹

**适用场景**: 被 × N 渲染的列表项组件，父组件因轮询频繁更新

```tsx
export default memo(function ListItem({ item, filter }) {
  // ...
}, (prev, next) => prev.item.id === next.item.id && prev.filter === next.filter);
```

### 模式 D: next/image 替换 img

**适用场景**: 所有用户可见的 `<img>` 标签

```tsx
// Before
<img src={url} className="w-5 h-5" />

// After
<Image src={url} width={20} height={20} className="rounded-full" />
// 首屏关键图片加 priority
```

### 模式 E: next/font 替换 Google Fonts

**适用场景**: globals.css 中的 `@import url('https://fonts.googleapis.com/...')`

```tsx
// app/fonts.ts
import { Orbitron } from 'next/font/google';
export const orbitron = Orbitron({ subsets: ['latin'], variable: '--font-orbitron' });
```

### 模式 F: 路由级骨架屏

**适用场景**: 任何使用服务端数据预取的页面

```tsx
// app/[locale]/{page}/loading.tsx
export default function Loading() {
  return <PageSkeleton />;  // 复用已有的 Skeleton 组件
}
```

---

## 输出交付物清单

审计完成后，交付以下内容：

1. **研究文档** → `.progress/dev-docs/research/RES-NNN-{page}-perf-audit.md`
   - 组件清单 + 五维度分析 + 发现项 + 基线数据

2. **ENH 文档** → `.progress/dev-docs/ENH/ENH-NNN-{page}-perf.md`
   - Batch 化的实施计划 + 预期效果

3. **基线截图**（若有测量）→ `.progress/dev-docs/research/`

---

## 不做什么

- 不做无数据支撑的"猜测性优化"——必须先测量再优化
- 不为了用技术而优化——SSR 不适合纯交互页面（如 Swap），不强推
- 不做收益 < 50ms 且工作量 > 1 天的优化项
- 不在审计阶段直接修改代码——审计输出方案，开发由 autopilot 或手动执行
- 不重复已有的 enh-todo 条目——发现已有跟踪项时引用而非新建
