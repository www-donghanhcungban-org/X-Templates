"""T-3984: `scripts/xt_guard_profile.py` — đo chỉ đọc chi phí compile, họ hàm, cạnh gọi và hằng dùng chung của guard."""

import contextlib
import importlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
gp = importlib.import_module("xt_guard_profile")  # đường dẫn scripts phải có trước khi nhập

SAMPLE = """\
LIMIT = 3
MAX_X: int = 5
ONLY_GH = 7
lower = 1
left, RIGHT = 1, 2
import os


def git_push():
    return gh_call() + git_log() + LIMIT + MAX_X


def gh_call():
    total = git_log()
    return total + MAX_X + LIMIT


async def gh_async():
    return lower + ONLY_GH


def git_log():
    return LIMIT + lower


def _helper_a():
    git_log = 1
    return 1


class GitThing:
    pass
"""


CLOSURE_SAMPLE = """\
LIMIT = 3
OTHER = 4


def git_a():
    return util_x() + LIMIT


def git_b():
    return git_a()


def util_x():
    return util_y()


def util_y():
    return 1


def tool_c():
    return util_x() + git_b()


def lonely():
    return OTHER


class Box:
    pass
"""


def write(directory: str, name: str, text: str) -> Path:
    path = Path(directory) / name
    path.write_text(text, encoding="utf-8")
    return path


class FamilyNameTest(unittest.TestCase):
    def test_family_takes_prefix_without_leading_underscores(self):
        self.assertEqual(gp.family("git_push"), "git")
        self.assertEqual(gp.family("_gh_call"), "gh")
        self.assertEqual(gp.family("__init__"), "init")
        self.assertEqual(gp.family("main"), "main")
        self.assertEqual(gp.family("_"), "_")


class ProfileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.path = write(self.tmp, "sample.py", SAMPLE)

    def profile(self, repeat=3, clock=None):
        return gp.profile(self.path, repeat, clock or gp.time.perf_counter)

    def test_compile_runs_use_the_clock_twice_per_run(self):
        # ba lần đo 1 s, 5 s, 2 s: không đối xứng và chưa sắp, nên trung bình (2,67 s) hay phần tử giữa (5 s) đều sai
        ticks = iter([0.0, 1.0, 1.0, 6.0, 6.0, 8.0])
        result = self.profile(repeat=3, clock=lambda: next(ticks))
        self.assertEqual(result["compile_ms"], {"runs": 3, "median": 2000.0, "min": 1000.0, "max": 5000.0})

    def test_size_and_definition_counts(self):
        result = self.profile()
        self.assertEqual(result["lines"], SAMPLE.count("\n"))
        self.assertEqual(result["bytes"], len(SAMPLE.encode("utf-8")))
        self.assertEqual(result["defs"], 6)  # git_push, gh_call, gh_async, git_log, _helper_a, GitThing

    def test_families_are_sorted_by_lines_then_name(self):
        families = {f["family"]: f for f in self.profile()["families"]}
        self.assertEqual(families["git"]["defs"], 2)
        self.assertEqual(families["gh"]["defs"], 2)  # `async def` cũng là định nghĩa
        self.assertEqual(families["gh"]["lines"], 3 + 2)  # gh_call 3 dòng, gh_async 2 dòng
        self.assertEqual(families["GitThing"]["defs"], 1)
        ordered = [(-f["lines"], f["family"]) for f in self.profile()["families"]]
        self.assertEqual(ordered, sorted(ordered))
        self.assertAlmostEqual(sum(f["share_pct"] for f in self.profile()["families"]), 100.0, places=0)

    def test_edges_only_count_calls_across_families(self):
        edges = {(e["from"], e["to"]): e["edges"] for e in self.profile()["edges"]}
        # git_push→gh_call, gh_call→git_log. Không có: git_push→git_log (cùng họ), `_helper_a` chỉ GÁN `git_log` (Store).
        self.assertEqual(edges, {("git", "gh"): 1, ("gh", "git"): 1})

    def test_shared_constants_need_two_families(self):
        shared = {c["name"]: c["families"] for c in self.profile()["shared_constants"]}
        # MAX_X khai kiểu (`NAME: int = …`) và LIMIT đều được hai họ dùng; `lower` cũng hai họ dùng nhưng không IN HOA,
        # `RIGHT` là gán bộ.
        self.assertEqual(shared, {"LIMIT": ["gh", "git"], "MAX_X": ["gh", "git"]})

    def test_top_limits_every_table(self):
        result = gp.profile(self.path, 1, gp.time.perf_counter, top=1)
        self.assertEqual(
            [len(result[k]) for k in ("families", "edges", "shared_constants")],
            [1, 1, 1],
        )

    def test_render_mentions_every_section(self):
        text = gp.render(self.profile(), self.path)
        for needle in ("sample.py", "compile", "Họ hàm", "Cạnh gọi", "Hằng dùng chung", "git -> gh", "LIMIT"):
            self.assertIn(needle, text)

    def test_render_without_edges_or_shared_constants(self):
        write(self.tmp, "flat.py", "def one():\n    return 1\n")
        text = gp.render(gp.profile(Path(self.tmp) / "flat.py", 1, gp.time.perf_counter), Path("flat.py"))
        self.assertIn("(không có)", text)


