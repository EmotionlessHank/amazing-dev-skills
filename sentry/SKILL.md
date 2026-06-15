---
name: sentry
description: Sentry error patrol and regression test generation. Triggers when the user says "/sentry", "check Sentry", "Sentry scan", "sentry scan", or "generate regression tests". When the user pastes a Sentry Issue URL, automatically enters single-issue diagnosis mode (diagnose) — parses the Issue ID from the URL → fetches metadata and stack trace via API → locates source code → performs root cause analysis → applies fix. In patrol mode, connects to the Sentry API to fetch unresolved Fatal/Error issues, filters by threshold rules, automatically locates source files, generates regression test skeletons, and outputs a list for review.
version: 1.1.0
---

# /sentry — Sentry Error Patrol and Regression Test Auto-Generation

Connect to the Sentry API, fetch unresolved critical errors in production, and automatically generate regression test skeletons.
Design document: DD-028 §7.2

---

## Prerequisites Check

Before running the skill, verify that the Sentry environment is ready:

```bash
# Load from .env.local first (Claude Code's shell does not auto-export these variables)
if [ -f .env.local ]; then
  source <(grep -E '^SENTRY_(LOCAL_AUTH_TOKEN|ORG|PROJECT)=' .env.local)
fi

# Check environment variables
echo "SENTRY_LOCAL_AUTH_TOKEN: ${SENTRY_LOCAL_AUTH_TOKEN:+SET}"
echo "SENTRY_ORG: ${SENTRY_ORG:-NOT_SET}"
echo "SENTRY_PROJECT: ${SENTRY_PROJECT:-NOT_SET}"
```

> **Note**: All subsequent curl commands must `source` Sentry variables from `.env.local` before execution (each Bash call is an independent shell).

**If environment variables are not configured**:
1. Inform the user: "Sentry environment variables are not configured. Please complete the setup in DD-028 §3.1 Step 4 first."
2. Offer a fallback: ask the user whether to manually input error details (see "Manual Mode" section)
3. Abort the automated patrol flow

**If environment variables are configured**: proceed with automated patrol.

---

## Phase 1: Fetch Sentry Issues

### 1.1 Call the Sentry API

Sentry Issues search does not support native OR syntax — `level:fatal level:error` is interpreted as AND (mutually exclusive, always returns empty). Therefore, you must **make two separate requests** to fetch Fatal and Error level issues, then merge and deduplicate by `id`.

```bash
source <(grep -E '^SENTRY_(LOCAL_AUTH_TOKEN|ORG|PROJECT)=' .env.local)

# Request 1: Fetch unresolved Fatal-level issues (last 14 days)
# Note: Sentry Issues API statsPeriod only supports '', '24h', '14d' — '7d' is not supported
FATAL_ISSUES=$(curl -s -H "Authorization: Bearer ${SENTRY_LOCAL_AUTH_TOKEN}" \
  "https://sentry.io/api/0/projects/${SENTRY_ORG}/${SENTRY_PROJECT}/issues/?query=is:unresolved+level:fatal&statsPeriod=14d&limit=20")

# Request 2: Fetch unresolved Error-level issues (last 14 days)
ERROR_ISSUES=$(curl -s -H "Authorization: Bearer ${SENTRY_LOCAL_AUTH_TOKEN}" \
  "https://sentry.io/api/0/projects/${SENTRY_ORG}/${SENTRY_PROJECT}/issues/?query=is:unresolved+level:error&statsPeriod=14d&limit=20")

# Validate that responses are JSON arrays (prevents jq failure from rate limit / auth errors)
for VAR in FATAL_ISSUES ERROR_ISSUES; do
  echo "${!VAR}" | jq -e 'type == "array"' > /dev/null 2>&1 || { echo "ERROR: ${VAR} is not an array, check API response"; exit 1; }
done

# Merge and deduplicate by Issue id
echo "$FATAL_ISSUES" "$ERROR_ISSUES" | jq -s 'add | unique_by(.id)'
```

