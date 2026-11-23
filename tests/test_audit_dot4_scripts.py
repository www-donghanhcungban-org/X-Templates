"""T-3927 (PLAN-harden-2026-11-17 đợt 4, ADR-0080): sửa phát hiện `scripts/` của audit delta cổng ký 2026-11-17.

Mỗi ID một lớp: AUD-HAR-415 (`.autopilot` symlink kẹt phiên), AUD-HAR-416 (`--separate-git-dir` thật), AUD-HAR-417
(`go_snapshot` gặp thư mục không đọc được), AUD-DOC-296 (log `guard_ok` tách lỗi runtime), AUD-HAR-418 (`_trial_hold`
không khoá xuyên liên kết)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import xt
from test_xt_cli import TmpDirCase, run_main

PLAN = "- [ ] `T-001` việc — Gate: `true`\n"
SESSION = "11111111-aaaa-bbbb-cccc-000000000001"
GIT_ID = ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false"]


def git(cwd: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(cwd), *GIT_ID, *args], capture_output=True, text=True, check=True)
    return r.stdout.strip()


class SymlinkLoopUnstuckTest(TmpDirCase):
    """AUD-HAR-415: vòng đang bật mà `.autopilot` là symlink — lượt Stop thường vẫn chặn (AUD-HAR-405), lượt do chính Stop
    hook kích (`stop_hook_active`) cho dừng kèm `systemMessage` nói NGƯỜI phải thay liên kết; không ghi gì qua liên
    kết ở cả hai lượt. `loop stop` từ chối ghi qua liên kết và nói rõ người phải làm gì."""

    def setUp(self) -> None:
        super().setUp()
        (self.tmp / "docs" / "autopilot").mkdir(parents=True)
        (self.tmp / "docs" / "autopilot" / "PLAN.md").write_text(PLAN, encoding="utf-8")
        self.enterContext(
            unittest.mock.patch.dict(
                os.environ, {"CLAUDE_PROJECT_DIR": str(self.tmp), "CLAUDE_CODE_SESSION_ID": SESSION}
            )
        )
        self.assertEqual(run_main("loop", "init")[0], 0)
        self.real = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve() / "ap"
        (self.tmp / ".autopilot").rename(self.real)
        (self.tmp / ".autopilot").symlink_to(self.real)
        self.before = sorted(p.name for p in self.real.iterdir())
        self.state = (self.real / "state.json").read_text(encoding="utf-8")

    def stop(self, **extra: object) -> tuple[int, dict[str, object]]:
        rc, out, err = run_main("loop", "hook-stop", stdin=json.dumps({"session_id": SESSION, **extra}))
        self.assertEqual(err, "")
        return rc, json.loads(out or "{}")

    def assert_untouched(self) -> None:
        self.assertEqual(sorted(p.name for p in self.real.iterdir()), self.before)
        self.assertEqual((self.real / "state.json").read_text(encoding="utf-8"), self.state)

    def test_hook_stop_reentry_lets_session_stop_with_human_message(self) -> None:
        rc, first = self.stop(stop_hook_active=False)
        self.assertEqual((rc, first.get("decision")), (0, "block"))
        self.assertIn("lượt Stop kế tiếp được cho dừng", str(first["reason"]))
        rc, again = self.stop(stop_hook_active=True)
        self.assertEqual(rc, 0)
        self.assertNotIn("decision", again)
        self.assertIn("NGƯỜI thay liên kết bằng thư mục thật", str(again["systemMessage"]))
        self.assert_untouched()

    def test_hook_stop_flag_must_be_true(self) -> None:
        for flag in ("true", 1, None):
            with self.subTest(flag=flag):
                self.assertEqual(self.stop(stop_hook_active=flag)[1].get("decision"), "block")
        self.assert_untouched()

    def test_real_dir_reentry_still_blocks(self) -> None:
        """Đối chứng: thư mục thật — `stop_hook_active` không mở cửa dừng (vòng tự đếm và có trần)."""
        (self.tmp / ".autopilot").unlink()
        self.real.rename(self.tmp / ".autopilot")
        self.assertEqual(self.stop(stop_hook_active=True)[1].get("decision"), "block")

    def test_loop_stop_refuses_write_and_names_human_action(self) -> None:
        rc, out, err = run_main("loop", "stop", "--reason", "thoát")
        self.assertEqual((rc, out), (2, ""), err)
        self.assertIn("symlink", err)
        self.assertIn("NGƯỜI thay liên kết bằng thư mục thật", err)
        self.assertIn("lượt Stop kế tiếp", err)
        self.assert_untouched()


class SeparateGitDirRootsTest(TmpDirCase):
    """AUD-HAR-416: repo `git init --separate-git-dir` THẬT — `git worktree list` in thư mục git làm mục chính và
    `rev-parse --show-toplevel` ở đó rỗng; cây chính là toplevel của chính `base` khi `base` dùng đúng thư mục git đó."""

    def setUp(self) -> None:
        super().setUp()
        self.gitdir = self.tmp / "meta"
        self.proj = self.tmp / "proj"
        subprocess.run(
            ["git", "init", "-q", "-b", "main", f"--separate-git-dir={self.gitdir}", str(self.proj)],
            check=True,
            capture_output=True,
        )
        (self.proj / "a.txt").write_text("a\n", encoding="utf-8")
        git(self.proj, "add", "-A")
        git(self.proj, "commit", "-q", "-m", "init")

    def test_real_layout_is_what_audit_saw(self) -> None:
        listing = git(self.proj, "worktree", "list", "--porcelain").splitlines()
        self.assertEqual(Path(listing[0].removeprefix("worktree ")).resolve(), self.gitdir.resolve())
        top = subprocess.run(["git", "-C", str(self.gitdir), "rev-parse", "--show-toplevel"], capture_output=True)
        self.assertEqual(top.stdout.strip(), b"")

    def test_roots_resolve_main_tree(self) -> None:
        self.assertEqual(xt._worktree_roots(self.proj, xt._perf_env()), [self.proj])
        self.assertEqual(xt.worktree_state_files(self.proj), [])

    def test_release_verify_not_applicable(self) -> None:
        row = xt._release_verify(self.proj)
        self.assertEqual((row["result"], row["level"]), ("N/A", "SHOULD"), row)

    def test_sign_sees_state_of_main_tree(self) -> None:
        (self.proj / ".autopilot").mkdir()
        (self.proj / ".autopilot" / "state.json").write_text("{}", encoding="utf-8")
        self.assertEqual(xt._sign_state_files(self.proj), [self.proj / ".autopilot" / "state.json"])

    def test_linked_worktree_still_fails_closed(self) -> None:
        """`base` là worktree phụ: thư mục git của nó không phải mục chính — không đoán cây chính (fail-closed)."""
        wt = self.tmp / "wt"
        git(self.proj, "worktree", "add", "-q", "--detach", str(wt))
        self.assertIsNone(xt._worktree_roots(wt, xt._perf_env()))
        self.assertEqual(xt._release_verify(wt)["result"], "FAIL")

    def test_real_submodule_uses_core_worktree(self) -> None:
        """Đối chứng (AUD-HAR-371): submodule thật — thư mục git có `core.worktree`, toplevel lấy ngay tại đó."""
        parent = self.tmp / "parent"
        parent.mkdir()
        git(parent, "init", "-q", "-b", "main")
        git(parent, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(self.proj), "mod")
        mod = parent / "mod"
        listing = git(mod, "worktree", "list", "--porcelain").splitlines()
        self.assertFalse(os.path.lexists(Path(listing[0].removeprefix("worktree ")) / ".git"))
        self.assertEqual(xt._worktree_roots(mod, xt._perf_env()), [mod])

    def test_rev_parse_error_fails_closed(self) -> None:
        real = xt._git

        def fake(cwd: Path, *args: str, **kw: Any) -> subprocess.CompletedProcess[str]:
            if args == ("rev-parse", "--absolute-git-dir"):
                return subprocess.CompletedProcess(args, 128, "", "fatal")
            return real(cwd, *args, **kw)

        with unittest.mock.patch.object(xt, "_git", side_effect=fake):
            self.assertIsNone(xt._worktree_roots(self.proj, xt._perf_env()))


class TrialHoldSymlinkTest(TmpDirCase):
    """AUD-HAR-418: `_trial_hold` mở `perf-trial.lock` qua `state_write_dir` — `.autopilot` là symlink thì từ chối
    (TrialRefused 2), không tạo khoá ở đích liên kết; thư mục thật vẫn khoá như cũ."""

    def test_symlinked_state_dir_refused_without_creating_lock(self) -> None:
        dest = self.tmp / "outside"
        dest.mkdir()
        proj = self.tmp / "proj"
        proj.mkdir()
        (proj / ".autopilot").symlink_to(dest)
        with self.assertRaises(xt.TrialRefused) as ctx, xt._trial_hold(proj):
            self.fail("không được giữ khoá qua liên kết")
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("symlink", str(ctx.exception))
        self.assertEqual(list(dest.iterdir()), [])

    def test_real_dir_still_locks(self) -> None:
        with xt._trial_hold(self.tmp):
            self.assertTrue((self.tmp / ".autopilot" / xt.PERF_TRIAL_LOCK).is_file())


ROW = "| Người ký | (chưa ký) |\n"


class DevTaskUnreadableDirTest(unittest.TestCase):
    """AUD-HAR-417: thư mục không đọc được trong cây (dữ liệu docker mode 700 của user khác; ở đây chmod 000) không làm
    `go_snapshot` lỗi — formatter vẫn chạy, `format`/`format-file` exit 0, GO-NO-GO vẫn được khôi phục. Lỗi khác của
    `find` vẫn dừng formatter (fail-closed)."""

    def setUp(self) -> None:
        if os.geteuid() == 0:
            self.skipTest("root đọc được thư mục chmod 000 — không tái hiện được")
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        (self.tmp / "scripts").mkdir()
        shutil.copy(ROOT / "scripts" / "dev-task.sh", self.tmp / "scripts" / "dev-task.sh")
        self.go = self.tmp / "docs" / "GO-NO-GO-v1.md"
        self.go.parent.mkdir()
        self.go.write_text(ROW, encoding="utf-8")
        self.locked = self.tmp / "pgdata"
        self.locked.mkdir()
        (self.locked / "GO-NO-GO-hidden.md").write_text(ROW, encoding="utf-8")
        self.locked.chmod(0o000)
        self.addCleanup(self.locked.chmod, 0o700)

    def run_task(self, *args: str, path_prefix: Path | None = None) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.tmp))
        if path_prefix:
            env["PATH"] = f"{path_prefix}:{env['PATH']}"
        return subprocess.run(
            ["bash", str(self.tmp / "scripts" / "dev-task.sh"), *args],
            capture_output=True,
            text=True,
            cwd=self.tmp,
            env=env,
        )

    def config(self, text: str) -> None:
        (self.tmp / "xt.yaml").write_text(text, encoding="utf-8")

    def test_format_runs_and_protects_go_no_go(self) -> None:
        self.config("format: touch format-ran && printf FORMATTED > docs/GO-NO-GO-v1.md\n")
        r = self.run_task("format")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.tmp / "format-ran").exists())
        self.assertEqual(self.go.read_text(encoding="utf-8"), ROW)
        self.assertIn("khôi phục", r.stderr)
        self.assertIn("bỏ qua 1 thư mục không đọc được", r.stderr)

    def test_format_file_runs(self) -> None:
        (self.tmp / "a.md").write_text("x\n", encoding="utf-8")
        self.config("format_file: printf FORMATTED > {}\n")
        r = self.run_task("format-file", "a.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.tmp / "a.md").read_text(encoding="utf-8"), "FORMATTED")

    def test_other_find_error_still_stops_formatter(self) -> None:
        shim = self.tmp / "bin"
        shim.mkdir()
        (shim / "find").write_text("#!/bin/sh\necho 'find: ./x: Input/output error' >&2\nexit 1\n", encoding="utf-8")
        (shim / "find").chmod(0o755)
        self.config("format: touch format-ran\n")
        r = self.run_task("format", path_prefix=shim)
        self.assertNotEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.tmp / "format-ran").exists())
        self.assertIn("Input/output error", r.stderr)

    def test_silent_find_failure_still_stops_formatter(self) -> None:
        shim = self.tmp / "bin"
        shim.mkdir()
        (shim / "find").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        (shim / "find").chmod(0o755)
        self.config("format: touch format-ran\n")
        r = self.run_task("format", path_prefix=shim)
        self.assertNotEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.tmp / "format-ran").exists())

    def test_go_no_go_copy_failure_still_stops_formatter(self) -> None:
        """Sao lưu một GO-NO-GO đã tìm thấy bị hỏng (file không đọc được) → dừng formatter."""
        self.go.chmod(0o000)
        self.addCleanup(self.go.chmod, 0o600)
        self.config("format: touch format-ran\n")
        r = self.run_task("format")
        self.assertNotEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.tmp / "format-ran").exists())


class GuardRuntimeLogTest(unittest.TestCase):
    """AUD-DOC-296: `guard-check` exit 126 vì runtime sai (ADR-0078) không được log là "guard cấm một lệnh"; guard cấm
    thật vẫn log như cũ. Python giả in đúng lời từ chối runtime của xt.py và exit 126."""

    def setUp(self) -> None:
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        (self.tmp / "scripts").mkdir()
        (self.tmp / ".claude" / "hooks").mkdir(parents=True)
        for src, dst in (
            ("scripts/dev-task.sh", "scripts/dev-task.sh"),
            ("scripts/xt.py", "scripts/xt.py"),
            (".claude/hooks/guard.py", ".claude/hooks/guard.py"),
        ):
            shutil.copy(ROOT / src, self.tmp / dst)
        (self.tmp / "xt.yaml").write_text("lint: touch l\ntypecheck: true\nbuild: true\ntest: true\n", encoding="utf-8")
        self.old = self.tmp / "python-old"
        self.old.write_text("#!/bin/sh\necho '✗ cần CPython 3.13 trở lên — hiện là cpython 3.12.0' >&2\nexit 126\n")
        self.old.chmod(0o755)

    def gate(self, **env: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(self.tmp / "scripts" / "dev-task.sh"), "gate"],
            capture_output=True,
            text=True,
            cwd=self.tmp,
            env=dict(os.environ, CLAUDE_PROJECT_DIR=str(self.tmp), XT_GUARD_POLICY="", **env),
        )

    def test_wrong_runtime_is_not_logged_as_guard_deny(self) -> None:
        r = self.gate(XT_FRAMEWORK_PYTHON=str(self.old))
        self.assertEqual(r.returncode, 126, r.stderr)
        self.assertNotIn("guard cấm", r.stderr)
        self.assertIn("cần CPython 3.13 trở lên — ADR-0094", r.stderr)
        self.assertFalse((self.tmp / "l").exists())

    def run_task(self, task: str, **env: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(self.tmp / "scripts" / "dev-task.sh"), task],
            capture_output=True,
            text=True,
            cwd=self.tmp,
            env=dict(os.environ, CLAUDE_PROJECT_DIR=str(self.tmp), XT_GUARD_POLICY="", **env),
        )

    def test_declared_runtime_without_handshake_is_closed(self) -> None:
        """T-3958: XT_FRAMEWORK_PYTHON khai rõ mà chạy được nhưng không phải CPython ≥ 3.13 (`true` exit 0 không in gì,
        `echo` in lại đối số) hoặc tên không có → 126, không lệnh nào chạy — cả đường `gate` (guard_ok_all) lẫn task
        đơn (guard_ok)."""
        for runtime in ("true", "echo", str(self.tmp / "khong-co-python")):
            for task in ("gate", "lint"):
                with self.subTest(runtime=runtime, task=task):
                    r = self.run_task(task, XT_FRAMEWORK_PYTHON=runtime)
                    self.assertEqual(r.returncode, 126, r.stderr)
                    self.assertIn("không qua bắt tay (cần CPython 3.13 trở lên — ADR-0094)", r.stderr)
                    self.assertNotIn("guard cấm", r.stderr)
                    self.assertFalse((self.tmp / "l").exists())

    def test_declared_supported_cpython_runs(self) -> None:
        """Ca được phép: XT_FRAMEWORK_PYTHON là CPython ≥ 3.13 thật (ADR-0094) → qua bắt tay, guard cho lệnh lành chạy."""
        for task in ("lint", "gate"):
            with self.subTest(task=task):
                r = self.run_task(task, XT_FRAMEWORK_PYTHON=sys.executable)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertTrue((self.tmp / "l").exists())
                (self.tmp / "l").unlink()

    def test_real_guard_deny_still_logged(self) -> None:
        (self.tmp / "xt.yaml").write_text("lint: touch l && git push origin main\n", encoding="utf-8")
        r = self.gate(XT_FRAMEWORK_PYTHON=sys.executable)
        self.assertEqual(r.returncode, 126, r.stderr)
        self.assertIn("guard cấm một lệnh của xt.yaml", r.stderr)
        self.assertFalse((self.tmp / "l").exists())


if __name__ == "__main__":
    unittest.main()
