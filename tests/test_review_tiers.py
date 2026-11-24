"""ADR-0098 (lát R2): bậc khai báo `author_tier`/`reviewer_tier` ở xt.yaml — kiểm cấu hình, review sạch theo bậc khi harness
máy không xếp hạng được, `doctor` cảnh báo agent reviewer ghim model trái bậc."""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import xt

TIERS_JSON = ROOT / "framework" / "templates" / "harness" / "model-tiers.json"


def args(**kw: object) -> argparse.Namespace:
    base = {"clean": True, "reviewer_model": None, "author_model": None, "reviewer_effort": None, "author_effort": None}
    return argparse.Namespace(**{**base, **kw})


class TierConfigTest(unittest.TestCase):
    def test_tier_order_matches_the_table(self):
        import json

        self.assertEqual(list(xt.TIER_ORDER), json.loads(TIERS_JSON.read_text(encoding="utf-8"))["tiers"])

    def test_names_must_be_known(self):
        self.assertIn("không thuộc các bậc", xt.review_tier_config_error({"reviewer_tier": "mid"}) or "")
        self.assertIn("author_tier", xt.review_tier_config_error({"author_tier": "bottom2"}) or "")

    def test_one_side_only_is_not_compared(self):
        self.assertIsNone(xt.review_tier_config_error({"reviewer_tier": "top-1"}))
        self.assertIsNone(xt.review_tier_config_error({}))

    def test_reviewer_must_be_higher_or_equal_with_higher_effort(self):
        err = xt.review_tier_config_error
        self.assertIsNone(err({"author_tier": "top-2", "reviewer_tier": "top-1"}))
        self.assertIsNone(err({"author_tier": "bottom", "reviewer_tier": "top"}))
        self.assertIsNone(
            err({"author_tier": "top-1", "reviewer_tier": "top-1", "author_effort": "high", "reviewer_effort": "max"})
        )
        for bad in (
            {"author_tier": "top-1", "reviewer_tier": "top-2"},  # thấp hơn
            {"author_tier": "top-1", "reviewer_tier": "top-1"},  # cùng bậc, thiếu effort
            {"author_tier": "top-1", "reviewer_tier": "top-1", "author_effort": "max", "reviewer_effort": "max"},
            {"author_tier": "top", "reviewer_tier": "top-1", "author_effort": "low", "reviewer_effort": "max"},
        ):
            with self.subTest(cfg=bad):
                self.assertIn("không cao hơn", xt.review_tier_config_error(bad) or "")

    def test_family_config_error_includes_tier_errors(self):
        cfg = {"author_tier": "top", "reviewer_tier": "top-1"}
        self.assertEqual(xt.review_family_config_error(cfg), xt.review_tier_config_error(cfg))
        self.assertIsNone(xt.review_family_config_error({"author_tier": "top-2", "reviewer_tier": "top-1"}))

    def test_keys_are_read_from_the_target_branch_config(self):
        for k in xt.REVIEW_TIER_KEYS:
            self.assertIn(k, xt.REVIEW_KEYS)


class CleanReviewByTierTest(unittest.TestCase):
    def test_tiers_replace_model_names_and_leave_a_trace(self):
        a = args()
        self.assertIsNone(xt._review_models_error(a, {"author_tier": "top-2", "reviewer_tier": "top-1"}))
        self.assertEqual((a.reviewer_model, a.author_model), ("tier:top-1", "tier:top-2"))

    def test_effort_comes_from_config_for_the_same_bucket(self):
        a = args()
        cfg = {"author_tier": "top-1", "reviewer_tier": "top-1", "author_effort": "high", "reviewer_effort": "max"}
        self.assertIsNone(xt._review_models_error(a, cfg))
        self.assertEqual((a.reviewer_effort, a.author_effort), ("max", "high"))

    def test_wrong_tier_config_is_refused(self):
        err = xt._review_models_error(args(), {"author_tier": "top", "reviewer_tier": "top-1"})
        self.assertIn("không cao hơn", err or "")

    def test_models_given_on_the_command_line_still_use_the_family_rule(self):
        cfg = {"author_tier": "top-2", "reviewer_tier": "top-1"}
        ok = args(reviewer_model="claude-opus-5-5", author_model="claude-sonnet-5-5")
        self.assertIsNone(xt._review_models_error(ok, cfg))
        bad = args(reviewer_model="claude-sonnet-5-5", author_model="claude-opus-5-5")
        self.assertIn("LOOP-ORCH-005", xt._review_models_error(bad, cfg) or "")

    def test_without_tiers_nothing_changes(self):
        err = xt._review_models_error(args(), {})
        self.assertIn("--clean cần --reviewer-model", err or "")

    def test_not_clean_is_not_checked(self):
        self.assertIsNone(xt._review_models_error(args(clean=False), {"author_tier": "top", "reviewer_tier": "bottom"}))


class DoctorReviewTiersTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.base / ".claude" / "agents").mkdir(parents=True)
        (self.base / "framework" / "templates" / "harness").mkdir(parents=True)
        shutil.copy(TIERS_JSON, self.base / "framework" / "templates" / "harness" / "model-tiers.json")
        for name, model in (("reviewer", "opus"), ("reviewer-alt", "opus"), ("executor", "sonnet")):
            (self.base / ".claude" / "agents" / f"{name}.md").write_text(
                f"---\nname: {name}\nmodel: {model}\n---\n\nthân\n", encoding="utf-8"
            )

    def doctor(self, yaml: str) -> list[str]:
        (self.base / "xt.yaml").write_text(yaml, encoding="utf-8")
        return [f.msg for f in xt._doctor_review_tiers(self.base)]

    def test_matching_tier_is_silent(self):
        self.assertEqual(self.doctor("reviewer_tier: top-1\n"), [])

    def test_mismatch_warns_for_each_reviewer_agent_but_not_executor(self):
        msgs = self.doctor("reviewer_tier: top\n")
        self.assertEqual(len(msgs), 2)
        self.assertTrue(all("top-1" in m and "reviewer_tier" in m for m in msgs))
        self.assertEqual(sorted(m.split()[0] for m in msgs), ["reviewer-alt.md", "reviewer.md"])

    def test_missing_or_invalid_config_and_table_fail_open(self):
        self.assertEqual(self.doctor("lint: x\n"), [])
        self.assertEqual(self.doctor("reviewer_tier: mid\n"), [])
        (self.base / "framework" / "templates" / "harness" / "model-tiers.json").write_text("{", encoding="utf-8")
        self.assertEqual(self.doctor("reviewer_tier: top\n"), [])
        self.assertEqual(xt._doctor_review_tiers(self.base / "absent"), [])
        with unittest.mock.patch.object(xt, "_xt_keys", side_effect=OSError("không đọc được")):
            self.assertEqual(xt._doctor_review_tiers(self.base), [])

    def test_target_project_table_path_is_found(self):
        moved = self.base / ".xtemplates"
        moved.mkdir()
        shutil.move(str(self.base / "framework"), str(moved / "framework"))
        self.assertEqual(len(self.doctor("reviewer_tier: top\n")), 2)


if __name__ == "__main__":
    unittest.main()
