"""T-4001: corpus và oracle phủ verdict merge cùng ca đối chứng (AUD-HAR-454)."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import xt
from test_merge_verdict_codes import HEAD, POLICIES, VERDICTS, merge_result

CORPUS = ROOT / "tests" / "fixtures" / "autonomy"


def merge_cases() -> list[dict]:
    rows, _ = xt.autonomy_corpus(CORPUS)
    return [row for row in rows if row["id"].startswith("guard-har454-")]


def entry(row: dict) -> str:
    inp = row["input"]
    if inp.get("tool") == "mcp":
        return "mcp"
    return "rest" if inp["command"].startswith("gh api ") else "cli"


class MergeVerdictCorpusTest(unittest.TestCase):
    def test_matrix_has_every_verdict_entry_and_policy_with_allow_controls(self):
        rows = merge_cases()
        self.assertTrue(rows)
        required = {
            (verdict, path, policy) for verdict in VERDICTS for path in ("cli", "rest", "mcp") for policy in POLICIES
        }
        actual = set()
        controls, mismatches = set(), set()
        for row in rows:
            self.assertIn("AUD-HAR-454", row["refs"])
            self.assertEqual(row["group"], "guard")
            inp, expected = row["input"], row["expect"]
            path_policy = (entry(row), inp["policy"])
            if expected["allowed"]:
                self.assertEqual((row["origin"], expected["code"]), ("control", "RULE_ALLOW"))
                self.assertEqual(inp["merge_check"]["head"], HEAD)
                controls.add(path_policy)
            elif expected["code"] == "MERGE_HEAD_MISMATCH":
                self.assertEqual(inp["merge_check"]["verdict"], "merge")
                self.assertNotEqual(inp["merge_check"]["head"], HEAD)
                mismatches.add(path_policy)
            else:
                self.assertEqual(expected["code"], "MERGE_INELIGIBLE")
                actual.add((inp["merge_check"]["verdict"], *path_policy))
        self.assertEqual(actual, required)
        self.assertEqual(controls, {(path, policy) for path in ("cli", "rest", "mcp") for policy in POLICIES})
        self.assertEqual(mismatches, controls)

    def test_every_new_case_runs_through_real_bench(self):
        with tempfile.TemporaryDirectory(prefix="xt-merge-corpus-") as tmp:
            env = xt.BenchEnv(Path(tmp))
            with mock.patch.dict(os.environ, {"XT_GUARD_PHASE": "harden"}):
                for case in merge_cases():
                    with self.subTest(case=case["id"]):
                        result = xt._bench_run(case, env)
                        self.assertEqual(result["status"], "pass", result)

    def test_oracle_detects_lost_code_as_false_green(self):
        """Bỏ kênh mã riêng trong bộ nhớ tái hiện OTHER_ASK cũ; corpus phải báo false-green."""
        cases = [row for row in merge_cases() if not row["expect"]["allowed"] and row["input"]["policy"] == "default"]
        self.assertEqual(len(cases), 18)
        with tempfile.TemporaryDirectory(prefix="xt-merge-oracle-") as tmp:
            env = xt.BenchEnv(Path(tmp))
            guard = env.module("guard")
            real = guard.decide

            def without_merge_code(out):
                decision = real(out)
                if decision.code in ("MERGE_INELIGIBLE", "MERGE_HEAD_MISMATCH"):
                    return guard.Decision("ask", "OTHER_ASK", "sure", (), decision.reason)
                return decision

            with mock.patch.object(guard, "decide", side_effect=without_merge_code):
                for case in cases:
                    with self.subTest(case=case["id"]):
                        result = xt._bench_run(case, env)
                        self.assertEqual(result["status"], "false_green", result)

    def test_pr_next_and_steward_do_not_emit_merge_for_ineligible_verdict(self):
        for verdict in VERDICTS:
            with self.subTest(verdict=verdict):
                decision = {**merge_result(verdict), "pr": 7, "lane": "nhanh", "review_optional": True}
                action = xt.pr_next(decision, False, {})
                self.assertNotEqual(action["action"], "merge", action)
                commands = xt._steward_command(action, "repos/o/r")
                self.assertFalse(any("--match-head-commit" in command for command in commands), commands)
                self.assertFalse(
                    any(any("/merge" in argument for argument in command) for command in commands), commands
                )
        decision = {**merge_result(), "pr": 7, "lane": "nhanh", "review_optional": True}
        action = xt.pr_next(decision, False, {})
        self.assertEqual(action["action"], "merge", action)
        commands = xt._steward_command(action, "repos/o/r")
        self.assertEqual(
            commands,
            [["gh", "api", "-X", "PUT", "repos/o/r/pulls/7/merge", "-f", "merge_method=squash", "-f", f"sha={HEAD}"]],
        )


if __name__ == "__main__":
    unittest.main()
