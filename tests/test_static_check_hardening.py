"""Rà #776: đọc tệp không tin cậy an toàn (liên kết, FIFO, thiết bị), `--opt` sai thành lỗi dùng sai, lọc tệp khi quét thư mục
(`SNIFF`) và các regex không bậc hai trên dòng dài (ReDoS)."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import xt_checks
from cpu_budget import assert_not_quadratic
from xt_checks import kind_motion, kind_pii_vn, kind_tokens


class TmpTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def put(self, name: str, text: str) -> Path:
        path = self.base / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path


class SafeReadTest(TmpTest):
    def test_symlink_is_not_followed_even_when_named_directly(self):
        real = self.put("real.md", "xin chào")
        link = self.base / "link.md"
        link.symlink_to(real)
        self.assertIsNone(xt_checks.read_text(link))

    def test_device_link_and_fifo_do_not_hang_or_eat_memory(self):
        dev = self.base / "CREDITS.md"
        dev.symlink_to("/dev/zero")
        self.assertIsNone(xt_checks.read_text(dev))
        fifo = self.base / "a.md"
        os.mkfifo(fifo)
        self.assertIsNone(xt_checks.read_text(fifo))  # không treo: mở O_NONBLOCK rồi fstat

    def test_directory_and_oversize_and_grown_file_are_none(self):
        folder = self.base / "d.md"
        folder.mkdir()
        self.assertIsNone(xt_checks.read_text(folder))
        small = self.put("s.md", "abcd")
        with unittest.mock.patch.object(xt_checks, "MAX_BYTES", 2):
            self.assertIsNone(xt_checks.read_text(small))

    def test_file_that_grew_after_fstat_is_refused(self):
        grown = self.put("g.md", "ab")
        real_fstat = os.fstat

        def fake(fd: int) -> os.stat_result:
            return real_fstat(fd)  # kích thước lúc fstat = 2

        with unittest.mock.patch.object(xt_checks, "MAX_BYTES", 2), unittest.mock.patch.object(os, "fstat", fake):
            grown.write_text("abc", encoding="utf-8")  # lớn thêm sau khi trần đặt ở 2: đọc MAX+1 byte thấy ngay
            self.assertIsNone(xt_checks.read_text(grown))

    def test_walk_skips_fifo_and_links_without_opening_them(self):
        good = self.put("tree/a.md", "x")
        os.mkfifo(self.base / "tree" / "b.md")
        (self.base / "tree" / "c.md").symlink_to(good)
        self.assertEqual(xt_checks.collect([str(self.base / "tree")], (".md",)), [good])


class OptsAndSniffTest(TmpTest):
    def test_unknown_option_is_a_usage_error_for_every_kind(self):
        for kind in xt_checks.KINDS:
            with self.subTest(kind=kind), self.assertRaisesRegex(xt_checks.CheckError, "--opt lạ"):
                xt_checks.run(kind, [str(self.base)], {"ignroe": "ABC123"})

    def test_every_kind_declares_opts_as_a_tuple_of_names(self):
        for kind in xt_checks.KINDS:
            module = xt_checks.load(kind)
            with self.subTest(kind=kind):
                self.assertIsInstance(module.OPTS, tuple)
                self.assertTrue(all(isinstance(k, str) for k in module.OPTS))

    def test_ignore_must_be_a_code(self):
        self.put("a.md", "x\n")
        with self.assertRaisesRegex(xt_checks.CheckError, "ABC123"):
            xt_checks.run("nfc", [str(self.base)], {"ignore": "nfc1"})
        self.assertEqual(xt_checks.run("nfc", [str(self.base)], {"ignore": "NFC001,"}), [])

    def test_directory_scan_keeps_only_files_that_look_like_the_format(self):
        self.put("bom.json", '{"bomFormat": "CycloneDX", "components": []}')
        self.put("other.json", '{"unrelated": true}')
        scanned = xt_checks.collect([str(self.base)], (".json",), lambda text: '"bomFormat"' in text)
        self.assertEqual([p.name for p in scanned], ["bom.json"])
        named = xt_checks.collect([str(self.base / "other.json")], (".json",), lambda text: False)
        self.assertEqual([p.name for p in named], ["other.json"])  # tệp nêu đích danh luôn được kiểm

    def test_sbom_vex_trace_do_not_flag_unrelated_json_in_a_directory(self):
        self.put("settings.json", '{"hooks": {}}')
        for kind in ("sbom", "vex", "trace"):
            with self.subTest(kind=kind):
                self.assertEqual(xt_checks.run(kind, [str(self.base)], {}), [])


class LinearTimeTest(TmpTest):
    """Dòng dài base64/hex/dấu gạch (mysqldump --hex-blob, fixture, log) không được làm thời gian bậc hai theo độ dài."""

    N = 8000

    def run_check(self, module, suffix: str, text: str, opts: dict[str, str] | None = None) -> None:
        path = self.put("x" + suffix, text)
        module.check([path], opts or {})

    def test_pii_vn_long_runs(self):
        for name, build in (
            ("base64", lambda n: "A" * n),
            ("email-like", lambda n: "a." * (n // 2)),
            ("key-like", lambda n: "k-" * (n // 2)),
            ("digits", lambda n: "1" * n),
        ):
            with self.subTest(shape=name):
                assert_not_quadratic(self, lambda n, b=build: self.run_check(kind_pii_vn, ".log", b(n)), self.N)

    def test_tokens_long_runs(self):
        design = self.put("t.css", ":root { --a: 1; }\n")
        opts = {"tokens": str(design)}
        for name, build in (
            ("dashes", lambda n: "-" * n),
            ("var-spaces", lambda n: "var(" + " " * n),
            ("names", lambda n: "--a" * (n // 3)),
        ):
            with self.subTest(shape=name):
                assert_not_quadratic(self, lambda n, b=build: self.run_check(kind_tokens, ".css", b(n), opts), self.N)

    def test_motion_long_runs(self):
        shapes = {
            "duration-digits": lambda n: "a { animation-duration: " + "1" * n + "; }",
            "repeat-transition": lambda n: "transition:" * (n // 11),
            "unclosed-comments": lambda n: "/*" * (n // 2),
            "repeat-media": lambda n: "@media " * (n // 7),
            "repeat-animation": lambda n: "animation:1s infinite;" * (n // 22),
            "animation-glued": lambda n: "animation" * (n // 9),
            "time-digits": lambda n: "a { animation: " + "1" * n + "s; }",
        }
        for name, build in shapes.items():
            with self.subTest(shape=name):
                assert_not_quadratic(self, lambda n, b=build: self.run_check(kind_motion, ".css", b(n)), self.N)

    def test_unterminated_comment_runs_to_the_end_of_the_file(self):
        self.assertEqual(kind_motion._blank_comments("a/*b\nc"), "a   \n ")  # như CSS; số dòng giữ nguyên
        self.assertEqual(kind_motion._blank_comments("a/*b*/c/*d*/e"), "a     c     e")
        self.assertEqual(kind_motion._blank_comments("không có"), "không có")


if __name__ == "__main__":
    unittest.main()