> **Note**: Use `jq` rather than `python3 -m json.tool`. macOS 12.3+ no longer ships Python by default; `jq` is lighter and typically already installed by developers.

### 1.2 Parse Issue List

Extract key fields from each issue in the API response:

| Field | Purpose |
|-------|---------|
| `id` | Sentry Issue ID (used for test naming: `SENTRY-{id}`) |
| `title` | Error title (used for test description) |
| `level` | Severity level (fatal / error) |
| `count` | Occurrence count |
| `culprit` | File/function path where the error occurred |
| `metadata.type` | Exception type (TypeError / ReferenceError, etc.) |
| `metadata.value` | Exception message |
| `firstSeen` / `lastSeen` | First/last occurrence timestamps |

### 1.3 Fetch Issue Details (Stack Trace)

For each issue that needs to be processed, fetch the stack trace from the latest event:

```bash
source <(grep -E '^SENTRY_(LOCAL_AUTH_TOKEN|ORG|PROJECT)=' .env.local)
curl -s -H "Authorization: Bearer ${SENTRY_LOCAL_AUTH_TOKEN}" \
  "https://sentry.io/api/0/issues/{issue_id}/events/latest/" \
  | jq '.'
```

Extract from the event:
- Stack frames (`exception.values[0].stacktrace.frames`)
- Source file and line number within the project (filter out `node_modules` frames)
- Tag `domain` if present (e.g., balance / betting / odds)

---

## Phase 2: Threshold Filtering

### 2.0 Pre-filter: Third-Party Code Detection

Before applying threshold rules, check whether each issue's stack trace contains **frames from project code**:

```
For each issue:
  Step A: Error message keyword check
    Check exception.values[0].value for the following keywords:
      - "tronlinkParams"    (TronLink injected Proxy property)
      - "ethereum"          (MetaMask / other EVM wallet injection)
      - "solana"            (Phantom and other Solana wallet injection)
    If any keyword matches → mark as SKIP

  Step B: Stack frame path check
    Fetch stack frames from the latest event
    Filter to frames where inApp == true
    Then exclude frames from the following paths (even if inApp is true):
      - injected/           (browser extension injected scripts)
      - extensions/         (browser extensions)
      - chrome-extension://
      - moz-extension://
    If 0 project frames remain after filtering → mark as SKIP

  For SKIP issues:
    → Output: "[SKIP] #{id} — third-party extension error ({keyword or path}), not our code"
    → Skip subsequent threshold evaluation
    → Recommend user perform "Delete and discard future events" in Sentry
```

> **Background**: Web3 users frequently install wallet extensions (TronLink, MetaMask, Phantom, etc.) that inject JS into pages and can trigger TypeError/Proxy errors. These errors are not fixable by us and must not enter the regression test pipeline.
>
> **Dual defense**: `instrumentation-client.ts`'s `beforeSend` intercepts these on the client side (preventing reporting); this `/sentry` skill applies a second filter here to catch any that slip through. When new wallet extension keywords are encountered, update both locations.

### 2.1 Threshold Evaluation

Apply rules from DD-028 §7.4 to determine how each issue is handled:

```
For each issue (that passed third-party code detection):
  │
  ├─ tag domain IN [balance, betting] ?
  │   → YES: mark as MUST_TEST (financial-critical, zero tolerance)
  │
  ├─ level = fatal ?
  │   → YES: mark as MUST_TEST (page crash, zero tolerance)
  │
  ├─ level = error AND frequency >= 3 per hour ?
  │   → YES: mark as MUST_TEST (regular error, frequency threshold triggered)
  │   Frequency calculation: count / (hours between lastSeen and firstSeen)
  │   If firstSeen == lastSeen (only occurred once), frequency is treated as 0
  │
  └─ Otherwise
      → mark as SKIP (does not enter the flywheel)
```

### Output Filter Results

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Sentry Patrol Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Summary: {N} unresolved issues total, {M} require test generation

