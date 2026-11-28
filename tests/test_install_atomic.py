"""T-5043: install.py ghi tệp của dự án đích nguyên tử (tệp tạm cùng thư mục + `os.replace`), hook git 0 byte được thay,
`main` báo lỗi ghi kèm cách khôi phục thay vì traceback."""

from __future__ import annotations

import errno
import io
import json
import os
import resource
import signal
import stat
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any
from unittest import TestCase, main, mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import install

REAL_REPLACE = os.replace


def tmp_leftovers(root: Path) -> list[Path]:
    """Tệp tạm của `write_bytes_atomic`/`write_atomic` còn sót (`.<tên>.<…>.tmp`) — mọi cấp, kể cả thư mục ẩn."""
    return [p for p in root.rglob(".*.tmp") if p.is_file()]


@contextmanager
def file_size_limit(limit: int) -> Iterator[None]:
    """Giới hạn cỡ tệp thật của hệ điều hành (RLIMIT_FSIZE): ghi vượt ném `OSError(EFBIG)` thay vì nhận SIGXFSZ."""
    soft, hard = resource.getrlimit(resource.RLIMIT_FSIZE)
    previous = signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    resource.setrlimit(resource.RLIMIT_FSIZE, (limit, hard))
    try:
        yield
    finally:
        resource.setrlimit(resource.RLIMIT_FSIZE, (soft, hard))
        signal.signal(signal.SIGXFSZ, previous)


def current_umask() -> int:
    mask = os.umask(0)
    os.umask(mask)
    return mask


