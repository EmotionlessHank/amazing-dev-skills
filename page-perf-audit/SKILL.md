# /page-perf-audit — Page Performance Audit and Optimization

Performs a full-stack performance analysis of a specified page, covering **every component** involved in loading that page (including Layout, navigation, side panels, and other shared components). Outputs an actionable optimization plan.

---

## Trigger Conditions

Any of the following:
- `/page-perf-audit`, "optimize XX page", "XX page performance audit", "analyze XX page load speed"
- Requires the target page route (e.g. `/markets`, `/swap`, `/trade`)

---

## Mental Model

All optimizations are anchored to a single core path — **what the user experiences between clicking and seeing content**:

```
Request sent → Server processing (TTFB)
  → HTML arrives → Parse HTML + download blocking resources (CSS/fonts)
    → First render (FCP — user sees something)
      → JS download → React hydration (TTI — page becomes interactive)
        → Images/async data loaded (LCP — largest content rendered)
```

**Auditing means walking this path segment by segment to find bottlenecks, evaluating ROI for each bottleneck, and outputting a prioritized plan.**

---

## Phase 0: Define Audit Scope

### 0.1 Identify the Full Component Tree

Audit not just the page route file, but **everything the user visually sees**:

```bash
# Trace all layouts from the route file upward
app/[locale]/layout.tsx          # Root layout (TopNav, MobileTabBar, Providers)
app/[locale]/{page}/layout.tsx   # Page-level layout (e.g. BetSlip panel for Markets)
app/[locale]/{page}/page.tsx     # The page itself
```

When listing components, organize by visual region:

| Region | Examples |
|--------|---------|
| Global navigation | TopNav, MobileTabBar |
| Global providers | Providers (Web3, Query, i18n) |
| Page-level layout | Side panels, right column, floating buttons |
| Page core content | Lists, cards, charts, forms |
| Modals / drawers | Modal, Sheet, Settings |

### 0.2 Read All Relevant Files

**Must actually read the code** — no analysis based on assumptions. Read in this order:

1. Page route file (`page.tsx`)
2. Page layout file (`layout.tsx`)
3. Root layout (`app/[locale]/layout.tsx`)
4. `providers.tsx`
5. All components imported by the page (recursively trace imports)
6. Related hooks, stores, and API functions

---

## Phase 1: Five-Dimension Analysis

Walk the loading path and audit across five dimensions:

### Dimension 1: What Does the Server Return? (TTFB → FCP)

**Goal**: Does the user see content when the HTML arrives?

**Checklist**:

- [ ] **SSR output verification**: Is the page a Server Component or Client Component?
  - `'use client'` at the top of page.tsx → SSR does not render page content
  - async Server Component + data prefetch → SSR outputs real data

- [ ] **Data fetching location**: Where is data fetched?
  - Server-side prefetch (`prefetchQuery` / `fetch` with `revalidate`) → good
  - Client-side `useQuery` / `useEffect` → must wait for JS to load before fetching → waterfall

- [ ] **Provider blocking**: Are there `mounted` guards, `typeof window` checks, or similar that cause SSR output to be empty?

- [ ] **Cache strategy**: Does the Route Handler or fetch have a reasonable `Cache-Control` / `revalidate`?

**Decision rule**:
```
Can SSR → should SSR (pages where data does not depend on user state)
Cannot SSR → confirm whether the reason is justified (wallet state, user-private data)
```

### Dimension 2: How Much JS Does the Browser Download? (Bundle Size)

**Goal**: Is unnecessary JS loaded on the critical path of the first screen?

**Checklist**:

- [ ] **Build analysis**: What is the First Load JS for this route in `next build` output?
  - < 200 KB → good
  - 200–300 KB → can be optimized
  - \> 300 KB → requires focused attention

- [ ] **Unused dependencies**: Are there any packages declared in `package.json` with 0 imports in the codebase?
  - Confirm with `grep -r "from 'xxx'" src/`

- [ ] **Lazy-loadable components**: Decision rule — **is this component on the critical path for the first screen?**
  - Modals → only appear on user action → `dynamic({ ssr: false })`
  - Settings panels → conditionally rendered → `dynamic({ ssr: false })`
  - Side panels (e.g. BetSlip) → first screen shows "empty state" → can be deferred
  - Chart components → large library → must use `dynamic({ ssr: false })`

