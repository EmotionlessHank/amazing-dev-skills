#!/usr/bin/env python3
import argparse
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DEFAULT_ROOT = Path(os.environ.get("WORKTREE_CLEANUP_ROOT", str(Path.home() / "AI")))
STATE_DIR = Path(os.environ.get("WORKTREE_CLEANUP_STATE_DIR", str(Path.home() / ".local/state/worktree-cleanup")))
MERGED_STATE = STATE_DIR / "merged-first-seen.json"
LATEST_JSON = STATE_DIR / "latest.json"
HISTORY_JSONL = STATE_DIR / "history.jsonl"
PENDING_REPORT = STATE_DIR / "pending-report.txt"
LOCK_PATH = STATE_DIR / "run.lock"
LOG_PATH = STATE_DIR / "worktree-cleanup.log"
GIT = "/usr/bin/git"
SSH = "/usr/bin/ssh"
DU = "/usr/bin/du"
LSOF = "/usr/sbin/lsof"
RMDIR = "/bin/rmdir"
SSH_ALIAS = os.environ.get("WORKTREE_CLEANUP_SSH_ALIAS", "worktree-relay")
RELAY_PATH = os.environ.get("WORKTREE_CLEANUP_RELAY_PATH", "~/.hermes/scripts/worktree-cleanup-relay.py")
MERGED_DAYS = 14
MAX_ATTENTION = 10
SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".cache",
    ".next",
    "dist",
    "build",
    "target",
    ".pytest_cache",
}


class CommandError(RuntimeError):
    def __init__(self, argv, returncode, stdout, stderr):
        super().__init__(f"Command failed: {argv[0]} rc={returncode}")
        self.argv = argv
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class CommandTimeout(RuntimeError):
    def __init__(self, argv):
        super().__init__(f"Command timed out: {argv[0]}")
        self.argv = argv


@dataclass
class WorktreeRecord:
    repo: str
    common_dir: str
    path: str
    head: str = ""
    branch_ref: str = ""
    locked: bool = False
    detached: bool = False
    prunable: bool = False
    is_main: bool = False
    status: str = "attention"
    reasons: list[str] = field(default_factory=list)
    size_kb: int = 0
    branch: str = ""
    merged: bool = False
    first_seen_at: Optional[float] = None
    eligible_at: Optional[float] = None

    def to_dict(self):
        return {
            "repo": self.repo,
            "common_dir": self.common_dir,
            "path": self.path,
            "head": self.head,
            "branch": self.branch,
            "locked": self.locked,
            "detached": self.detached,
            "prunable": self.prunable,
            "is_main": self.is_main,
            "status": self.status,
            "reasons": self.reasons,
            "size_kb": self.size_kb,
            "merged": self.merged,
            "first_seen_at": self.first_seen_at,
            "eligible_at": self.eligible_at,
        }


def now_ts():
    return time.time()


def iso_now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run_cmd(argv, timeout=30, check=True, cwd=None, input_text=None):
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise CommandTimeout(argv) from exc
    if check and result.returncode != 0:
        raise CommandError(argv, result.returncode, result.stdout, result.stderr)
    return result


def ensure_state_dir():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.touch(exist_ok=True)
    for path in (LATEST_JSON, HISTORY_JSONL, MERGED_STATE, PENDING_REPORT):
        if not path.exists():
            if path.suffix == ".json":
                path.write_text("{}\n", encoding="utf-8")
            else:
                path.touch()


