#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
from pathlib import Path

CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")
ASCII_TEXT_RE = re.compile(r"^[\x09\x0a\x0d\x20-\x7e]+$")
SUBJECT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .,:;!?()/_#'\"+-]{4,}$")
AI_NAME_RE = r"\b(codex|claude|chatgpt|openai|gpt|gemini|copilot|cursor|anthropic|ai)\b"
AI_COAUTHOR_RE = re.compile(
    r"^co-authored-by:\s*(codex|openai( codex)?|chatgpt|claude code|gemini|github copilot|copilot|cursor|anthropic|ai assistant|.*\[(bot|ai)\])\b",
    re.IGNORECASE | re.MULTILINE,
)
AI_SIGNATURE_RE = re.compile(
    rf"(generated\s+(with|by)\s+{AI_NAME_RE}|ai-generated|{AI_NAME_RE}-generated|codex-session:|🤖)",
    re.IGNORECASE,
)


def message_is_english(message: str) -> tuple[bool, str]:
    lines = [line.strip() for line in message.splitlines() if line.strip() and not line.startswith("#")]
    if not lines:
        return False, "empty commit message"
    text = "\n".join(lines)
    if AI_COAUTHOR_RE.search(text) or AI_SIGNATURE_RE.search(text):
        return False, "commit message contains an AI signature"
    if CJK_RE.search(text):
        return False, "commit message contains CJK characters"
    if not ASCII_TEXT_RE.match(text):
        return False, "commit message contains non-ASCII characters"
    subject = lines[0]
    if not SUBJECT_RE.match(subject):
        return False, "commit subject must be readable English text"
    if len(subject) > 100:
        return False, "commit subject is longer than 100 characters"
    return True, ""


def check_file(path: Path) -> int:
    ok, reason = message_is_english(path.read_text(encoding="utf-8"))
    if ok:
        return 0
    print(f"commit-msg gate failed: {reason}", file=sys.stderr)
    print("Use an English commit message before merging to main.", file=sys.stderr)
    return 1


def check_range(commit_range: str) -> int:
    result = subprocess.run(
        ["git", "log", "--format=%H%x00%B%x00END%x00", commit_range],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        print(result.stderr.strip() or "failed to read commit range", file=sys.stderr)
        return 2
    parts = result.stdout.split("\0")
    failures = []
    index = 0
    while index + 2 < len(parts):
        commit = parts[index].strip()
        body = parts[index + 1]
        marker = parts[index + 2]
        index += 3
        if not commit or marker != "END":
            continue
        ok, reason = message_is_english(body)
        if not ok:
            failures.append((commit[:12], reason))
    if failures:
        print("commit message gate failed for outgoing main commits:", file=sys.stderr)
        for commit, reason in failures:
            print(f"- {commit}: {reason}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate English commit messages.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=Path)
    group.add_argument("--range")
    args = parser.parse_args()
    if args.file:
        return check_file(args.file)
    return check_range(args.range)


if __name__ == "__main__":
    raise SystemExit(main())
