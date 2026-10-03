#!/bin/bash
# usage: run.sh script.py [timeout_seconds]
# Runs a browser-harness script with the tab-hygiene prelude and a finally block that closes every tab it opened.
# The time limit sends SIGINT (not SIGTERM), so Python raises KeyboardInterrupt and the finally block still runs;
# SIGKILL follows 30 seconds later only if the script ignores that. Never use kill -9 yourself, or the cleanup will not run.
# macOS has no timeout by default: brew install coreutils gives gtimeout.
HERE="$(cd "$(dirname "$0")" && pwd)"
TMO="$(command -v timeout || command -v gtimeout || true)"
if [ -n "$TMO" ]; then
  RUN=("$TMO" -s INT -k 30 "${2:-280}" browser-harness)
else
  echo "warning: no timeout or gtimeout found; running without a time limit" >&2
  RUN=(browser-harness)
fi
{ cat "$HERE/prelude.py"; printf 'try:\n    exec(open("%s").read())\nfinally:\n    cleanup_tabs()\n' "$1"; } | "${RUN[@]}"
