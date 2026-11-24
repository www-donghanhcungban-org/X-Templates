"""Rà #776: đọc tệp không tin cậy an toàn (liên kết, FIFO, thiết bị), `--opt` sai thành lỗi dùng sai, lọc tệp khi quét thư mục
(`SNIFF`) và các regex không bậc hai trên dòng dài (ReDoS)."""

from __future__ import annotations

import io
import os
import sys
import tempfile
import types
import unittest
import unittest.mock
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import xt
import xt_checks
from cpu_budget import assert_not_quadratic
from xt_checks import kind_credits, kind_motion, kind_pii_vn, kind_tokens


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


class SecondRoundTest(TmpTest):
    """Rà #776 lượt hai: `motion` bậc hai ở tên thuộc tính lặp và số dòng/`animation-play-state` quét lại cho mỗi lần khớp,
    sniff bỏ im lặng tệp đúng định dạng, lỗi đọc sau khi mở, đua `lstat`, email dính liền, CSV ô khổng lồ, tên quá dài."""

    def run_css(self, text: str) -> None:
        kind_motion.check([self.put("x.css", text)], {})

    def test_motion_repeated_property_names_are_linear(self):
        # N lớn hơn các ca khác: bản lỗi chỉ đỏ từ cỡ này (8000 vẫn xanh nếu bậc hai)
        for name, build in (
            ("animation-", lambda n: "animation-" * (n // 10)),
            ("-animation", lambda n: "-animation" * (n // 10)),
            ("transition-", lambda n: "transition-" * (n // 11)),
        ):
            with self.subTest(shape=name):
                assert_not_quadratic(self, lambda n, b=build: self.run_css(b(n)), 40000)

    def test_motion_many_findings_do_not_rescan_the_whole_file(self):
        for name, build in (
            ("infinite", lambda n: "a{animation:1s infinite}" * (n // 24)),
            ("all", lambda n: "a{transition:all}" * (n // 17)),
        ):
            with self.subTest(shape=name):
                # N lớn: đếm dòng bằng count('\n') cho mỗi phát hiện chỉ lộ ra từ cỡ này (rà #776 lượt hai: N=100000 để lọt)
                assert_not_quadratic(self, lambda n, b=build: self.run_css(b(n)), 400000)

    def test_motion_still_sees_vendor_prefixed_and_numbers_lines(self):
        path = self.put("v.css", "a{}\nb{ -webkit-animation: spin 1s linear }\n")
        self.assertEqual([(f.line, f.code) for f in kind_motion.check([path], {})], [(2, "MOT002")])
        late = self.put("l.css", "\n" * 5 + "a{transition:all 1s}" + "\n" + "@media (prefers-reduced-motion: reduce){}")
        self.assertEqual([(f.line, f.code) for f in kind_motion.check([late], {})], [(6, "MOT001")])

    def test_sniff_keeps_formats_that_check_cannot_read(self):
        big = '{"bomFormat": "CycloneDX", "x": "' + "a" * 300 + '"}'
        self.put("big.json", big)
        (self.base / "utf16.json").write_bytes('{"bomFormat": "CycloneDX"}'.encode("utf-16"))
        self.put("other.json", '{"unrelated": true}')
        with unittest.mock.patch.object(xt_checks, "MAX_BYTES", 100):
            found = xt_checks.run("sbom", [str(self.base)], {})
        self.assertEqual(
            sorted((Path(f.path).name, f.code) for f in found), [("big.json", "SBM000"), ("utf16.json", "SBM000")]
        )
        self.assertIsNone(xt_checks.read_head(self.base / "absent"))

    def test_sniff_keeps_files_it_cannot_open_so_check_reports_them(self):
        self.put("locked.json", '{"bomFormat": "CycloneDX"}')
        with unittest.mock.patch.object(os, "open", side_effect=PermissionError("EACCES")):
            self.assertEqual(
                xt_checks.collect([str(self.base)], (".json",), lambda text: False), [self.base / "locked.json"]
            )

    def test_sniff_sees_a_marker_after_the_first_64_kib(self):
        late = "\n".join(['{"resourceLogs": []}'] * 4000 + ['{"resourceSpans": []}']) + "\n"
        self.assertGreater(late.index("resourceSpans"), 65536)
        self.put("otel.jsonl", late)
        self.put("other.jsonl", '{"resourceLogs": []}\n' * 10)
        kept = xt_checks.collect([str(self.base)], (".jsonl",), lambda text: '"resourceSpans"' in text)
        self.assertEqual([p.name for p in kept], ["otel.jsonl"])

    def test_pii_csv_with_only_carriage_returns_is_still_checked(self):
        path = self.put("mac.csv", "hoten,ghichu\rNguyen Van A,x\rTran Thi B,y\r")
        found = kind_pii_vn.check([path], {})
        self.assertEqual([(f.line, f.code) for f in found], [(2, "PII004"), (3, "PII004")])

    def test_read_errors_after_open_are_not_a_crash_and_leak_nothing(self):
        path = self.put("r.md", "xin chào")
        before = len(os.listdir("/proc/self/fd")) if os.path.isdir("/proc/self/fd") else None
        with unittest.mock.patch.object(os, "fdopen", side_effect=OSError("EIO")):
            self.assertIsNone(xt_checks.read_text(path))
        if before is not None:
            self.assertEqual(len(os.listdir("/proc/self/fd")), before)

    def test_file_that_grew_after_fstat_is_refused(self):
        grown = self.put("g.md", "abc")
        real = os.stat(grown)  # không mở fd (bản trước rò một fd)
        fake = types.SimpleNamespace(st_mode=real.st_mode, st_size=2)  # fstat nói 2 byte, trên đĩa đã 3
        with (
            unittest.mock.patch.object(xt_checks, "MAX_BYTES", 2),
            unittest.mock.patch.object(os, "fstat", return_value=fake),
        ):
            self.assertIsNone(xt_checks.read_text(grown))

    def test_walk_survives_a_file_vanishing_between_listing_and_lstat(self):
        keep = self.put("tree/a.md", "x")
        self.put("tree/b.md", "x")
        real = os.lstat

        def flaky(path, *args, **kwargs):
            if str(path).endswith("b.md"):
                raise FileNotFoundError(path)
            return real(path, *args, **kwargs)

        with unittest.mock.patch.object(os, "lstat", flaky):
            self.assertEqual(xt_checks.collect([str(self.base / "tree")], (".md",)), [keep])

    def test_pii_email_glued_after_another_token_and_line_numbers(self):
        path = self.put("e.log", "dev@example.com_an@gmail.com\n")
        self.assertEqual([f.code for f in kind_pii_vn.check([path], {})], ["PII003"])
        path = self.put("n.log", "a" + chr(12) + "b\nemail: an@gmail.com\n")
        self.assertEqual([(f.line, f.code) for f in kind_pii_vn.check([path], {})], [(2, "PII003"), (2, "PII004")])

    def test_pii_csv_with_a_huge_cell_does_not_crash(self):
        path = self.put("big.csv", "cccd,ghi_chu\n" + "x" * 200000 + ",y\n")
        self.assertIsInstance(kind_pii_vn.check([path], {}), list)

    def test_credits_row_with_an_overlong_name_does_not_crash(self):
        logo = self.put("assets/logo.png", "png")
        credits = self.put(
            "assets/CREDITS.md", "| tệp | nguồn | license |\n|---|---|---|\n| " + "a" * 300 + ".png | me | MIT |\n"
        )
        found = kind_credits.check([logo], {"credits": str(credits)})
        self.assertIn("CRD004", [f.code for f in found])

    def test_script_dir_is_added_to_sys_path_when_missing(self):
        self.put("a.md", "xin chào\n")
        without = [p for p in sys.path if p != str(xt.SCRIPT_DIR)]
        out = io.StringIO()
        with unittest.mock.patch.object(sys, "path", without), redirect_stdout(out):
            self.assertEqual(xt.main(["static-check", "nfc", str(self.base)]), 0)


if __name__ == "__main__":
    unittest.main()
