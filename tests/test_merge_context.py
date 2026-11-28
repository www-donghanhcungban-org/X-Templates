"""Offline acceptance tests for merge-watch context checkpoints."""

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cpu_budget
from test_merge_target_binding import HOST, PR, SLUG, RouteDouble, pr_url
from test_xt_cli import TmpRepoCase, run_main, xt
import xt_merge_intent


class MergeContextTest(TmpRepoCase):
    def setUp(self):
        super().setUp()
        self.init_repo()
        env = {k: v for k, v in os.environ.items() if not k.startswith(("GH_", "GITHUB_"))}
        self.enterContext(mock.patch.dict(os.environ, {**env, "CLAUDE_PROJECT_DIR": str(self.repo)}, clear=True))
        self.basis = self.commit_files(
            {".gitignore": ".autopilot/\n", "xt.yaml": "merge_autonomy: L3\nmerge_review: optional\n"}, 1700000000
        )
        self.git("update-ref", "refs/remotes/origin/main", self.basis)
        self.head = self.commit_files({"README.md": "candidate\n"}, 1700000001)
        self.git("remote", "add", "origin", f"https://{HOST}/{SLUG}.git")
        self.gh = RouteDouble(self.head, self.basis)
        self.gh.merged = True
        self.enterContext(mock.patch.object(xt.subprocess, "run", side_effect=self.gh.respond))

    def watch(self, *extra):
        return run_main("merge-watch", "--pr", pr_url(), *extra)

    def checkpoints(self):
        return list((self.repo / ".autopilot").glob("merge-context-*.json"))

    def test_only_opt_in_records_pinned_merge_metadata(self):
        rc, out, err = self.watch()
        self.assertEqual(rc, 0, err)
        self.assertIn("PR đã MERGED", out)
        self.assertEqual(self.checkpoints(), [])
        (original_read,) = [call for call in self.gh.calls if call[2].endswith(f"/pulls/{PR}")]
        self.gh.calls.clear()
        rc, observed, err = self.watch("--observe-context")
        self.assertEqual(rc, 0, err)
        self.assertEqual(out.partition("]")[2], observed.partition("]")[2])
        self.assertEqual([call for call in self.gh.calls if call[2].endswith(f"/pulls/{PR}")], [original_read] * 2)
        (checkpoint,) = self.checkpoints()
        self.assertEqual(
            json.loads(checkpoint.read_bytes()),
            {
                "schema": 1,
                "host": HOST,
                "repo": SLUG,
                "pr": int(PR),
                "head": self.head,
                "merge_sha": self.gh.merged_sha,
                "base_branch": "main",
            },
        )
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertEqual(self.git("rev-parse", "HEAD"), self.head)

    def test_closed_unmerged_and_eligible_pr_do_not_record(self):
        self.gh.merged = False
        for state, rc in [("closed", 1), ("open", 0)]:
            with (
                self.subTest(state=state),
                mock.patch.object(self.gh, "pull", return_value={**self.gh.pull(HOST, SLUG), "state": state}),
            ):
                before = self.watch()
                calls = len(self.gh.calls)
                self.gh.calls.clear()
                after = self.watch("--observe-context")
                self.assertEqual(before[0], rc, before)
                self.assertEqual(after[0], rc, after)
                self.assertEqual(len(self.gh.calls), calls)
                self.assertEqual(self.checkpoints(), [])
                self.gh.calls.clear()

    def test_recovery_rejects_bad_bytes_and_rebuilds_from_rest(self):
        self.assertEqual(self.watch("--observe-context")[0], 0)
        (checkpoint,) = self.checkpoints()
        canonical = checkpoint.read_bytes()
        stale = canonical.replace(self.gh.merged_sha.encode(), b"b" * 40)
        mismatched = canonical.replace(HOST.encode(), b"another.example")
        for raw in (b"[", b"\xff", stale, mismatched, canonical + b" " * 4096, canonical.replace(b"1", b"2", 1)):
            with self.subTest(raw=raw[:50]):
                checkpoint.write_bytes(raw)
                self.assertEqual(self.watch("--observe-context")[0], 0)
                self.assertEqual(checkpoint.read_bytes(), canonical)
        with mock.patch.object(xt, "write_atomic", wraps=xt.write_atomic) as write:
            self.assertEqual(self.watch("--observe-context")[0], 0)
        write.assert_not_called()
        self.assertTrue(all(call[0:2] == ("GET", HOST) for call in self.gh.calls))

    def test_disagreement_and_failed_read_leave_checkpoint_untouched(self):
        self.assertEqual(self.watch("--observe-context")[0], 0)
        (checkpoint,) = self.checkpoints()
        checkpoint.write_bytes(b"stale")
        rest = self.gh.pull(HOST, SLUG)
        route = f"repos/{SLUG}/pulls/{PR}"
        responses = [
            (1, ""),
            (0, "{"),
            (0, "{} {}"),
            (0, "[null]"),
            (0, json.dumps({**rest, "html_url": pr_url("another.example")})),
            (0, json.dumps({**rest, "head": {"sha": "b" * 40}})),
            (0, json.dumps({**rest, "merged": 1})),
            (0, json.dumps({**rest, "state": "open"})),
            (0, json.dumps({**rest, "merge_commit_sha": None})),
            (0, json.dumps({**rest, "merge_commit_sha": "short"})),
            (0, json.dumps({**rest, "base": {**rest["base"], "ref": None}})),
            (0, json.dumps({**rest, "base": {**rest["base"], "ref": "x" * 256}})),
            (0, json.dumps({**rest, "base": {**rest["base"], "ref": "\n"}})),
            (0, json.dumps({**rest, "base": {**rest["base"], "ref": "main..next"}})),
        ]
        for rc, body in responses:
            self.gh.calls.clear()

            def run(argv, **kwargs):
                if route in argv and any(c[2] == route for c in self.gh.calls):
                    return subprocess.CompletedProcess(argv, rc, body, "fixture")
                return self.gh.respond(argv, **kwargs)

            with self.subTest(body=body[:60]), mock.patch.object(xt.subprocess, "run", side_effect=run):
                result, out, err = self.watch("--observe-context")
                self.assertEqual((result, err), (0, ""), out)
                self.assertIn("PR đã MERGED", out)
                self.assertEqual(checkpoint.read_bytes(), b"stale")

    def test_storage_errors_do_not_change_merged_exit(self):
        with mock.patch.object(xt, "write_atomic", side_effect=OSError("fixture")):
            self.assertEqual(self.watch("--observe-context")[0], 0)
        self.assertEqual(self.checkpoints(), [])
        with mock.patch.object(xt_merge_intent, "MAX_CHECKPOINT_BYTES", 30):
            self.assertEqual(self.watch("--observe-context")[0], 0)
        self.assertEqual(self.checkpoints(), [])
        self.assertEqual(self.watch("--observe-context")[0], 0)
        (checkpoint,) = self.checkpoints()
        checkpoint.unlink()
        checkpoint.mkdir()
        self.assertEqual(self.watch("--observe-context")[0], 0)
        self.assertTrue(checkpoint.is_dir())
        checkpoint.rmdir()
        outside = self.tmp / "outside"
        outside.write_text("fixture", encoding="utf-8")
        checkpoint.symlink_to(outside)
        self.assertEqual(self.watch("--observe-context")[0], 0)
        self.assertTrue(checkpoint.is_symlink())
        self.assertEqual(outside.read_text(encoding="utf-8"), "fixture")

    def test_only_ignored_untracked_state_can_be_written(self):
        ignore = self.repo / ".gitignore"
        ignore.write_text("", encoding="utf-8")
        self.assertEqual(self.watch("--observe-context")[0], 0)
        self.assertFalse((self.repo / ".autopilot").exists())
        ignore.write_text(".autopilot/merge-context-*.json\n", encoding="utf-8")
        self.assertEqual(self.watch("--observe-context")[0], 0)
        self.assertFalse((self.repo / ".autopilot").exists())
        ignore.write_text(".autopilot/\n", encoding="utf-8")
        self.assertEqual(self.watch("--observe-context")[0], 0)
        (checkpoint,) = self.checkpoints()
        checkpoint.write_bytes(b"tracked")
        self.git("add", "-f", str(checkpoint))
        self.assertEqual(self.watch("--observe-context")[0], 0)
        self.assertEqual(checkpoint.read_bytes(), b"tracked")

    def test_simultaneous_observers_commit_once(self):
        _, decision, _ = xt._merge_check_json(pr_url())
        before_save = Barrier(2, timeout=cpu_budget.HANG_FLOOR)
        save = xt_merge_intent._save_context_checkpoint

        def save_together(*args):
            before_save.wait()
            save(*args)

        with (
            mock.patch.object(xt_merge_intent, "_save_context_checkpoint", side_effect=save_together),
            mock.patch.object(xt, "write_atomic", wraps=xt.write_atomic) as write,
            ThreadPoolExecutor(max_workers=2) as pool,
        ):
            results = [pool.submit(xt_merge_intent.observe_merge, xt, decision) for _ in range(2)]
            self.assertEqual([future.result() for future in results], [None, None])
        write.assert_called_once()
        (checkpoint,) = self.checkpoints()
        self.assertEqual(json.loads(checkpoint.read_bytes())["merge_sha"], self.gh.merged_sha)

    def test_check_without_pinned_selector_stays_read_only(self):
        decision = {"verdict": "closed", "pr": int(PR), "reasons": ["PR đã MERGED"], "next": ""}
        with mock.patch.object(xt, "_merge_check_json", return_value=(1, decision, "")):
            self.assertEqual(self.watch("--observe-context")[0], 0)
        self.assertEqual(self.gh.calls, [])
        self.assertEqual(self.checkpoints(), [])
