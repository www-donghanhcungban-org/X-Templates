"""Sàn runtime CPython 3.13 (ADR-0094): mã của khung không dùng cú pháp chỉ có từ 3.14 trở lên.

CI có job `compat-py313` chạy cả bộ test trên 3.13 thật; bài này bắt lỗi cú pháp sớm trên mọi bản Python (kể cả khi
chạy cục bộ bằng 3.15) mà không cần cài 3.13.
"""

from __future__ import annotations

import ast
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FLOOR = (3, 13)


def tracked_python_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.py"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    return [ROOT / name for name in out.split("\0") if name]


class PythonFloorTest(unittest.TestCase):
    def test_floor_parse_rejects_unparenthesised_except_group(self):
        """Đối chứng: bộ đọc theo `feature_version` bắt đúng cú pháp 3.14 (PEP 758) đã gây lỗi ở 3.13."""
        source = "try:\n    pass\nexcept OSError, ValueError:\n    pass\n"
        with self.assertRaises(SyntaxError):
            ast.parse(source, feature_version=FLOOR)

    def test_floor_parse_accepts_parenthesised_except_group(self):
        ast.parse("try:\n    pass\nexcept (OSError, ValueError):\n    pass\n", feature_version=FLOOR)

    def test_every_tracked_python_file_parses_at_floor(self):
        files = tracked_python_files()
        self.assertGreater(len(files), 100)
        for path in files:
            with self.subTest(file=str(path.relative_to(ROOT))):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=FLOOR)


if __name__ == "__main__":
    unittest.main()
