---
description: Local-CI-gate-then-push — when paid cloud CI is off, a local pre-push git hook becomes the single gate (lint → build → test); this skill is the standard "green-then-push" front door: gate self-heal → guard green → multi-account-aware push → switch back. Triggers on "/ship", "push", "ship it", "green then push".
allowed-tools: Bash(git *), Bash(gh *), Bash(bash bin/setup-hooks.sh)
---

# /ship — Local-CI-Gate-Then-Push

> **Why**: Cloud CI (e.g. GitHub Actions on macOS runners) can be expensive. A **local `pre-push` git hook** can fully replace it as the gate — it runs your CI-equivalent chain (`{CI_CHAIN}`) before every `git push` and **blocks the push on any red**. This skill makes "green then push" a repeatable front door: install/repair the gate (fresh-clone self-heal) → guard green → `gh` multi-account-aware push → switch back to the default account. **Never bypass with `--no-verify`.**
>
> The hard gate is the hook itself (`{HOOKS_DIR}/pre-push`); this skill is its ergonomic front door + account automation. Pairs with any "run the CI chain locally" skill you have for in-dev verification.

## When to use
User says "/ship", "push", "ship it", "green then push", "push it up". **Only pushes already-committed work** — uncommitted changes must be committed first (don't bundle them into the push).

---

## Flow

### 0. Gate self-heal (ensure the pre-push hook is actually mounted — required on fresh clone)
The gate is a **local git config + hook file**; it does NOT survive a fresh `clone` automatically. Mount it first:
```bash
bash bin/setup-hooks.sh   # idempotent: sets core.hooksPath={HOOKS_DIR} + chmod +x the hooks
```
Or verify manually:
- `git config core.hooksPath` must equal `{HOOKS_DIR}`; if not → `git config core.hooksPath {HOOKS_DIR}`.
- `{HOOKS_DIR}/pre-push` must exist and be executable (`chmod +x`).
- Missing a tool the gate needs ({TOOLS}) → tell the user how to install it and **stop** (don't push past a gate that can't run).

### 1. Pre-flight
- `git status` clean (uncommitted changes → commit / stash first; don't bundle into the push).
- `git log @{u}..HEAD --oneline` (or `origin/<branch>..HEAD`) has commits to push; **none → report "already up to date" and stop**.
- Confirm the target branch (default: current branch; pushing to the main branch should be intentional).

### 2. Multi-account-aware push (push only if the gate is green)
`gh` may be logged into multiple accounts at once. `git push` uses the **currently active** account's credentials, but the repo may belong to a different account.
1. Resolve the remote owner: `git remote get-url origin` → `<owner>`.
2. `gh auth status` → active account. If active ≠ `<owner>` and lacks access → `gh auth switch -u <owner>` (a private repo with no access returns **404**, not 403).
3. `git push` — **this triggers the pre-push gate**: it runs `{CI_CHAIN}` locally; on red the hook aborts the push (non-zero exit, nothing pushed).
   - ⛔ **Never `--no-verify`** (bypassing the gate defeats the purpose; only for a genuine hook false-positive with explicit human confirmation).
4. After push, **immediately** `gh auth switch -u {DEFAULT_ACCOUNT}` to switch back (avoid polluting subsequent operations on other repos).

### 3. Report
- **Gate result**: green / red. On red → paste the failing lines from the gate's log, **do not push**, give a fix direction.
- **Push result**: `<old>..<new> <branch> → <remote>`.
- Red → **leave no half-pushed state**: report root cause, fix, then ship again.

---

## Red lines
- **Gate red = no push.** Never `--no-verify` (unless a human confirms it's a hook false-positive).
- **Always switch back** to the default account after pushing.
- Only push committed work; never bundle uncommitted changes.
- Run your CI chain locally *during dev* (so failures surface before the push attempt) — don't lean on the gate as your first check and waste a full gate run.

> **Single-account projects**: delete the `gh auth switch` steps in §2 — they only matter when `gh` holds multiple accounts.
> **Restoring cloud CI**: re-enable your cloud workflow trigger; the local gate and cloud CI can then run in tandem.

See `SETUP.md` for placeholder substitution and the hook + installer templates.
