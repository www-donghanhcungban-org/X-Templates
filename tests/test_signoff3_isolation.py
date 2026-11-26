"""Cô lập mạng của lớp test guard/hook/adapter (AUD-TEST-109/112) và `go_skippable` của dev-task.sh (AUD-HAR-417/422).

Mở rộng `tests.test_signoff2_scripts._NoNetworkCase`: shim `gh` VÀ `curl` lỗi ở đầu PATH, mọi lời gọi ghi vào tệp log.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
import nonet

ROW = "| Chủ | A | GO | 2026-11-07 |\n"
NET_CLASSES = (
    "tests.test_adapters.AdapterHostTest",
    "tests.test_hooks.PreBashGuardTest",
    "tests.test_hooks.GuardMatrixTest",
    "tests.test_hooks.GuardDeltaAuditTest",
    "tests.test_hooks.GuardEgressAuditTest",
    "tests.test_guard_strict.ReasonCodeLockTest",
)


class NetworkShimTest(unittest.TestCase):
    def test_shim_logs_calls_and_fails(self) -> None:
        td = Path(self.enterContext(tempfile.TemporaryDirectory()))
        log = nonet.make_shims(td)
        env = {**os.environ, "PATH": f"{td}{os.pathsep}{os.environ['PATH']}", "NET_SHIM_LOG": str(log)}
        self.assertEqual(nonet.calls(log), [])
        for tool in nonet.SHIM_TOOLS:
            r = subprocess.run([tool, "api", "x"], env=env, capture_output=True, check=False)
            self.assertEqual(r.returncode, 1)
        self.assertEqual(nonet.calls(log), ["gh api x", "curl api x"])

    def test_isolate_network_mocks_merge_check_and_shims_path(self) -> None:
        sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
        import guard

        real = guard.merge_check
        log = nonet.isolate_network(self, nonet.MERGE_OK)
        self.assertIsNot(guard.merge_check, real)
        self.assertEqual(guard.merge_check(["5"], str(ROOT)), nonet.MERGE_OK)
        self.assertEqual(Path(str(shutil.which("gh"))).read_text(encoding="utf-8"), nonet.SHIM)
        self.assertEqual(nonet.calls(log), [])


class _GuardLayerNoNetwork:
    """Mixin, không phải TestCase: mỗi lớp con chạy MỘT lớp của `NET_CLASSES` (D-608) để CI không dồn vào một shard."""

    index: int

    def test_class_makes_no_network_calls(self) -> None:
        """Lớp từng gọi `gh api repos/{owner}/{repo}/pulls/N` thật chạy xanh dưới shim lỗi và 0 lời gọi mạng."""
        with tempfile.TemporaryDirectory() as td:
            log = nonet.make_shims(Path(td))
            env = {**os.environ, "PATH": f"{td}{os.pathsep}{os.environ['PATH']}", "NET_SHIM_LOG": str(log)}
            r = subprocess.run(
                [sys.executable, "-m", "unittest", NET_CLASSES[self.index]],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=900,
                check=False,
            )
            self.assertEqual(r.returncode, 0, r.stderr[-2000:])
            self.assertEqual(nonet.calls(log), [])


class GuardLayersAdapterHostNoNetworkTest(_GuardLayerNoNetwork, unittest.TestCase):
    index = 0


class GuardLayersPreBashGuardNoNetworkTest(_GuardLayerNoNetwork, unittest.TestCase):
    index = 1


class GuardLayersGuardMatrixNoNetworkTest(_GuardLayerNoNetwork, unittest.TestCase):
    index = 2


class GuardLayersDeltaAuditNoNetworkTest(_GuardLayerNoNetwork, unittest.TestCase):
    index = 3


class GuardLayersEgressAuditNoNetworkTest(_GuardLayerNoNetwork, unittest.TestCase):
    index = 4


class GuardLayersReasonCodeLockNoNetworkTest(_GuardLayerNoNetwork, unittest.TestCase):
    index = 5


class GuardLayersPartitionTest(unittest.TestCase):
    def test_one_test_class_per_net_class(self) -> None:
        owners = [
            cls
            for cls in globals().values()
            if isinstance(cls, type) and issubclass(cls, _GuardLayerNoNetwork) and issubclass(cls, unittest.TestCase)
        ]
        self.assertEqual(sorted(cls.index for cls in owners), list(range(len(NET_CLASSES))))
        self.assertEqual(len(set(NET_CLASSES)), len(NET_CLASSES))
        for cls in owners:
            self.assertEqual(unittest.defaultTestLoader.loadTestsFromTestCase(cls).countTestCases(), 1)


@unittest.skipIf(shutil.which("bash") is None or shutil.which("find") is None, "cần bash + find")
@unittest.skipIf(os.geteuid() == 0, "root đi xuyên mọi thư mục")
class GoSkippableTest(unittest.TestCase):
    """AUD-HAR-417/422: thư mục không đi xuyên được không dừng formatter oan; lỗi lạ vẫn dừng (fail-closed)."""

    def setUp(self) -> None:
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        (self.tmp / "scripts").mkdir()
        shutil.copy(ROOT / "scripts" / "dev-task.sh", self.tmp / "scripts" / "dev-task.sh")
        self.go = self.tmp / "docs" / "GO-NO-GO-v1.md"
        self.go.parent.mkdir()
        self.go.write_text(ROW, encoding="utf-8")
        (self.tmp / "xt.yaml").write_text("format: touch format-ran\n", encoding="utf-8")

    @contextlib.contextmanager
    def locked(self, name: str, mode: int, child: str | None = None) -> Iterator[Path]:
        """Thư mục `name` mode `mode`; thoát khối (kể cả assert đỏ) thì mở khoá, xoá và xoá dấu `format-ran`."""
        d = self.tmp / name
        d.mkdir()
        if child:
            (d / child).mkdir()
        d.chmod(mode)
        try:
            yield d
        finally:
            d.chmod(0o700)
            shutil.rmtree(d)
            (self.tmp / "format-ran").unlink(missing_ok=True)

    def old_find(self) -> Path:
        """`find` không biết `-executable` (như BSD/busybox cũ) → dev-task.sh dùng đường go_skippable."""
        shim = self.tmp / "bin"
        shim.mkdir(exist_ok=True)
        real = shutil.which("find")
        (shim / "find").write_text(
            f'#!/bin/sh\nfor a in "$@"; do case "$a" in -executable) echo "find: unknown predicate" >&2; exit 1;; esac; done\nexec {real} "$@"\n',
            encoding="utf-8",
        )
        (shim / "find").chmod(0o755)
        return shim

    def run_format(self, shim: Path | None = None, **env: str) -> subprocess.CompletedProcess[str]:
        penv = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.tmp), **env)
        if shim:
            penv["PATH"] = f"{shim}{os.pathsep}{penv['PATH']}"
        return subprocess.run(
            ["bash", str(self.tmp / "scripts" / "dev-task.sh"), "format"],
            capture_output=True,
            text=True,
            cwd=self.tmp,
            env=penv,
            check=False,
        )

    def test_dir_with_r_without_x_holding_subdir(self) -> None:
        """(a) 0o644/0o600 + thư mục con: find báo `./pgdata/sub`, `[ -d ]` không stat được — vẫn bỏ qua."""
        for mode in (0o600, 0o644):
            for shim in (None, "old"):
                with self.subTest(mode=oct(mode), find=shim or "gnu"):
                    with self.locked("pgdata", mode, child="sub"):
                        r = self.run_format(self.old_find() if shim else None)
                        self.assertEqual(r.returncode, 0, r.stderr)
                        self.assertTrue((self.tmp / "format-ran").exists())
                        self.assertIn("bỏ qua", r.stderr)

    def test_unicode_and_quote_names_under_c_locale(self) -> None:
        """(b) `LC_ALL=C` làm GNU find escape tên (`\\303\\240`, `\\'`, `\\\\`) — không được dừng formatter oan."""
        for name in ("pgdàta", "it's", "back\\slash", "dấu'và\\"):
            with self.subTest(name=name):
                with self.locked(name, 0o000):
                    r = self.run_format()
                    self.assertEqual(r.returncode, 0, r.stderr)
                    self.assertTrue((self.tmp / "format-ran").exists())
                    self.assertIn("bỏ qua 1 thư mục", r.stderr)

    def test_unknown_find_error_with_escaped_name_still_stops(self) -> None:
        """Không có `-executable` và tên bị escape không khớp thư mục thật → fail-closed (dừng formatter)."""
        with self.locked("pgdàta", 0o000):
            r = self.run_format(self.old_find())
            self.assertNotEqual(r.returncode, 0, r.stderr)
            self.assertFalse((self.tmp / "format-ran").exists())

    def test_dir_with_x_without_r_still_stops(self) -> None:
        """AUD-HAR-422: còn `x` mất `r` (formatter theo chỉ mục git vẫn mở được file trong đó) → dừng."""
        with self.locked("only-x", 0o311):
            r = self.run_format()
            self.assertNotEqual(r.returncode, 0, r.stderr)
            self.assertFalse((self.tmp / "format-ran").exists())


if __name__ == "__main__":
    unittest.main()