- [ ] **Large third-party libraries**:
  - Chart libraries (lightweight-charts ~90 KB, recharts ~200 KB)
  - Animation libraries (framer-motion ~150 KB)
  - Web3 libraries (wagmi+viem ~80 KB, rainbowkit ~40 KB)
  - Icon libraries (phosphor-icons, lucide-react)
  - Is each needed on the first screen? If not, defer loading.

### Dimension 3: Is There Wasted Work During Rendering? (Runtime Re-renders)

**Goal**: Is React doing unnecessary work?

**memo decision flow**:
```
1. Is it rendered in a list? (× N instances)
   → Yes → high probability of needing memo

2. Does the parent component re-render frequently? (polling, WebSocket push, global state changes)
   → Yes → high probability of needing memo

3. Is this component expensive to render? (many DOM nodes? many child components?)
   → Yes → even more reason for memo

4. Do props change frequently?
   → Changes every time → memo is useless, don't add it
   → Mostly stable → memo provides benefit
```

**Checklist**:

- [ ] **List components have memo**: Check each list item component (MatchRow, TokenRow, etc.)
- [ ] **Zustand selector granularity**: Entire store subscribed (`const {...} = useStore()`) vs precise selector (`useStore(s => s.field)`)
- [ ] **useMemo / useCallback correctness**: Are derived data computations cached? Are event callbacks stable?
- [ ] **Context propagation scope**: Does a Provider value change trigger re-renders in unrelated components?

### Dimension 4: Resource Loading Strategy (Images, Fonts, CSS)

**Goal**: Are non-JS resources loading efficiently?

**Image checks**:
- [ ] Using `next/image` instead of native `<img>`?
  - `next/image` automatically handles: WebP/AVIF conversion, lazy loading, responsive srcset, CDN caching
  - Add `priority` to critical first-screen images (e.g. hero banner, logo)
  - Default lazy loading for images in lists

- [ ] Does `next.config` `remotePatterns` include all external image domains?

**Font checks**:
- [ ] Any Google Fonts `@import` or external `<link>` requests?
  - Yes → replace with `next/font/google` (downloaded at build time, served from same domain)
- [ ] Are local fonts using woff2 format + `font-display: swap`?

**CSS checks**:
- [ ] Any large third-party CSS (e.g. RainbowKit styles) loaded on the first screen?
- [ ] Is Tailwind `purge`/`content` configured correctly (unused styles excluded from bundle)?

### Dimension 5: Perceived User Experience (Skeletons, Transitions, CLS)

**Goal**: What does the user see during loading?

- [ ] **loading.tsx exists**: Is there a skeleton screen rather than a blank page during route transitions?
- [ ] **Skeleton fidelity**: Does the skeleton layout match the actual content (to avoid CLS)?
- [ ] **Data loading state**: Showing Skeleton rather than Spinner during `isLoading`?
- [ ] **Image placeholders**: Are width and height reserved to prevent layout shift after load?

---

## Phase 2: Generate Optimization Plan

### 2.1 Summarize Findings

Organize findings by dimension. For each item, include:

```
[Dimension] Finding description
  Affected metric: FCP / LCP / TTI / Bundle / CLS
  Severity: Critical / Major / Minor
  Fix: Specific action
  Effort: Time estimate
  Benefit: Expected performance metric change
```

### 2.2 ROI Prioritization

Use a 2×2 matrix to prioritize:

```
              High benefit         Low benefit
           ┌──────────────────┬──────────────────┐
Low effort │  S-tier (do now)  │ Do if convenient  │
           │ e.g. remove unused│ e.g. add memo     │
           │     deps          │     add loading   │
           │     remove guards │                   │
           ├──────────────────┼──────────────────┤
High effort│  A-tier (plan)    │ Skip              │
           │ e.g. SSR refactor │ e.g. deep         │
           │     image migration│    component      │
           │                  │    splitting       │
           └──────────────────┴──────────────────┘
```

### 2.3 Output Format

Generate an ENH document (`.progress/dev-docs/ENH/ENH-NNN-{page}-perf.md`) containing:

