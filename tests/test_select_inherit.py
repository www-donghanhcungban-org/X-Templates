"""T-4012 (AUD-TEST-131): `test-select` bắc cầu qua tệp test khác — lớp con ở tệp B kế thừa (hay dùng) lớp nền ở tệp A
được chọn khi lớp nền đó được chọn; chuỗi A → B → C; `import test_a` dùng qua thuộc tính → cả tệp; tên không trúng → không."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import xt

FILES = {
    "test_a.py": """import unittest


class TmpRepoCase(unittest.TestCase):
    def setUp(self):
        self.path = "lib.py"


class Unrelated(unittest.TestCase):
    pass


class ATest(TmpRepoCase):
    pass
""",
    "test_b.py": """import unittest
from test_a import TmpRepoCase as Base, Unrelated


class BTest(Base):
    pass


class BOther(unittest.TestCase):
    pass


class BUsesUnrelated(Unrelated):
    pass
""",
    "test_c.py": """from test_b import (
    BTest,
)


class CTest(BTest):
    pass
""",
    "test_d.py": """import unittest
import test_a


class DTest(test_a.TmpRepoCase):
    pass


class DOther(unittest.TestCase):
    pass
""",
    "test_e.py": """from test_a import Unrelated


class ETest(Unrelated):
    pass
""",
    "test_h.py": """class HTest:
    pass
""",
    "test_f.py": """from test_a import *


class FTest(TmpRepoCase):
    pass
""",
}


class SelectInheritTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.root / "tests").mkdir()
        for name, text in FILES.items():
            (self.root / "tests" / name).write_text(text, encoding="utf-8")

    def plan(self, *files: str):
        return xt.test_select_plan(self.root, "tests", list(files))

    def test_subclass_in_other_file_is_selected(self):
        plan = self.plan("lib.py")
        self.assertEqual(plan["tests/test_a.py"], {"Unrelated"})
        self.assertEqual(plan["tests/test_b.py"], {"BOther", "BUsesUnrelated"})  # alias `Base`, chỉ lớp dùng nó

    def test_chain_through_two_files(self):
        self.assertEqual(self.plan("lib.py")["tests/test_c.py"], set())

    def test_module_import_or_star_selects_whole_file(self):
        plan = self.plan("lib.py")
        self.assertEqual(plan["tests/test_d.py"], set())
        self.assertEqual(plan["tests/test_f.py"], set())

    def test_unselected_base_does_not_spread(self):
        plan = self.plan("lib.py")
        self.assertNotIn("tests/test_e.py", plan)
        self.assertNotIn("tests/test_h.py", plan)  # không import gì

    def test_whole_base_file_spreads_every_imported_name(self):
        (self.root / "tests" / "test_a.py").write_text(FILES["test_a.py"] + '\nHELPER = "lib.py"\n', encoding="utf-8")
        plan = self.plan("lib.py")
        self.assertEqual(plan["tests/test_a.py"], set())
        self.assertIn("tests/test_e.py", plan)
        self.assertEqual(plan["tests/test_b.py"], {"BOther"})

    def test_unparseable_importer_is_whole_file(self):
        (self.root / "tests" / "test_g.py").write_text("from test_a import TmpRepoCase\nclass (:\n", encoding="utf-8")
        self.assertEqual(self.plan("lib.py")["tests/test_g.py"], set())

    def test_nothing_selected_keeps_old_behavior(self):
        self.assertIsNone(self.plan("unknown-file.xyz"))


if __name__ == "__main__":
    unittest.main()
