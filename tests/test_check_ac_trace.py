"""Loại `ac-trace` của `static-check` (ADR-0099, WF-SDD-003): fixture tốt/xấu trong thư mục tạm."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from xt_checks import kind_ac_trace


class AcTraceOptsTest(unittest.TestCase):
    def test_opts(self) -> None:
        self.assertEqual(kind_ac_trace.OPTS, ("tests", "test_suffixes"))


class AcTraceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def put(self, name: str, text: str | bytes) -> Path:
        path = self.base / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, bytes):
            path.write_bytes(text)
        else:
            path.write_text(text, encoding="utf-8")
        return path

    def run_check(self, specs: list[Path], **extra: str) -> list[tuple[str, int, str]]:
        opts = {"tests": str(self.base / "tests"), **extra}
        found = kind_ac_trace.check(specs, opts)
        return [(Path(f.path).name, f.line, f.code) for f in found]

    def test_good(self) -> None:
        spec = self.put("s.md", "# Tiêu chí\n- AC-1 Given… Then…\n| **AC-2** | rỗng |\nGhi chú nhắc AC-9 ở giữa dòng\n")
        self.put("tests/test_a.py", 'def test_ac_1():\n    """AC-1"""\n# AC-2\n')
        self.assertEqual(self.run_check([spec]), [])

    def test_missing_test_and_unknown_mention(self) -> None:
        spec = self.put("s.md", "* AC-1 có\n  AC-2 thiếu\nxAC-3 và AC-3x không phải định nghĩa\n")
        self.put("tests/a.go", "// AC-1 AC-1 AC-7\nxAC-5 AC-5x AC-5-6\n")
        self.assertEqual(self.run_check([spec]), [("a.go", 1, "ACT002"), ("s.md", 2, "ACT001")])

    def test_only_lf_starts_a_new_line(self) -> None:
        for char in ("\u2028", "\f"):
            with self.subTest(char=char):
                spec = self.put("s.md", f"note{char}AC-7\nAC-1\n")
                self.put("tests/t.py", f"# note{char}AC-9\n")
                self.assertEqual(self.run_check([spec]), [("t.py", 1, "ACT002"), ("s.md", 2, "ACT001")])

    def test_duplicate_definition(self) -> None:
        one = self.put("a.md", "AC-1 một\n")
        two = self.put("b.md", "intro\n- AC-1 hai\n")
        self.put("tests/t.rb", "# AC-1\n")
        found = kind_ac_trace.check([one, two], {"tests": str(self.base / "tests")})
        self.assertEqual([(Path(f.path).name, f.line, f.code) for f in found], [("b.md", 2, "ACT003")])
        self.assertIn("a.md:1", found[0].message)

    def test_missing_tests_dir_and_file_instead_of_dir(self) -> None:
        spec = self.put("s.md", "AC-1\n")
        self.assertEqual(self.run_check([spec]), [("tests", 0, "ACT000")])
        self.put("tests", "không phải thư mục")
        self.assertEqual(self.run_check([spec]), [("tests", 0, "ACT000")])

    def test_symlink_tests_dir(self) -> None:
        real = self.base / "real"
        real.mkdir()
        (self.base / "tests").symlink_to(real, target_is_directory=True)
        self.assertEqual(self.run_check([self.put("s.md", "AC-1\n")]), [("tests", 0, "ACT000")])

    def test_suffix_option_and_non_utf8(self) -> None:
        spec = self.put("s.md", "AC-1\n")
        self.put("tests/a.txt", "AC-1\n")
        self.put("tests/b.py", b"\xff\xfe AC-1\n")
        self.assertEqual(self.run_check([spec]), [("s.md", 1, "ACT001")])
        self.assertEqual(self.run_check([spec], test_suffixes=" .TXT, ,"), [])

    def test_unreadable_spec_ignored_and_empty(self) -> None:
        self.put("tests/a.py", "")
        bad = self.put("bad.md", b"\xff\xfe AC-1")
        self.assertEqual(self.run_check([bad]), [])
        self.assertEqual(self.run_check([]), [])


if __name__ == "__main__":
    unittest.main()
