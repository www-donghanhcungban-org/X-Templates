"""ADR-0099: loại `credits` (UX-VISUAL-007, CMP-LIC-026) — fixture tốt/xấu trong thư mục tạm, phủ mọi mã CRD000–CRD004."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from xt_checks import Finding, kind_credits

HEAD = "| Tệp | Nguồn | License |\n|---|---|---|\n"


class CreditsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.credits = self.base / "assets" / "CREDITS.md"

    def media(self, *names: str) -> list[Path]:
        out: list[Path] = []
        for name in names:
            path = self.base / "assets" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"x")
            out.append(path)
        return out

    def run_check(self, table: str | None, files: list[Path], **opts: str) -> list[Finding]:
        if table is not None:
            self.credits.parent.mkdir(parents=True, exist_ok=True)
            self.credits.write_text(table, encoding="utf-8")
        return kind_credits.check(files, {"credits": str(self.credits), **opts})

    def codes(self, found: list[Finding]) -> list[tuple[str, int]]:
        return [(f.code, f.line) for f in found]

    def test_interface(self) -> None:
        self.assertTrue(kind_credits.HELP)
        self.assertIn(".woff2", kind_credits.SUFFIXES)

    def test_good_table_is_clean(self) -> None:
        files = self.media("a.png", "img/b.JPG")
        table = HEAD + "| a.png | https://example.org/a | CC0-1.0 |\n| `./img/b.JPG` | Nguyễn An | mit |\n"
        self.assertEqual(self.run_check(table, files), [])

    def test_no_media_means_nothing_to_check(self) -> None:
        notes = self.base / "notes.md"
        notes.write_text("x", encoding="utf-8")
        self.assertEqual(kind_credits.check([], {}), [])
        self.assertEqual(kind_credits.check([notes], {}), [])

    def test_crd000_unreadable_credits(self) -> None:
        found = self.run_check(None, self.media("a.png"))
        self.assertEqual([(f.code, f.line) for f in found], [("CRD000", 0)])
        self.assertEqual(found[0].path, str(self.credits))

    def test_nul_in_key_cell_is_crd004_not_crash(self) -> None:
        files = self.media("a.png")
        table = HEAD + "| a.png | An | MIT |\n| gone" + chr(0) + ".png | me | MIT |\n"
        self.assertEqual(self.codes(self.run_check(table, files)), [("CRD004", 4)])

    def test_opts_constant(self) -> None:
        self.assertEqual(kind_credits.OPTS, ("credits", "allow"))

    def test_crd001_media_without_row(self) -> None:
        files = self.media("a.png", "b.mp3")
        found = self.run_check(HEAD + "| a.png | src | MIT |\nprose line\n", files)
        self.assertEqual(self.codes(found), [("CRD001", 0)])
        self.assertEqual(found[0].path, str(files[1]))

    def test_crd002_missing_source_and_short_row(self) -> None:
        files = self.media("a.png", "b.png", "c.png")
        table = HEAD + "| a.png | | MIT |\n| b.png | TBD | MIT |\n| c.png |\n"
        self.assertEqual(
            self.codes(self.run_check(table, files)), [("CRD002", 3), ("CRD002", 4), ("CRD002", 5), ("CRD003", 5)]
        )

    def test_crd003_license_outside_allow(self) -> None:
        files = self.media("a.png", "b.png")
        table = HEAD + "| a.png | src | Proprietary |\n| b.png | src |  |\n"
        self.assertEqual(self.codes(self.run_check(table, files)), [("CRD003", 3), ("CRD003", 4)])

    def test_allow_option_replaces_default(self) -> None:
        files = self.media("a.png")
        table = HEAD + "| a.png | src | GPL-3.0-only |\n"
        self.assertEqual(self.run_check(table, files, allow="GPL-3.0-only, ,MIT"), [])
        self.assertEqual(self.codes(self.run_check(table, files)), [("CRD003", 3)])

    def test_header_order_and_default_columns(self) -> None:
        files = self.media("a.png")
        swapped = "| File | Giấy phép | Tác giả |\n| :-- | --- | --- |\n| a.png | MIT | An |\n"
        self.assertEqual(self.run_check(swapped, files), [])
        no_header_words = "| x | y | z |\n|---|---|---|\n| a.png | An | MIT |\n"
        self.assertEqual(self.run_check(no_header_words, files), [])

    def test_table_without_separator_is_all_data(self) -> None:
        files = self.media("a.png")
        self.assertEqual(self.run_check("| a.png | An | MIT |\n", files), [])

    def test_non_media_rows_are_ignored(self) -> None:
        files = self.media("a.png")
        table = HEAD + "| a.png | An | MIT |\n| README | | |\n"
        self.assertEqual(self.run_check(table, files), [])

    def test_match_by_filename_in_subfolder(self) -> None:
        files = self.media("img/deep/logo.png")
        self.assertEqual(self.run_check(HEAD + "| logo.png | An | MIT |\n", files), [])
        self.assertEqual(self.codes(self.run_check(HEAD + "| go.png | An | MIT |\n", files)), [("CRD001", 0)])

    def test_crd004_row_for_vanished_file(self) -> None:
        files = self.media("a.png")
        self.media("extra.png")
        table = (
            HEAD
            + "| a.png | An | MIT |\n| gone.png | An | MIT |\n| extra.png | An | MIT |\n| ../elsewhere/x.png | An | MIT |\n"
        )
        found = self.run_check(table, files)
        self.assertEqual(self.codes(found), [("CRD004", 4)])
        self.assertEqual(found[0].path, str(self.credits))


if __name__ == "__main__":
    unittest.main()