🔴 MUST_TEST (regression tests required):
  1. SENTRY-{id}: {title}
     Level: {level} | Occurrences: {count} | File: {culprit}
     Reason: {financial-critical / page crash / frequency threshold exceeded}

  2. SENTRY-{id}: {title}
     ...

🚫 SKIP (third-party code, not under our control):
  - SENTRY-{id}: {title} (source: {injected.js / chrome-extension, etc.})
  ...

⏭️ SKIP (below threshold):
  - SENTRY-{id}: {title} ({level}, {count} occurrences — below threshold)
  ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If MUST_TEST count is 0, output "No Sentry issues require action at this time" and stop.

---

## Phase 3: Generate Regression Tests

For each MUST_TEST issue:

### 3.1 Locate Test File

Determine the test file location based on the source file path (co-location pattern):

```
Source: lib/decimal.ts       → Test: lib/decimal.test.ts
Source: stores/tradeStore.ts → Test: stores/tradeStore.test.ts
Source: hooks/useWallet.ts   → Test: hooks/useWallet.test.ts
```

- If the test file already exists → append a new `it()` to the end of the relevant `describe` block
- If the test file does not exist → create a new file with basic imports and a describe structure

### 3.2 Generate Test Skeleton

**Naming convention** (DD-028 §3.2.2):

```typescript
it('regression: SENTRY-{id} — {error description in English}', () => {
  // Sentry Issue: https://sentry.io/organizations/{org}/issues/{id}/
  // Error: {exception type}: {exception message}
  // File: {source file}:{line number}
  // First seen: {date}, Count: {count}
  //
  // TODO: implement assertion
})
```

**Smart generation rules**:

Based on the source file and error type, attempt to generate specific test logic (rather than just a TODO):

| Error Pattern | Auto-Generated Content |
|---------------|------------------------|
| `lib/decimal.ts` related | Import the function directly; infer input values from the error message; generate `expect().toBe()` |
| `TypeError: Cannot read properties of undefined` | Generate null/undefined input tests |
| `RangeError` / `DecimalError` | Generate boundary value tests |
| Other | Generate a TODO skeleton for the user to fill in |

### 3.3 Check for Potential ESLint Rules

If the error pattern can be matched with an AST selector, suggest adding an ESLint rule:

```
Found: SENTRY-456 — Math.random() used directly in odds calculation
Suggestion: Add ESLint rule:
  {
    "selector": "CallExpression[callee.object.name='Math'][callee.property.name='random']",
    "message": "Do not use Math.random() for odds calculation"
  }
```

Output as a suggestion only; do not automatically write to .eslintrc.json.

### 3.4 Output Generation Results

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 Regression Test Generation Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Generated {N} regression tests:

  1. SENTRY-{id} → lib/decimal.test.ts
     it('regression: SENTRY-{id} — ...')
     Status: Full assertion generated / TODO requires manual completion

  2. SENTRY-{id} → hooks/useWallet.test.ts
     it('regression: SENTRY-{id} — ...')
     Status: TODO requires manual completion

💡 Suggested ESLint rules: {N} (see details above)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 3.5 Wait for User Confirmation

After outputting the test list above, **pause execution** and ask the user:

> "The {N} regression tests above have been generated. Confirm writing them to the corresponding .test.ts files?"

- User confirms → write files, proceed to Phase 4
- User requests changes → adjust based on feedback and re-output
- User cancels → terminate the skill

> This gate is consistent with the core protocol in CLAUDE.md §1: "confirm the plan before writing code".

---

## Phase 4: Verification and Wrap-Up

### 4.1 Run Tests

```bash
pnpm test --run
```

- All green → "All tests pass, ready to commit"
- TODO tests present → "N tests require assertion logic to be filled in"
- Failures → locate the failure cause and fix it

### 4.2 Update LESSONS.md

For Fatal-level issues, append an entry to `.progress/rewind-docs/LESSONS.md`:

