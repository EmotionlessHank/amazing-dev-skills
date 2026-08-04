#!/usr/bin/env python3
"""从精确 allowlist 构造唯一允许外发的 DeepSeek 请求文件。"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path


DENIED_COMPONENTS = {".aws", ".ssh", ".gnupg", ".kube", ".config", "keychains", "cookies", "profiles", "downloads", "logs", "exports"}
DENIED_NAMES = {".npmrc", ".netrc", "auth.json", "credentials", "credential", "secret", "secrets", "token", "tokens", "id_rsa", "id_ed25519"}
DENIED_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".kdbx", ".sqlite", ".db", ".log", ".har"}
SECRET_PATTERNS = (
    rb"-----BEGIN [A-Z ]*PRIVATE KEY-----", rb"\bsk-[A-Za-z0-9]{16,}\b", rb"\bghp_[A-Za-z0-9]{20,}\b",
    rb"\bgithub_pat_[A-Za-z0-9_]{20,}\b", rb"\bAKIA[0-9A-Z]{16}\b", rb"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9._~+/=-]{12,}",
    rb"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b", rb"(?i)(?:mongodb(?:\+srv)?|postgres(?:ql)?|mysql)://[^\s]{8,}",
    rb"(?i)(?:api[_-]?key|secret|token|password|cookie)\s*[:=]\s*[\"']?[A-Za-z0-9_./+=-]{16,}",
)


def fail(message: str) -> None:
    print(f"OUTBOUND_REJECTED: {message}", file=sys.stderr)
    raise SystemExit(1)


def within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def check_bytes(data: bytes, label: str, limit: int) -> str:
    if not data or len(data) > limit or b"\0" in data:
        fail(f"{label} 为空、过大或包含二进制内容")
    for pattern in SECRET_PATTERNS:
        if re.search(pattern, data):
            fail(f"{label} 疑似含凭据")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        fail(f"{label} 不是 UTF-8 文本")


def read_allowed(raw: str, root: Path, limit: int) -> tuple[str, bytes]:
    candidate = Path(raw) if Path(raw).is_absolute() else root / raw
    if not candidate.exists() or not candidate.is_file() or candidate.is_symlink():
        fail(f"允许文件无效: {raw}")
    resolved = candidate.resolve(strict=True)
    if not within(resolved, root):
        fail(f"允许文件逃离工作树: {raw}")
    relative = resolved.relative_to(root)
    if any(part.lower() in DENIED_COMPONENTS for part in relative.parts[:-1]):
        fail(f"允许文件命中敏感目录: {raw}")
    name = resolved.name.lower()
    if name.startswith(".env") or name in DENIED_NAMES or resolved.suffix.lower() in DENIED_SUFFIXES:
        fail(f"允许文件命中敏感规则: {raw}")
    current = root
    for part in candidate.relative_to(root).parts:
        current /= part
        if current.is_symlink():
            fail(f"允许文件路径含符号链接: {raw}")
    data = resolved.read_bytes()
    check_bytes(data, f"允许文件 {relative}", limit)
    return relative.as_posix(), data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--task-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow", action="append", required=True)
    parser.add_argument("--max-bytes", type=int, default=200_000)
    args = parser.parse_args()
    root_input = Path(args.worktree)
    if root_input.is_symlink():
        fail("工作树根目录不能是符号链接")
    root = root_input.resolve(strict=True)
    if not root.is_dir():
        fail("工作树无效")
    task_path = Path(args.task_file)
    if task_path.is_symlink() or not task_path.is_file():
        fail("任务说明必须是普通文件")
    task = check_bytes(task_path.read_bytes(), "任务说明", args.max_bytes)
    files = [read_allowed(raw, root, args.max_bytes) for raw in args.allow]
    if len({path for path, _ in files}) != len(files):
        fail("allowlist 含重复文件")
    chunks = ["只返回 unified diff，不要 Markdown、解释、命令或新增文件。", "任务说明:\n" + task, "允许修改的文件:"]
    for relative, data in files:
        digest = hashlib.sha256(data).hexdigest()
        chunks.append(f"文件: {relative}\nSHA256: {digest}\n内容:\n{data.decode('utf-8')}")
    payload = "\n\n".join(chunks).encode("utf-8")
    if len(payload) > args.max_bytes:
        fail("最终外发载荷过大")
    output = Path(args.output)
    if output.exists() or output.is_symlink() or not output.parent.is_dir():
        fail("输出路径必须是不存在且父目录存在的普通路径")
    output.write_bytes(payload)
    output.chmod(0o600)
    print("OUTBOUND_VALID")


if __name__ == "__main__":
    main()
