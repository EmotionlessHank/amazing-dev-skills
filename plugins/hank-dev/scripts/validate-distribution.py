#!/usr/bin/env python3
"""验证 hank-dev 的 Claude 与 Codex 分发 metadata 不漂移。"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REQUIRED_EXECUTABLES = (
    "scripts/check-review-patch.sh",
    "scripts/run-deepseek-review.py",
    "scripts/validate-review-security.sh",
)
RELEASE_PATH_PREFIXES = (
    ".agents/plugins/marketplace.json",
    ".claude-plugin/marketplace.json",
    "plugins/hank-dev/.claude-plugin/",
    "plugins/hank-dev/.codex-plugin/",
    "plugins/hank-dev/scripts/",
    "plugins/hank-dev/skills/",
    "plugins/hank-dev/CHANGELOG.md",
)


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def read_json(path: Path) -> dict:
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"invalid-json {path}: {error}")
    if not isinstance(content, dict):
        fail(f"json-object-required {path}")
    return content


def git_show_json(repo_root: Path, revision: str, relative_path: str) -> dict | None:
    result = subprocess.run(
        ["git", "show", f"{revision}:{relative_path}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        return None
    try:
        content = json.loads(result.stdout)
    except json.JSONDecodeError:
        fail(f"invalid-base-json {relative_path}")
    if not isinstance(content, dict):
        fail(f"base-json-object-required {relative_path}")
    return content


def parse_version(value: object, description: str) -> tuple[int, int, int]:
    if not isinstance(value, str) or not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", value):
        fail(f"invalid-semver {description}")
    return tuple(int(part) for part in value.split("."))


def git_show_text(repo_root: Path, revision: str, relative_path: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f"{revision}:{relative_path}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    return result.stdout if result.returncode == 0 else None


def validate_release_version(repo_root: Path, base: str, head: str) -> None:
    changed = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    if not any(path.startswith(RELEASE_PATH_PREFIXES) for path in changed):
        return

    head_claude = git_show_json(repo_root, head, "plugins/hank-dev/.claude-plugin/plugin.json")
    head_codex = git_show_json(repo_root, head, "plugins/hank-dev/.codex-plugin/plugin.json")
    changelog = git_show_text(repo_root, head, "plugins/hank-dev/CHANGELOG.md")
    if head_claude is None or head_codex is None or changelog is None:
        fail("missing-head-release-files")
    if head_claude.get("version") != head_codex.get("version"):
        fail("head-manifest-version-mismatch")
    head_version = head_claude.get("version")
    if not re.search(rf"^## {re.escape(str(head_version))}$", changelog, re.MULTILINE):
        fail("changelog-version")
    head_semver = parse_version(head_version, "head")

    base_claude = git_show_json(repo_root, base, "plugins/hank-dev/.claude-plugin/plugin.json")
    base_codex = git_show_json(repo_root, base, "plugins/hank-dev/.codex-plugin/plugin.json")
    if base_claude is None and base_codex is None:
        return
    if base_claude is None:
        fail("missing-base-claude-manifest")
    if base_codex is None:
        return
    if base_claude.get("version") != base_codex.get("version"):
        fail("base-manifest-version-mismatch")
    if head_semver <= parse_version(base_claude.get("version"), "base"):
        fail("release-version-not-increased")


def validate_head_tree(repo_root: Path, head: str) -> None:
    paths = {
        "claude_manifest": "plugins/hank-dev/.claude-plugin/plugin.json",
        "codex_manifest": "plugins/hank-dev/.codex-plugin/plugin.json",
        "claude_marketplace": ".claude-plugin/marketplace.json",
        "codex_marketplace": ".agents/plugins/marketplace.json",
    }
    data = {name: git_show_json(repo_root, head, path) for name, path in paths.items()}
    if any(value is None for value in data.values()):
        fail("missing-head-distribution-file")
    claude_manifest = data["claude_manifest"]
    codex_manifest = data["codex_manifest"]
    assert claude_manifest is not None and codex_manifest is not None
    for field in ("name", "version", "description"):
        if not claude_manifest.get(field) or not codex_manifest.get(field):
            fail(f"missing-head-manifest-field {field}")
        if claude_manifest.get(field) != codex_manifest.get(field):
            fail(f"head-manifest-mismatch {field}")
    if codex_manifest.get("skills") != "./skills/":
        fail("head-codex-skills-path")
    claude_entries = data["claude_marketplace"].get("plugins", [])
    codex_entries = data["codex_marketplace"].get("plugins", [])
    if not isinstance(claude_entries, list) or not isinstance(codex_entries, list):
        fail("head-marketplace-plugin-list")
    claude_entry = next((entry for entry in claude_entries if entry.get("name") == "hank-dev"), None)
    codex_entry = next((entry for entry in codex_entries if entry.get("name") == "hank-dev"), None)
    if claude_entry is None or codex_entry is None:
        fail("head-marketplace-hank-dev-entry")
    if claude_entry.get("source") != "./plugins/hank-dev":
        fail("head-claude-marketplace-source")
    if codex_entry.get("source") != {"source": "local", "path": "./plugins/hank-dev"}:
        fail("head-codex-marketplace-source")
    if codex_entry.get("policy") != {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}:
        fail("head-codex-marketplace-policy")
    if codex_entry.get("category") != "Productivity":
        fail("head-codex-marketplace-category")
    tree = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", head, "plugins/hank-dev/skills"],
        cwd=repo_root, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    skill_dirs = sorted({Path(path).parts[3] for path in tree if len(Path(path).parts) >= 5})
    for skill_dir in skill_dirs:
        if f"plugins/hank-dev/skills/{skill_dir}/SKILL.md" not in tree:
            fail(f"head-missing-skill {skill_dir}")
    expected_skills = claude_manifest.get("skills", [])
    if not isinstance(expected_skills, list) or not expected_skills:
        fail("head-claude-manifest-skills")
    expected = sorted(expected_skills)
    actual = [f"./skills/{skill_dir}/" for skill_dir in skill_dirs]
    if expected != actual:
        fail("head-claude-skill-list")
    for relative_path in REQUIRED_EXECUTABLES:
        result = subprocess.run(
            ["git", "ls-tree", head, f"plugins/hank-dev/{relative_path}"],
            cwd=repo_root, capture_output=True, text=True, check=True,
        )
        if not result.stdout.startswith("100755 "):
            fail(f"head-not-executable {relative_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()
    if args.base is None and args.head != "HEAD":
        fail("head-requires-base")

    plugin_root = Path(__file__).resolve().parent.parent
    repo_root = plugin_root.parent.parent
    if args.base:
        validate_head_tree(repo_root, args.head)
        validate_release_version(repo_root, args.base, args.head)
        print("PASS hank-dev dual distribution")
        return

    claude_manifest = read_json(plugin_root / ".claude-plugin/plugin.json")
    codex_manifest = read_json(plugin_root / ".codex-plugin/plugin.json")
    claude_marketplace = read_json(repo_root / ".claude-plugin/marketplace.json")
    codex_marketplace = read_json(repo_root / ".agents/plugins/marketplace.json")

    for field in ("name", "version", "description"):
        if not claude_manifest.get(field) or not codex_manifest.get(field):
            fail(f"missing-manifest-field {field}")
        if claude_manifest[field] != codex_manifest[field]:
            fail(f"manifest-mismatch {field}")
    if codex_manifest.get("skills") != "./skills/":
        fail("codex-skills-path")

    expected_skill_paths = claude_manifest.get("skills", [])
    if not isinstance(expected_skill_paths, list) or not expected_skill_paths:
        fail("claude-manifest-skills")
    skill_directories = sorted(path for path in (plugin_root / "skills").iterdir() if path.is_dir())
    actual_skill_paths = [f"./skills/{path.name}/" for path in skill_directories]
    if sorted(expected_skill_paths) != actual_skill_paths:
        fail("claude-skill-list")
    for skill_dir in skill_directories:
        if not (skill_dir / "SKILL.md").is_file():
            fail(f"missing-skill {skill_dir.name}")

    claude_entries = claude_marketplace.get("plugins", [])
    codex_entries = codex_marketplace.get("plugins", [])
    if not isinstance(claude_entries, list) or not isinstance(codex_entries, list):
        fail("marketplace-plugin-list")
    claude_entry = next((entry for entry in claude_entries if entry.get("name") == "hank-dev"), None)
    codex_entry = next((entry for entry in codex_entries if entry.get("name") == "hank-dev"), None)
    if claude_entry is None or codex_entry is None:
        fail("marketplace-hank-dev-entry")
    if claude_entry.get("source") != "./plugins/hank-dev":
        fail("claude-marketplace-source")
    if codex_entry.get("source") != {"source": "local", "path": "./plugins/hank-dev"}:
        fail("codex-marketplace-source")
    if codex_entry.get("policy") != {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}:
        fail("codex-marketplace-policy")
    if codex_entry.get("category") != "Productivity":
        fail("codex-marketplace-category")

    for relative_path in REQUIRED_EXECUTABLES:
        path = plugin_root / relative_path
        if not path.is_file() or not os.access(path, os.X_OK):
            fail(f"not-executable {relative_path}")

    print("PASS hank-dev dual distribution")


if __name__ == "__main__":
    main()
