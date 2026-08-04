#!/usr/bin/env python3
"""验证 hank-dev 的 Claude 与 Codex 分发 metadata 不漂移。"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REQUIRED_EXECUTABLES = (
    "scripts/check-review-patch.sh",
    "scripts/run-deepseek-review.py",
    "scripts/validate-review-security.sh",
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


def main() -> None:
    plugin_root = Path(__file__).resolve().parent.parent
    repo_root = plugin_root.parent.parent
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