class ClosureTest(unittest.TestCase):
    """T-3995: bao đóng phụ thuộc ở mức hàm của một tập hạt giống — dữ liệu để chọn ranh giới tách."""

    def setUp(self):
        self.tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.path = write(self.tmp, "closure.py", CLOSURE_SAMPLE)

    def report(self, *specs, top=10):
        return gp.closure_report(self.path, list(specs), top)

    def test_family_seed_pulls_in_helpers_and_constants(self):
        r = self.report("family:git")
        self.assertEqual((r["seeds"], r["seed_lines"]), (2, 4))  # git_a, git_b: 2 dòng mỗi hàm
        self.assertEqual((r["closure_defs"], r["closure_lines"]), (4, 8))  # thêm util_x, util_y
        self.assertEqual(r["constants"], ["LIMIT"])  # OTHER không nằm trong bao đóng
        self.assertEqual([b["name"] for b in r["baggage"]], ["util_x", "util_y"])
        self.assertEqual(r["baggage_total"], 2)
        self.assertEqual(
            r["total_def_lines"], 7 * 2
        )  # git_a, git_b, util_x, util_y, tool_c, lonely, Box: 2 dòng mỗi cái

    def test_entry_points_are_callers_outside_the_closure(self):
        r = self.report("family:git")
        self.assertEqual(r["entry_points"], [{"name": "tool_c", "into": ["git_b", "util_x"]}])
        self.assertEqual(r["entry_total"], 1)

    def test_exact_name_seed_and_entry_points_sorted(self):
        r = self.report("util_x")
        self.assertEqual((r["seeds"], r["closure_defs"], r["constants"]), (1, 2, []))
        self.assertEqual([e["name"] for e in r["entry_points"]], ["git_a", "tool_c"])

    def test_cycle_and_repeated_seed_do_not_loop_forever(self):
        write(self.tmp, "cycle.py", "def a_x():\n    return a_y()\n\n\ndef a_y():\n    return a_x()\n")
        r = gp.closure_report(Path(self.tmp) / "cycle.py", ["a_x", "family:a"], 10)
        self.assertEqual((r["seeds"], r["closure_defs"], r["entry_total"]), (2, 2, 0))

    def test_top_limits_tables_but_not_totals(self):
        r = self.report("family:git", top=1)
        self.assertEqual([b["name"] for b in r["baggage"]], ["util_x"])  # dòng bằng nhau → theo tên
        self.assertEqual(r["baggage_total"], 2)

    def test_unknown_seed_is_an_error(self):
        for spec in ("nope", "family:nope", "LIMIT"):  # hằng không phải định nghĩa nên không làm hạt giống
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                self.report(spec)

    def test_render_closure_mentions_every_section(self):
        text = gp.render_closure(self.report("family:git"), self.path)
        for needle in ("closure.py", "hạt giống", "LIMIT", "util_x", "tool_c", "git_b"):
            self.assertIn(needle, text)

    def test_render_closure_without_baggage_or_entries(self):
        write(self.tmp, "solo.py", "def solo_a():\n    return 1\n")
        r = gp.closure_report(Path(self.tmp) / "solo.py", ["solo_a"], 10)
        self.assertEqual(gp.render_closure(r, Path("solo.py")).count("(không có)"), 3)

    def test_main_closure_text_json_and_errors(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(gp.main(["--path", str(self.path), "--closure", "family:git"]), 0)
            self.assertEqual(gp.main(["--path", str(self.path), "--closure", "util_x", "--json"]), 0)
            self.assertEqual(gp.main(["--path", str(self.path), "--closure", "nope"]), 2)
        self.assertIn("hạt giống", out.getvalue())
        self.assertIn('"closure_defs"', out.getvalue())
        self.assertIn("không đọc được", err.getvalue())


class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.path = write(self.tmp, "sample.py", SAMPLE)

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = gp.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_text_and_json_output(self):
        code, out, _ = self.run_main("--path", str(self.path), "--repeat", "1")
        self.assertEqual(code, 0)
        self.assertIn("Họ hàm", out)
        code, out, _ = self.run_main("--path", str(self.path), "--repeat", "1", "--json", "--top", "2")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["defs"], 6)
        self.assertLessEqual(len(data["families"]), 2)

    def test_valid_python_with_bom_or_coding_cookie_is_measured(self):
        """Đọc byte như bộ nạp hook: BOM UTF-8 và coding cookie latin-1 là Python hợp lệ."""
        Path(self.tmp, "bom.py").write_bytes(b"\xef\xbb\xbfdef a_x():\n    return 1\n")
        Path(self.tmp, "cookie.py").write_bytes(b"# -*- coding: latin-1 -*-\ndef a_x():\n    return '\xe9'\n")
        for name in ("bom.py", "cookie.py"):
            with self.subTest(name=name):
                code, out, err = self.run_main("--path", str(Path(self.tmp) / name), "--repeat", "1", "--json")
                self.assertEqual((code, err), (0, ""))
                self.assertEqual(json.loads(out)["defs"], 1)

    def test_parser_overflow_is_exit_two_not_a_traceback(self):
        for error in (RecursionError, MemoryError):
            with self.subTest(error=error.__name__), mock.patch.object(gp.ast, "parse", side_effect=error("sâu quá")):
                code, out, err = self.run_main("--path", str(self.path), "--repeat", "1")
                self.assertEqual((code, out), (2, ""))
                self.assertIn("không đọc được", err)

    def test_unreadable_inputs_exit_two_with_a_message(self):
        write(self.tmp, "bad.py", "def (:\n")
        Path(self.tmp, "latin.py").write_bytes(b"x = '\xff'\n")
        for target in (
            Path(self.tmp) / "none.py",
            Path(self.tmp),
            Path(self.tmp) / "bad.py",
            Path(self.tmp) / "latin.py",
        ):
            with self.subTest(target=target.name):
                code, out, err = self.run_main("--path", str(target))
                self.assertEqual((code, out), (2, ""))
                self.assertIn("không đọc được", err)

    def test_repeat_and_top_must_be_positive(self):
        for flag in ("--repeat", "--top"):
            for value in ("0", "x"):
                with self.subTest(flag=flag, value=value), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as caught:
                        gp.main(["--path", str(self.path), flag, value])
                    self.assertEqual(caught.exception.code, 2)

    def test_script_entry_point(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "xt_guard_profile.py"), "--path", str(self.path), "--repeat", "1"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Họ hàm", r.stdout)


class RealGuardTest(unittest.TestCase):
    def test_profile_of_the_repository_guard(self):
        """Đọc `.claude/hooks/guard.py` thật bằng API (không qua Bash); không kiểm thời gian, chỉ cấu trúc."""
        result = gp.profile(ROOT / ".claude" / "hooks" / "guard.py", 1, gp.time.perf_counter)
        self.assertGreater(result["defs"], 1000)
        self.assertGreater(result["lines"], 20000)
        lines = [f["lines"] for f in result["families"]]
        self.assertEqual(lines, sorted(lines, reverse=True))
        self.assertGreater(result["compile_ms"]["median"], 0)


if __name__ == "__main__":
    unittest.main()
