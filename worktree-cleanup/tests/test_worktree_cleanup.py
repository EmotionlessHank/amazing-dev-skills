import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "worktree_cleanup.py"
RELAY = Path(__file__).resolve().parents[1] / "scripts" / "worktree_cleanup_relay.py"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


wtc = load_module(SCRIPT, "wtc_under_test")
relay = load_module(RELAY, "relay_under_test")


def git(cwd, *args, check=True):
    return subprocess.run(
        ["/usr/bin/git", "-C", str(cwd), *args],
        text=True,
        capture_output=True,
        check=check,
    )


def git_with_env(cwd, env, *args, check=True):
    merged_env = os.environ.copy()
    merged_env.update(env)
    return subprocess.run(
        ["/usr/bin/git", "-C", str(cwd), *args],
        text=True,
        capture_output=True,
        check=check,
        env=merged_env,
    )


class RepoFixture:
    def __init__(self, case):
        self.case = case
        self.tmp = tempfile.TemporaryDirectory(prefix="wtc-test-", dir="/private/tmp")
        self.root = Path(self.tmp.name) / "AI"
        self.root.mkdir()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git(self.repo, "init")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "Tester")
        (self.repo / "README.md").write_text("base\n", encoding="utf-8")
        git(self.repo, "add", "README.md")
        git(self.repo, "commit", "-m", "base")
        git(self.repo, "branch", "-M", "main")

    def close(self):
        self.tmp.cleanup()

    def add_worktree(self, name="feature", path=None):
        git(self.repo, "branch", name)
        wt_path = path or (self.root / ".worktrees" / name)
        wt_path.parent.mkdir(parents=True, exist_ok=True)
        git(self.repo, "worktree", "add", str(wt_path), name)
        return wt_path


