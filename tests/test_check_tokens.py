"""ADR-0099: loại `tokens` của `static-check` (fixture tốt/xấu trong thư mục tạm)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from xt_checks import CheckError, kind_tokens

DESIGN = ":root { --color-bg: #ffffff; --space-1: 4px; }\n.x { color: var(--color-bg); }\n"


class TokensTest(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.design = self.put("tokens.css", DESIGN)

    def put(self, name: str, text: str | bytes) -> Path:
        path = self.base / name
        if isinstance(text, bytes):
            path.write_bytes(text)
        else:
            path.write_text(text, encoding="utf-8")
        return path

    def run_check(self, files: list[Path], **opts: str) -> list[tuple[int, str]]:
        merged = {"tokens": str(self.design), **opts}
        return [(f.line, f.code) for f in kind_tokens.check(files, merged)]

    def test_interface(self) -> None:
        self.assertTrue(kind_tokens.HELP and ".css" in kind_tokens.SUFFIXES and callable(kind_tokens.check))

    def test_missing_option_is_usage_error(self) -> None:
        with self.assertRaises(CheckError):
            kind_tokens.check([], {})

    def test_opts_constant(self) -> None:
        self.assertEqual(kind_tokens.OPTS, ("tokens", "allow"))

    def test_crlf_lines_keep_numbers(self) -> None:
        file = self.put("crlf.css", "a { color: var(--color-bg); }\r\nb { color: #fff; }\r\n")
        self.assertEqual(self.run_check([file]), [(2, "TOK002")])

    def test_unreadable_design_file_is_tok000(self) -> None:
        found = kind_tokens.check([], {"tokens": str(self.base / "absent.css")})
        self.assertEqual([(f.line, f.code) for f in found], [(0, "TOK000")])

    def test_good_file_is_clean(self) -> None:
        good = self.put("a.css", "a { color: var(--color-bg); margin: var(--space-1); background: transparent; }\n")
        self.assertEqual(self.run_check([good, self.design]), [])

    def test_undefined_var_and_fallback(self) -> None:
        bad = self.put("b.tsx", "x = 'var(--nope)';\ny = 'var(--ghost, red)';\n")
        found = kind_tokens.check([bad], {"tokens": str(self.design)})
        self.assertEqual([(f.line, f.code) for f in found], [(1, "TOK001"), (2, "TOK001")])
        self.assertNotIn("fallback", found[0].message)
        self.assertIn("fallback", found[1].message)

    def test_var_defined_in_checked_file(self) -> None:
        own = self.put("c.css", ".a { --local: 1px; margin: var(--local); }\n")
        self.assertEqual(self.run_check([own]), [])

    def test_hardcoded_colors(self) -> None:
        text = "a { color: #fff; b: #ABCDEF; c: #11223344; d: rgb(1,2,3); e: hsla(0,0%,0%,1); f: oklch(1 0 0); g: color(srgb 1 1 1); }\n"
        found = self.run_check([self.put("d.css", text)])
        self.assertEqual(found, [(1, "TOK002")] * 7)

    def test_not_colors(self) -> None:
        text = '<a href="#abcd1">&#123;</a> <b class="#fffff">\n'
        self.assertEqual(self.run_check([self.put("e.html", text)]), [])

    def test_allow_option_and_always_allowed(self) -> None:
        file = self.put("f.css", "a { color: #FFF; b: #000; c: inherit; d: currentColor; }\n")
        self.assertEqual(self.run_check([file], allow=" #fff, "), [(1, "TOK002")])

    def test_comment_and_xt_allow_lines_skipped(self) -> None:
        text = "// #fff\n/* #fff */\n * #fff\na { color: #fff; } /* xt-allow: TOK002 */\nb = '#fff'; // xt-allow: TOK002\n  c: #fff\n"
        self.assertEqual(self.run_check([self.put("g.scss", text)]), [(6, "TOK002")])

    def test_design_file_may_hold_colors(self) -> None:
        self.assertEqual(self.run_check([self.design]), [])

    def test_design_file_undefined_var_still_reported(self) -> None:
        design = self.put("t2.css", ":root { --a: #fff; --b: var(--zzz); }\n")
        found = kind_tokens.check([design], {"tokens": str(design)})
        self.assertEqual([(f.line, f.code) for f in found], [(1, "TOK001")])

    def test_unreadable_checked_file_is_skipped(self) -> None:
        self.assertEqual(self.run_check([self.put("h.css", b"\xff\xfe"), self.base / "absent.css"]), [])


if __name__ == "__main__":
    unittest.main()
