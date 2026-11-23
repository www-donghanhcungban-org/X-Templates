"""T-4020: README không ghi cứng "bản đã gắn tag" (sửa tay mỗi lần cắt bản và lệch ngay khi tag mới ra) mà trỏ tới danh sách tag
trên GitHub; `validate` (mục của `xt.py checks`) từ chối dòng ghi cứng số phiên bản."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import xt

TAGS = "https://github.com/www-donghanhcungban-org/X-Templates/tags"


class ReadmeTagRuleTest(unittest.TestCase):
    def test_link_to_tag_list_passes(self):
        text = f"# X\n\nBản đã gắn tag: xem [danh sách tag]({TAGS}) hoặc `git describe --tags`.\n"
        self.assertEqual(xt.readme_tag_errors(text), [])

    def test_no_such_line_is_not_checked(self):
        self.assertEqual(xt.readme_tag_errors("# Dự án đích\n\nÁp dụng từ phiên bản v3.35.0.\n"), [])
        self.assertEqual(xt.readme_tag_errors(""), [])

    def test_pinned_version_is_rejected_in_every_form(self):
        for line in (
            "Bản đã gắn tag là [`v3.34.0`](https://github.com/o/r/tree/v3.34.0).",
            f"Bản đã gắn tag là v3.35.0, xem [tag]({TAGS}).",
            "Bản đã gắn tag là [mới nhất](https://github.com/o/r/tree/v10.0.0).",
        ):
            with self.subTest(line=line):
                errors = xt.readme_tag_errors(f"x\n{line}\n")
                self.assertEqual(len(errors), 1)
                self.assertIn("ghi cứng", errors[0])

    def test_line_without_tag_list_link_is_rejected(self):
        errors = xt.readme_tag_errors("Bản đã gắn tag: xem GitHub.\n")
        self.assertEqual(len(errors), 1)
        self.assertIn("/tags", errors[0])

    def test_each_offending_line_is_reported_once(self):
        text = "Bản đã gắn tag là v1.0.0.\nBản đã gắn tag: xem GitHub.\n"
        self.assertEqual(len(xt.readme_tag_errors(text)), 2)


class ValidateIntegrationTest(unittest.TestCase):
    def test_real_readme_passes(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Bản đã gắn tag", text)  # dòng vẫn còn, ở dạng liên kết
        self.assertEqual(xt.readme_tag_errors(text), [])
        self.assertEqual([e for e in xt.validate(ROOT / "framework") if "gắn tag" in e], [])

    def test_validate_reports_a_pinned_readme_next_to_the_framework(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "framework").mkdir()
            (root / "README.md").write_text("Bản đã gắn tag là v3.34.0.\n", encoding="utf-8")
            errors = [e for e in xt.validate(root / "framework") if "gắn tag" in e]
            self.assertEqual(len(errors), 1)
            self.assertTrue(errors[0].startswith("README.md:"))
            (root / "README.md").write_text(f"Bản đã gắn tag: [tag]({TAGS}).\n", encoding="utf-8")
            self.assertEqual([e for e in xt.validate(root / "framework") if "gắn tag" in e], [])
            (root / "README.md").unlink()
            self.assertEqual([e for e in xt.validate(root / "framework") if "gắn tag" in e], [])

    def test_unreadable_readme_is_not_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "framework").mkdir()
            (root / "README.md").write_bytes(b"\xff\xfe\x00 khong phai utf-8 \xc3\x28")
            self.assertEqual(xt._check_readme_tag(root / "framework"), [])


if __name__ == "__main__":
    unittest.main()
