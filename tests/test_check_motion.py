"""ADR-0099: loại `motion` — fixture CSS tốt/xấu cho từng mã MOT001..MOT004."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from xt_checks import kind_motion

REDUCED = "@media (prefers-reduced-motion: reduce) { * { animation: none; transition: none; } }\n"
STOP = ".s:hover { animation-play-state: paused; }\n"


class MotionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def codes(self, css: str, **opts: str) -> list[tuple[int, str]]:
        path = self.base / "a.css"
        path.write_text(css, encoding="utf-8")
        return [(f.line, f.code) for f in kind_motion.check([path], opts)]

    def test_interface(self) -> None:
        self.assertTrue(kind_motion.HELP)
        self.assertEqual(kind_motion.SUFFIXES, (".css", ".scss"))

    def test_clean_files(self) -> None:
        self.assertEqual(self.codes(""), [])
        self.assertEqual(self.codes("a { color: red; }\n"), [])
        good = ".a { transition: opacity 200ms; }\n.b { animation: spin 1s linear infinite; }\n" + STOP + REDUCED
        self.assertEqual(self.codes(good), [])

    def test_transition_all(self) -> None:
        css = ".a { transition: all 0.3s; }\n.b { transition-property: all; }\n" + REDUCED
        self.assertEqual(self.codes(css), [(1, "MOT001"), (2, "MOT001")])

    def test_missing_reduced_motion_reports_first_line_once(self) -> None:
        css = "a { color: red; }\n.a { transition: opacity 1s; }\n.b { animation: x 2s; }\n"
        self.assertEqual(self.codes(css), [(2, "MOT002")])
        self.assertEqual(self.codes("@keyframes x { to { opacity: 1; } }\n"), [(1, "MOT002")])

    def test_short_infinite_in_ms_and_seconds(self) -> None:
        for dur in ("100ms", "0.2s", ".3s"):
            with self.subTest(dur=dur):
                css = f".a {{ animation: blink {dur} infinite; }}\n" + STOP + REDUCED
                self.assertEqual(self.codes(css), [(1, "MOT003")])
        ok = ".a { animation: blink 340ms infinite; }\n" + STOP + REDUCED
        self.assertEqual(self.codes(ok), [])

    def test_duration_property_and_no_duration(self) -> None:
        tail = STOP + REDUCED
        long_ = ".a {\n animation-name: x;\n animation-duration: 2s;\n animation-iteration-count: infinite;\n}\n"
        short = ".a {\n animation-duration: 150ms;\n animation-iteration-count: infinite;\n}\n"
        self.assertEqual(self.codes(long_ + tail), [])
        self.assertEqual(self.codes(short + tail), [(3, "MOT003")])
        self.assertEqual(self.codes(".a { animation: x infinite; }\n" + tail), [])

    def test_unterminated_block_and_no_stop(self) -> None:
        self.assertEqual(self.codes(".a { animation: x 1s infinite", ignore="MOT002"), [(1, "MOT004")])
        self.assertEqual(self.codes(".a { animation: x 1s infinite; }\n" + REDUCED), [(1, "MOT004")])

    def test_comments_are_ignored(self) -> None:
        css = "/* transition: all 1s;\n animation: x 1ms infinite; */\n" + "a { color: red; }\n"
        self.assertEqual(self.codes(css), [])

    def test_allow_marker_and_ignore(self) -> None:
        css = ".a { transition: all 1s; } /* xt-allow: MOT001, MOT002 */\n"
        self.assertEqual(self.codes(css), [])
        other = ".a { transition: all 1s; } /* xt-allow: MOT002 */\n"
        self.assertEqual(self.codes(other), [(1, "MOT001")])
        self.assertEqual(self.codes(other, ignore="MOT001,"), [])
        self.assertEqual(self.codes(".a { transition: all 1s; }\n", ignore="MOT001,MOT002"), [])

    def test_line_numbers_follow_editor_counting(self) -> None:
        self.assertEqual(
            self.codes("a { }" + chr(0x2028) + "\n.b { transition: all 1s; }\n" + REDUCED), [(2, "MOT001")]
        )
        allowed = "a { }" + chr(12) + "\n.b { transition: all 1s; } /* xt-allow: MOT001 */\n" + REDUCED
        self.assertEqual(self.codes(allowed), [])

    def test_opts_constant(self) -> None:
        self.assertEqual(kind_motion.OPTS, ("ignore",))

    def test_unreadable_file_is_skipped(self) -> None:
        path = self.base / "b.css"
        path.write_bytes(b"\xff\xfe")
        self.assertEqual(kind_motion.check([path], {}), [])

    def test_unicode_content(self) -> None:
        css = "/* Việt hoá */\n.a::after { content: 'Đang tải'; animation: x 1s infinite; }\n" + STOP + REDUCED
        self.assertEqual(self.codes(css), [])


if __name__ == "__main__":
    unittest.main()
