# Worktree Cleanup Setup

This skill is intentionally conservative. Scheduled runs never remove linked worktrees. They only audit, report, and optionally remove empty `.worktrees` container directories with `rmdir`.

## 1. Install the Skill

Copy the skill directory into your Codex or Claude Code skill location, for example:

```bash
mkdir -p ~/.codex/skills
cp -R worktree-cleanup ~/.codex/skills/worktree-cleanup
```

If you install it elsewhere, set:

```bash
export WORKTREE_CLEANUP_SKILL_DIR=/absolute/path/to/worktree-cleanup
```

## 2. Configure Local Paths

Defaults:

- development root: `~/AI`
- state directory: `~/.local/state/worktree-cleanup`

Override them when needed:

```bash
export WORKTREE_CLEANUP_ROOT=/absolute/path/to/dev/root
export WORKTREE_CLEANUP_STATE_DIR=$HOME/.local/state/worktree-cleanup
```

## 3. Optional Telegram Relay

Telegram delivery is optional. The Mac script sends report text to a server-side relay over SSH stdin. The token stays on the server.

Server requirements:

- a working SSH alias, default `worktree-relay`
- a relay script at `~/.hermes/scripts/worktree-cleanup-relay.py`
- a server-side env file with `TELEGRAM_BOT_TOKEN` and `TELEGRAM_HOME_CHANNEL`
- env file mode `600`

Deploy the relay as one file:

```bash
scp ~/.codex/skills/worktree-cleanup/scripts/worktree_cleanup_relay.py worktree-relay:~/.hermes/scripts/worktree-cleanup-relay.py
ssh worktree-relay 'chmod 700 ~/.hermes/scripts/worktree-cleanup-relay.py'
```

Override SSH or relay paths when needed:

```bash
export WORKTREE_CLEANUP_SSH_ALIAS=worktree-relay
export WORKTREE_CLEANUP_RELAY_PATH=~/.hermes/scripts/worktree-cleanup-relay.py
```

On the server, override the env location or owner check when needed:

```bash
export WORKTREE_CLEANUP_RELAY_ENV=~/.hermes/.env
export WORKTREE_CLEANUP_RELAY_ENV_OWNER=$(whoami)
```

## 4. Test Manually

```bash
/usr/bin/python3 ~/.codex/skills/worktree-cleanup/scripts/worktree_cleanup.py audit --root ~/AI
```

If Telegram relay is configured:

```bash
/usr/bin/python3 ~/.codex/skills/worktree-cleanup/scripts/worktree_cleanup.py audit --root ~/AI --send-telegram
```

## 5. Install LaunchAgent

The bundled plist template is rendered by `install_launch_agent.py` using the environment variables above.

```bash
/usr/bin/python3 ~/.codex/skills/worktree-cleanup/scripts/install_launch_agent.py
launchctl print gui/$(id -u)/com.example.worktree-cleanup
```

Default schedule: Sunday 10:30, Mac local timezone.

## 6. Uninstall

```bash
launchctl bootout gui/$(id -u)/com.example.worktree-cleanup
rm ~/Library/LaunchAgents/com.example.worktree-cleanup.plist
```

Keep `~/.local/state/worktree-cleanup` if you want the audit history.