class WorktreeCleanupTests(unittest.TestCase):
    def setUp(self):
        self.old_state_dir = wtc.STATE_DIR
        self.old_merged = wtc.MERGED_STATE
        self.old_latest = wtc.LATEST_JSON
        self.old_history = wtc.HISTORY_JSONL
        self.old_pending = wtc.PENDING_REPORT
        self.old_lock = wtc.LOCK_PATH
        self.old_log = wtc.LOG_PATH
        self.state_tmp = tempfile.TemporaryDirectory(prefix="wtc-state-", dir="/private/tmp")
        state = Path(self.state_tmp.name)
        wtc.STATE_DIR = state
        wtc.MERGED_STATE = state / "merged-first-seen.json"
        wtc.LATEST_JSON = state / "latest.json"
        wtc.HISTORY_JSONL = state / "history.jsonl"
        wtc.PENDING_REPORT = state / "pending-report.txt"
        wtc.LOCK_PATH = state / "run.lock"
        wtc.LOG_PATH = state / "worktree-cleanup.log"

    def tearDown(self):
        wtc.STATE_DIR = self.old_state_dir
        wtc.MERGED_STATE = self.old_merged
        wtc.LATEST_JSON = self.old_latest
        wtc.HISTORY_JSONL = self.old_history
        wtc.PENDING_REPORT = self.old_pending
        wtc.LOCK_PATH = self.old_lock
        wtc.LOG_PATH = self.old_log
        self.state_tmp.cleanup()

    def audit(self, root):
        wtc.ensure_state_dir()
        repos, records, errors = wtc.classify_records(root)
        return wtc.build_summary(root, repos, records, errors, [])

    def test_main_worktree_is_never_candidate(self):
        fixture = RepoFixture(self)
        try:
            summary = self.audit(fixture.root)
            self.assertEqual(summary["linked_worktree_count"], 0)
            self.assertEqual(summary["candidate_count"], 0)
        finally:
            fixture.close()

    def test_periodic_candidate_is_reported_not_removed(self):
        fixture = RepoFixture(self)
        try:
            wt_path = fixture.add_worktree()
            wtc.ensure_state_dir()
            repos, records, _ = wtc.classify_records(fixture.root)
            linked = [record for record in records if not record.is_main][0]
            key = wtc.merged_key(linked.common_dir, linked.path, linked.head)
            prefix = wtc.MERGED_STATE.read_text(encoding="utf-8")
            state = json.loads(prefix)
            state[key]["first_seen_at"] = time.time() - 15 * 86400
            wtc.MERGED_STATE.write_text(json.dumps(state), encoding="utf-8")
            summary = self.audit(fixture.root)
            self.assertTrue(wt_path.exists())
            self.assertEqual(summary["candidate_count"], 1)
        finally:
            fixture.close()

    def test_unmerged_clean_worktree_is_attention(self):
        fixture = RepoFixture(self)
        try:
            wt_path = fixture.add_worktree()
            (wt_path / "feature.txt").write_text("feature\n", encoding="utf-8")
            git(wt_path, "add", "feature.txt")
            git(wt_path, "commit", "-m", "feature")
            summary = self.audit(fixture.root)
            self.assertEqual(summary["candidate_count"], 0)
            self.assertIn("branch is not merged into the default baseline", summary["attention"][0]["reasons"])
        finally:
            fixture.close()

    def test_ignored_content_blocks_cleanup_approved(self):
        fixture = RepoFixture(self)
        try:
            wt_path = fixture.add_worktree()
            (wt_path / ".gitignore").write_text(".env\n", encoding="utf-8")
            git(wt_path, "add", ".gitignore")
            git(wt_path, "commit", "-m", "ignore-env")
            git(fixture.repo, "merge", "feature")
            (wt_path / ".env").write_text("ignored fixture\n", encoding="utf-8")
            rc = wtc.main(["cleanup-approved", "--root", str(fixture.root), "--path", str(wt_path)])
            self.assertNotEqual(rc, 0)
            self.assertTrue(wt_path.exists())
        finally:
            fixture.close()

    def test_dirty_locked_detached_and_submodule_are_blocked(self):
        fixture = RepoFixture(self)
        try:
            dirty = fixture.add_worktree("dirty")
            (dirty / "README.md").write_text("changed\n", encoding="utf-8")
            locked = fixture.add_worktree("locked")
            git(fixture.repo, "worktree", "lock", str(locked))
            detached = fixture.root / ".worktrees" / "detached"
            git(fixture.repo, "worktree", "add", "--detach", str(detached), "main")
            sub = fixture.add_worktree("submodule")
            (sub / ".gitmodules").write_text("[submodule]\n", encoding="utf-8")
            summary = self.audit(fixture.root)
            reasons = {Path(item["path"]).name: "；".join(item["reasons"]) for item in summary["attention"]}
            self.assertIn("tracked", reasons["dirty"])
            self.assertIn("locked", reasons["locked"])
            self.assertIn("detached", reasons["detached"])
            self.assertIn("submodule", reasons["submodule"])
        finally:
            fixture.close()

    def test_path_prefix_and_symlink_escape_are_attention(self):
        with tempfile.TemporaryDirectory(prefix="wtc-prefix-", dir="/private/tmp") as tmp:
            root = Path(tmp) / "AI"
            outside = Path(tmp) / "AI-other"
            root.mkdir()
            outside.mkdir()
            repo = root / "repo"
            repo.mkdir()
            git(repo, "init")
            git(repo, "config", "user.email", "test@example.com")
            git(repo, "config", "user.name", "Tester")
            (repo / "README.md").write_text("base\n", encoding="utf-8")
            git(repo, "add", "README.md")
            git(repo, "commit", "-m", "base")
            git(repo, "branch", "-M", "main")
            git(repo, "branch", "outside")
            git(repo, "worktree", "add", str(outside / "wt"), "outside")
            summary = self.audit(root)
            self.assertIn("path is outside the allowed root", summary["attention"][0]["reasons"])

            link_target = Path(tmp) / "link-target"
            link_target.mkdir()
            link = root / "link"
            link.symlink_to(link_target)
            git(repo, "branch", "symlinked")
            git(repo, "worktree", "add", str(link / "wt"), "symlinked")
            summary = self.audit(root)
            all_reasons = [reason for item in summary["attention"] for reason in item["reasons"]]
            self.assertIn("path is outside the allowed root", all_reasons)
            _, direct_reasons = wtc.path_reasons(root, str(link / "wt"))
            self.assertIn("symlink ancestor exists between root and target", direct_reasons)

    def test_common_dir_outside_root_is_not_pruned(self):
        with tempfile.TemporaryDirectory(prefix="wtc-common-", dir="/private/tmp") as tmp:
            root = Path(tmp) / "AI"
            root.mkdir()
            repo = Path(tmp) / "work" / "repo"
            repo.mkdir(parents=True)
            git(repo, "init")
            git(repo, "config", "user.email", "test@example.com")
            git(repo, "config", "user.name", "Tester")
            (repo / "README.md").write_text("base\n", encoding="utf-8")
            git(repo, "add", "README.md")
            git(repo, "commit", "-m", "base")
            git(repo, "branch", "-M", "main")
            git(repo, "branch", "linked")
            wt_path = root / "linked"
            git(repo, "worktree", "add", str(wt_path), "linked")
            with mock.patch.object(wtc, "run_cmd", wraps=wtc.run_cmd) as wrapped:
                summary = self.audit(root)
            self.assertTrue(wt_path.exists())
            self.assertEqual(summary["linked_worktree_count"], 1)
            calls = [" ".join(call.args[0]) for call in wrapped.call_args_list]
            self.assertFalse(any("prune" in call for call in calls))

    def test_old_commit_first_observed_is_not_candidate(self):
        fixture = RepoFixture(self)
        try:
            wt_path = fixture.add_worktree()
            (wt_path / "old.txt").write_text("old\n", encoding="utf-8")
            git(wt_path, "add", "old.txt")
            git_with_env(
                wt_path,
                {
                    "GIT_AUTHOR_DATE": "2001-01-01T00:00:00+0000",
                    "GIT_COMMITTER_DATE": "2001-01-01T00:00:00+0000",
                },
                "commit",
                "-m",
                "old-commit",
            )
            git(fixture.repo, "merge", "feature")
            summary = self.audit(fixture.root)
            self.assertEqual(summary["candidate_count"], 0)
            self.assertIn("merged but not continuously observed for 14 days", summary["attention"][0]["reasons"])
        finally:
            fixture.close()

    def test_head_change_resets_merge_timer(self):
        fixture = RepoFixture(self)
        try:
            wt_path = fixture.add_worktree()
            self.audit(fixture.root)
            state = json.loads(wtc.MERGED_STATE.read_text(encoding="utf-8"))
            for value in state.values():
                value["first_seen_at"] = time.time() - 15 * 86400
            wtc.MERGED_STATE.write_text(json.dumps(state), encoding="utf-8")
            (wt_path / "new.txt").write_text("new\n", encoding="utf-8")
            git(wt_path, "add", "new.txt")
            git(wt_path, "commit", "-m", "new")
            git(fixture.repo, "merge", "feature")
            summary = self.audit(fixture.root)
            self.assertEqual(summary["candidate_count"], 0)
            self.assertIn("merged but not continuously observed for 14 days", summary["attention"][0]["reasons"])
        finally:
            fixture.close()

    def test_lsof_timeout_is_attention(self):
        fixture = RepoFixture(self)
        try:
            fixture.add_worktree()
            real_run = wtc.run_cmd

            def fake_run(argv, *args, **kwargs):
                if argv and argv[0] == wtc.LSOF:
                    raise wtc.CommandTimeout(argv)
                return real_run(argv, *args, **kwargs)

            with mock.patch.object(wtc, "run_cmd", side_effect=fake_run):
                summary = self.audit(fixture.root)
            self.assertIn("lsof check timed out", summary["attention"][0]["reasons"])
        finally:
            fixture.close()

    def test_empty_container_rmdir_race_leaves_directory(self):
        with tempfile.TemporaryDirectory(prefix="wtc-rmdir-", dir="/private/tmp") as tmp:
            root = Path(tmp) / "AI"
            empty = root / ".worktrees" / "old"
            empty.mkdir(parents=True)
            real_run = wtc.run_cmd

            def fake_run(argv, *args, **kwargs):
                if argv and argv[0] == wtc.RMDIR:
                    (empty / "late").write_text("x", encoding="utf-8")
                return real_run(argv, *args, **kwargs)

            with mock.patch.object(wtc, "run_cmd", side_effect=fake_run):
                cleaned, errors = wtc.prune_empty_containers(root)
            self.assertEqual(cleaned, [])
            self.assertTrue(errors)
            self.assertTrue(empty.exists())

    def test_relay_http_ok_false_fails(self):
        with tempfile.TemporaryDirectory(prefix="wtc-relay-", dir="/private/tmp") as tmp:
            env = Path(tmp) / ".env"
            env.write_text("TELEGRAM_BOT_TOKEN=dummy\nTELEGRAM_HOME_CHANNEL=123\n", encoding="utf-8")
            os.chmod(env, 0o600)

            class Response:
                status = 200

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

                def read(self):
                    return b'{"ok": false}'

                def getcode(self):
                    return 200

            with mock.patch("pwd.getpwuid", return_value=type("P", (), {"pw_name": "ubuntu"})()):
                with mock.patch("urllib.request.urlopen", return_value=Response()):
                    with self.assertRaises(RuntimeError):
                        relay.send_message("hello", str(env))

    def test_token_not_logged_on_relay_failure(self):
        with tempfile.TemporaryDirectory(prefix="wtc-relay-", dir="/private/tmp") as tmp:
            env = Path(tmp) / ".env"
            env.write_text("TELEGRAM_BOT_TOKEN=dummy\nTELEGRAM_HOME_CHANNEL=123\n", encoding="utf-8")
            os.chmod(env, 0o600)
            stderr = io.StringIO()

            def fail_urlopen(request, timeout=20):
                self.assertIn("dummy", request.full_url)
                raise RuntimeError("network down")

            with mock.patch("pwd.getpwuid", return_value=type("P", (), {"pw_name": "ubuntu"})()):
                with mock.patch("urllib.request.urlopen", side_effect=fail_urlopen) as opened:
                    with mock.patch("sys.stderr", stderr):
                        with self.assertRaises(RuntimeError):
                            relay.send_message("hello", str(env))
            self.assertTrue(opened.called)
            self.assertNotIn("dummy", stderr.getvalue())

    def test_cleanup_approved_removes_worktree_keeps_branch_and_commit(self):
        fixture = RepoFixture(self)
        try:
            wt_path = fixture.add_worktree()
            self.audit(fixture.root)
            state = json.loads(wtc.MERGED_STATE.read_text(encoding="utf-8"))
            for value in state.values():
                value["first_seen_at"] = time.time() - 15 * 86400
            wtc.MERGED_STATE.write_text(json.dumps(state), encoding="utf-8")
            rc = wtc.main(["cleanup-approved", "--root", str(fixture.root), "--path", str(wt_path)])
            self.assertEqual(rc, 0)
            self.assertFalse(wt_path.exists())
            self.assertEqual(git(fixture.repo, "show-ref", "--verify", "--quiet", "refs/heads/feature").returncode, 0)
            head = git(fixture.repo, "rev-parse", "feature").stdout.strip()
            self.assertEqual(git(fixture.repo, "cat-file", "-e", f"{head}^{{commit}}").returncode, 0)
        finally:
            fixture.close()


if __name__ == "__main__":
    unittest.main()
