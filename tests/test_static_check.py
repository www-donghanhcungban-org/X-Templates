"""ADR-0099: lệnh `static-check`, bộ duyệt tệp dùng chung của gói `xt_checks` và loại `nfc` (fixture tốt/xấu)."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import types
import unicodedata
import unittest
import unittest.mock
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import xt
import xt_checks
from xt_checks import kind_nfc

NFC = unicodedata.normalize("NFC", "Tiếng Việt có dấu")
NFD = unicodedata.normalize("NFD", NFC)
REPL, BOM, ZWSP = chr(0xFFFD), chr(0xFEFF), chr(0x200B)  # bằng mã: nguồn không chứa ký tự ẩn thật


def run_cli(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = xt.main(["static-check", *argv])
    return rc, out.getvalue(), err.getvalue()


class TmpTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def put(self, name: str, text: str | bytes) -> Path:
        path = self.base / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, bytes):
            path.write_bytes(text)
        else:
            path.write_text(text, encoding="utf-8")
        return path


class RegistryTest(TmpTest):
    def test_every_kind_has_the_interface(self):
        for kind in xt_checks.KINDS:
            with self.subTest(kind=kind):
                module = xt_checks.load(kind)
                self.assertTrue(module.HELP and isinstance(module.SUFFIXES, tuple) and callable(module.check))

    def test_unknown_kind_is_a_usage_error(self):
        with self.assertRaisesRegex(xt_checks.CheckError, "loại lạ"):
            xt_checks.load("khong-co")

    def test_parse_opts(self):
        self.assertEqual(xt_checks.parse_opts(["a=1", "b="]), {"a": "1", "b": ""})
        for bad in (["a"], ["=1"], ["a=1", "a=2"]):
            with self.subTest(bad=bad), self.assertRaises(xt_checks.CheckError):
                xt_checks.parse_opts(bad)

    def test_read_text_limits(self):
        self.assertEqual(xt_checks.read_text(self.put("a.md", "xin chào")), "xin chào")
        self.assertIsNone(xt_checks.read_text(self.put("b.md", b"\xff\xfe")))
        self.assertIsNone(xt_checks.read_text(self.base / "absent.md"))
        big = self.put("c.md", "x")
        with unittest.mock.patch.object(xt_checks, "MAX_BYTES", 0):
            self.assertIsNone(xt_checks.read_text(big))

    def test_collect_filters_dirs_but_not_named_files(self):
        keep = self.put("docs/a.md", "x")
        self.put("docs/b.bin", "x")
        self.put("node_modules/p/c.md", "x")
        self.put(".git/d.md", "x")
        named = self.put("e.bin", "x")
        self.assertEqual(xt_checks.collect([str(self.base / "docs")], (".md",)), [keep])
        self.assertEqual(xt_checks.collect([str(named)], (".md",)), [named])
        self.assertEqual(xt_checks.collect([str(self.base)], (".md",)), [keep])
        self.assertEqual(len(xt_checks.collect([str(self.base / "docs")], ())), 2)  # không khai đuôi = mọi tệp

    def test_collect_names_filter_only_applies_to_directory_scan(self):
        keep = self.put("site/llms.txt", "x")
        self.put("site/notes.txt", "x")
        named = self.put("other.txt", "x")
        names = frozenset({"llms.txt"})
        self.assertEqual(xt_checks.collect([str(self.base / "site")], (".txt",), None, names), [keep])
        self.assertEqual(xt_checks.collect([str(named)], (".txt",), None, names), [named])
        self.assertEqual(len(xt_checks.collect([str(self.base / "site")], (".txt",), None, None)), 2)

    def test_sniff_for_binds_options_when_sniff_takes_two_arguments(self):
        plain = types.ModuleType("plain")
        self.assertIsNone(xt_checks.sniff_for(plain, {}))
        plain.SNIFF = lambda text: text == "x"
        one = xt_checks.sniff_for(plain, {"field": "y"})
        self.assertTrue(one is not None and one("x") and not one("y"))
        aware = types.ModuleType("aware")
        aware.SNIFF = lambda text, opts: opts.get("field", "f") in text
        bound = xt_checks.sniff_for(aware, {"field": "arm"})
        self.assertTrue(bound is not None and bound("uid,arm") and not bound("uid,f"))

    def test_run_passes_names_and_bound_sniff(self):
        self.put("t/llms.txt", "# A\n> t\n## B\n- [x](/x)\n")
        self.put("t/notes.txt", "rác")
        self.assertEqual(xt_checks.run("llms-txt", [str(self.base / "t")], {}), [])

    def test_collect_refuses_missing_and_links(self):
        real = self.put("real.md", "x")
        link = self.base / "link.md"
        link.symlink_to(real)
        with self.assertRaisesRegex(xt_checks.CheckError, "liên kết"):
            xt_checks.collect([str(link)], ())
        with self.assertRaisesRegex(xt_checks.CheckError, "không thấy"):
            xt_checks.collect([str(self.base / "absent")], ())

    def test_collect_skips_links_found_while_walking(self):
        real = self.put("tree/a.md", "x")
        (self.base / "tree" / "l.md").symlink_to(real)
        (self.base / "tree" / "ld").symlink_to(self.base / "tree", target_is_directory=True)
        self.assertEqual(xt_checks.collect([str(self.base / "tree")], (".md",)), [real])

    def test_run_sorts_findings(self):
        self.put("b.md", NFD + "\n")
        self.put("a.md", "ok\n" + NFD + "\n")
        found = xt_checks.run("nfc", [str(self.base)], {})
        self.assertEqual([(Path(f.path).name, f.line) for f in found], [("a.md", 2), ("b.md", 1)])


class NfcKindTest(TmpTest):
    def check(self, text: str | bytes, **opts: str) -> list[tuple[int, str]]:
        path = self.put("x.md", text)
        return [(f.line, f.code) for f in kind_nfc.check([path], opts)]

    def test_clean_vietnamese_is_silent(self):
        self.assertEqual(self.check(NFC + "\nHà Nội\n"), [])

    def test_decomposed_line_is_flagged_with_its_line_number(self):
        self.assertEqual(self.check("ok\n" + NFD + "\nok\n"), [(2, "NFC001")])

    def test_replacement_char_and_hidden_chars(self):
        self.assertEqual(self.check("Vi" + REPL + "t\n"), [(1, "NFC002")])
        self.assertEqual(self.check(BOM + "xin chào\n"), [(1, "NFC003")])
        self.assertEqual(self.check("a" + ZWSP + "b\n"), [(1, "NFC003")])

    def test_line_numbers_follow_editor_counting(self):
        self.assertEqual(self.check("a" + chr(0x2028) + "b\n" + NFD + "\n"), [(2, "NFC001")])
        self.assertEqual(self.check("a" + chr(12) + "b\r\n" + NFD + "\r\n"), [(2, "NFC001")])
        self.assertEqual(kind_nfc.OPTS, ("ignore",))

    def test_invalid_utf8_is_reported_as_unreadable(self):
        self.assertEqual(self.check(b"\xa4\xb1\xff"), [(0, "NFC000")])

    def test_ignore_option_silences_codes(self):
        self.assertEqual(self.check(BOM + "a\n" + NFD + "\n", ignore="NFC003,NFC001"), [])
        self.assertEqual(self.check(b"\xff", ignore="NFC000"), [])
        self.assertEqual(self.check("a" + REPL + "b\n", ignore="NFC002"), [])


class CliTest(TmpTest):
    def test_clean_tree_exits_zero(self):
        self.put("a.md", NFC + "\n")
        rc, out, _ = run_cli("nfc", str(self.base))
        self.assertEqual(rc, 0)
        self.assertIn("không phát hiện", out)

    def test_findings_exit_one_text_and_json(self):
        self.put("a.md", NFD + "\n")
        rc, out, _ = run_cli("nfc", str(self.base))
        self.assertEqual(rc, 1)
        self.assertIn("[NFC001]", out)
        rc, out, _ = run_cli("nfc", str(self.base), "--json")
        self.assertEqual(rc, 1)
        doc = json.loads(out)
        self.assertEqual((doc["schema"], doc["kind"], doc["findings"][0]["code"]), (1, "nfc", "NFC001"))
        self.assertEqual(doc["checked"], {"files": 1})
        rc, out, _ = run_cli("nfc", str(self.base), "--json", "--opt", "ignore=NFC001")
        self.assertEqual((rc, json.loads(out)["findings"]), (0, []))

    def test_checked_counts_files_and_only_visited_items(self):
        for kind, header, key, mixed, count in (
            ("sbom", {"bomFormat": "CycloneDX"}, "components", [None, {"components": [{}]}], 2),
            ("vex", {"@context": "https://openvex.dev/ns"}, "statements", [None, {}, {}], 2),
        ):
            with self.subTest(kind=kind):
                empty, out, _ = run_cli(kind, str(self.base), "--json")
                self.assertEqual((empty, json.loads(out)["checked"]), (0, {"files": 0, key: 0}))
                self.put("data.json", json.dumps({**header, key: mixed}))
                self.put("other.json", "{}")
                invalid = self.put("broken.txt", "[")
                rc, out, _ = run_cli(kind, str(self.base), str(invalid), "--json")
                doc = json.loads(out)
                self.assertEqual((rc, doc["schema"], doc["checked"]), (1, 1, {"files": 2, key: count}))
                rc, out, _ = run_cli(kind, str(invalid), "--json")
                self.assertEqual((rc, json.loads(out)["checked"]), (1, {"files": 1, key: 0}))

    def test_usage_errors_exit_two(self):
        for argv in (("khong-co",), ("nfc", "/không/có/đường/này"), ("nfc", "--opt", "sai")):
            with self.subTest(argv=argv):
                rc, _, err = run_cli(*argv)
                self.assertEqual(rc, 2)
                self.assertIn("static-check", err)

    def test_unexpected_kind_error_exits_two_not_as_findings(self):
        """Lỗi ngoài dự kiến của một loại không được thoát mã 1 (trùng "có phát hiện") hay ném traceback."""
        for exc in (
            ValueError("x"),
            RecursionError("x"),
            ZeroDivisionError("x"),
            UnicodeEncodeError("u", "x", 0, 1, "y"),
        ):
            with (
                self.subTest(exc=type(exc).__name__),
                unittest.mock.patch.object(xt_checks, "run_report", side_effect=exc),
            ):
                rc, out, err = run_cli("nfc", str(self.base))
            self.assertEqual((rc, out), (2, ""))
            self.assertIn("lỗi nội bộ", err)
            self.assertIn(type(exc).__name__, err)

    def test_default_path_is_the_current_directory(self):
        self.put("a.md", NFC + "\n")
        with unittest.mock.patch.object(
            xt_checks, "run_report", return_value=xt_checks.CheckReport([], {"files": 0})
        ) as run:
            self.assertEqual(run_cli("nfc")[0], 0)
        self.assertEqual(run.call_args.args[1], ["."])

    def test_missing_package_is_a_clear_error(self):
        with unittest.mock.patch.dict(sys.modules, {"xt_checks": None}):
            rc, _, err = run_cli("nfc")
        self.assertEqual(rc, 2)
        self.assertIn("xt_checks", err)


if __name__ == "__main__":
    unittest.main()
