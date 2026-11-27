"""T-5082 (D-629 khay, D-630 cổng tải, ADR-0112): `scripts/xt_cpu_share.py` và chỗ nối ở `dev-task.sh`/`xt.yaml`.

Bảng giá trị với số nhân giả (1, 2, 4, 14, 64), PSI/loadavg giả (thiếu, hỏng, vượt 100 %), 0 nhân hiệu dụng; đồng thời
thật (hai tiến trình đăng ký cùng lúc thấy nhau, việc vượt khay chờ rồi chạy, khoá của PID đã chết hết hạn, thư mục cache
không ghi được); `run` trả đúng mã thoát và tín hiệu của lệnh con. Khay của test luôn ở thư mục tạm (`XDG_CACHE_HOME`),
không đụng khay thật của máy."""

from __future__ import annotations

import io
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import xt_cpu_share as cs

SCRIPT = ROOT / "scripts" / "xt_cpu_share.py"
HAS_AFFINITY = hasattr(os, "sched_getaffinity")
REC = (
    "import json, os, sys\nfrom pathlib import Path\n"
    "aff = len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None\n"
    "data = {'jobs': os.environ.get('XT_JOBS'), 'id': os.environ.get('XT_CPU_SHARE_ID'), 'aff': aff, 'nice': os.nice(0)}\n"
    "(Path(os.environ['OUT']) / (sys.argv[1] + '.json')).write_text(json.dumps(data))\n"
    "sys.exit(int(os.environ.get('REC_RC', '0')))\n"
)


