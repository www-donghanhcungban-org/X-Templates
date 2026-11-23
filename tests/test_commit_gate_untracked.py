"""T-4013 (AUD-HAR-443, D-518): tệp CHƯA TRACK chỉ bị bỏ khỏi tập tệp đổi của cổng commit khi guard khẳng định cả lệnh
là `git commit` đứng một mình; `git add -A && git commit` và mọi ca nghi ngờ giữ cách thận trọng cũ."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
import guard

ALONE = [
    "git commit -m x",
    'git commit -m "feat(merge): sửa (T-4013)"',
    "git commit -am 'a; b && c | d'",
    "git commit -q -F msg.txt",
    "git commit --amend --no-edit",
]
NOT_ALONE = [
    "git add -A && git commit -m x",
    "git add . ; git commit -m x",
    "git commit -m x; touch y",
    "git commit -m x | cat",
    "git commit -m x &",
    "git commit -m x > log",
    'git commit -m "$(date)"',
    "git commit -m `date`",
    "git commit -m x\ngit add y",
    "git commit -m x \\\n -q",
    "git commit --interactive",
    "git commit --interactive=yes",
    "git commit --interact",  # git nhận tiền tố duy nhất của --interactive
    "git commit --int",
    "git commit -m fix#12 --interactive < feed.txt",  # shlex coi `#` giữa từ là comment, bash thì không
    "git commit -m wip#1 | cat",
    "git commit -m a#1 ; git add -A",
    "git -C sub commit -m x",
    "GIT_X=1 git commit -m x",
    "( git commit -m x )",
    "git commit -m 'chưa đóng nháy",
    "git status",
]


class CommitAloneRuleTest(unittest.TestCase):
    def test_alone(self):
        for cmd in ALONE:
            with self.subTest(cmd=cmd):
                self.assertTrue(guard.commit_alone(cmd))

    def test_not_alone(self):
        for cmd in NOT_ALONE:
            with self.subTest(cmd=cmd):
                self.assertFalse(guard.commit_alone(cmd))


class GuardNulFieldTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def fields(self, cmd: str) -> list[str]:
        payload = json.dumps({"tool_input": {"command": cmd}, "cwd": str(self.root)})
        r = subprocess.run(
            [sys.executable, str(ROOT / ".claude" / "hooks" / "guard.py"), "bash", "nul"],
            input=payload,
            capture_output=True,
            text=True,
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(self.root)},
            check=True,
        )
        return r.stdout.split("\0")

    def test_field_appended_after_old_fields(self):
        alone = self.fields("git commit -m x")
        self.assertEqual((alone[0], alone[3], alone[6]), ("ok", "true", "true"))
        chained = self.fields("git add -A && git commit -m x")
        self.assertEqual((chained[3], chained[6]), ("true", "false"))
        other = self.fields("git status")
        self.assertEqual((other[3], other[6]), ("false", ""))  # không phải commit: không khẳng định


class DevTaskTrackedOnlyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.tmp / "scripts").mkdir()
        shutil.copy(ROOT / "scripts" / "dev-task.sh", self.tmp / "scripts" / "dev-task.sh")
        git = ["git", "-C", str(self.tmp), "-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run([*git, "init", "-q"], check=True)
        (self.tmp / "a.txt").write_text("1\n", encoding="utf-8")
        (self.tmp / ".gitignore").write_text("seen\n", encoding="utf-8")
        (self.tmp / "xt.yaml").write_text(
            "lint: sh -c 'exit 0'\ntest_fast: sh -c 'printf \"%s\\n\" \"$XT_CHANGED_FILES\" > seen'\n", encoding="utf-8"
        )
        subprocess.run([*git, "add", "-A"], check=True)
        subprocess.run([*git, "commit", "-q", "-m", "init"], check=True)
        (self.tmp / "a.txt").write_text("2\n", encoding="utf-8")
        (self.tmp / "moi.txt").write_text("x\n", encoding="utf-8")  # chưa track

    def seen(self, **env: str) -> list[str]:
        base = {k: v for k, v in os.environ.items() if k not in ("XT_CHANGED_FILES", "XT_CHANGED_TRACKED_ONLY")}
        r = subprocess.run(
            ["bash", str(self.tmp / "scripts" / "dev-task.sh"), "gate-fast"],
            capture_output=True,
            text=True,
            cwd=self.tmp,
            env={**base, "CLAUDE_PROJECT_DIR": str(self.tmp), **env},
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        return sorted((self.tmp / "seen").read_text(encoding="utf-8").splitlines())

    def test_flag_does_not_leak_into_the_test_command(self):
        (self.tmp / "xt.yaml").write_text(
            "lint: sh -c 'exit 0'\ntest_fast: sh -c 'printf \"%s\" \"${XT_CHANGED_TRACKED_ONLY-unset}\" > seen'\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "-C", str(self.tmp), "add", "xt.yaml"], check=True)
        self.assertEqual(self.seen(XT_CHANGED_TRACKED_ONLY="1"), ["unset"])

    def test_untracked_kept_by_default_dropped_only_with_flag(self):
        self.assertEqual(self.seen(), ["a.txt", "moi.txt"])
        self.assertEqual(self.seen(XT_CHANGED_TRACKED_ONLY="0"), ["a.txt", "moi.txt"])
        self.assertEqual(self.seen(XT_CHANGED_TRACKED_ONLY="1"), ["a.txt"])


class HookWiringTest(unittest.TestCase):
    def test_hook_sets_flag_only_from_guard_field(self):
        hook = (ROOT / ".claude" / "hooks" / "pre-bash-guard.sh").read_text(encoding="utf-8")
        self.assertIn('if [ "$XG_COMMIT_ALONE" = "true" ]; then export XT_CHANGED_TRACKED_ONLY=1;', hook)
        self.assertIn("else unset XT_CHANGED_TRACKED_ONLY; fi", hook)
        lib = (ROOT / ".claude" / "hooks" / "_lib.sh").read_text(encoding="utf-8")
        self.assertIn("IFS= read -r -d '' XG_COMMIT_ALONE || true", lib)


if __name__ == "__main__":
    unittest.main()