1. **Current baseline** (measured data)
2. **Findings inventory** (organized by dimension)
3. **Optimization plan** (batch list sorted by ROI)
4. **Expected impact** (projected metrics after optimization)
5. **What we will NOT do** (explicit scope boundaries)

---

## Phase 3: Baseline Measurement (Optional — run when user requests quantitative data)

### 3.1 SSR Output Verification

```bash
# 1. Production build
pnpm build

# 2. Start production server
PORT=3999 pnpm start

# 3. Obtain access cookie (if protected by invite code)
curl -c cookies.txt -X POST http://localhost:3999/api/auth/verify \
  -H "Content-Type: application/json" -d '{"code":"..."}'

# 4. Fetch HTML
curl -b cookies.txt -o page.html http://localhost:3999/{route}

# 5. Analyze HTML: how much visible content remains after removing <script> tags?
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

### 3.2 Browser Web Vitals

Navigate to the page with Playwright and collect via the Performance API:

```javascript
// Execute inside browser_evaluate
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

### 3.3 Bundle Size

Extract the First Load JS value for the target route from `next build` output.

### 3.4 TTFB Multi-Run Test

```bash
for i in 1 2 3 4 5; do
  curl -b cookies.txt -o /dev/null -w "R$i: %{time_starttransfer}s\n" \
    http://localhost:3999/{route}
done
```

---

## Common Optimization Patterns

### Pattern A: Client → Server Component + prefetchQuery

**Use when**: Page data does not depend on user state (public lists, detail pages)

```tsx
// Before: page.tsx ('use client' + useQuery)
// After:
export default async function Page({ params }) {
  const qc = new QueryClient();
  await qc.prefetchQuery({ queryKey, queryFn });
  return (
    <HydrationBoundary state={dehydrate(qc)}>
      <PageClient />  // 'use client', useQuery hits prefetched cache
    </HydrationBoundary>
  );
}
```

### Pattern B: Dynamic Import for Non-First-Screen Components

**Use when**: Modals, side panels, settings panels, charts

```tsx
const Modal = dynamic(() => import('./Modal'), { ssr: false });
const Chart = dynamic(() => import('./Chart'), {
  ssr: false,
  loading: () => <ChartSkeleton />
});
```

### Pattern C: memo Wrapping for List Items

**Use when**: List item components rendered × N times where the parent re-renders frequently due to polling

```tsx
export default memo(function ListItem({ item, filter }) {
  // ...
}, (prev, next) => prev.item.id === next.item.id && prev.filter === next.filter);
```

### Pattern D: Replace img with next/image

**Use when**: All user-visible `<img>` tags

```tsx
// Before
<img src={url} className="w-5 h-5" />

// After
<Image src={url} width={20} height={20} className="rounded-full" />
// Add priority for critical first-screen images
```

### Pattern E: Replace Google Fonts with next/font

**Use when**: `@import url('https://fonts.googleapis.com/...')` in globals.css

```tsx
// app/fonts.ts
import { Orbitron } from 'next/font/google';
export const orbitron = Orbitron({ subsets: ['latin'], variable: '--font-orbitron' });
```

### Pattern F: Route-Level Skeleton Screen

**Use when**: Any page using server-side data prefetch

```tsx
// app/[locale]/{page}/loading.tsx
export default function Loading() {
  return <PageSkeleton />;  // Reuse existing Skeleton component
}
```

---

## Deliverables

After the audit, deliver the following:

1. **Research document** → `.progress/dev-docs/research/RES-NNN-{page}-perf-audit.md`
   - Component inventory + five-dimension analysis + findings + baseline data

2. **ENH document** → `.progress/dev-docs/ENH/ENH-NNN-{page}-perf.md`
   - Batched implementation plan + expected impact

3. **Baseline screenshots** (if measured) → `.progress/dev-docs/research/`

---

## What This Skill Does NOT Do

- No speculative optimizations without data — measure first, then optimize
- No forcing SSR where it doesn't fit — SSR is wrong for pure interaction pages (e.g. Swap); do not push it
- No optimizations with < 50 ms benefit that require > 1 day of work
- No code changes during the audit phase — the audit outputs a plan; development is executed by autopilot or manually
- No duplicating existing enh-todo entries — when an existing tracking item is found, reference it rather than creating a new one
