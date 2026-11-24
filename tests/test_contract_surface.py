"""P0 (ADR-0097): đóng băng bề mặt hợp đồng công khai — đích và hook gọi những thứ này, nên xoá hay đổi tên là phá bản
đã cài. Thêm vào thì được; test chỉ đòi các mục đã ghim vẫn còn."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import xt

GOLDEN = json.loads((ROOT / "tests" / "fixtures" / "contract-surface.json").read_text(encoding="utf-8"))


def subcommands() -> set[str]:
    for action in xt.build_parser()._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices)
    return set()


class ContractSurfaceTest(unittest.TestCase):
    def test_commands_that_hooks_ci_and_skills_call_still_exist(self):
        missing = sorted(set(GOLDEN["commands"]) - subcommands())
        self.assertEqual(missing, [], "lệnh con của hợp đồng bị xoá hoặc đổi tên")

    def test_template_config_keys_still_exist(self):
        text = (ROOT / "framework" / "templates" / "xt.yaml").read_text(encoding="utf-8")
        keys = set(re.findall(r"^#?\s?([a-z_]+):", text, flags=re.M))
        missing = sorted(set(GOLDEN["config_keys"]) - keys)
        self.assertEqual(missing, [], "khoá xt.yaml của hợp đồng bị xoá hoặc đổi tên ở mẫu")

    def test_machine_readable_schema_numbers_are_still_read(self):
        self.assertTrue(set(GOLDEN["schemas"]["release_check"]) <= set(xt.RELEASE_SCHEMAS))
        self.assertIn(xt.RELEASE_SCHEMA, xt.RELEASE_SCHEMAS)
        install = (ROOT / "scripts" / "install.py").read_text(encoding="utf-8")
        self.assertIn(f'"schema": {GOLDEN["schemas"]["install_manifest"]}', install)

    def test_golden_is_sorted_and_contract_number_is_positive(self):
        self.assertEqual(GOLDEN["commands"], sorted(GOLDEN["commands"]))
        self.assertEqual(GOLDEN["config_keys"], sorted(GOLDEN["config_keys"]))
        self.assertGreaterEqual(GOLDEN["contract"], 1)

    def test_review_mark_still_reads_v1_and_v2(self):
        sha = "a" * 40
        self.assertTrue(xt.REVIEW_MARK_RE.search(f"<!-- xt-review v1 head={sha} verdict=clean -->"))
        self.assertTrue(xt.REVIEW_MARK_RE.search(f"<!-- xt-review v2 head={sha} verdict=clean base={sha} -->"))


if __name__ == "__main__":
    unittest.main()
