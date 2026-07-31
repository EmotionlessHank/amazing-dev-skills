---
name: worktree-cleanup
description: "Audit and safely clean local Git worktrees. Use this when the user asks to clean worktrees, audit linked worktrees, run a weekly worktree check, remove merged worktrees, or inspect stale worktrees under a configured development root. The default mode is read-only audit; actual linked-worktree removal requires cleanup-approved with an explicit absolute path."
compatibility: "macOS, /usr/bin/python3, Git, OpenSSH, launchd"
metadata:
  version: 1.0.0
  triggers:
    - "clean up worktrees"
    - "worktree cleanup"
    - "audit worktrees"
    - "weekly worktree check"
  platforms:
    - macos
---

# Worktree Cleanup

## Safety Rules

1. Run audit by default. Do not remove linked worktrees during scheduled runs.
2. Scheduled runs may only send a report and atomically remove truly empty `.worktrees` container directories.
3. Do not use forced deletion, delete branches, or provide a bulk "clean all candidates" switch.
4. `cleanup-approved` may process only one user-specified absolute path.
5. Any ignored, untracked, tracked change, locked worktree, detached HEAD, submodule, path anomaly, ambiguous baseline, active process, or failed check blocks cleanup.
6. Do not read, print, or store Telegram tokens on the Mac. If Telegram delivery is configured, send report text over SSH stdin to a server-side relay.
7. Use the bundled scripts as the only execution path. Do not manually assemble deletion commands.

## Configuration

The scripts are configurable through environment variables:

- `WORKTREE_CLEANUP_ROOT`, default: `~/AI`
- `WORKTREE_CLEANUP_STATE_DIR`, default: `~/.local/state/worktree-cleanup`
- `WORKTREE_CLEANUP_SKILL_DIR`, default: `~/.codex/skills/worktree-cleanup`
- `WORKTREE_CLEANUP_SSH_ALIAS`, default: `worktree-relay`
- `WORKTREE_CLEANUP_RELAY_PATH`, default: `~/.hermes/scripts/worktree-cleanup-relay.py`
- `WORKTREE_CLEANUP_RELAY_ENV`, server-side default: `~/.hermes/.env`
- `WORKTREE_CLEANUP_RELAY_ENV_OWNER`, server-side default: current user
- `WORKTREE_CLEANUP_LAUNCHD_LABEL`, default: `com.example.worktree-cleanup`

See `SETUP.md` before installing the LaunchAgent or relay.

## Commands

Read-only audit:

```bash
/usr/bin/python3 ~/.codex/skills/worktree-cleanup/scripts/worktree_cleanup.py audit --root ~/AI
```

Audit and send a compact Telegram report through the configured SSH relay:

```bash
/usr/bin/python3 ~/.codex/skills/worktree-cleanup/scripts/worktree_cleanup.py audit --root ~/AI --send-telegram
```

User-approved cleanup for one explicit linked worktree:

```bash
/usr/bin/python3 ~/.codex/skills/worktree-cleanup/scripts/worktree_cleanup.py cleanup-approved --root ~/AI --path /absolute/path/to/linked-worktree
```

Install or refresh the LaunchAgent:

```bash
/usr/bin/python3 ~/.codex/skills/worktree-cleanup/scripts/install_launch_agent.py
```

## Workflow

1. Run read-only audit first and inspect the `Manual cleanup candidates`, `Needs attention`, and `Anomalies` sections.
2. Run `cleanup-approved` only when the user explicitly names one absolute path.
3. `cleanup-approved` re-audits the target, takes a second snapshot, and calls Git's standard worktree removal without force.
4. After cleanup, the script verifies that the branch and commit still exist.
5. The LaunchAgent runs every Sunday at 10:30 in the Mac local timezone.

## Output

- State directory: `~/.local/state/worktree-cleanup/`
- Latest structured report: `latest.json`
- Run history: `history.jsonl`
- Merge observation ledger: `merged-first-seen.json`
- Pending report cache: `pending-report.txt`
- LaunchAgent log: `worktree-cleanup.log`

## Candidate Semantics

A manual cleanup candidate is not an auto-delete authorization. It means the worktree passed conservative gates and can be reviewed by a human before running `cleanup-approved`.

A worktree must be observed as merged for at least 14 consecutive days before it becomes a candidate. The observation key includes the Git common dir, normalized worktree path, and HEAD OID. HEAD, path, or merge-state changes reset the timer.

The compact report shows at most 10 attention items. Full details are in `latest.json`.