```markdown
### §{N}: {Error Category}

**Sentry Issue**: SENTRY-{id}
**Root Cause**: {analysis}
**Fix**: {solution}
**Prevention**: regression test in {test file}
```

### 4.3 Close Sentry Issue

After tests pass, prompt:
> "Recommend marking SENTRY-{id} as Resolved in the Sentry Dashboard. If the error recurs, Sentry will automatically reopen and alert."

---

## Manual Mode (fallback when Sentry is not configured)

When Sentry environment variables are not configured, or the user manually describes an error:

```
/sentry manual
```

Prompt the user to provide:
1. Error description (one sentence)
2. Affected file/function (if known)
3. Severity (fatal / error / warning)

Then skip Phases 1–2 and go directly to Phase 3 to generate a test skeleton.

Test naming uses `MANUAL-{date}` instead of `SENTRY-{id}`:

```typescript
it('regression: MANUAL-20260320 — {description}', () => {
  // Reported manually
  // TODO: implement assertion
})
```

---

## Single Issue Diagnosis Mode (Diagnose)

### Trigger Condition

The user pastes a Sentry Issue URL (e.g., `https://oddfi.sentry.io/issues/7364402444/...`), or says "locate this Sentry error" or "diagnose this issue".

### Step 1: URL Parsing

Extract key parameters from the URL:

```
https://{org}.sentry.io/issues/{issue_id}/?environment={env}&project={project_id}
                                            ↑                  ↑
                                            optional filter    project ID
```

Extract: `issue_id` (required), `org` (from subdomain; fall back to .env.local)

### Step 2: Load Authentication

```bash
source <(grep -E '^SENTRY_(LOCAL_AUTH_TOKEN|ORG|PROJECT)=' .env.local)
```

Prefer `SENTRY_LOCAL_AUTH_TOKEN` (Personal Token with issue read access).
`SENTRY_AUTH_TOKEN` (Org Token) typically only has source map upload access and will return 403 when querying issues.

### Step 3: Fetch Issue Metadata

```bash
curl -s -H "Authorization: Bearer ${SENTRY_LOCAL_AUTH_TOKEN}" \
  "https://sentry.io/api/0/organizations/${SENTRY_ORG}/issues/${ISSUE_ID}/" \
  | jq '{
    id, title, level, status,
    substatus, priority, count, userCount,
    firstSeen, lastSeen,
    culprit,
    type: .metadata.type,
    value: .metadata.value,
    filename: .metadata.filename,
    platform,
    release: .firstRelease.shortVersion
  }'
```

**Key fields at a glance**:

| Field | Diagnostic Value |
|-------|-----------------|
| `title` | One-line error summary |
| `culprit` | Route/function where the error occurred (e.g., `GET /zh/markets`) |
| `metadata.filename` | Source file path of the error |
| `platform` | `node` = SSR side / `javascript` = client side — **determines fix direction** |
| `count` / `userCount` | Frequency and number of affected users |
| `substatus` | `new` / `regressed` / `escalating` — determines if it's a new issue or a regression |
| `priority` | Sentry's automatic rating (high/medium/low) |

### Step 4: Fetch Latest Event (Full Stack Trace)

```bash
curl -s -H "Authorization: Bearer ${SENTRY_LOCAL_AUTH_TOKEN}" \
  "https://sentry.io/api/0/organizations/${SENTRY_ORG}/issues/${ISSUE_ID}/events/latest/" \
  | jq '.'
```

**Extract three types of information from the event**:

#### 4a. Stack Frames (read bottom to top)

```
entries[0].data.values[0].stacktrace.frames[]
```

- `inApp: true` frames = project code (focus here)
- `inApp: false` frames = node_modules (trace the dependency call chain)
- Trace from the deepest frame (trigger point) up to the project code frame = **root cause location path**

#### 4b. Tags (environment context)

```
tags[] → { key, value }
```