class WriteBytesAtomicTest(TestCase):
    def setUp(self) -> None:
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.path = self.tmp / "hook.sh"

    def test_new_file_gets_open_default_mode_plus_extra_bits(self) -> None:
        install.write_bytes_atomic(self.path, b"#!/bin/sh\n", add_mode=stat.S_IXUSR)
        self.assertEqual(self.path.read_bytes(), b"#!/bin/sh\n")
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), (0o666 & ~current_umask()) | stat.S_IXUSR)
        self.assertEqual(tmp_leftovers(self.tmp), [])

    def test_existing_mode_kept_and_explicit_mode_wins(self) -> None:
        self.path.write_bytes(b"cu")
        self.path.chmod(0o640)
        inode = self.path.stat().st_ino
        install.write_bytes_atomic(self.path, "mới Đ".encode("utf-8"))
        self.assertEqual(self.path.read_text(encoding="utf-8"), "mới Đ")
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o640)
        self.assertNotEqual(self.path.stat().st_ino, inode)  # tệp mới thay tệp cũ, không ghi đè tại chỗ
        install.write_bytes_atomic(self.path, b"", mode=0o755)
        self.assertEqual((self.path.read_bytes(), stat.S_IMODE(self.path.stat().st_mode)), (b"", 0o755))

    def test_read_only_target_is_replaced_and_keeps_its_mode(self) -> None:
        """Tệp đích 0444 (ghi được thư mục cha) được thay, giữ quyền cũ — `write_bytes` cũ ném PermissionError."""
        self.path.write_bytes(b"cu")
        self.path.chmod(0o444)
        install.write_bytes_atomic(self.path, b"moi")
        self.assertEqual((self.path.read_bytes(), stat.S_IMODE(self.path.stat().st_mode)), (b"moi", 0o444))
        self.assertEqual(tmp_leftovers(self.tmp), [])

    def test_writable_file_in_read_only_parent_raises_permission_error(self) -> None:
        """Tệp ghi được nhưng thư mục cha không ghi được: không tạo được tệp tạm → PermissionError mang tên đích."""
        sub = self.tmp / "ro"
        sub.mkdir()
        target = sub / "f.txt"
        target.write_bytes(b"cu")
        sub.chmod(0o555)
        self.addCleanup(sub.chmod, 0o755)
        if os.access(sub, os.W_OK):  # chạy bằng root: quyền thư mục không chặn được
            self.skipTest("tiến trình bỏ qua quyền thư mục (root)")
        with self.assertRaises(PermissionError) as caught:
            install.write_bytes_atomic(target, b"moi")
        self.assertEqual(caught.exception.filename, str(target))
        self.assertEqual(target.read_bytes(), b"cu")

    def test_temp_file_is_created_owner_only(self) -> None:
        """Tệp tạm mở 0600 rồi mới nới theo quyền cuối: không có khoảng hở tệp tạm đọc/ghi được cho nhóm/người khác."""
        modes: list[int] = []
        real_fchmod = os.fchmod

        def spy(fd: int, mode: int) -> None:
            modes.append(stat.S_IMODE(os.fstat(fd).st_mode))
            real_fchmod(fd, mode)

        with mock.patch.object(install.os, "fchmod", side_effect=spy):
            install.write_bytes_atomic(self.path, b"x")
        self.assertEqual(modes, [0o600])

    def test_replace_failure_keeps_old_file_and_names_destination(self) -> None:
        self.path.write_bytes(b"ban cu")
        with mock.patch.object(install.os, "replace", side_effect=OSError("đĩa đầy")):
            with self.assertRaises(OSError) as caught:
                install.write_bytes_atomic(self.path, b"ban moi")
        self.assertEqual((caught.exception.filename, caught.exception.strerror), (str(self.path), "đĩa đầy"))
        self.assertIsInstance(caught.exception.__cause__, OSError)
        self.assertEqual(self.path.read_bytes(), b"ban cu")
        self.assertEqual(tmp_leftovers(self.tmp), [])

    def test_interrupt_cleans_temp_and_propagates_unchanged(self) -> None:
        self.path.write_bytes(b"ban cu")
        with mock.patch.object(install.os, "replace", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                install.write_bytes_atomic(self.path, b"ban moi")
        self.assertEqual(self.path.read_bytes(), b"ban cu")
        self.assertEqual(tmp_leftovers(self.tmp), [])

    def test_symlink_destination_is_refused_not_followed(self) -> None:
        outside = self.tmp / "ngoai.txt"
        outside.write_bytes(b"ngoai")
        self.path.symlink_to(outside)
        with self.assertRaises(OSError) as caught:
            install.write_bytes_atomic(self.path, b"xuyen")
        self.assertEqual((caught.exception.errno, caught.exception.filename), (errno.ELOOP, str(self.path)))
        self.assertTrue(self.path.is_symlink())
        self.assertEqual(outside.read_bytes(), b"ngoai")

    def test_open_failure_never_removes_a_file_it_did_not_create(self) -> None:
        """Tên tạm trùng tệp có sẵn (O_EXCL từ chối): tệp đó không phải của lần ghi này nên không bị xoá; thư mục cha
        thiếu: lỗi mang tên tệp đích."""
        stamp = b"\x01" * 6
        foreign = self.tmp / f".{self.path.name}.{stamp.hex()}.tmp"
        foreign.write_bytes(b"cua tien trinh khac")
        with mock.patch.object(install.os, "urandom", return_value=stamp), self.assertRaises(FileExistsError) as caught:
            install.write_bytes_atomic(self.path, b"x")
        self.assertEqual(caught.exception.filename, str(self.path))
        self.assertEqual(foreign.read_bytes(), b"cua tien trinh khac")
        self.assertFalse(self.path.exists())
        missing = self.tmp / "chua-co" / "f"
        with self.assertRaises(FileNotFoundError) as caught_missing:
            install.write_bytes_atomic(missing, b"x")
        self.assertEqual(caught_missing.exception.filename, str(missing))

    def test_real_file_size_limit_leaves_no_truncated_file(self) -> None:
        """EFBIG thật (RLIMIT_FSIZE): `write_bytes` cũ để tệp cụt; ghi nguyên tử để bản cũ nguyên vẹn, không rác."""
        probe, data = self.tmp / "probe.sh", b"#" * 8192
        self.path.write_bytes(b"ban cu")
        with file_size_limit(4096):
            with self.assertRaises(OSError):
                probe.write_bytes(data)
            with self.assertRaises(OSError) as caught:
                install.write_bytes_atomic(self.path, data)
        self.assertEqual(probe.stat().st_size, 4096)  # đối chứng: cách ghi cũ cụt thật dưới cùng giới hạn
        self.assertEqual(caught.exception.errno, errno.EFBIG)
        self.assertEqual(self.path.read_bytes(), b"ban cu")
        self.assertEqual(tmp_leftovers(self.tmp), [])

    def test_concurrent_writers_and_reader_never_see_partial_content(self) -> None:
        payloads = [bytes([65 + i]) * (512 * 1024) for i in range(3)]
        install.write_bytes_atomic(self.path, payloads[0])
        seen: set[bytes] = set()
        errors: list[Exception] = []
        done = threading.Event()

        def writer(data: bytes) -> None:
            try:
                for _ in range(15):
                    install.write_bytes_atomic(self.path, data)
            except Exception as exc:  # thread không ném ra test: gom lại để kiểm (ngắt chỉ tới luồng chính)
                errors.append(exc)

        def reader() -> None:
            while not done.is_set():
                seen.add(self.path.read_bytes()[:1] + str(self.path.stat().st_size).encode())

        threads = [threading.Thread(target=writer, args=(p,)) for p in payloads]
        watcher = threading.Thread(target=reader)
        watcher.start()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        done.set()
        watcher.join()
        self.assertEqual(errors, [])
        self.assertIn(self.path.read_bytes(), payloads)
        self.assertTrue(seen <= {p[:1] + str(len(p)).encode() for p in payloads}, seen)
        self.assertEqual(tmp_leftovers(self.tmp), [])


class InstallInterruptedWriteTest(TestCase):
    def setUp(self) -> None:
        self.target = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        subprocess.run(["git", "init", "-q", str(self.target)], check=True)
        self.hooks = self.target / ".git" / "hooks"

    def test_retry_after_settings_publish_keeps_rule_provenance(self) -> None:
        for mode in ("fresh", "merge", "own"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as scratch:
                root = Path(scratch)
                clean = root / "clean"
                retry = root / "retry"
                for target in (clean, retry):
                    (target / ".xtemplates").mkdir(parents=True)
                    if mode != "fresh":
                        settings = target / ".claude" / "settings.json"
                        settings.parent.mkdir()
                        settings.write_text(json.dumps({"permissions": {"allow": ["Read(README.md)"]}}))
                    if mode == "own":
                        (target / "xt.yaml").write_text("harness_permissions: own\n")

                install.install_harness(clean, False)
                with mock.patch.object(install, "write_manifests", side_effect=OSError(errno.ENOSPC, "simulated")):
                    with self.assertRaises(OSError):
                        install.install_harness(retry, False)
                install.install_harness(retry, False)
                self.assertEqual(install.load_rules(retry), install.load_rules(clean))
                self.assertNotIn("Read(README.md)", install.load_rules(retry)["allow"])
                self.assertEqual(install.load_manifest_doc(retry), install.load_manifest_doc(clean))
                install.install_harness(retry, False)
                self.assertEqual(install.load_rules(retry), install.load_rules(clean))

    def test_settings_transition_uses_only_the_published_snapshot(self) -> None:
        settings = self.target / ".claude" / "settings.json"
        settings.parent.mkdir()
        expected = b'{"permissions":{"allow":["Read(README.md)"]}}'
        prior = {key: [] for key in install.RULE_KEYS}
        rules = {**prior, "allow": ["Read(README.md)"]}
        install.stage_settings_rules(self.target, expected, rules, prior)
        self.assertEqual(install.recover_settings_rules(self.target), prior)
        settings.write_bytes(b"{}")
        self.assertEqual(install.recover_settings_rules(self.target), prior)
        settings.write_bytes(expected)
        install.write_manifests(self.target, {}, prior)
        self.assertEqual(install.recover_settings_rules(self.target), rules)
        install.update_manifest_doc(
            self.target,
            **{install.PENDING_SETTINGS: {"settings_hash": install.hash_label(install.sha256(expected)), "rules": []}},
        )
        self.assertEqual(install.recover_settings_rules(self.target), prior)
        install.stage_settings_rules(self.target, expected, {"allow": rules["allow"]}, prior)
        self.assertEqual(install.recover_settings_rules(self.target), prior)

    def test_interruption_before_second_snapshot_keeps_first_confirmed_rules(self) -> None:
        with (
            mock.patch.object(Path, "read_bytes", return_value=b'{"fixture":1}'),
            mock.patch.object(Path, "is_symlink", return_value=False),
        ):
            first = {key: ["Read(README.md)"] if key == "allow" else [] for key in install.RULE_KEYS}
            empty = {key: [] for key in install.RULE_KEYS}
            install.stage_settings_rules(self.target, b'{"fixture":1}', first, empty)
            confirmed = install.recover_settings_rules(self.target)
            self.assertEqual(confirmed, first)
            install.stage_settings_rules(self.target, b'{"fixture":2}', empty, confirmed)
            self.assertEqual(install.recover_settings_rules(self.target), first)
            self.assertEqual(install.load_rules(self.target), first)

    def test_failed_force_copy_of_identical_settings_does_not_claim_existing_rules(self) -> None:
        prior = {key: [] for key in install.RULE_KEYS}
        with (
            mock.patch.object(install, "classify_copy", return_value=("copied", b"{}")),
            mock.patch.object(install, "write_copy", side_effect=OSError(errno.ENOSPC, "simulated")),
            mock.patch.object(Path, "is_file", return_value=True),
            mock.patch.object(Path, "read_bytes", return_value=b"{}"),
        ):
            with self.assertRaises(OSError):
                install.install_settings(self.target, True, install.Counter(), prior)
            self.assertEqual(install.recover_settings_rules(self.target), prior)

    def run_install(self, *extra: str) -> tuple[int, str]:
        err = io.StringIO()
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            code = install.main([str(self.target), "--label", "t", *extra])
        return code, err.getvalue()

    def harness_matches_source(self) -> None:
        for src in (ROOT / ".claude" / "hooks").iterdir():
            if src.is_file() and src.suffix in (".sh", ".py"):
                self.assertEqual((self.target / ".claude/hooks" / src.name).read_bytes(), src.read_bytes(), src.name)
        self.assertEqual(sorted(self.target.rglob("*.xtemplates-new")), [])

    def test_replace_failure_mid_install_keeps_old_hook_and_rerun_converges(self) -> None:
        self.assertEqual(self.run_install()[0], 0)
        hook = self.target / ".claude/hooks/pre-bash-guard.sh"
        hook.write_bytes(b"#!/bin/sh\n# ban cu\n")

        def replace(src: Any, dst: Any, **kw: Any) -> None:
            if Path(dst).name == "pre-bash-guard.sh":
                raise OSError(errno.ENOSPC, "No space left on device")
            REAL_REPLACE(src, dst, **kw)

        with mock.patch.object(install.os, "replace", side_effect=replace):
            code, err = self.run_install("--force-harness")
        self.assertEqual(code, 1)
        self.assertIn(f"khi ghi {hook}: No space left on device", err)
        self.assertIn("chạy lại đúng lệnh install.py", err)
        self.assertNotIn("Traceback", err)
        self.assertEqual(hook.read_bytes(), b"#!/bin/sh\n# ban cu\n")
        self.assertEqual(tmp_leftovers(self.target), [])
        self.assertEqual(self.run_install("--force-harness")[0], 0)
        self.harness_matches_source()

    def test_file_size_limit_during_harness_leaves_no_empty_hook(self) -> None:
        """EFBIG thật giữa bước harness (cài mới): installer cũ để `.sh` rỗng/cụt (fail-open); nay hook hoặc chưa có hoặc
        đủ nội dung, và chạy lại không cần `--force-harness` thì khớp bản khung."""
        real = install.install_harness

        def limited(target: Path, force: bool) -> None:
            with file_size_limit(4096):
                real(target, force)

        with mock.patch.object(install, "install_harness", side_effect=limited):
            code, err = self.run_install()
        self.assertEqual(code, 1, err)
        self.assertIn("File too large", err)
        installed = [p for p in (self.target / ".claude/hooks").iterdir() if p.is_file()]
        self.assertLess(len(installed), len([p for p in (ROOT / ".claude/hooks").iterdir() if p.is_file()]))
        for path in installed:
            self.assertEqual(path.read_bytes(), (ROOT / ".claude/hooks" / path.name).read_bytes(), path.name)
        self.assertEqual(tmp_leftovers(self.target), [])
        self.assertEqual(self.run_install()[0], 0)
        self.harness_matches_source()

    def test_file_size_limit_on_git_hooks_leaves_no_empty_hook(self) -> None:
        with redirect_stderr(io.StringIO()), file_size_limit(512), self.assertRaises(OSError):
            install.install_git_hooks(self.target)
        self.assertEqual([p.name for p in self.hooks.iterdir() if p.name in install.GIT_HOOKS], [])
        self.assertEqual(tmp_leftovers(self.hooks), [])

    def test_empty_git_hook_is_replaced_but_foreign_hook_kept(self) -> None:
        self.hooks.mkdir(parents=True, exist_ok=True)
        empty, foreign = self.hooks / "pre-commit", self.hooks / "pre-push"
        empty.write_bytes(b"")
        foreign.write_bytes(b"#!/bin/sh\nexit 0\n")
        self.assertEqual((install.git_hook_action(empty), install.git_hook_action(foreign)), ("copied", "kept-own"))
        plan = {row["name"]: row["action"] for row in install.git_hooks_plan(self.target, False, False)["hooks"]}
        self.assertEqual((plan["pre-commit"], plan["pre-push"]), ("copied", "kept-own"))
        code, _ = self.run_install()
        self.assertEqual(code, 0)
        self.assertEqual(empty.read_bytes(), (ROOT / "framework/templates/git-hooks/pre-commit").read_bytes())
        self.assertEqual(stat.S_IMODE(empty.stat().st_mode), 0o755)
        self.assertEqual(foreign.read_bytes(), b"#!/bin/sh\nexit 0\n")


class WriteSitesAtomicTest(TestCase):
    """Mọi điểm ghi của T-5043 đi qua `write_bytes_atomic` (lỗi `os.replace` → tệp cũ nguyên, không rác)."""

    def setUp(self) -> None:
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()

    def assert_untouched_on_replace_failure(self, path: Path, call: Callable[[], object]) -> None:
        before = path.read_bytes() if path.exists() else None
        with mock.patch.object(install.os, "replace", side_effect=OSError("hỏng")), self.assertRaises(OSError):
            call()
        self.assertEqual(path.read_bytes() if path.exists() else None, before)
        self.assertEqual(tmp_leftovers(self.tmp), [])

    def test_each_write_site(self) -> None:
        src = self.tmp / "src.sh"
        src.write_bytes(b"#!/bin/sh\nmoi\n")
        dst = self.tmp / "dst.sh"
        dst.write_bytes(b"cu")
        self.assert_untouched_on_replace_failure(dst, lambda: install.write_copy(src, dst, "updated", b"moi"))
        new = self.tmp / "dst.sh.xtemplates-new"
        self.assert_untouched_on_replace_failure(new, lambda: install.write_copy(src, dst, "updated-new", b"moi"))
        install.write_copy(src, dst, "updated-new", b"moi")
        self.assertEqual((new.read_bytes(), dst.read_bytes()), (b"moi", b"cu"))
        gem, gsrc = self.tmp / "gemini.json", ROOT / "framework/templates/harness" / install.ADAPTERS["gemini"][0]
        gem.write_text("{}", encoding="utf-8")
        self.assert_untouched_on_replace_failure(gem, lambda: install.merge_gemini_settings(gem, gsrc))
        gi, gisrc = self.tmp / ".gitignore", self.tmp / "starter.gitignore"
        gi.write_text("a\n", encoding="utf-8")
        gisrc.write_text("b\n", encoding="utf-8")
        self.assert_untouched_on_replace_failure(gi, lambda: install.merge_gitignore(gi, gisrc))
        fresh = self.tmp / "fresh"
        fresh.mkdir()
        self.assert_untouched_on_replace_failure(fresh / ".gitignore", lambda: install.ensure_gitignore(fresh))
        yaml = self.tmp / "xt.yaml"
        yaml.write_text("lint: ''\n", encoding="utf-8")
        with redirect_stderr(io.StringIO()):
            self.assert_untouched_on_replace_failure(
                yaml, lambda: install.install_pack_yaml(self.tmp, "p", "fresh", {"lint": "npm run lint"})
            )


if __name__ == "__main__":
    main()