def clean_env(**extra: str) -> dict[str, str]:
    """Môi trường của tiến trình con: bỏ dấu khay/XT_JOBS của cổng đang chạy test (test chạy bên trong một việc nặng) và
    `CI` (ở CI khay mặc định tắt — test khay phải chạy như máy dev; ca CI có test riêng)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("XT_CPU", "XT_JOBS", "XT_RESOURCE_")) and k != "CI"}
    env.update(extra)
    return env


class FormulaTest(unittest.TestCase):
    def test_shape_table_by_core_count(self):
        # n → (reserve, slots, usable, phần khi 1, 2, 3 việc)
        table = {
            1: (0, 1, 1, (1, 1, 1)),
            2: (1, 1, 1, (1, 1, 1)),
            4: (1, 1, 3, (2, 2, 2)),
            14: (2, 3, 12, (8, 6, 4)),
            64: (8, 16, 56, (38, 28, 18)),
        }
        for n, (reserve, slots, usable, shares) in table.items():
            with self.subTest(n=n):
                sh = cs.shape({}, ids=range(n))
                self.assertEqual((sh.n, sh.reserve, sh.slots, sh.usable), (n, reserve, slots, usable))
                self.assertEqual(tuple(cs.share(sh.usable, a) for a in (1, 2, 3)), shares)
        self.assertEqual(cs.share(56, 16), 3)
        self.assertEqual(cs.share(56, 100), 2)  # sàn min(2, usable)
        self.assertEqual(cs.share(1, 0), 1)

    def test_overrides_and_garbage(self):
        def dims(env: dict[str, str], n: int = 14) -> tuple[int, int, int]:
            sh = cs.shape(env, ids=range(n))
            return sh.reserve, sh.slots, sh.usable

        self.assertEqual(dims({"XT_CPU_RESERVE": "0", "XT_CPU_SLOTS": "5"}), (0, 5, 14))
        self.assertEqual(dims({"XT_CPU_RESERVE": " 3 ", "XT_CPU_SLOTS": "1"}), (3, 1, 11))
        for bad in ("-1", "abc", "1.5", "", "٣", "9999999"):
            with self.subTest(bad=bad):
                self.assertEqual(dims({"XT_CPU_RESERVE": bad, "XT_CPU_SLOTS": bad}), (2, 3, 12))
        self.assertEqual(dims({"XT_CPU_SLOTS": "0"}), (2, 3, 12))
        # 0 nhân hiệu dụng: dành hết nhân → vẫn còn 1 nhân dùng được
        self.assertEqual(dims({"XT_CPU_RESERVE": "14"}), (13, 3, 1))
        self.assertEqual(dims({"XT_CPU_RESERVE": "5"}, n=1), (0, 1, 1))
        self.assertEqual(cs.shape({}, ids=[]).n, 1)

    def test_quota_cuts_core_count(self):
        sh = cs.shape({}, ids=range(14), cores=4)
        self.assertEqual((sh.n, sh.reserve, sh.usable, len(sh.cpus)), (4, 1, 3, 14))
        self.assertEqual(cs.shape({}, ids=range(2), cores=8).n, 2)

    def test_fractional_quota_never_rounds_up_worker_budget(self):
        for cores, usable in ((Fraction(1, 2), 1), (Fraction(3, 2), 1), (Fraction(19, 2), 7)):
            with self.subTest(quota=cores):
                self.assertEqual(cs.shape({}, ids=range(14), cores=cores).usable, usable)

    def test_thresholds(self):
        self.assertEqual(cs.thresholds({}), (0.85, 0.85 - 0.15))
        self.assertEqual(cs.thresholds({"XT_CPU_HIGH": "90"}), (0.9, 0.9 - 0.15))
        self.assertEqual(cs.thresholds({"XT_CPU_HIGH": "10"}), (0.1, 0.0))
        self.assertEqual(cs.thresholds({"XT_CPU_HIGH": "80", "XT_CPU_LOW": "95.5"}), (0.8, 0.8))  # thấp ≤ cao
        self.assertEqual(cs.thresholds({"XT_CPU_HIGH": "x", "XT_CPU_LOW": "50"}), (0.85, 0.5))
        self.assertEqual(cs.thresholds({"XT_CPU_LOW": "-5"}), (0.85, 0.85 - 0.15))

    def test_off_by_switch_and_by_default_on_ci(self):
        rows = [
            ({}, False),
            ({"XT_CPU_SHARE": "OFF "}, True),
            ({"CI": "true"}, True),  # GitHub Actions: runner dành riêng → mặc định tắt
            ({"CI": "1"}, True),
            ({"CI": "true", "XT_CPU_SHARE": " On"}, False),  # bật lại ở CI
            ({"CI": "true", "XT_CPU_SHARE": "x"}, True),
            ({"CI": ""}, False),
            ({"CI": "False"}, False),
            ({"CI": "0"}, False),
        ]
        for env, want in rows:
            with self.subTest(env=env):
                self.assertEqual(cs.off(env), want)

    def test_gate_measured_only_when_it_decides(self):
        self.assertTrue(cs.gated(1, 3, False, False))
        for args in ((0, 3, False, False), (3, 3, False, False), (1, 3, True, False), (1, 3, False, True)):
            with self.subTest(args=args):
                self.assertFalse(cs.gated(*args))

    def test_pick_avoids_reserved_and_busy_cores(self):
        self.assertEqual(cs.pick(range(14), 2, [], 8), tuple(range(2, 10)))
        self.assertEqual(cs.pick(range(14), 2, [list(range(2, 10))], 6), (10, 11, 12, 13))
        self.assertEqual(cs.pick(range(14), 2, [[2, 3, 99]], 2), (4, 5))
        self.assertEqual(cs.pick([5], 0, [], 1), (5,))


class PressureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.psi = self.tmp / "cpu"

    def test_psi_parse(self):
        cases = {
            "some avg10=42.50 avg60=1.00 avg300=0.00 total=1\nfull avg10=0.00 avg60=0.00 avg300=0.00 total=0\n": 0.425,
            "some avg10=100.00 avg60=0 avg300=0 total=0": 1.0,
            "some avg10=0.00 avg60=0 avg300=0 total=0\n": 0.0,
            "some avg10=100.01 avg60=0\n": None,  # vượt 100 % là hỏng
            "some avg10=abc avg60=0\n": None,
            "full avg10=50.00\n": None,
            "": None,
        }
        for text, want in cases.items():
            with self.subTest(text=text):
                self.psi.write_text(text, encoding="ascii")
                self.assertEqual(cs.psi(self.psi), want)
        self.psi.write_bytes("some avg10=1 ü".encode())
        self.assertIsNone(cs.psi(self.psi))
        self.assertIsNone(cs.psi(self.tmp / "missing"))

    def test_loadavg(self):
        with mock.patch.object(cs.os, "getloadavg", return_value=(7.0, 1.0, 1.0)):
            self.assertEqual(cs.loadavg(14), 0.5)
        with mock.patch.object(cs.os, "getloadavg", side_effect=OSError("no")):
            self.assertIsNone(cs.loadavg(14))
        with mock.patch.object(cs, "os", SimpleNamespace()):
            self.assertIsNone(cs.loadavg(4))

    def stat_pair(self, first: str, second: str) -> tuple[Path, "list[float]"]:
        """/proc/stat giả: đọc lần 1 thấy `first`, `sleep` giả ghi `second` cho lần đọc 2."""
        path, slept = self.tmp / "stat", []
        path.write_text(first, encoding="ascii")

        def sleep(s: float) -> None:
            slept.append(s)
            path.write_text(second, encoding="ascii")

        self.sleep = sleep
        return path, slept

    def test_cpu_busy_from_proc_stat(self):
        line = "cpu  {} 0 {} {} {} 0 0 0 0 0\ncpu0 1 2 3 4\n"
        cases = [  # (user, system, idle, iowait) lần 1 → lần 2: bận = Δ(user+system) / Δtổng; iowait tính là rảnh
            ((100, 0, 100, 0), (160, 20, 120, 0), 0.8),
            ((100, 0, 100, 0), (100, 0, 150, 50), 0.0),
            ((100, 0, 100, 0), (200, 0, 100, 0), 1.0),
            ((100, 0, 100, 0), (100, 0, 100, 0), None),  # không có nhịp nào trôi qua
        ]
        for a, b, want in cases:
            with self.subTest(a=a, b=b):
                path, slept = self.stat_pair(line.format(*a), line.format(*b))
                got = cs.cpu_busy(path, self.sleep)
                self.assertEqual(None if got is None else round(got, 6), want)
                self.assertEqual(slept, [cs.SAMPLE])
        for bad in ("", "intr 1 2 3 4 5 6\n", "cpu 1 2 x 4 5\n", "cpu 1 2 3\n", "cpu 1 2 3 -4 5\n"):
            with self.subTest(bad=bad):
                path, slept = self.stat_pair(bad, bad)
                self.assertIsNone(cs.cpu_busy(path, self.sleep))
                self.assertEqual(slept, [])  # hỏng ngay lần đọc đầu: không chờ
        path, _ = self.stat_pair(line.format(1, 1, 1, 1), "broken")
        self.assertIsNone(cs.cpu_busy(path, self.sleep))  # lần đọc 2 hỏng
        self.assertIsNone(cs.cpu_busy(self.tmp / "missing", self.sleep))
        (self.tmp / "bin").write_bytes(b"cpu \xff\n")
        self.assertIsNone(cs.cpu_busy(self.tmp / "bin", self.sleep))

    def test_pressure_is_max_of_available_signals(self):
        """MAX(CPU bận, loadavg/n, PSI/100); mỗi tín hiệu thiếu/hỏng thì bỏ; thiếu cả ba → None (bỏ qua cổng)."""
        line = "cpu  {} 0 0 {} 0 0 0 0 0 0\n"
        stat_ok = (line.format(0, 0), line.format(90, 10))  # bận 0,9
        psi_ok = "some avg10=40.00 avg60=0\n"
        for busy in (True, False):
            for load in (0.6, None, 1.3):
                for p in (psi_ok, None, "some avg10=x\n"):
                    with self.subTest(busy=busy, load=load, psi=p):
                        path, _ = self.stat_pair(*stat_ok) if busy else self.stat_pair("broken", "broken")
                        if p is None:
                            self.psi.unlink(missing_ok=True)
                        else:
                            self.psi.write_text(p, encoding="ascii")
                        found = [
                            v for v in (0.9 if busy else None, load, 0.4 if p == psi_ok else None) if v is not None
                        ]
                        with mock.patch.object(cs, "loadavg", return_value=load):
                            got = cs.pressure(14, self.psi, path, self.sleep)
                        self.assertEqual(got, max(found) if found else None)

    def test_gate_hysteresis_and_decide(self):
        high, low = 0.85, 0.70
        self.assertFalse(cs.gate_closed(0.85, False, high, low))
        self.assertTrue(cs.gate_closed(0.86, False, high, low))
        self.assertTrue(cs.gate_closed(0.75, True, high, low))  # giữa hai ngưỡng: giữ đóng
        self.assertFalse(cs.gate_closed(0.69, True, high, low))
        self.assertTrue(cs.gate_closed(None, True, high, low))
        self.assertFalse(cs.gate_closed(None, False, high, low))

        def see(active=1, head=False, head_waiting=False, pressure: float | None = 0.1, closed=False) -> cs.Seen:
            return cs.Seen(active, 3, head, head_waiting, pressure, closed)

        rows = [
            (see(), (True, False)),
            (see(pressure=0.9), (False, True)),
            (see(pressure=0.9, active=0), (True, True)),  # khay trống: luôn nhận
            (see(pressure=0.9, head=True), (True, True)),  # PR đầu hàng: luôn nhận
            (see(pressure=None, closed=True), (True, True)),  # không đo được: bỏ qua cổng
            (see(pressure=0.75, closed=True), (False, True)),
            (see(pressure=0.5, closed=True), (True, False)),
            (see(active=3), (False, False)),  # khay đầy
            (see(active=3, head=True, pressure=0.99), (True, True)),  # PR đầu hàng bỏ qua cả khay đầy (slots + 1 việc)
            (cs.Seen(4, 3, True, False, 0.99, False), (False, True)),
            (see(head_waiting=True), (False, False)),  # nhường việc đầu hàng đang chờ
            (see(head_waiting=True, head=True), (True, False)),
        ]
        for seen, want in rows:
            with self.subTest(seen=seen):
                ok, closed, why = cs.decide(seen, high, low)
                self.assertEqual((ok, closed), want)
                self.assertEqual(why == "", ok)
        self.assertIn("áp lực CPU 90%", cs.decide(see(pressure=0.9), high, low)[2])
        self.assertIn("khay đầy (3/3", cs.decide(see(active=3), high, low)[2])


class ProcTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def stat(self, pid: int, state: str, ppid: int, start: int, comm: str = "py thon) (x") -> None:
        d = self.tmp / str(pid)
        d.mkdir(exist_ok=True)
        rest = " ".join(["0"] * 17)
        (d / "stat").write_text(f"{pid} ({comm}) {state} {ppid} {rest} {start} 0 0\n", encoding="utf-8")

    def test_cpu_ids_and_quota(self):
        with mock.patch.object(cs.os, "sched_getaffinity", return_value={3, 1}, create=True):
            self.assertEqual(cs.cpu_ids(), [1, 3])
        with mock.patch.object(cs.os, "sched_getaffinity", return_value=set(), create=True):
            with mock.patch.object(cs.os, "cpu_count", return_value=None):
                self.assertEqual(cs.cpu_ids(), [0])
        with mock.patch.object(cs, "os", SimpleNamespace(cpu_count=lambda: 3)):
            self.assertEqual(cs.cpu_ids(), [0, 1, 2])
        proc, cg = self.tmp / "proc", self.tmp / "cg"
        (proc / "self").mkdir(parents=True)
        (cg / "a" / "b").mkdir(parents=True)
        self.assertIsNone(cs.quota(proc, cg))  # không có /proc/self/cgroup
        (proc / "self" / "cgroup").write_text("1:cpu:/x\n", encoding="utf-8")
        self.assertIsNone(cs.quota(proc, cg))  # không phải cgroup v2
        (proc / "self" / "cgroup").write_text("0::/a/b\n", encoding="utf-8")
        self.assertIsNone(cs.quota(proc, cg))  # không có cpu.max
        for raw, want in (
            ("200000 100000", 2),
            ("150000 100000", Fraction(3, 2)),
            ("50000 100000", Fraction(1, 2)),
            ("max 100000", None),
            ("0 100000", None),
            ("100 0", None),
            ("", None),
        ):
            with self.subTest(raw=raw):
                (cg / "a" / "b" / "cpu.max").write_text(raw + "\n", encoding="utf-8")
                self.assertEqual(cs.quota(proc, cg), want)

    def test_quota_and_available_ram_include_ancestor_limits(self):
        proc, cg = self.tmp / "proc", self.tmp / "cg"
        (proc / "self").mkdir(parents=True)
        leaf = cg / "a" / "b"
        leaf.mkdir(parents=True)
        membership = proc / "self" / "cgroup"
        membership.write_text("0::/a/b\n")
        (leaf.parent / "cpu.max").write_text("150000 100000\n")
        (leaf / "cpu.max").write_text("max 100000\n")
        self.assertEqual(cs.quota(proc, cg), Fraction(3, 2))
        (proc / "meminfo").write_text("MemAvailable:       3000 kB\n")
        (leaf.parent / "memory.max").write_text("4096000\n")
        (leaf.parent / "memory.current").write_text("2048000\n")
        (leaf / "memory.max").write_text("max\n")
        self.assertEqual(cs.memory_kib(proc, cg), 2000)
        (proc / "meminfo").write_text("MemTotal:           7000 kB\n")
        (leaf.parent / "memory.current").write_text("4096001\n")
        self.assertEqual(cs.memory_kib(proc, cg), 0)
        (leaf.parent / "memory.current").write_text("-1\n")
        self.assertIsNone(cs.memory_kib(proc, cg))
        membership.write_text("0::/a/../b\n")
        self.assertEqual(cs.cgroup_paths(proc, cg), ())
        self.assertIsNone(cs.memory_kib(self.tmp, cg))

    def test_stat_alive_ancestors(self):
        self.stat(100, "S", 50, 777)
        self.stat(50, "S", 20, 1)
        self.stat(20, "S", 1, 1)
        self.assertEqual(cs.started(100, self.tmp), "777")
        self.assertIsNone(cs.started(4242, self.tmp))
        self.assertEqual(cs.ancestors(100, self.tmp), {50, 20})
        self.stat(60, "S", 61, 1)
        self.stat(61, "S", 60, 1)  # vòng lặp (hỏng) — trần độ sâu chặn
        self.assertEqual(cs.ancestors(60, self.tmp), {60, 61})
        (self.tmp / "70").mkdir()
        (self.tmp / "70" / "stat").write_text("70 (x) S abc\n", encoding="utf-8")
        self.assertEqual(cs.ancestors(70, self.tmp), set())
        with mock.patch.object(cs.os, "kill") as kill:
            self.assertTrue(cs.alive(100, "777", self.tmp))
            self.assertFalse(cs.alive(100, "778", self.tmp))  # PID bị tái dùng
            self.assertTrue(cs.alive(100, None, self.tmp))
            self.assertTrue(cs.alive(4242, "1", self.tmp))  # không có /proc: tin os.kill
            self.stat(101, "Z", 1, 5)
            self.assertFalse(cs.alive(101, "5", self.tmp))  # zombie
            kill.side_effect = ProcessLookupError
            self.assertFalse(cs.alive(100, "777", self.tmp))
            kill.side_effect = PermissionError
            self.assertTrue(cs.alive(100, "777", self.tmp))
        self.assertEqual(cs.ancestors(os.getpid()) & {os.getppid()}, {os.getppid()} if os.getppid() > 1 else set())

    def test_read_entry(self):
        f = self.tmp / "job-1.json"
        for text, want in (
            ("{", None),
            ("[]", None),
            ('{"pid": "1"}', None),
            ('{"pid": 0}', None),
            ('{"pid": true}', None),
            ('{"pid": 5, "cpus": "x"}', {"pid": 5, "cpus": []}),
            ('{"pid": 5, "cpus": [1, "a", 2.0, 3]}', {"pid": 5, "cpus": [1, 3]}),
        ):
            with self.subTest(text=text):
                f.write_text(text, encoding="utf-8")
                self.assertEqual(cs.read_entry(f), want)
        self.assertIsNone(cs.read_entry(self.tmp / "missing.json"))


class TrayTest(unittest.TestCase):
    """Khay trong thư mục tạm; /proc giả để đăng ký của "tiến trình khác" (PID của chính test) không bị coi là tổ tiên."""

    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.d = self.tmp / "tray"
        self.proc = self.tmp / "proc"
        self.proc.mkdir()
        self.psi = self.tmp / "psi"
        self.sh = cs.shape({}, ids=range(14))
        self.limits = (0.85, 0.70)
        self.err = io.StringIO()
        self.enterContext(redirect_stderr(self.err))

    def other(self, pid: int, prefix: str = cs.JOB, **data: object) -> Path:
        self.d.mkdir(exist_ok=True)
        f = self.d / f"{prefix}{pid}.json"
        f.write_text(json.dumps({"pid": pid, **data}), encoding="utf-8")
        return f

    def measure(self, n: int) -> float | None:
        self.measured.append(n)
        return cs.psi(self.psi)

    def attempt(self, head: bool = False) -> cs.Job | str:
        self.measured: list[int] = getattr(self, "measured", [])
        return cs.attempt(self.d, self.sh, head, self.limits, self.proc, self.measure)

    def test_tray_dir(self):
        self.assertEqual(cs.tray_dir({"XDG_CACHE_HOME": "/c"}), Path("/c/xt-cpu"))
        with mock.patch.dict(os.environ, {"HOME": "/h"}):
            self.assertEqual(cs.tray_dir({"XDG_CACHE_HOME": "rel"}), Path("/h/.cache/xt-cpu"))
            self.assertEqual(cs.tray_dir({}), Path("/h/.cache/xt-cpu"))

    def test_first_job_alone_then_share_shrinks(self):
        self.psi.write_text("some avg10=99.00 avg60=0\n", encoding="ascii")
        got = self.attempt()
        self.assertEqual(got, cs.Job(tuple(range(2, 10)), 8))  # khay trống: nhận dù áp lực cao
        me = json.loads((self.d / f"{cs.JOB}{os.getpid()}.json").read_text(encoding="utf-8"))
        self.assertEqual((me["cpus"], me["jobs"], me["head"]), (list(range(2, 10)), 8, False))
        self.assertEqual(self.measured, [])  # khay trống: không đo (đo CPU bận tốn 0,5 s)
        self.assertFalse((self.d / cs.CLOSED).exists())
        (self.d / f"{cs.JOB}{os.getpid()}.json").unlink()
        self.other(os.getppid(), cpus=list(range(2, 10)), jobs=8)  # việc khác đang chạy
        self.assertEqual(self.attempt(), "áp lực CPU 99% (nhận lại khi dưới 70%)")
        self.assertEqual(self.measured, [14])
        self.assertTrue((self.d / cs.CLOSED).exists())
        self.assertTrue((self.d / f"{cs.WAIT}{os.getpid()}.json").exists())
        # PR đầu hàng bỏ qua cổng tải nhưng chỉ nhận phần còn trống.
        self.assertEqual(self.attempt(head=True), cs.Job((10, 11, 12, 13), 4))
        self.assertEqual(self.measured, [14])
        self.assertTrue((self.d / cs.CLOSED).exists())  # không đo → giữ trạng thái cổng
        self.assertFalse((self.d / f"{cs.WAIT}{os.getpid()}.json").exists())

    def test_share_with_another_job_and_pressure_reopens(self):
        self.other(os.getppid(), cpus=list(range(2, 10)), jobs=8)
        self.psi.write_text("some avg10=10.00 avg60=0\n", encoding="ascii")
        got = self.attempt()
        assert isinstance(got, cs.Job)
        self.assertEqual(got.jobs, 4)
        self.assertEqual(got.cpus, (10, 11, 12, 13))
        self.assertFalse((self.d / cs.CLOSED).exists())
        self.assertFalse((self.d / f"{cs.WAIT}{os.getpid()}.json").exists())

    def test_full_tray_and_head_waiter(self):
        for pid in (os.getppid(), 1):
            self.other(pid, jobs=2, cpus=[])
        self.sh = cs.shape({"XT_CPU_SLOTS": "2"}, ids=range(14))
        self.assertEqual(self.attempt(), "khay đầy (2/2 việc)")
        got = self.attempt(head=True)  # PR đầu hàng vượt khay đầy: việc thứ slots + 1, vẫn đăng ký và chia phần
        self.assertEqual(got, cs.Job(got.cpus, cs.share(self.sh.usable, 3)) if isinstance(got, cs.Job) else None)
        head_job = json.loads((self.d / f"{cs.JOB}{os.getpid()}.json").read_text(encoding="utf-8"))
        self.assertEqual((head_job["head"], head_job["jobs"]), (True, 4))
        (self.d / f"{cs.JOB}{os.getpid()}.json").unlink()
        self.sh = cs.shape({"XT_CPU_SLOTS": "5"}, ids=range(14))
        self.other(1, prefix=cs.WAIT, head=True)
        self.assertEqual(self.attempt(), "nhường việc của PR đầu hàng đang chờ")
        self.assertIsInstance(self.attempt(head=True), cs.Job)

    def test_dead_lease_expires_and_broken_lease_blocks_admission(self):
        dead = subprocess.run([sys.executable, "-c", "import os; print(os.getpid())"], capture_output=True, text=True)
        stale = self.other(int(dead.stdout), cpus=[2, 3])
        broken = self.other(7)
        broken.write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "lease CPU hỏng"):
            self.attempt()
        self.assertTrue(broken.exists())
        broken.unlink()
        self.assertEqual(self.attempt(), cs.Job(tuple(range(2, 10)), 8))
        self.assertFalse(stale.exists())

    def test_oversized_pid_lease_is_dead_not_a_traceback(self):
        huge = self.other(99999999999999, jobs=1)
        self.assertFalse(cs.alive(99999999999999, None, self.proc))
        self.assertEqual(self.attempt(), cs.Job(tuple(range(2, 10)), 8))
        self.assertFalse(huge.exists())

    def test_nested_job_is_not_registered(self):
        self.other(os.getppid(), jobs=6)  # tiến trình còn sống, đóng vai việc cha đã đăng ký
        with mock.patch.object(cs, "ancestors", return_value={os.getppid(), 9}):
            self.assertEqual(self.attempt(), cs.Job((), 6, nested=True))
        self.assertFalse((self.d / f"{cs.JOB}{os.getpid()}.json").exists())

    def test_raw_requests_and_priority_cannot_exceed_leases(self):
        self.other(os.getppid(), cpus=list(range(2, 10)), jobs=8, usable=12)
        self.other(1, cpus=list(range(10, 14)), jobs=4, usable=12)
        self.assertEqual(self.attempt(head=True), "hết ngân sách CPU")
        (self.d / f"{cs.JOB}1.json").unlink()
        got = cs.attempt(self.d, self.sh, True, self.limits, self.proc, self.measure, 999)
        self.assertEqual(got, cs.Job((10, 11, 12, 13), 4))

    def test_ram_budget_is_checked_inside_admission(self):
        args = (self.d, self.sh, True, self.limits, self.proc, self.measure)
        self.other(os.getppid(), cpus=[2, 3], jobs=2, memory_mib=600)
        with mock.patch.object(cs, "memory_kib", return_value=1000 * 1024):
            self.assertEqual(cs.attempt(*args, memory=(200, 100)), cs.Job((4,), 1))
            own = self.d / f"{cs.JOB}{os.getpid()}.json"
            own.unlink()
            self.other(1, cpus=[4], jobs=1, memory_mib=200)
            self.assertEqual(cs.attempt(*args, memory=(200, 100)), "thiếu RAM khả dụng")
        with mock.patch.object(cs, "memory_kib", return_value=None):
            with self.assertRaisesRegex(ValueError, "không đo được RAM"):
                cs.attempt(*args, memory=(200, 100))
        self.assertEqual(cs.memory_workers(1200 * 1024, 100, 200, [{"jobs": 2}]), 3)

    def test_wait_timeout_clears_queue_entry(self):
        self.other(os.getppid(), jobs=12)
        with mock.patch.object(cs.time, "monotonic", side_effect=[1, 1, 2]):
            with self.assertRaisesRegex(ValueError, "hết thời gian chờ"):
                cs.admit({"XT_RESOURCE_WAIT_TIMEOUT": "1"}, self.sh, True, self.d, self.proc, sleep=lambda _: None)
        self.assertFalse((self.d / f"{cs.WAIT}{os.getpid()}.json").exists())

    def test_invalid_lease_fields_and_symlinked_registry_fail_closed(self):
        for data in ({"jobs": 0}, {"jobs": 1, "usable": False}, {"jobs": 1, "memory_mib": -1}):
            with self.subTest(data=data):
                self.other(os.getppid(), **data)
                with self.assertRaises(ValueError):
                    self.attempt()
        link = self.tmp / "link"
        link.symlink_to(self.d, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "quyền thư mục"), cs.locked(link):
            self.fail("không được khoá registry qua symlink")

    def test_admit_backs_off_without_deadline(self):
        answers = iter(["khay đầy (1/1 việc)", "khay đầy (1/1 việc)", "áp lực CPU 90%", "x", "x", "x", "x", "x"])
        waits: list[float] = []
        final = cs.Job((2,), 1)
        seq = [*answers, final]
        with mock.patch.object(cs, "attempt", side_effect=seq):
            self.assertEqual(cs.admit({}, self.sh, False, self.d, sleep=waits.append), final)
        self.assertEqual(waits, [1.0, 2.0, 4.0, 8.0, 16.0, 30.0, 30.0, 30.0])
        self.assertEqual(self.err.getvalue().count("chờ khay"), 3)  # chỉ log khi lý do đổi


class RunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.err = io.StringIO()
        self.enterContext(redirect_stderr(self.err))
        self.env = {"XDG_CACHE_HOME": str(self.tmp)}
        self.nice = self.enterContext(mock.patch.object(cs.os, "nice", return_value=0))
        self.aff = self.enterContext(mock.patch.object(cs.os, "sched_setaffinity", create=True))

    def test_off_nested_and_broken_tray(self):
        spawn = self.enterContext(mock.patch.object(cs, "spawn", return_value=9))
        envs = ({"XT_CPU_SHARE": "OFF "}, {"XT_CPU_SHARE_ID": "9"}, {"CI": "true"})
        for env in envs:
            with self.subTest(env=env):
                self.assertEqual(cs.run(["true", "a"], env, False), 9)
        self.assertEqual(spawn.call_args_list, [mock.call(["true", "a"], env) for env in envs])
        self.assertEqual(cs.run(["true"], {"XDG_CACHE_HOME": str(SCRIPT)}, False), 2)
        self.assertIn("khay CPU không dùng được (NotADirectoryError", self.err.getvalue())
        self.assertIn("XT_CPU_SHARE=off", self.err.getvalue())
        with mock.patch.object(cs, "admit", return_value=cs.Job((), 3, nested=True)):
            self.assertEqual(cs.run(["true"], self.env, False), 9)
        self.assertEqual(spawn.call_args.args[1]["XT_JOBS"], "3")
        self.nice.assert_not_called()
        self.aff.assert_not_called()

    def test_plain_keeps_exit_codes(self):
        self.assertEqual(cs.plain([sys.executable, "-c", "raise SystemExit(5)"], dict(os.environ)), 5)
        self.assertEqual(cs.plain(["khong-co-lenh-nay-xt"], {}), 127)
        with mock.patch.object(cs, "exit_code", return_value=143) as code:
            cs.plain(
                [sys.executable, "-c", "import os, signal; os.kill(os.getpid(), signal.SIGTERM)"], dict(os.environ)
            )
        code.assert_called_once_with(-signal.SIGTERM)

    def test_signal_before_child_starts_is_forwarded(self):
        child = mock.Mock(wait=mock.Mock(return_value=-signal.SIGINT))

        def popen(*_a: object, **_k: object) -> mock.Mock:
            os.kill(os.getpid(), signal.SIGINT)  # tới giữa lúc cài bộ chuyển và lúc lệnh con khởi động
            return child

        with mock.patch.object(cs.subprocess, "Popen", side_effect=popen):
            self.assertEqual(cs.spawn(["x"], {}), -signal.SIGINT)
        child.send_signal.assert_called_once_with(signal.SIGINT)

    def test_run_registers_limits_and_returns_child_code(self):
        sh = cs.shape({}, ids=range(14))
        with mock.patch.object(cs, "shape", return_value=sh):
            rc = cs.run(
                [sys.executable, "-c", "import os,sys; sys.exit(int(os.environ['XT_JOBS']) + 30)"], self.env, False
            )
        self.assertEqual(rc, 38)
        self.nice.assert_called_once_with(cs.NICE)
        self.aff.assert_called_once_with(0, tuple(range(2, 10)))
        self.assertEqual(list((self.tmp / "xt-cpu").glob("job-*")), [])  # xoá đăng ký khi xong
        self.nice.reset_mock()
        with mock.patch.object(cs, "shape", return_value=cs.shape({}, ids=range(1))):
            self.assertEqual(cs.run([sys.executable, "-c", "pass"], self.env, True), 0)
        self.nice.assert_called_once_with(0)  # đầu hàng: không hạ ưu tiên
        self.assertEqual(self.aff.call_args, mock.call(0, (0,)))

    def test_limit_failures_are_ignored(self):
        self.nice.side_effect = PermissionError
        self.aff.side_effect = OSError
        cs.limit(cs.Job((1, 2), 2), False)
        self.aff.assert_called_once_with(0, (1, 2))
        with mock.patch.object(cs, "os", SimpleNamespace(nice=lambda _n: 0)):
            cs.limit(cs.Job((1, 2), 2), True)  # hệ không có affinity
        cs.limit(cs.Job((), 2), True)
        self.assertEqual(self.aff.call_count, 1)

    def test_child_env_exports_granted_jobs(self):
        job = cs.Job((1,), 3)
        self.assertEqual(cs.child_env({}, job)["XT_JOBS"], "3")
        self.assertEqual(cs.child_env({"XT_JOBS": ""}, job)["XT_JOBS"], "3")
        self.assertEqual(cs.child_env({"XT_JOBS": "abc"}, job)["XT_JOBS"], "3")
        self.assertEqual(cs.child_env({"XT_JOBS": "5"}, job)["XT_CPU_SHARE_ID"], str(os.getpid()))

    def test_spawn_forwards_signals_and_restores_handlers(self):
        before = signal.getsignal(signal.SIGTERM)
        code = "import os, signal, time; os.kill(os.getppid(), signal.SIGTERM); time.sleep(60)"
        self.assertEqual(cs.spawn([sys.executable, "-c", code], dict(os.environ)), -signal.SIGTERM)
        self.assertIs(signal.getsignal(signal.SIGTERM), before)
        self.assertEqual(cs.spawn(["khong-co-lenh-nay-xt"], {}), 127)
        with mock.patch.object(cs.subprocess, "Popen", side_effect=PermissionError("denied")):
            self.assertEqual(cs.spawn(["x"], {}), 126)

    def test_exit_code(self):
        kill = mock.Mock()
        self.assertEqual(cs.exit_code(3, kill), 3)
        with mock.patch.object(cs.signal, "signal") as sig:
            self.assertEqual(cs.exit_code(-15, kill), 143)
            sig.assert_called_once_with(15, signal.SIG_DFL)
            sig.side_effect = OSError
            self.assertEqual(cs.exit_code(-9, kill), 137)
        self.assertEqual(kill.call_args_list, [mock.call(os.getpid(), 15), mock.call(os.getpid(), 9)])


class JobsAndCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.env = {"XDG_CACHE_HOME": str(self.tmp)}
        self.sh = cs.shape({}, ids=range(14))
        self.enterContext(mock.patch.object(cs, "shape", return_value=self.sh))

    def test_jobs(self):
        self.assertEqual(cs.jobs({**self.env, "XT_CPU_SHARE": "off"}, "fb"), "fb")
        self.assertEqual(cs.jobs({**self.env, "XT_JOBS": "5"}, "fb"), "5")
        self.assertEqual(cs.jobs({**self.env, "XT_JOBS": "999"}, "fb"), "8")
        self.assertEqual(cs.jobs({**self.env, "XT_CPU_SHARE_ID": "1"}, "fb"), "14")
        self.assertEqual(cs.jobs({"XDG_CACHE_HOME": str(SCRIPT)}, "fb"), "1")
        self.assertEqual(cs.jobs({**self.env, "XT_JOBS": "abc"}, "fb"), "8")  # rác: bỏ qua
        tray = self.tmp / "xt-cpu"
        (tray / f"{cs.JOB}{os.getpid()}.json").write_text(json.dumps({"pid": os.getpid(), "jobs": 8}), encoding="utf-8")
        self.assertEqual(cs.jobs(self.env, "fb"), "4")
        with mock.patch.object(cs, "ancestors", return_value={os.getpid()}):
            self.assertEqual(cs.jobs(self.env, "fb"), "8")  # phục hồi ngân sách từ lease cha

    def test_info_reports_available_measurements(self):
        with (
            mock.patch.object(cs, "quota", return_value=Fraction(3, 2)),
            mock.patch.object(cs, "memory_kib", return_value=2048),
        ):
            rc, out, _ = self.main("info", env=self.env)
            self.assertEqual(rc, 0)
            info = json.loads(out)
            self.assertEqual((info["cpu_quota"], info["memory_available_mib"]), ("3/2", 2))
        with mock.patch.object(cs, "quota", return_value=None), mock.patch.object(cs, "memory_kib", return_value=None):
            info = cs.resource_info(self.env)
            self.assertIsNone(info["cpu_quota"])
            self.assertIsNone(info["memory_available_mib"])

    def test_probe(self):
        self.assertTrue(cs.probe({}))
        self.assertFalse(cs.probe({"XT_CPU_SHARE": "off"}))
        with mock.patch.object(cs.importlib, "import_module", side_effect=ImportError):
            self.assertFalse(cs.probe({}))

    def main(self, *argv: str, env: dict[str, str] | None = None) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {"CI": "", **(env or {})}), redirect_stdout(out), redirect_stderr(err):
            rc = cs.main(list(argv))
        return rc, out.getvalue(), err.getvalue()

    def test_main(self):
        self.assertEqual(self.main("probe", env={"XT_CPU_SHARE": ""})[:2], (0, cs.MARK + "\n"))
        self.assertEqual(self.main("probe", env={"XT_CPU_SHARE": "off"})[:2], (0, ""))
        self.assertEqual(self.main("jobs", "--fallback", "auto", env={"XT_CPU_SHARE": "off"})[:2], (0, "auto\n"))
        rc, out, _ = self.main("jobs", env={"XT_CPU_SHARE": "off"})
        self.assertEqual((rc, out), (0, f"{len(cs.cpu_ids())}\n"))
        for bad in (
            ("jobs", "--fallback"),
            ("jobs", "x", "y"),
            ("probe", "x"),
            ("run", "true"),
            ("run", "--"),
            ("run", "--fast", "--", "true"),
            ("nope",),
            (),
        ):
            with self.subTest(argv=bad):
                rc, _, err = self.main(*bad)
                self.assertEqual(rc, 2)
                self.assertIn("dùng: xt_cpu_share.py", err)
        with mock.patch.object(cs, "run", return_value=4) as run:
            self.assertEqual(self.main("run", "--head", "--", "a", "--", "b")[0], 4)
            self.assertEqual(self.main("run", "--", "a", env={"XT_CPU_HEAD": "1"})[0], 4)
            self.assertEqual(self.main("run", "--", "a", env={"XT_CPU_HEAD": "0"})[0], 4)
        self.assertEqual(
            [(c.args[0], c.args[2]) for c in run.call_args_list],
            [(["a", "--", "b"], True), (["a"], True), (["a"], False)],
        )
        with mock.patch.object(sys, "argv", ["xt_cpu_share.py", "nope"]), redirect_stderr(io.StringIO()):
            self.assertEqual(cs.main(), 2)


def cli(*args: str, env: dict[str, str], timeout: float = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env, timeout=timeout
    )


WAIT_FOR = (
    "import json, os, sys, time\nfrom pathlib import Path\n"
    "tray = Path(sys.argv[1]); want = int(sys.argv[2]); go = Path(sys.argv[3])\n"
    "end = time.monotonic() + 60\n"
    "while len(list(tray.glob('job-*.json'))) < want and time.monotonic() < end:\n    time.sleep(0.05)\n"
    "seen = len(list(tray.glob('job-*.json')))\n"
    "if want == 2:\n    go.touch()\n"
    "while not go.exists() and time.monotonic() < end:\n    time.sleep(0.05)\n"
    "aff = sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else []\n"
    "print(json.dumps({'jobs': os.environ.get('XT_JOBS'), 'seen': seen, 'aff': aff}))\n"
)


class ConcurrencyTest(unittest.TestCase):
    """Tiến trình thật, khay thật trong thư mục tạm (flock, đăng ký, xoá khi xong)."""

    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.tray = self.tmp / "xt-cpu"
        self.waiter = self.tmp / "wait_for.py"
        self.waiter.write_text(WAIT_FOR, encoding="utf-8")
        # cổng tải luôn mở (máy chạy test đang tải cao) — khay đếm là thứ được kiểm ở đây
        self.env = clean_env(XDG_CACHE_HOME=str(self.tmp), XT_CPU_HIGH="9999")

    def popen(self, want: int, **extra: str) -> subprocess.Popen[str]:
        cmd = [sys.executable, str(SCRIPT), "run", "--", sys.executable, str(self.waiter), str(self.tray), str(want)]
        return subprocess.Popen(
            [*cmd, str(self.tmp / "go")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**self.env, **extra},
        )

    def test_two_jobs_register_concurrently_and_see_each_other(self):
        settings = {"XT_CPU_SLOTS": "4", "XT_CPU_RESERVE": "0"}
        sh = cs.shape(settings, cores=cs.quota())
        first = self.popen(1, **settings, XT_JOBS="1")
        if sh.usable == 1:
            (self.tmp / "go").touch()
        second = self.popen(min(2, sh.usable), **settings, XT_JOBS="1")
        outs = [p.communicate(timeout=120) for p in (first, second)]
        self.assertEqual([p.returncode for p in (first, second)], [0, 0], outs)
        a, b = (json.loads(out) for out, _ in outs)
        self.assertEqual((a["jobs"], b["jobs"]), ("1", "1"), outs)
        self.assertEqual(max(a["seen"], b["seen"]), min(2, sh.usable))
        if HAS_AFFINITY and sh.usable >= 2:
            self.assertFalse(set(a["aff"]) & set(b["aff"]))
        self.assertEqual(list(self.tray.glob("job-*.json")), [])


class DevTaskIntegrationTest(unittest.TestCase):
    """Chỗ nối dev-task.sh/xt.yaml (đỏ trước khi nối, xanh sau): gate/gate-fast chạy trong khay; `test_jobs()` lấy phần của
    khay khi XT_JOBS không đặt; `test_fast` của xt.yaml lấy -P từ `xt_cpu_share.py jobs`; XT_CPU_SHARE=off như cũ."""

    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        (self.tmp / "scripts").mkdir()
        shutil.copy(ROOT / "scripts" / "dev-task.sh", self.tmp / "scripts" / "dev-task.sh")
        shutil.copy(SCRIPT, self.tmp / "scripts" / "xt_cpu_share.py")
        (self.tmp / "rec.py").write_text(REC, encoding="utf-8")
        self.out = self.tmp / "out"
        self.out.mkdir()
        self.cache = self.tmp / "cache"
        self.env = clean_env(CLAUDE_PROJECT_DIR=str(self.tmp), OUT=str(self.out), XDG_CACHE_HOME=str(self.cache))
        self.env.pop("XT_CHANGED_FILES", None)
        self.sh = cs.shape({}, cores=cs.quota())

    def dt(self, *args: str, **extra: str) -> subprocess.CompletedProcess[str]:
        cmd = [shutil.which("bash") or "bash", str(self.tmp / "scripts" / "dev-task.sh"), *args]
        return subprocess.run(cmd, capture_output=True, text=True, cwd=self.tmp, env={**self.env, **extra}, timeout=300)

    def rec(self, name: str) -> dict[str, object]:
        data: dict[str, object] = json.loads((self.out / f"{name}.json").read_text(encoding="utf-8"))
        return data

    def yaml(self) -> None:
        (self.tmp / "xt.yaml").write_text(
            'format_check: ""\nlint: python3 rec.py lint\ntypecheck: ""\nbuild: ""\n'
            "test: python3 rec.py test\ntest_fast: python3 rec.py test\n",
            encoding="utf-8",
        )

    def test_gate_and_gate_fast_run_inside_the_tray(self):
        self.yaml()
        base_nice = os.nice(0)
        for task in ("gate", "gate-fast", "test"):
            with self.subTest(task=task):
                r = self.dt(task)
                self.assertEqual(r.returncode, 0, r.stderr)
                got = self.rec("test")
                self.assertTrue(got["id"], r.stderr)  # đỏ trước khi nối: không có dấu khay
                self.assertEqual(got["jobs"], str(cs.share(self.sh.usable, 1)), r.stderr)
                self.assertEqual(got["nice"], min(19, base_nice + cs.NICE))
                if HAS_AFFINITY and self.sh.reserve > 0:
                    self.assertEqual(got["aff"], cs.share(self.sh.usable, 1))
                self.assertIn("[xt-cpu] việc nặng:", r.stderr)
                self.assertEqual(list((self.cache / "xt-cpu").glob("job-*.json")), [])

    def test_off_nested_and_exit_codes_unchanged(self):
        self.yaml()
        r = self.dt("gate-fast", XT_CPU_SHARE="off")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.rec("test")["id"], self.rec("test")["jobs"]), (None, None))
        self.assertNotIn("[xt-cpu]", r.stderr)
        r = self.dt("gate-fast", CI="true")  # CI không đặt XT_CPU_SHARE: hành vi cũ, không vào khay
        self.assertEqual((r.returncode, self.rec("test")["id"], self.rec("test")["jobs"]), (0, None, None), r.stderr)
        self.assertNotIn("[xt-cpu]", r.stderr)
        r = self.dt("gate", CI="true", XT_CPU_SHARE="on")
        self.assertEqual((r.returncode, self.rec("test")["jobs"]), (0, str(cs.share(self.sh.usable, 1))), r.stderr)
        r = self.dt("gate", XT_CPU_SHARE_ID="outer", XT_JOBS="3")  # đã ở trong khay: không bọc lần hai
        self.assertEqual((r.returncode, self.rec("test")["id"], self.rec("test")["jobs"]), (0, "outer", "3"))
        for share in ("off", ""):
            with self.subTest(share=share):
                r = self.dt("gate-fast", XT_CPU_SHARE=share, REC_RC="3")
                self.assertEqual(r.returncode, 1, r.stderr)  # đỏ vẫn đỏ, cùng mã như không có khay
                self.assertIn("GATE-FAST ĐỎ ở 'lint'", r.stderr)
        r = self.dt("gate", XT_JOBS="5")
        self.assertEqual((r.returncode, self.rec("test")["jobs"]), (0, str(min(5, cs.share(self.sh.usable, 1)))))

    def test_gate_par_shares_budget_and_preserves_failure_code(self):
        (self.tmp / "xt.yaml").write_text(
            "lint: python3 rec.py lint\ntypecheck: python3 rec.py types\n"
            "build: python3 rec.py build\ntest: python3 rec.py test\n"
        )
        for budget in (1, 2, 3, 6):
            with self.subTest(budget=budget):
                r = self.dt("gate-par", XT_CPU_SHARE_ID="outer", XT_JOBS=str(budget))
                self.assertEqual(r.returncode, 0, r.stderr)
                expected = (budget, budget, budget) if budget < 3 else (1, 1, budget - 2)
                got = tuple(int(self.rec(task)["jobs"]) for task in ("lint", "types", "test"))
                self.assertEqual(got, expected)
        r = self.dt("gate-par", XT_CPU_SHARE_ID="outer", XT_JOBS="1", REC_RC="3")
        self.assertEqual(r.returncode, 3, r.stderr)
        self.assertIn("GATE-PAR ĐỎ", r.stderr)

    def test_test_shard_inherits_budget_and_runs_all_ids(self):
        expected = {f"unit-{i}" for i in range(100)}
        (self.tmp / "list_tests.py").write_text("for i in range(100): print(f'unit-{i}')\n", encoding="utf-8")
        (self.tmp / "xt.yaml").write_text('test_list: python3 list_tests.py\ntest_unit: python3 rec.py "$1"\n')
        r = self.dt("test-shard", "1", "1", XT_JOBS="1", XT_MIN_TESTS="100")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual({p.stem for p in self.out.glob("*.json")}, expected)
        for test_id in expected:
            self.assertEqual(self.rec(test_id)["jobs"], "1")

    def test_missing_module_or_python_runs_as_before(self):
        self.yaml()
        (self.tmp / "scripts" / "xt_cpu_share.py").unlink()
        r = self.dt("gate")
        self.assertEqual((r.returncode, self.rec("test")["id"]), (0, None), r.stderr)
        shutil.copy(SCRIPT, self.tmp / "scripts" / "xt_cpu_share.py")
        r = self.dt("gate", XT_FRAMEWORK_PYTHON="/khong/co/python")  # probe hỏng → không bọc; fw_ready xử lý như cũ
        self.assertNotIn("[xt-cpu]", r.stderr)

    def fake_pytest(self) -> None:
        self.bin = self.tmp / ".bin"
        self.bin.mkdir()
        (self.bin / "pytest").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        (self.bin / "pytest").chmod(0o755)
        py = self.tmp / ".py"
        for mod in ("xdist", "_pytest"):
            (py / mod).mkdir(parents=True)
            (py / mod / "__init__.py").write_text("", encoding="utf-8")
        (py / "pluggy.py").write_text("", encoding="utf-8")
        (py / "pytest.py").write_text("import sys\nprint('ARGS: ' + ' '.join(sys.argv[1:]))\n", encoding="utf-8")
        (self.tmp / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
        self.env.update(PATH=f"{self.bin}:{self.env.get('PATH', '')}", PYTHONPATH=str(py))

    def ran(self, r: subprocess.CompletedProcess[str]) -> str:
        m = re.search(r"^\[dev-task\] run \[test\]: (.*)$", r.stderr, re.M)
        self.assertIsNotNone(m, r.stderr)
        return m.group(1) if m else ""

    def test_test_jobs_honors_grant_and_preserves_off_mode(self):
        self.fake_pytest()
        want = cs.share(self.sh.usable, 1)
        for extra, jobs in (
            ({}, want),
            ({"XT_JOBS": "3"}, min(3, want)),
            ({"XT_JOBS": "abc"}, want),
            ({"XT_CPU_SHARE": "off"}, "auto"),
            ({"CI": "true"}, "auto"),  # CI: như trước khi có khay
            ({"CI": "true", "XT_CPU_SHARE": "on"}, want),
        ):
            with self.subTest(extra=extra):
                r = self.dt("test", **extra)
                self.assertEqual(r.returncode, 0, r.stderr)
                expected = "pytest -q" if jobs == 1 else f"python3 -P -m pytest -q -n {jobs}"
                self.assertEqual(self.ran(r), expected)
        (self.tmp / "scripts" / "xt_cpu_share.py").unlink()
        self.assertEqual(self.ran(self.dt("test")), "python3 -P -m pytest -q -n auto")  # vắng mô-đun → như cũ


class XtYamlTestFastTest(unittest.TestCase):
    """`test_fast` của xt.yaml: -P = XT_JOBS người đặt · phần của khay · ceil(nproc/2) khi XT_CPU_SHARE=off; qua guard."""

    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        line = next(
            x for x in (ROOT / "xt.yaml").read_text(encoding="utf-8").splitlines() if x.startswith("test_fast:")
        )
        self.cmd = line.split(":", 1)[1].strip()
        (self.tmp / "scripts").mkdir()
        shutil.copy(SCRIPT, self.tmp / "scripts" / "xt_cpu_share.py")
        (self.tmp / "scripts" / "xt.py").write_text("print('tests.test_a.A')\n", encoding="utf-8")
        self.bin = self.tmp / ".bin"
        self.bin.mkdir()
        (self.bin / "xargs").write_text('#!/bin/sh\ncat >/dev/null\necho "$@" > "$OUT"\n', encoding="utf-8")
        (self.bin / "xargs").chmod(0o755)
        self.env = clean_env(
            PATH=f"{self.bin}:{os.environ.get('PATH', '')}", OUT=str(self.tmp / "args"), XDG_CACHE_HOME=str(self.tmp)
        )

    def procs(self, **extra: str) -> int:
        r = subprocess.run(
            ["bash", "-o", "pipefail", "-c", self.cmd],
            capture_output=True,
            text=True,
            cwd=self.tmp,
            env={**self.env, **extra},
            timeout=120,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        m = re.search(r"-P (\d+)", (self.tmp / "args").read_text(encoding="utf-8"))
        self.assertIsNotNone(m)
        return int(m.group(1)) if m else 0

    def test_parallelism_follows_tray(self):
        nproc = int(subprocess.run(["nproc"], capture_output=True, text=True, check=True).stdout)
        sh = cs.shape({}, cores=cs.quota())
        self.assertEqual(self.procs(XT_JOBS="5"), min(5, cs.share(sh.usable, 1)))
        self.assertEqual(self.procs(), cs.share(sh.usable, 1))
        self.assertEqual(self.procs(XT_CPU_SHARE="off"), math.ceil(nproc / 2))
        self.assertEqual(self.procs(CI="true"), math.ceil(nproc / 2))  # CI: khay mặc định tắt → như cũ
        self.assertEqual(self.procs(CI="true", XT_CPU_SHARE="on"), cs.share(sh.usable, 1))

    def test_command_passes_guard(self):
        for policy in ("", "strict"):
            with self.subTest(policy=policy):
                env = clean_env(CLAUDE_PROJECT_DIR=str(ROOT), XT_GUARD_POLICY=policy)
                cmd = [sys.executable, str(ROOT / "scripts" / "xt.py"), "guard-check", "--", self.cmd]
                r = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=ROOT, timeout=120)
                self.assertEqual(r.returncode, 0, r.stderr)


class LiveCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.env = clean_env(XDG_CACHE_HOME=str(self.tmp))

    def test_run_propagates_exit_code_and_signal(self):
        r = cli("run", "--", sys.executable, "-c", "import sys; sys.exit(7)", env=self.env)
        self.assertEqual(r.returncode, 7, r.stderr)
        r = cli(
            "run", "--", sys.executable, "-c", "import os, signal; os.kill(os.getpid(), signal.SIGTERM)", env=self.env
        )
        self.assertEqual(r.returncode, -signal.SIGTERM, r.stderr)
        r = cli("run", "--", "khong-co-lenh-nay-xt", env=self.env)
        self.assertEqual(r.returncode, 127, r.stderr)

    def test_sigterm_to_run_is_forwarded_and_tray_cleaned(self):
        """SIGTERM gửi tới `run` tới được lệnh con (lệnh con bắt, ghi dấu, thoát 42); `run` trả 42; khay được dọn."""
        ready, mark = self.tmp / "ready", self.tmp / "mark"
        child = (
            "import signal, sys, time\nfrom pathlib import Path\n"
            f"def bye(*_):\n    Path({str(mark)!r}).write_text('term')\n    sys.exit(42)\n"
            f"signal.signal(signal.SIGTERM, bye)\nPath({str(ready)!r}).touch()\ntime.sleep(60)\n"
        )
        for extra in ({}, {"XT_CPU_SHARE": "off"}):
            with self.subTest(extra=extra):
                ready.unlink(missing_ok=True)
                mark.unlink(missing_ok=True)
                p = subprocess.Popen(
                    [sys.executable, str(SCRIPT), "run", "--", sys.executable, "-c", child],
                    env={**self.env, **extra},
                    stderr=subprocess.PIPE,
                    text=True,
                )
                LiveCliTest.poll_until(lambda: ready.exists() or p.poll() is not None)
                self.assertTrue(ready.exists())
                p.send_signal(signal.SIGTERM)
                _, err = p.communicate(timeout=120)
                self.assertEqual(p.returncode, 42, err)
                self.assertEqual(mark.read_text(), "term")
                self.assertEqual(list((self.tmp / "xt-cpu").glob("job-*.json")), [])

    def test_unwritable_cache_stops_managed_run(self):
        blocker = self.tmp / "file"
        blocker.write_text("", encoding="utf-8")
        env = {**self.env, "XDG_CACHE_HOME": str(blocker)}
        r = cli(
            "run",
            "--",
            sys.executable,
            "-c",
            "raise SystemExit(9)",
            env=env,
        )
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("khay CPU không dùng được", r.stderr)
        self.assertIn("XT_CPU_SHARE=off", r.stderr)
        self.assertEqual(cli("jobs", "--fallback", "auto", env=env).stdout, "1\n")

    def test_dead_pid_lock_expires(self):
        dead = subprocess.run([sys.executable, "-c", "import os; print(os.getpid())"], capture_output=True, text=True)
        tray = self.tmp / "xt-cpu"
        tray.mkdir()
        stale = tray / f"job-{int(dead.stdout)}.json"
        stale.write_text(json.dumps({"pid": int(dead.stdout), "cpus": [2, 3]}), encoding="utf-8")
        sh = cs.shape({}, cores=cs.quota())
        r = cli("jobs", env=self.env)
        self.assertEqual(r.stdout, f"{cs.share(sh.usable, 1)}\n", r.stderr)
        self.assertFalse(stale.exists())

    @staticmethod
    def poll_until(done: Callable[[], bool]) -> None:
        for _ in range(1200):  # chống treo (~60 s), không phải trần tốc độ: điều kiện được kiểm ngay sau
            if done():
                return
            time.sleep(0.05)

    def test_waiting_job_runs_after_slot_frees(self):
        env = {**self.env, "XT_CPU_SLOTS": "1", "XT_CPU_HIGH": "9999"}
        go = self.tmp / "go"
        hold = f"import time\nfrom pathlib import Path\nwhile not Path({str(go)!r}).exists(): time.sleep(0.05)\n"
        first = subprocess.Popen(
            [sys.executable, str(SCRIPT), "run", "--", sys.executable, "-c", hold],
            env=env,
            stderr=subprocess.PIPE,
            text=True,
        )
        tray = self.tmp / "xt-cpu"
        self.poll_until(lambda: (tray / f"job-{first.pid}.json").exists() or first.poll() is not None)
        self.assertTrue((tray / f"job-{first.pid}.json").exists(), "việc 1 phải giữ chỗ duy nhất của khay")
        second = subprocess.Popen(
            [sys.executable, str(SCRIPT), "run", "--", sys.executable, "-c", "pass"],
            env=env,
            stderr=subprocess.PIPE,
            text=True,
        )
        waiting = tray / f"wait-{second.pid}.json"
        self.poll_until(lambda: waiting.exists() or second.poll() is not None)
        self.assertTrue(waiting.exists(), "việc 2 phải chờ khay khi việc 1 giữ chỗ duy nhất")
        self.assertIsNone(second.poll())
        go.touch()
        _, err1 = first.communicate(timeout=120)
        _, err2 = second.communicate(timeout=120)
        self.assertEqual((first.returncode, second.returncode), (0, 0), err1 + err2)
        self.assertIn("chờ khay: khay đầy (1/1 việc)", err2)
        self.assertEqual(list(tray.glob("*.json")), [])


if __name__ == "__main__":
    unittest.main()