Key tags:
- `runtime` → `node` indicates the error triggered during SSR
- `transaction` → the route that triggered it (e.g., `GET /zh/markets`)
- `browser` / `os` → client environment (only useful for client-side errors)
- `mechanism` → `auto.node.onunhandledrejection` / `onerror`, etc.

#### 4c. Contexts (runtime environment details)

```
contexts.runtime → { name, version }   // node v24.13.0 = Vercel SSR
contexts.cloud_resource → { cloud.provider, cloud.region }
```

### Step 5: Root Cause Analysis Decision Tree

```
1. platform == "node" ?
   ├─ YES → SSR-side error
   │   ├─ Error involves browser APIs (indexedDB/localStorage/window/document)?
   │   │   → Module top-level code executed a browser-only API during SSR
   │   │   → Fix: typeof window guard / dynamic import / lazy initialization
   │   │
   │   ├─ Error originates from a node_modules dependency?
   │   │   → Dependency is not SSR-compatible
   │   │   → Fix: next/dynamic + ssr:false / conditional import
   │   │
   │   └─ Error from project API Route / Server Component?
   │       → Inspect data-fetching logic
   │
   └─ NO → Client-side error
       ├─ Stack frames are all from node_modules? (wallet extension / third-party injection)
       │   → SKIP, recommend "Delete and discard" in Sentry
       │
       └─ Project code frames present?
           → Regular bug; locate the source file and fix it
```

### Step 6: Source Code Tracing

Starting from **project code frames** in the stack trace, locate the code locally:

```bash
# 1. Identify the project file in the stack trace
# Stack shows: lib/connectors.ts → read that file in the project

# 2. Trace the import chain (who imports this module, causing it to execute during SSR)
grep -r "from.*connectors" --include="*.ts" --include="*.tsx" | grep -v node_modules

# 3. Verify that 'use client' boundaries are correctly placed
# Check every file in the import chain for a 'use client' directive
```

### Step 7: Fix → Verify → Commit

1. **Minimal fix**: only modify the file with the problem; do not expand scope
2. **Type check**: `pnpm tsc --noEmit`
3. **Build verification**: `pnpm build` (confirm compilation succeeds)
4. **Tests**: `pnpm test` (confirm no regressions)
5. **Commit**: include `Sentry: ODDFI-FRONTEND-{N}` in the commit message

### Output Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Sentry Issue Diagnosis Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Issue: ODDFI-FRONTEND-{N} (#{issue_id})
Error: {exception type}: {exception message}
Route: {culprit}
Environment: {platform} / {runtime} / {cloud provider}
Frequency: {count} occurrences ({firstSeen} ~ {lastSeen})
Priority: {priority}

📍 Call chain:
  {project file} → {intermediate dependency} → {trigger point (deepest frame)}

🔬 Root cause:
  {one-sentence root cause description}

🛠️ Fix:
  File: {modified file}
  Approach: {brief description of the fix}
  Commit: {commit hash}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Sentry API Endpoint Reference

| Purpose | Endpoint | Notes |
|---------|----------|-------|
| Issue metadata | `GET /api/0/organizations/{org}/issues/{id}/` | Title, level, frequency |
| Latest event | `GET /api/0/organizations/{org}/issues/{id}/events/latest/` | Stack trace, tags, contexts |
| Event list | `GET /api/0/organizations/{org}/issues/{id}/events/` | All events (paginated) |
| Issue list | `GET /api/0/projects/{org}/{project}/issues/` | Batch query (used in patrol mode) |

> **Note**: `sentry-cli issues` subcommand only supports `list/mute/resolve` — it does not support viewing individual issue details.
> Single-issue diagnosis must use the REST API (curl).

---

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| `/preflight` | Check 7 verifies whether there are unhandled Sentry issues (see preflight updates) |
| `/quality-scan` | Shares LESSONS.md as a source of inspection rules |
| `/feat` | Before development, automatically flags whether the relevant module has unresolved Sentry issues |