def acquire_lock():
    ensure_state_dir()
    handle = open(LOCK_PATH, "a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(f"{iso_now()} another worktree-cleanup run is active, skipping this run.")
        return None
    return handle


def load_json(path, default):
    try:
        if not path.exists() or path.stat().st_size == 0:
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def atomic_write(path, text):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def is_relative_to(path: Path, parent: Path):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def normalized_path(path):
    expanded = Path(path).expanduser()
    if not expanded.is_absolute():
        expanded = Path.cwd() / expanded
    return Path(os.path.normpath(str(expanded)))


def has_symlink_ancestor(root: Path, target: Path):
    root = normalized_path(root)
    target = normalized_path(target)
    if not is_relative_to(target, root):
        return False
    rel = target.relative_to(root)
    current = root
    for part in rel.parts:
        current = current / part
        try:
            if current.is_symlink():
                return True
        except OSError:
            return True
    return False


def path_reasons(root: Path, path_text: str):
    reasons = []
    root_norm = normalized_path(root)
    path_norm = normalized_path(path_text)
    real = Path(os.path.realpath(str(path_norm)))
    if not is_relative_to(path_norm, root_norm):
        reasons.append("path is outside the allowed root")
    if str(path_norm) != str(real):
        reasons.append("normalized path does not match real target")
    if has_symlink_ancestor(root_norm, path_norm):
        reasons.append("symlink ancestor exists between root and target")
    return path_norm, reasons


def find_repo_roots(root: Path):
    roots = set()
    root_norm = normalized_path(root)
    if not root_norm.exists():
        return []
    for current, dirs, files in os.walk(root_norm):
        current_path = Path(current)
        if ".git" in dirs or ".git" in files:
            roots.add(str(current_path))
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    return sorted(roots)


def git_common_dir(repo):
    result = run_cmd([GIT, "-C", repo, "rev-parse", "--git-common-dir"], timeout=30)
    value = result.stdout.strip()
    common = Path(value)
    if not common.is_absolute():
        common = Path(repo) / common
    return str(normalized_path(common))


def has_external_git_config(repo):
    result = run_cmd(
        [GIT, "-C", repo, "config", "--local", "--get-regexp", "^(core\\.hooksPath|core\\.fsmonitor|filter\\..*\\.(process|clean|smudge)|diff\\..*\\.command)$"],
        timeout=30,
        check=False,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def parse_porcelain_z(text):
    tokens = [token for token in text.split("\0") if token]
    entries = []
    current = {}
    for token in tokens:
        if token.startswith("worktree "):
            if current:
                entries.append(current)
            current = {"worktree": token[len("worktree "):]}
        elif token.startswith("HEAD "):
            current["HEAD"] = token[len("HEAD "):]
        elif token.startswith("branch "):
            current["branch"] = token[len("branch "):]
        elif token == "detached":
            current["detached"] = True
        elif token.startswith("locked"):
            current["locked"] = True
        elif token.startswith("prunable"):
            current["prunable"] = True
        elif token == "bare":
            current["bare"] = True
    if current:
        entries.append(current)
    return entries


def list_worktrees(repo):
    result = run_cmd([GIT, "-C", repo, "worktree", "list", "--porcelain", "-z"], timeout=30)
    return parse_porcelain_z(result.stdout)


def branch_name(branch_ref):
    prefix = "refs/heads/"
    if branch_ref.startswith(prefix):
        return branch_ref[len(prefix):]
    return branch_ref


def status_reasons(path):
    reasons = []
    result = run_cmd(
        [GIT, "-C", path, "status", "--porcelain=v2", "-z", "--untracked-files=all"],
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        return ["git status check failed"]
    records = [item for item in result.stdout.split("\0") if item]
    for item in records:
        if item.startswith("? "):
            reasons.append("untracked files exist")
            break
    for item in records:
        if item.startswith(("1 ", "2 ", "u ")):
            reasons.append("tracked changes exist")
            break
    if records and not reasons:
        reasons.append("uncommitted state exists")
    return reasons


def ignored_count(path):
    result = run_cmd(
        [GIT, "-C", path, "ls-files", "--others", "--ignored", "--exclude-standard", "-z"],
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        return -1
    return len([item for item in result.stdout.split("\0") if item])


def has_submodule(path):
    if (Path(path) / ".gitmodules").exists():
        return True
    result = run_cmd([GIT, "-C", path, "submodule", "status", "--recursive"], timeout=30, check=False)
    return result.returncode == 0 and bool(result.stdout.strip())


def default_baseline(repo):
    result = run_cmd([GIT, "-C", repo, "symbolic-ref", "-q", "refs/remotes/origin/HEAD"], timeout=30, check=False)
    if result.returncode == 0:
        value = result.stdout.strip()
        if value:
            return value
    for ref in ("refs/heads/main", "refs/heads/master"):
        exists = run_cmd([GIT, "-C", repo, "show-ref", "--verify", "--quiet", ref], timeout=30, check=False)
        if exists.returncode == 0:
            return ref
    return None


def is_merged(repo, head, baseline):
    result = run_cmd([GIT, "-C", repo, "merge-base", "--is-ancestor", head, baseline], timeout=30, check=False)
    return result.returncode == 0


def size_kb(path):
    result = run_cmd([DU, "-sk", path], timeout=60, check=False)
    if result.returncode != 0:
        return 0
    try:
        return int(result.stdout.split()[0])
    except Exception:
        return 0


def lsof_reason(path):
    if not Path(LSOF).exists():
        return "lsof is unavailable"
    try:
        result = run_cmd([LSOF, "+D", path], timeout=5, check=False)
    except CommandTimeout:
        return "lsof check timed out"
    if result.returncode == 0 and result.stdout.strip():
        return "active process is using this worktree"
    if result.returncode not in (0, 1):
        return "lsof check failed"
    return None


def merged_key(common_dir, path, head):
    raw = f"{common_dir}\n{path}\n{head}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def update_merged_state(state, record, merged, current_time):
    prefix = hashlib.sha256(f"{record.common_dir}\n{record.path}\n".encode("utf-8")).hexdigest()
    stale = [key for key, value in state.items() if value.get("prefix") == prefix]
    key = merged_key(record.common_dir, record.path, record.head)
    if not merged:
        for item in stale:
            state.pop(item, None)
        return None, None
    if key not in state:
        for item in stale:
            state.pop(item, None)
        state[key] = {"prefix": prefix, "first_seen_at": current_time}
    first_seen = float(state[key]["first_seen_at"])
    eligible_at = first_seen + MERGED_DAYS * 86400
    return first_seen, eligible_at


def snapshot(path):
    st = Path(path).stat()
    return {
        "path": str(normalized_path(path)),
        "inode": st.st_ino,
        "mtime_ns": st.st_mtime_ns,
        "head": run_cmd([GIT, "-C", path, "rev-parse", "HEAD"], timeout=30).stdout.strip(),
        "branch": run_cmd([GIT, "-C", path, "branch", "--show-current"], timeout=30, check=False).stdout.strip(),
        "status": status_reasons(path),
        "ignored": ignored_count(path),
        "submodule": has_submodule(path),
        "lsof": lsof_reason(path),
    }


def classify_records(root: Path):
    root_norm = normalized_path(root)
    repos = find_repo_roots(root_norm)
    common_seen = {}
    state = load_json(MERGED_STATE, {})
    current_time = now_ts()
    records = []
    errors = []
    for repo in repos:
        try:
            common = git_common_dir(repo)
            if common in common_seen:
                continue
            common_seen[common] = repo
            external_config = has_external_git_config(repo)
            entries = list_worktrees(repo)
        except Exception as exc:
            errors.append({"repo": repo, "error": str(exc)})
            continue
        repo_anchor = str(normalized_path(entries[0].get("worktree", repo))) if entries else repo
        baseline = None if external_config else default_baseline(repo_anchor)
        for index, entry in enumerate(entries):
            raw_path = entry.get("worktree", "")
            path_norm, reasons = path_reasons(root_norm, raw_path)
            record = WorktreeRecord(
                repo=repo_anchor,
                common_dir=common,
                path=str(path_norm),
                head=entry.get("HEAD", ""),
                branch_ref=entry.get("branch", ""),
                locked=bool(entry.get("locked")),
                detached=bool(entry.get("detached")),
                prunable=bool(entry.get("prunable")),
                is_main=index == 0,
                branch=branch_name(entry.get("branch", "")),
            )
            record.reasons.extend(reasons)
            if record.is_main:
                record.status = "main"
                records.append(record)
                continue
            if external_config:
                record.reasons.append("repository has external Git extension configuration")
            if record.locked:
                record.reasons.append("worktree is locked")
            if record.detached or not record.branch_ref:
                record.reasons.append("detached HEAD")
            if record.prunable:
                record.reasons.append("Git metadata is prunable")
            if not Path(record.path).exists():
                record.reasons.append("worktree path does not exist")
            if not record.reasons:
                try:
                    record.reasons.extend(status_reasons(record.path))
                    ignored = ignored_count(record.path)
                    if ignored < 0:
                        record.reasons.append("ignored file check failed")
                    elif ignored > 0:
                        record.reasons.append(f"{ignored} ignored object(s) exist")
                    if has_submodule(record.path):
                        record.reasons.append("submodule exists")
                    baseline_ref = baseline
                    if not baseline_ref:
                        record.reasons.append("default baseline is ambiguous")
                    else:
                        record.merged = is_merged(repo, record.head, baseline_ref)
                        if not record.merged:
                            record.reasons.append("branch is not merged into the default baseline")
                    active = lsof_reason(record.path)
                    if active:
                        record.reasons.append(active)
                except Exception as exc:
                    record.reasons.append(f"audit failed: {exc}")
            record.size_kb = size_kb(record.path) if Path(record.path).exists() else 0
            if not record.reasons and record.merged:
                first_seen, eligible_at = update_merged_state(state, record, True, current_time)
                record.first_seen_at = first_seen
                record.eligible_at = eligible_at
                if eligible_at and current_time >= eligible_at:
                    record.status = "candidate"
                else:
                    record.status = "attention"
                    record.reasons.append("merged but not continuously observed for 14 days")
            else:
                update_merged_state(state, record, False, current_time)
                if record.status != "main":
                    record.status = "attention" if record.reasons else "attention"
            records.append(record)
    atomic_write(MERGED_STATE, json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return list(common_seen.values()), records, errors


def prune_empty_containers(root: Path):
    cleaned = []
    errors = []
    root_norm = normalized_path(root)
    candidates = []
    for container in root_norm.glob(".worktrees/*"):
        if not container.is_dir() or container.is_symlink():
            continue
        try:
            next(container.iterdir())
        except StopIteration:
            candidates.append(container)
        except OSError as exc:
            errors.append({"path": str(container), "error": str(exc)})
    for item in candidates:
        try:
            run_cmd([RMDIR, str(item)], timeout=5, check=True)
            cleaned.append(str(item))
        except Exception as exc:
            errors.append({"path": str(item), "error": str(exc)})
    return cleaned, errors


def build_summary(root, repos, records, errors, cleaned):
    linked = [record for record in records if not record.is_main]
    candidates = [record for record in linked if record.status == "candidate"]
    attention = [record for record in linked if record.status == "attention"]
    anomaly_count = len(errors) + sum(1 for record in attention if any("path" in reason or "failed" in reason for reason in record.reasons))
    candidate_size = sum(record.size_kb for record in candidates)
    return {
        "generated_at": iso_now(),
        "root": str(normalized_path(root)),
        "repo_count": len(repos),
        "linked_worktree_count": len(linked),
        "empty_containers_cleaned": len(cleaned),
        "empty_container_paths": cleaned,
        "candidate_count": len(candidates),
        "candidate_size_kb": candidate_size,
        "attention_count": len(attention),
        "anomaly_count": anomaly_count,
        "candidates": [record.to_dict() for record in candidates],
        "attention": [record.to_dict() for record in attention],
        "main": [record.to_dict() for record in records if record.is_main],
        "errors": errors,
    }


def human_size(kb):
    if kb >= 1024 * 1024:
        return f"{kb / 1024 / 1024:.1f} GB"
    if kb >= 1024:
        return f"{kb / 1024:.1f} MB"
    return f"{kb} KB"


def report_text(summary):
    lines = [
        f"Worktree audit {summary['generated_at']}",
        "",
        f"Scanned: {summary['repo_count']} repos, {summary['linked_worktree_count']} linked worktrees",
        f"Empty containers removed: {summary['empty_containers_cleaned']}",
        f"Manual cleanup candidates: {summary['candidate_count']}, approx {human_size(summary['candidate_size_kb'])}",
        f"Attention: {summary['attention_count']}",
        f"Anomalies: {summary['anomaly_count']}",
    ]
    candidates = summary["candidates"][:MAX_ATTENTION]
    attention = summary["attention"][:MAX_ATTENTION]
    if candidates:
        lines.extend(["", "Manual cleanup candidates"])
        for item in candidates:
            lines.append(f"* {Path(item['repo']).name} / {item['branch'] or Path(item['path']).name}: {human_size(item['size_kb'])}, requires explicit cleanup-approved")
    if attention:
        lines.extend(["", "Needs attention"])
        for item in attention[: max(0, MAX_ATTENTION - len(candidates))]:
            reason = "; ".join(item["reasons"][:3]) or "requires manual review"
            lines.append(f"* {Path(item['repo']).name} / {item['branch'] or Path(item['path']).name}: {reason}, {human_size(item['size_kb'])}")
    if summary["errors"]:
        lines.extend(["", "Anomalies"])
        for item in summary["errors"][:MAX_ATTENTION]:
            lines.append(f"* {Path(item['repo']).name}: {item['error']}")
    if not candidates and not attention and not summary["errors"]:
        lines.append("")
        lines.append("No linked worktree needs action in this run.")
    lines.append("")
    lines.append(f"Full report: {LATEST_JSON}")
    return "\n".join(lines)


def persist_summary(summary, text):
    atomic_write(LATEST_JSON, json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    with open(HISTORY_JSONL, "a", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "generated_at": summary["generated_at"],
            "repo_count": summary["repo_count"],
            "linked_worktree_count": summary["linked_worktree_count"],
            "candidate_count": summary["candidate_count"],
            "attention_count": summary["attention_count"],
            "anomaly_count": summary["anomaly_count"],
        }, ensure_ascii=False) + "\n")
    atomic_write(PENDING_REPORT, text + "\n")


def send_telegram(text):
    argv = [
        SSH,
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "ConnectTimeout=10",
        SSH_ALIAS,
        "/usr/bin/python3",
        RELAY_PATH,
    ]
    last_error = None
    for _ in range(3):
        try:
            result = run_cmd(argv, timeout=45, check=False, input_text=text)
        except Exception as exc:
            last_error = str(exc)
            continue
        if result.returncode == 0:
            PENDING_REPORT.write_text("", encoding="utf-8")
            return True, result.stdout.strip()
        last_error = result.stderr.strip() or result.stdout.strip() or f"rc={result.returncode}"
    return False, last_error or "send failed"


def run_audit(args):
    root = normalized_path(args.root)
    repos, records, errors = classify_records(root)
    cleaned = []
    clean_errors = []
    if args.prune_empty_containers:
        cleaned, clean_errors = prune_empty_containers(root)
        errors.extend(clean_errors)
    summary = build_summary(root, repos, records, errors, cleaned)
    text = report_text(summary)
    persist_summary(summary, text)
    if args.send_telegram:
        ok, detail = send_telegram(text)
        summary["telegram_sent"] = ok
        summary["telegram_detail"] = detail
        atomic_write(LATEST_JSON, json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        if not ok:
            print(f"Telegram send failed: {detail}", file=sys.stderr)
            print(text)
            return 3
    print(text)
    return 0


def find_record_for_path(root, target_path):
    repos, records, errors = classify_records(root)
    target = str(normalized_path(target_path))
    for record in records:
        if record.path == target:
            return record, errors
    return None, errors


def branch_exists(repo, branch):
    if not branch:
        return False
    result = run_cmd([GIT, "-C", repo, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], timeout=30, check=False)
    return result.returncode == 0


def commit_exists(repo, head):
    result = run_cmd([GIT, "-C", repo, "cat-file", "-e", f"{head}^{{commit}}"], timeout=30, check=False)
    return result.returncode == 0


def run_cleanup_approved(args):
    root = normalized_path(args.root)
    target = normalized_path(args.path)
    if not Path(args.path).is_absolute():
        print("cleanup-approved requires an absolute path", file=sys.stderr)
        return 2
    record, errors = find_record_for_path(root, target)
    if errors:
        print("audit has anomalies, cleanup stopped", file=sys.stderr)
        return 3
    if not record:
        print("specified path is not a registered linked worktree", file=sys.stderr)
        return 4
    if record.is_main:
        print("refusing to clean the main worktree", file=sys.stderr)
        return 5
    if record.status != "candidate":
        print("specified object did not pass all cleanup gates:", "; ".join(record.reasons), file=sys.stderr)
        return 6
    before = snapshot(record.path)
    if before["status"] or before["ignored"] != 0 or before["submodule"] or before["lsof"]:
        print("second snapshot found risk, cleanup stopped", file=sys.stderr)
        return 7
    result = run_cmd([GIT, "-C", record.repo, "worktree", "remove", record.path], timeout=30, check=False)
    if result.returncode != 0:
        print("Git refused to remove the worktree", file=sys.stderr)
        return 8
    branch_ok = branch_exists(record.repo, record.branch)
    commit_ok = commit_exists(record.repo, record.head)
    payload = {
        "cleaned_at": iso_now(),
        "path": record.path,
        "repo": record.repo,
        "branch": record.branch,
        "head": record.head,
        "branch_exists": branch_ok,
        "commit_exists": commit_ok,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    if not branch_ok or not commit_ok:
        return 9
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description="Audit and safely clean Git worktrees")
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit")
    audit.add_argument("--root", default=str(DEFAULT_ROOT))
    audit.add_argument("--send-telegram", action="store_true")
    audit.add_argument("--prune-empty-containers", action="store_true")
    cleanup = sub.add_parser("cleanup-approved")
    cleanup.add_argument("--root", default=str(DEFAULT_ROOT))
    cleanup.add_argument("--path", required=True)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    lock = acquire_lock()
    if lock is None:
        return 0
    start = now_ts()
    try:
        if args.command == "audit":
            rc = run_audit(args)
        else:
            rc = run_cleanup_approved(args)
        if now_ts() - start > 15 * 60:
            print("task exceeded the 15 minute budget", file=sys.stderr)
            return 124
        return rc
    finally:
        lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
