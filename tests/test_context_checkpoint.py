"""Checkpoint merge quan sát với phản hồi GitHub giả."""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import xt
from xt_merge_intent import (
    merged_checkpoint,
    observe_merge_checkpoint,
    record_merge_checkpoint,
    recover_merge_checkpoint,
)

URL = "https://github.example/team/test/pull/7"
MERGED = {"verdict": "closed", "reasons": ["PR đã MERGED"]}
PULL = {
    "html_url": URL,
    "number": 7,
    "state": "closed",
    "merged": True,
    "base": {"ref": "main", "repo": {"full_name": "team/test"}},
    "head": {"sha": "1" * 40},
    "merge_commit_sha": "2" * 40,
    "body": "fixture omitted from checkpoint",
}


class ContextCheckpointTests(unittest.TestCase):
    def test_two_observers_write_once_and_recover_from_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            directory = xt.state_write_dir(base)
            fetch = Mock(return_value=[PULL])
            write = Mock(wraps=xt.write_atomic)
            with ThreadPoolExecutor(max_workers=2) as executor:
                workers = [
                    executor.submit(record_merge_checkpoint, URL, fetch, xt._state_lock(base), lambda: directory, write)
                    for _ in range(2)
                ]
                self.assertCountEqual([worker.result() for worker in workers], [True, False])
            write.assert_called_once()
            fetch.assert_called_with("repos/team/test/pulls/7", host="github.example")
            (path,) = directory.glob("*.json")
            point = merged_checkpoint(URL, PULL)
            self.assertEqual(recover_merge_checkpoint(path, point), point)
            self.assertNotIn(PULL["body"], path.read_text())
            with self.assertRaisesRegex(ValueError, "khác mốc"):
                recover_merge_checkpoint(path, {**point, "merge": "3" * 40})
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(ValueError):
                recover_merge_checkpoint(path, point)
            path.unlink()
            path.symlink_to(directory / "missing")
            with self.assertRaises(OSError):
                recover_merge_checkpoint(path, point)

    def test_reject_unknown_unmerged_and_mismatched_git_hub_responses(self):
        for url, payload in (
            ("7", [PULL]),
            (URL, []),
            (URL, [PULL, PULL]),
            (URL, [None]),
            (URL, [{**PULL, "number": 8}]),
            (URL, [{**PULL, "merged": False}]),
            (URL, [{**PULL, "state": "open"}]),
            (URL, [{**PULL, "merge_commit_sha": "unknown"}]),
        ):
            with self.subTest(url=url, payload=payload), self.assertRaises(ValueError):
                record_merge_checkpoint(url, Mock(return_value=payload), contextlib.nullcontext(), Mock(), Mock())

    def test_failed_write_warns_and_can_be_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            args = (URL, Mock(return_value=[PULL]), contextlib.nullcontext(), lambda: directory)
            warnings = io.StringIO()
            with contextlib.redirect_stderr(warnings):
                observe_merge_checkpoint(MERGED, *args, Mock(side_effect=OSError), RuntimeError)
            self.assertIn("không lưu được", warnings.getvalue())
            self.assertEqual(list(directory.iterdir()), [])
            self.assertTrue(record_merge_checkpoint(*args, xt.write_atomic))
            with contextlib.redirect_stderr(warnings):
                observe_merge_checkpoint(MERGED, *args, xt.write_atomic, RuntimeError)

    def test_watch_only_observes_confirmed_merge_when_opted_in(self):
        for opt_in, verdict, reason, expected in (
            (False, "closed", "PR đã MERGED", False),
            (True, "closed", "PR đã đóng", False),
            (True, "merge", "CI xanh", False),
            (True, "closed", "PR đã MERGED", True),
        ):
            result = {"verdict": verdict, "pr": 7, "reasons": [reason], "live_selector": URL}
            with (
                self.subTest(opt_in=opt_in, verdict=verdict, reason=reason),
                patch.object(xt, "_merge_check_json", return_value=(0, result, "")),
                patch.object(xt, "_watch_final", return_value=0),
                patch("xt_merge_intent.record_merge_checkpoint") as observe,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                args = type("Args", (), {"observe_context": opt_in, "pr": "7", "max_minutes": 1})()
                self.assertEqual(xt.cmd_merge_watch(args), 0)
                self.assertEqual(observe.called, expected)
