"""T-4003 (ADR-0095): PR chạm lớp "tác động tức thì" cần review ở head dù `merge_review: optional`; PR ngoài lớp giữ
nguyên đường optional; chính sách đọc từ nhánh đích."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import xt
from test_merge import commit_base_xt
from test_merge_review_source import STANDARD, std

OPTIONAL = "merge_autonomy: L3\nmerge_hard_exceptions: auto\nmerge_review: optional\ndelivery_phase: build\n"
IN_CLASS = [
    ".claude/hooks/guard.py",
    ".claude/hooks/pre-bash-guard.sh",
    ".claude/settings.json",
    ".codex/hooks.json",
    ".github/workflows/ci.yml",
    ".github/rulesets/main.json",
    "xt.yaml",
]
OUT_OF_CLASS = ["scripts/xt.py", "README.md", "docs/adr/0001-x.md", ".github/CODEOWNERS", "src/auth/login.py"]


class ImmediateEffectReviewTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(unittest.mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.base)}))
        self.enterContext(unittest.mock.patch.object(xt, "project_dir", return_value=self.base))

    def decide(self, *paths: str, prefix: str = ""):
        files = [*STANDARD, *({"path": p, "additions": 1, "deletions": 0} for p in paths)]
        with unittest.mock.patch.object(xt, "project_prefix", return_value=prefix):
            return xt._merge_eval(std() | {"files": files, "baseRefName": "main"})[0]

    def test_each_class_path_needs_review_even_when_optional(self):
        commit_base_xt(self.base, OPTIONAL)
        for path in IN_CLASS:
            with self.subTest(path=path):
                d = self.decide(path)
                self.assertEqual(d["verdict"], "review", d)
                self.assertNotEqual(d["review"], "optional")
                self.assertFalse(d["eligible"])

    def test_out_of_class_keeps_optional_path(self):
        commit_base_xt(self.base, OPTIONAL)
        for path in OUT_OF_CLASS:
            with self.subTest(path=path):
                d = self.decide(path)
                self.assertEqual((d["verdict"], d["review"]), ("merge", "optional"), d)

    def test_renamed_away_from_class_path_still_counts(self):
        commit_base_xt(self.base, OPTIONAL)
        files = [*STANDARD, {"path": "docs/x.yml", "previous": ".github/workflows/ci.yml"}]
        d = xt._merge_eval(std() | {"files": files, "baseRefName": "main"})[0]
        self.assertEqual(d["verdict"], "review", d)

    def test_monorepo_prefix_matches_project_and_repo_root(self):
        commit_base_xt(self.base, OPTIONAL)
        for path in ("apps/web/.claude/hooks/guard.py", "apps/web/xt.yaml", ".github/workflows/ci.yml"):
            with self.subTest(path=path):
                self.assertEqual(self.decide(path, prefix="apps/web/")["verdict"], "review")
        self.assertEqual(self.decide("apps/api/xt.yaml", prefix="apps/web/")["verdict"], "merge")

    def test_policy_comes_from_target_branch_not_working_tree(self):
        commit_base_xt(self.base, OPTIONAL, working=OPTIONAL + "immediate_review: off\n")
        self.assertEqual(self.decide(".claude/hooks/guard.py")["verdict"], "review")

    def test_target_branch_can_turn_it_off(self):
        commit_base_xt(self.base, OPTIONAL + "immediate_review: off\n")
        d = self.decide(".claude/hooks/guard.py")
        self.assertEqual((d["verdict"], d["review"]), ("merge", "optional"), d)

    def test_required_mode_unchanged(self):
        commit_base_xt(self.base, OPTIONAL.replace("optional", "required").replace("build", "harden"))
        self.assertEqual(self.decide("scripts/xt.py")["verdict"], "review")

    def test_class_asks_for_review_not_for_a_human_under_human_exceptions(self):
        commit_base_xt(self.base, OPTIONAL.replace("hard_exceptions: auto", "hard_exceptions: human"))
        d = self.decide(".github/workflows/ci.yml")
        self.assertEqual(d["verdict"], "review", d)
        self.assertEqual(d["hard"], [])

    def test_phase_in_decision_is_the_real_one(self):
        commit_base_xt(self.base, OPTIONAL)
        self.assertEqual(self.decide(".claude/settings.json")["delivery_phase"], "build")

    def test_valid_review_at_head_clears_it(self):
        commit_base_xt(self.base, OPTIONAL)
        files = [*STANDARD, {"path": ".claude/hooks/guard.py", "additions": 1, "deletions": 0}]
        mark = {"head": "c" * 40, "clean": True, "at": "2026-11-23T10:00:00Z"}
        d = xt._merge_eval(std() | {"files": files, "baseRefName": "main", "xtReviews": [mark]})[0]
        self.assertEqual((d["verdict"], d["eligible"]), ("merge", True), d)
        stale = std() | {"files": files, "baseRefName": "main", "xtReviews": [{**mark, "head": "d" * 40}]}
        self.assertEqual(xt._merge_eval(stale)[0]["verdict"], "review")

    def test_invalid_value_is_reported(self):
        self.assertIsNone(xt.immediate_review_error({}))
        self.assertIsNone(xt.immediate_review_error({"immediate_review": "on"}))
        self.assertIsNone(xt.immediate_review_error({"immediate_review": "off"}))
        self.assertIn("immediate_review", xt.immediate_review_error({"immediate_review": "maybe"}))

    def test_invalid_value_falls_back_to_on(self):
        commit_base_xt(self.base, OPTIONAL + "immediate_review: maybe\n")
        self.assertEqual(self.decide(".claude/hooks/guard.py")["verdict"], "review")


if __name__ == "__main__":
    unittest.main()
