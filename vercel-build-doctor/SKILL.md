---
name: vercel-build-doctor
description: Diagnose Vercel production build errors. Automatically triggers when the user mentions a Vercel build failure, deployment error, or build error. Fetches error logs in one step via the Vercel CLI/API, identifies the root cause, and applies a fix.
triggers:
  - vercel build failed
  - production build error
  - deployment failed
  - build error
  - vercel error
  - /vercel-doctor
---

# Vercel Build Doctor

Fast diagnosis and fix skill for production build errors.

## Trigger Recognition

The following signals indicate this skill should activate:
- User mentions "Vercel build failed", "production error", "deployment failed"
- User shares a Vercel deployment URL (containing `vercel.com`)
- User says "build error" or "the build is broken"

## Execution Flow

### Step 1: Get the deployment ID

Extract the deployment ID from the information the user provides. If the user shares a Vercel URL, parse it from there. If not, use `vercel ls` to find the most recent failed deployment:

```bash
vercel ls 2>&1 | head -15
```

Locate the deployment URL with status `● Error`.

### Step 2: Extract build errors in one command

Use the following command to pull error information directly — **the core command, one shot**:

```bash
DPL_ID="<deployment_id_or_url>" && \
TOKEN=$(python3 -c "import json; print(json.load(open('/Users/hang/Library/Application Support/com.vercel.cli/auth.json')).get('token',''))") && \
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.vercel.com/v2/deployments/${DPL_ID}/events?builds=1&limit=2000&direction=forward" \
  | jq -r '.[].payload.text' \
  | grep -iEB2 -A2 'error:|fail|ELIFECYCLE' \
  | grep -v 'sourcemap'
```

**Parameter reference**:
| Parameter | Purpose |
|-----------|---------|
| `events?builds=1` | Return only build logs (exclude runtime logs) |
| `limit=2000` | Pull enough log lines to avoid truncation |
| `direction=forward` | Chronological order — errors appear near the end |
| `jq -r '.[].payload.text'` | Extract plain-text log lines |
| `grep -iEB2 -A2` | 2 lines of context before and after each error line |
| `grep -v 'sourcemap'` | Strip Sentry sourcemap noise |

If `jq` is unavailable, use this fallback:

```bash
curl -s ... | python3 -c "
import sys, json
for e in json.load(sys.stdin):
    t = e.get('payload',{}).get('text','')
    if t and any(k in t.lower() for k in ['error', 'fail', 'elifecycle']):
        if 'sourcemap' not in t.lower():
            print(t)
"
```

### Step 3: Diagnose and fix

Based on the extracted error type, apply the corresponding fix:

| Error type | Fix action |
|------------|-----------|
| ESLint error (e.g. `no-unused-vars`) | Locate file and line number, fix the code directly |
| Type error | Read the failing file, resolve the type issue |
| Module not found | Check import paths and dependencies |
| Build timeout | Check for infinite loops or heavy computation |

After applying the fix:
1. Verify locally with `pnpm lint && pnpm build`
2. Commit and push
3. Confirm the new deployment status with `vercel ls`

## Notes

- **Always use the CLI/API to get first-hand data** — do not use WebFetch to scrape the Vercel dashboard (requires login, data is inaccessible)
- **Do not reproduce the error with a local build** — fetching logs directly from Vercel is faster and more accurate
- Vercel auth token location: `/Users/hang/Library/Application Support/com.vercel.cli/auth.json`
- If the `vercel` CLI is not logged in or `link` fails, prompt the user to run `vercel login` and `vercel link --yes --scope <scope>`
