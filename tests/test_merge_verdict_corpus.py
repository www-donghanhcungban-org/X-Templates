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
import xt_adapter
from xt_merge_intent import MergeIntent, bind, current, verified
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

    def test_bound_target_corpus_blocks_wrong_repo_host_and_missing_pin(self):
        cases, _ = xt.autonomy_corpus(CORPUS)
        picked = [row for row in cases if row["id"].startswith("guard-har492-")]
        self.assertEqual(len(picked), 12)
        with tempfile.TemporaryDirectory() as tmp:
            env = xt.BenchEnv(Path(tmp))
            for row in picked:
                with self.subTest(row=row["id"]):
                    result = xt._bench_run(row, env)
                    self.assertEqual(result["status"], "pass", result)

    def test_incomplete_live_identity_cannot_authorize_a_pinned_merge(self):
        cli = f"gh pr merge 7 --squash --match-head-commit {HEAD}"
        valid = merge_result()
        with tempfile.TemporaryDirectory() as tmp:
            env = xt.BenchEnv(Path(tmp))
            for key, bad in (("host", ""), ("host", ".invalid"), ("repo", "?/repo"), ("pr", True), ("head", "short")):
                for data in ({k: v for k, v in valid.items() if k != key}, {**valid, key: bad}):
                    for policy in POLICIES:
                        with self.subTest(data=data, policy=policy):
                            got = xt._bench_guard({"command": cli, "policy": policy, "merge_check": data}, env)
                            self.assertEqual((got["code"], got["allowed"]), ("UNVERIFIED", False))
            for update, code in (
                ({"hard": ["x"]}, "HARD_EXCEPTION"),
                ({"verdict": "wait"}, "MERGE_INELIGIBLE"),
                ({"eligible": False, "review": "missing"}, "REVIEW_MISSING"),
            ):
                got = xt._bench_guard({"command": cli, "merge_check": {**valid, "host": "", **update}}, env)
                self.assertEqual(got["code"], code)

    def test_unverified_connector_still_requires_confirmation_with_full_pin(self):
        args = {"pr_number": 7, "repository_full_name": "O/R", "expected_head_sha": HEAD, "merge_method": "squash"}
        with tempfile.TemporaryDirectory() as tmp:
            env = xt.BenchEnv(Path(tmp))
            for policy in POLICIES:
                inp = {
                    "tool": "mcp",
                    "tool_name": "mcp__codex_apps__github_merge_pull_request",
                    "tool_input": args,
                    "merge_check": merge_result(host="github.com"),
                    "policy": policy,
                }
                with self.subTest(policy=policy):
                    result = xt._bench_guard(inp, env)
                    self.assertEqual((result["code"], result["allowed"]), ("UNVERIFIED", False))
                    cores = xt_adapter.to_core("codex", inp["tool_name"], args, tmp, tmp)
                    blocked, code, _ = xt_adapter.decide(env.module("guard"), cores)
                    self.assertEqual((blocked, code), (True, "UNVERIFIED"))

    def test_explicit_target_overrides_environment_only_for_its_own_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = xt.BenchEnv(Path(tmp))
            cli = f"gh pr merge 7 --squash --match-head-commit {HEAD}"
            endpoint = f"repos/o/r/pulls/7/merge -f sha={HEAD}"
            with mock.patch.dict(os.environ, {"GH_REPO": "other.example/other/r", "GH_HOST": "other.example"}):
                for command, code in (
                    (cli, "UNVERIFIED"),
                    (cli + " --repo git.example/o/r", "OTHER_ASK"),
                    ("gh api -X PUT --hostname git.example " + endpoint, "OTHER_ASK"),
                    ("GH_REPO=o/r GH_HOST=git.example " + cli, "OTHER_ASK"),
                    ("gh api -X PUT --hostname other.example " + endpoint, "UNVERIFIED"),
                    ("gh api -X PUT --hostname git.example --hostname other.example " + endpoint, "UNVERIFIED"),
                    ("gh api -X PUT https://git.example/api/v3/" + endpoint, "OTHER_ASK"),
                    ("gh api -X PUT --hostname other.example https://git.example/api/v3/" + endpoint, "UNVERIFIED"),
                    ("gh api -X PUT --hostname git.example --input body.json " + endpoint, "UNVERIFIED"),
                    ("gh api -X PUT --hostname git.example " + endpoint + " -F sha[]=x", "UNVERIFIED"),
                    (cli, "UNVERIFIED"),
                ):
                    result = xt._bench_guard(
                        {"command": command, "policy": "strict", "merge_check": merge_result(host="git.example")}, env
                    )
                    with self.subTest(command=command):
                        self.assertEqual(result["code"], code, result)

    def test_steward_reads_and_writes_same_enterprise_target(self):
        host = "git.example"
        pull = {
            "html_url": f"https://{host}/Org/Repo/pull/7",
            "number": 7,
            "base": {"repo": {"full_name": "org/repo"}},
            "head": {"sha": HEAD},
            "state": "open",
        }
        intent = verified(pull, "repos/org/repo", "7", host, ValueError)
        self.assertIsNotNone(intent)
        out = bind({"live_intent": intent._asdict(), "repo": "org/repo"}, {"action": "merge", "pr": 7, "head": HEAD})
        cmd = xt._steward_command(out, "repos/org/repo")[0]
        self.assertIn(f"--hostname {host} repos/org/repo/pulls/7/merge", out["do"])
        self.assertEqual(cmd[cmd.index("--hostname") + 1 :][:2], [host, "repos/org/repo/pulls/7/merge"])
        self.assertIn(f"sha={HEAD}", cmd)
        with_message = xt._steward_command(out, "repos/org/repo", "Tiêu đề", "Nội dung")[0]
        self.assertEqual(with_message[-4:], ["-f", "commit_title=Tiêu đề", "-f", "commit_message=Nội dung"])
        fetch = mock.Mock(return_value=[pull])
        self.assertEqual(current(out, "repos/org/repo", fetch), "")
        fetch.assert_called_once_with("repos/org/repo/pulls/7", host=host)
        self.assertFalse(xt._steward_command(out, "repos/other/target"))
        for bad in ({"host": "other.example"}, {"repo": "other/target"}, {"pr": 8}, {"expected_head": "b" * 40}):
            with self.subTest(bad=bad):
                changed = {**out, "merge_intent": {**out["merge_intent"], **bad}}
                self.assertTrue(current(changed, "repos/org/repo", fetch))
        fetch.return_value = []
        self.assertTrue(current(out, "repos/org/repo", fetch))
        fetch.return_value = [False]
        self.assertTrue(current(out, "repos/org/repo", fetch))
        self.assertEqual(bind({"live_intent": None}, out)["action"], "wait")
        for fields in ({"host": None}, {"repo": ".."}, {"pr": True}, {"expected_head": 1}):
            self.assertIsNone(
                MergeIntent.from_action({**out, "merge_intent": {**out["merge_intent"], **fields}}, "repos/org/repo")
            )
        for fields in (
            {"number": False},
            {"html_url": "https://git.example/other/repo/pull/7"},
            {"head": {"sha": "abcd"}},
        ):
            self.assertIsNone(MergeIntent.from_pull({**pull, **fields}))

    def test_live_read_binds_host_and_rejects_a_different_destination(self):
        selected = []

        def record(repo, number, local, raw, intent):
            selected.append((repo, number, xt.PR_READ_HOST.get()))
            return {}

        with (
            mock.patch.object(xt, "_gh_one", return_value={}),
            mock.patch.object(xt, "_pr_rest_details", side_effect=record),
        ):
            xt._pr_rest("https://Git.Example/O/R/pull/7")
            xt._pr_rest("o/r#7")
            with mock.patch.dict(os.environ, {"GH_REPO": "git.example/a/b", "GH_HOST": "other.example"}):
                xt._pr_rest("7")
                xt._pr_rest("o/r#7")
                xt._pr_rest("https://github.com/a/b/pull/7")
            with mock.patch.dict(os.environ, {"GH_REPO": "bad/repo/target/shape"}):
                with self.assertRaisesRegex(xt.PrInputError, "GH_REPO"):
                    xt._pr_rest("7")
            with mock.patch.dict(os.environ, {"GH_HOST": "https://git.example"}):
                with self.assertRaisesRegex(xt.PrInputError, "GH_HOST"):
                    xt._pr_rest("o/r#7")
            with self.assertRaises(xt.PrInputError):
                xt._pr_rest("https://user@git.example/o/r/pull/7")
        self.assertEqual(
            selected,
            [
                ("repos/O/R", "7", "git.example"),
                ("repos/o/r", "7", ""),
                ("repos/a/b", "7", "git.example"),
                ("repos/o/r", "7", "other.example"),
                ("repos/a/b", "7", "github.com"),
            ],
        )
        pull = {
            "number": 7,
            "html_url": "https://git.example/o/r/pull/7",
            "base": {"repo": {"full_name": "o/r"}},
            "head": {"sha": HEAD},
        }
        for repo, number, host in (
            ("repos/a/b", "7", "git.example"),
            ("repos/o/r", "8", "git.example"),
            ("repos/o/r", "7", "other.example"),
        ):
            with self.assertRaises(xt.PrInputError):
                verified(pull, repo, number, host, xt.PrInputError)

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
        self.assertEqual(xt._steward_command(action, "repos/o/r"), [])
        action["merge_intent"] = {"host": "github.com", "repo": "o/r", "pr": 7, "expected_head": HEAD}
        commands = xt._steward_command(action, "repos/o/r")
        self.assertEqual(
            commands,
            [
                [
                    "gh",
                    "api",
                    "-X",
                    "PUT",
                    "--hostname",
                    "github.com",
                    "repos/o/r/pulls/7/merge",
                    "-f",
                    "merge_method=squash",
                    "-f",
                    f"sha={HEAD}",
                ]
            ],
        )


if __name__ == "__main__":
    unittest.main()
