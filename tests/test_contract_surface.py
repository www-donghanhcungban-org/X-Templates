"""P0 (ADR-0097): đóng băng bề mặt hợp đồng công khai — đích và hook gọi những thứ này, nên xoá hay đổi tên là phá bản
đã cài. Thêm vào thì được; test chỉ đòi các mục đã ghim vẫn còn."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import xt

GOLDEN = json.loads((ROOT / "tests" / "fixtures" / "contract-surface.json").read_text(encoding="utf-8"))
TEMPLATE = (ROOT / "framework" / "templates" / "xt.yaml").read_text(encoding="utf-8")


def subparsers(parser: argparse.ArgumentParser) -> dict[str, Any]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return dict(action.choices)
    return {}


def active_keys(text: str) -> set[str]:
    """Khoá đang bật: dòng bắt đầu bằng `khoá:` (không phải dòng chú thích)."""
    return set(re.findall(r"^([a-z0-9_]+):", text, flags=re.M))


def commented_keys(text: str) -> set[str]:
    """Khoá chỉ có ở dạng ví dụ trong chú thích: `# khoá:`."""
    return set(re.findall(r"^#\s?([a-z0-9_]+):", text, flags=re.M))


class ContractSurfaceTest(unittest.TestCase):
    def test_commands_that_hooks_ci_skills_and_templates_call_still_exist(self):
        missing = sorted(set(GOLDEN["commands"]) - set(subparsers(xt.build_parser())))
        self.assertEqual(missing, [], "lệnh con của hợp đồng bị xoá hoặc đổi tên")

    def test_second_level_subcommands_still_exist(self):
        top = subparsers(xt.build_parser())
        for cmd, expected in GOLDEN["subcommands"].items():
            with self.subTest(cmd=cmd):
                self.assertLessEqual(set(expected), set(subparsers(top[cmd])), f"`{cmd}` mất lệnh con")
        action = next(a for a in top["upgrade"]._actions if a.dest == "upgrade_action")
        self.assertLessEqual(set(GOLDEN["upgrade_actions"]), set(action.choices))

    def test_third_level_subcommands_and_review_verdicts_still_exist(self):
        top = subparsers(xt.build_parser())
        for path, expected in GOLDEN["subcommands_level3"].items():
            first, second = path.split()
            with self.subTest(path=path):
                self.assertLessEqual(set(expected), set(subparsers(subparsers(top[first])[second])))
        for verdict in GOLDEN["review_verdicts"]:
            with self.subTest(verdict=verdict):
                self.assertTrue(xt.REVIEW_MARK_RE.search(f"<!-- xt-review v1 head={'a' * 40} verdict={verdict} -->"))

    def test_commands_called_by_dev_task_are_in_the_contract(self):
        text = (ROOT / "scripts" / "dev-task.sh").read_text(encoding="utf-8")
        called = set(re.findall(r"\bxt_py\s+([a-z][a-z-]+)", text))
        self.assertTrue(called, "dev-task.sh không gọi lệnh con nào của xt.py?")
        self.assertLessEqual(called, set(GOLDEN["commands"]), "dev-task.sh gọi lệnh con ngoài hợp đồng")

    def test_template_config_keys_still_exist(self):
        self.assertEqual(sorted(set(GOLDEN["config_keys"]) - active_keys(TEMPLATE)), [], "khoá đang bật bị xoá/đổi tên")
        optional_missing = set(GOLDEN["config_keys_optional"]) - commented_keys(TEMPLATE) - active_keys(TEMPLATE)
        self.assertEqual(sorted(optional_missing), [], "khoá ví dụ bị xoá/đổi tên")

    def test_a_commented_example_does_not_count_as_an_active_key(self):
        text = "# commit_gate: fast\nlint: x\n"
        self.assertEqual(active_keys(text), {"lint"})
        self.assertEqual(commented_keys(text), {"commit_gate"})
        self.assertEqual(active_keys("e2e_setup: y\n"), {"e2e_setup"})

    def test_machine_readable_schema_numbers_are_still_read(self):
        self.assertTrue(set(GOLDEN["schemas"]["release_check"]) <= set(xt.RELEASE_SCHEMAS))
        self.assertIn(xt.RELEASE_SCHEMA, xt.RELEASE_SCHEMAS)
        self.assertEqual(xt.STAGE_SCHEMA, GOLDEN["schemas"]["stage"])
        install = (ROOT / "scripts" / "install.py").read_text(encoding="utf-8")
        self.assertIn(f'doc = {{"schema": {GOLDEN["schemas"]["install_manifest"]}, "files": labelled', install)

    def test_golden_is_sorted_and_contract_number_is_positive(self):
        for key in ("commands", "config_keys", "config_keys_optional", "upgrade_actions"):
            self.assertEqual(GOLDEN[key], sorted(GOLDEN[key]), key)
        for cmd, subs in GOLDEN["subcommands"].items():
            self.assertEqual(subs, sorted(subs), cmd)
        self.assertGreaterEqual(GOLDEN["contract"], 1)

    def test_review_mark_still_reads_v1_and_v2_with_base_and_scope(self):
        sha = "a" * 40
        scope = "b" * 64
        self.assertTrue(xt.REVIEW_MARK_RE.search(f"<!-- xt-review v1 head={sha} verdict=clean -->"))
        v2 = xt.REVIEW_MARK_RE.search(f"<!-- xt-review v2 head={sha} verdict=clean base={sha} scope={scope} -->")
        self.assertIsNotNone(v2)
        assert v2 is not None
        self.assertEqual((v2[1], v2[3], v2[4]), (sha, sha, scope))


if __name__ == "__main__":
    unittest.main()
