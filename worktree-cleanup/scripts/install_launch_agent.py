#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(os.environ.get("WORKTREE_CLEANUP_SKILL_DIR", str(Path.home() / ".codex/skills/worktree-cleanup")))
SOURCE_PLIST = SKILL_DIR / "assets" / "com.example.worktree-cleanup.plist"
LABEL = os.environ.get("WORKTREE_CLEANUP_LAUNCHD_LABEL", "com.example.worktree-cleanup")
TARGET_PLIST = Path(os.environ.get("WORKTREE_CLEANUP_PLIST", str(Path.home() / f"Library/LaunchAgents/{LABEL}.plist")))
STATE_DIR = Path(os.environ.get("WORKTREE_CLEANUP_STATE_DIR", str(Path.home() / ".local/state/worktree-cleanup")))
ROOT_DIR = Path(os.environ.get("WORKTREE_CLEANUP_ROOT", str(Path.home() / "AI")))


def run(argv):
    return subprocess.run(argv, text=True, capture_output=True, timeout=30)


def main():
    if not SOURCE_PLIST.exists():
        print(f"Missing template: {SOURCE_PLIST}", file=sys.stderr)
        return 1
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / "worktree-cleanup.log").touch(exist_ok=True)
    TARGET_PLIST.parent.mkdir(parents=True, exist_ok=True)
    rendered = SOURCE_PLIST.read_text(encoding="utf-8")
    rendered = rendered.replace("{SKILL_DIR}", str(SKILL_DIR))
    rendered = rendered.replace("{ROOT_DIR}", str(ROOT_DIR))
    rendered = rendered.replace("{STATE_DIR}", str(STATE_DIR))
    rendered = rendered.replace("{LABEL}", LABEL)
    if TARGET_PLIST.exists():
        current = TARGET_PLIST.read_bytes()
        desired = rendered.encode("utf-8")
        if current != desired:
            print(f"Target plist already exists with different content, stopping: {TARGET_PLIST}", file=sys.stderr)
            return 2
    else:
        TARGET_PLIST.write_text(rendered, encoding="utf-8")
    lint = run(["/usr/bin/plutil", "-lint", str(TARGET_PLIST)])
    if lint.returncode != 0:
        print(lint.stdout, end="")
        print(lint.stderr, end="", file=sys.stderr)
        return lint.returncode
    uid = os.getuid()
    service = f"gui/{uid}/{LABEL}"
    domain = f"gui/{uid}"
    print(lint.stdout.strip())
    boot = run(["/bin/launchctl", "bootstrap", domain, str(TARGET_PLIST)])
    if boot.returncode != 0 and "already bootstrapped" not in boot.stderr.lower():
        print(boot.stdout, end="")
        print(boot.stderr, end="", file=sys.stderr)
        return boot.returncode
    kick = run(["/bin/launchctl", "kickstart", "-k", service])
    if kick.returncode != 0:
        print(kick.stdout, end="")
        print(kick.stderr, end="", file=sys.stderr)
        return kick.returncode
    print(f"Installed and kicked: {TARGET_PLIST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
