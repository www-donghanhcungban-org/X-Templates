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

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
gp = importlib.import_module("xt_guard_profile")  # đường dẫn scripts phải có trước khi nhập

SAMPLE = """\
LIMIT = 3
MAX_X: int = 5
lower = 1
left, RIGHT = 1, 2
import os


def git_push():
    return gh_call() + LIMIT


def gh_call():
    total = git_log()
    return total + MAX_X + LIMIT


async def gh_async():
    return 1


def git_log():
    return LIMIT


def _helper_a():
    return 1


class GitThing:
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
        ticks = iter([0.0, 1.0, 1.0, 3.0, 3.0, 6.0])
        result = self.profile(repeat=3, clock=lambda: next(ticks))
        self.assertEqual(result["compile_ms"], {"runs": 3, "median": 2000.0, "min": 1000.0, "max": 3000.0})

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
        self.assertEqual(edges, {("git", "gh"): 1, ("gh", "git"): 1})  # git_push→gh_call, gh_call→git_log

    def test_shared_constants_need_two_families(self):
        shared = {c["name"]: c["families"] for c in self.profile()["shared_constants"]}
        self.assertEqual(shared, {"LIMIT": ["gh", "git"]})  # MAX_X chỉ họ gh; `lower`, `RIGHT` không phải hằng khai báo

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
