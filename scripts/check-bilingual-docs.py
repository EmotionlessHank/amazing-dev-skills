#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

DOC_SUFFIXES = {".md", ".mdx"}
EXEMPT_NAMES = {"LICENSE", "LICENSE.md"}
CJK_RE = re.compile(r"[\u3400-\u9fff]")
EN_WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z'-]{2,}\b")
CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`]*`")
URL_RE = re.compile(r"https?://\S+")


def is_doc(path: str) -> bool:
    p = Path(path)
    if p.name in EXEMPT_NAMES:
        return False
    return p.suffix.lower() in DOC_SUFFIXES


def tracked_changed_docs(commit_range: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", commit_range],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        print(result.stderr.strip() or "failed to read changed files", file=sys.stderr)
        raise SystemExit(2)
    return [line.strip() for line in result.stdout.splitlines() if is_doc(line.strip())]


def changed_docs_between(base: str, head: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", base, head],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        print(result.stderr.strip() or "failed to read changed files", file=sys.stderr)
        raise SystemExit(2)
    return [line.strip() for line in result.stdout.splitlines() if is_doc(line.strip())]


def staged_docs() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        print(result.stderr.strip() or "failed to read staged files", file=sys.stderr)
        raise SystemExit(2)
    return [line.strip() for line in result.stdout.splitlines() if is_doc(line.strip())]


def range_head(commit_range: str) -> Optional[str]:
    if ".." not in commit_range:
        return None
    return commit_range.rsplit("..", 1)[1]


def read_from_git(ref: str, raw_path: str) -> tuple[bool, str]:
    show = subprocess.run(
        ["git", "show", f"{ref}:{raw_path}"],
        text=True,
        capture_output=True,
        check=False,
    )
    return show.returncode == 0, show.stdout


def prose_content(content: str) -> str:
    content = CODE_FENCE_RE.sub(" ", content)
    content = INLINE_CODE_RE.sub(" ", content)
    content = URL_RE.sub(" ", content)
    return content


def has_bilingual_prose(content: str) -> bool:
    prose = prose_content(content)
    zh_chars = CJK_RE.findall(prose)
    en_words = EN_WORD_RE.findall(prose)
    return len(zh_chars) >= 4 and len(en_words) >= 5


def check_docs(paths: list[str], staged: bool = False, ref: Optional[str] = None) -> int:
    failures = []
    for raw_path in paths:
        path = Path(raw_path)
        if staged:
            show = subprocess.run(
                ["git", "show", f":{raw_path}"],
                text=True,
                capture_output=True,
                check=False,
            )
            if show.returncode != 0:
                failures.append((raw_path, "could not read staged content"))
                continue
            content = show.stdout
        elif ref:
            ok, content = read_from_git(ref, raw_path)
            if not ok:
                failures.append((raw_path, f"could not read content from {ref}"))
                continue
        else:
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
        if not has_bilingual_prose(content):
            failures.append((raw_path, "documentation must contain both Chinese and English text"))
    if failures:
        print("bilingual documentation gate failed:", file=sys.stderr)
        for path, reason in failures:
            print(f"- {path}: {reason}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate bilingual documentation changes.")
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--range")
    parser.add_argument("--base")
    parser.add_argument("--head")
    args = parser.parse_args()
    if args.staged:
        return check_docs(staged_docs(), staged=True)
    if args.range:
        return check_docs(tracked_changed_docs(args.range), ref=range_head(args.range))
    if args.base and args.head:
        return check_docs(changed_docs_between(args.base, args.head), ref=args.head)
    print("use --staged, --range, or --base with --head", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
