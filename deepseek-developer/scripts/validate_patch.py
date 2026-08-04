#!/usr/bin/env python3
"""严格验证 unified diff，只接受对精确 allowlist 的已有普通文件修改。"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path, PurePosixPath


HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?$")


def fail(message: str) -> None:
    print(f"PATCH_REJECTED: {message}", file=sys.stderr)
    raise SystemExit(1)


def within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def normalise(value: str, prefix: str) -> str:
    if not value.startswith(prefix) or value == prefix:
        fail(f"补丁文件头必须以 {prefix} 开头")
    path = PurePosixPath(value[len(prefix):])
    if path.is_absolute() or ".." in path.parts or "\\" in value:
        fail(f"补丁路径不安全: {value}")
    return str(path)


def load_allowlist(raw_paths: list[str], root: Path) -> set[Path]:
    result: set[Path] = set()
    for raw in raw_paths:
        candidate = Path(raw) if Path(raw).is_absolute() else root / raw
        if not candidate.exists() or not candidate.is_file() or candidate.is_symlink():
            fail(f"allowlist 文件无效: {raw}")
        resolved = candidate.resolve(strict=True)
        if not within(resolved, root):
            fail(f"allowlist 文件逃离工作树: {raw}")
        result.add(resolved)
    return result


def require_allowed(relative: str, root: Path, allowed: set[Path]) -> None:
    candidate = root / relative
    if not candidate.exists() or not candidate.is_file() or candidate.is_symlink():
        fail(f"补丁目标不是普通现有文件: {relative}")
    resolved = candidate.resolve(strict=True)
    if not within(resolved, root) or resolved not in allowed:
        fail(f"补丁目标不在精确 allowlist 中: {relative}")


def parse_hunk(lines: list[str], index: int) -> int:
    match = HUNK.fullmatch(lines[index])
    if not match:
        fail("hunk 文件头格式无效")
    old_expected = int(match.group(2) or 1)
    new_expected = int(match.group(4) or 1)
    old_seen = new_seen = 0
    index += 1
    while index < len(lines) and (old_seen < old_expected or new_seen < new_expected):
        line = lines[index]
        if line.startswith(" "):
            old_seen += 1
            new_seen += 1
        elif line.startswith("-"):
            old_seen += 1
        elif line.startswith("+"):
            new_seen += 1
        elif line == "\\ No newline at end of file":
            if index == 0:
                fail("无换行标记位置无效")
        else:
            fail("hunk 正文格式无效")
        if old_seen > old_expected or new_seen > new_expected:
            fail("hunk 行数超过头部声明")
        index += 1
    if old_seen != old_expected or new_seen != new_expected:
        fail("hunk 行数与头部声明不一致")
    return index


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--allow", action="append", required=True)
    parser.add_argument("--max-bytes", type=int, default=200_000)
    args = parser.parse_args()
    root_input = Path(args.worktree)
    if root_input.is_symlink():
        fail("工作树根目录不能是符号链接")
    root = root_input.resolve(strict=True)
    if not root.is_dir():
        fail("工作树无效")
    raw = sys.stdin.buffer.read()
    if not raw or len(raw) > args.max_bytes or b"\0" in raw:
        fail("补丁为空、过大或包含二进制内容")
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        fail("补丁不是 UTF-8 文本")
    allowed = load_allowlist(args.allow, root)
    index = files = hunks = 0
    while index < len(lines):
        if index + 1 >= len(lines) or not lines[index].startswith("--- ") or not lines[index + 1].startswith("+++ "):
            fail("补丁必须以成对文件头开始，且不允许额外文本")
        old_path, new_path = normalise(lines[index][4:], "a/"), normalise(lines[index + 1][4:], "b/")
        if old_path != new_path:
            fail("不允许新增、删除或重命名文件")
        require_allowed(old_path, root, allowed)
        files += 1
        index += 2
        file_hunks = 0
        while index < len(lines) and lines[index].startswith("@@ "):
            index = parse_hunk(lines, index)
            hunks += 1
            file_hunks += 1
        if file_hunks == 0:
            fail("每个文件必须包含至少一个合法 hunk")
    if files == 0 or hunks == 0:
        fail("补丁必须含修改")
    print("PATCH_VALID")


if __name__ == "__main__":
    main()
