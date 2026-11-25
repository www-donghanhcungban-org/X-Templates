"""T-4001: corpus và oracle phủ verdict merge cùng ca đối chứng (AUD-HAR-454)."""

from __future__ import annotations

import os
import subprocess
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
from xt_merge_intent import MergeIntent, RepoTarget, bind, current, verified
from test_merge_verdict_codes import HEAD, POLICIES, VERDICTS, merge_result
from test_xt_cli import TmpRepoCase

CORPUS = ROOT / "tests" / "fixtures" / "autonomy"


def merge_cases() -> list[dict]:
    rows, _ = xt.autonomy_corpus(CORPUS)
    return [row for row in rows if row["id"].startswith("guard-har454-")]


def entry(row: dict) -> str:
    inp = row["input"]
    if inp.get("tool") == "mcp":
        return "mcp"
    return "rest" if inp["command"].startswith("gh api ") else "cli"


class MergeVerdictCorpusTest(TmpRepoCase):
    def test_matrix_has_every_verdict_entry_and_policy_with_bound_controls(self):
        rows = merge_cases()
        self.assertTrue(rows)
        required = {
            (verdict, path, policy) for verdict in VERDICTS for path in ("cli", "rest", "mcp") for policy in POLICIES
        }
        actual = set()
        controls, mismatches, unverified = set(), set(), set()
        for row in rows:
            self.assertIn("AUD-HAR-454", row["refs"])
            self.assertEqual(row["group"], "guard")
            inp, expected = row["input"], row["expect"]
            path_policy = (entry(row), inp["policy"])
            if expected["code"] == "OTHER_ASK":
                self.assertEqual(row["origin"], "control")
                self.assertEqual(expected["allowed"], inp["policy"] == "default")
                self.assertEqual(inp["merge_check"]["head"], HEAD)
                controls.add(path_policy)
            elif expected["code"] == "MERGE_HEAD_MISMATCH":
                self.assertEqual(inp["merge_check"]["verdict"], "merge")
                self.assertNotEqual(inp["merge_check"]["head"], HEAD)
                mismatches.add(path_policy)
            elif expected["code"] == "UNVERIFIED":
                self.assertEqual(entry(row), "mcp")
                self.assertFalse(expected["allowed"])
                self.assertEqual(inp["tool_input"]["expectedHeadSha"], HEAD)
                unverified.add((inp["policy"], inp["merge_check"]["head"] == HEAD))
            else:
                self.assertEqual(expected["code"], "MERGE_INELIGIBLE")
                actual.add((inp["merge_check"]["verdict"], *path_policy))
        self.assertEqual(actual, required)
        self.assertEqual(controls, {(path, policy) for path in ("cli", "rest") for policy in POLICIES})
        self.assertEqual(mismatches, controls)
        self.assertEqual(unverified, {(policy, same_head) for policy in POLICIES for same_head in (False, True)})

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
        cases = [
            row
            for row in merge_cases()
            if row["input"]["policy"] == "default"
            and row["expect"]["code"] in ("MERGE_INELIGIBLE", "MERGE_HEAD_MISMATCH")
        ]
        self.assertEqual(len(cases), 17)
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
        cli = f"gh pr merge 7 --repo github.com/o/r --squash --match-head-commit {HEAD}"
        valid = merge_result()
        with tempfile.TemporaryDirectory() as tmp:
            env = xt.BenchEnv(Path(tmp))
            got = xt._bench_guard({"command": cli, "merge_check": valid}, env)
            self.assertEqual((got["code"], got["allowed"]), ("OTHER_ASK", True))
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

    def test_merge_uses_gh_option_value_boundaries(self):
        cli = f"gh pr merge 7 --match-head-commit {HEAD}"
        cases = (
            (cli + " -R github.com/o/r -sRother.example/o/r", "UNVERIFIED"),
            (cli + " -sR github.com/o/r --repo github.com/o/r", "UNVERIFIED"),
            (cli + " -sRgithub.com/o/r", "OTHER_ASK"),
            (cli + " -sR github.com/o/r", "OTHER_ASK"),
            (cli + " -sR=github.com/o/r", "OTHER_ASK"),
            (cli + " -s=false -R github.com/o/r", "OTHER_ASK"),
            (cli + " -R github.com/o/r -sb --repo", "OTHER_ASK"),
            (cli + " -R github.com/o/r -st title", "RULE_DENY"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            env = xt.BenchEnv(Path(tmp))
            for command, code in cases:
                for policy in POLICIES:
                    with self.subTest(command=command, policy=policy):
                        result = xt._bench_guard(
                            {"command": command, "policy": policy, "merge_check": merge_result()}, env
                        )
                        self.assertEqual(result["code"], code, result)
                        self.assertEqual(result["allowed"], code == "OTHER_ASK" and policy == "default", result)

    def test_gh_pr_normalization_does_not_apply_to_explicit_api_host(self):
        host = "www.git.example"
        cli = f"gh pr merge 7 -R {host}/o/r --squash --match-head-commit {HEAD}"
        rest = f"gh api -X PUT --hostname {host} repos/o/r/pulls/7/merge -f sha={HEAD}"
        with tempfile.TemporaryDirectory() as tmp:
            env = xt.BenchEnv(Path(tmp))
            for command, code in ((cli, "UNVERIFIED"), (rest, "OTHER_ASK")):
                for policy in POLICIES:
                    with self.subTest(command=command, policy=policy):
                        inp = {"command": command, "policy": policy, "merge_check": merge_result(host=host)}
                        result = xt._bench_guard(inp, env)
                        self.assertEqual(result["code"], code, result)
                        self.assertEqual(result["allowed"], code == "OTHER_ASK" and policy == "default", result)

    def test_merge_proves_selectors_after_env_unset_and_reset(self):
        cli = f"gh pr merge 7 --squash --match-head-commit {HEAD}"
        rest = f"gh api -X PUT --hostname github.com repos/o/r/pulls/7/merge -f sha={HEAD}"
        qualified = cli + " --repo github.com/o/r"
        cases = (
            ("env -u GH_REPO " + cli, "UNVERIFIED"),
            ('env -u "$SELECTOR_NAME" ' + cli, "UNVERIFIED"),
            ("env --unset=GH_HOST " + cli, "OTHER_ASK"),  # GH_REPO giàu host
            ("env -u GH_REPO env -i GH_REPO=o/r " + cli, "UNVERIFIED"),
            ("env -i " + cli, "UNVERIFIED"),
            ("env - " + cli, "UNVERIFIED"),
            ("env -i " + qualified, "OTHER_ASK"),
            ("env -i " + rest, "OTHER_ASK"),
            ("env --ignore-environment UNRELATED=value GH_REPO=o/r GH_HOST=github.com " + cli, "OTHER_ASK"),
            ("GH_REPO=o/r GH_HOST=github.com env -iuGH_REPO " + cli, "UNVERIFIED"),
        )
        with (
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.dict(os.environ, {"GH_REPO": "github.com/o/r", "GH_HOST": "github.com"}),
        ):
            env = xt.BenchEnv(Path(tmp))
            for command, code in cases:
                for policy in POLICIES:
                    with self.subTest(command=command, policy=policy):
                        result = xt._bench_guard(
                            {"command": command, "policy": policy, "merge_check": merge_result()}, env
                        )
                        self.assertEqual(result["code"], code, result)
                        self.assertEqual(result["allowed"], code == "OTHER_ASK" and policy == "default", result)

    def test_shell_selector_proof_matches_child_environment(self):
        host = "git.example"
        cli = f"gh pr merge 7 --squash --match-head-commit {HEAD}"
        cases = (
            ("{name}={value}; ", ""),
            ("export {name}={value}; unset {name}; ", ""),
            ("export {name}={value}; export -n {name}; ", ""),
            ("declare {name}={value}; ", ""),
            ("export {name}={value}; declare +x {name}; ", ""),
            ("(export {name}={value}); ", ""),
            ("export {name}={value} | true; ", ""),
            ("export {name}={value}; exec -c ", ""),
            ("declare -x {name}={value}; ", "{value}"),
            ("export {name}='{value}' && ", "{value}"),
            ("export {name}={value}; ", "{value}"),
            ("{name}={value} ", "{value}"),
        )
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ):
            env = xt.BenchEnv(Path(tmp))
            for key in ("GH_HOST", "GH_REPO"):
                os.environ.pop(key, None)
            for name, value, target in (("GH_HOST", host, cli + " -R o/r"), ("GH_REPO", host + "/o/r", cli)):
                for pattern, expected in cases:
                    prefix = pattern.format(name=name, value=value)
                    child = subprocess.run(
                        ["bash", "--noprofile", "--norc", "-c", prefix + "printenv " + name],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    with self.subTest(prefix=prefix):
                        self.assertEqual(child.returncode, 0 if expected else 1, child.stderr)
                        self.assertEqual(child.stdout.strip(), expected.format(value=value))
                        for policy in POLICIES:
                            data = {
                                "command": prefix + target,
                                "policy": policy,
                                "merge_check": merge_result(host=host),
                            }
                            result = xt._bench_guard(data, env)
                            self.assertEqual(result["code"], "OTHER_ASK" if expected else "UNVERIFIED", result)
                            self.assertEqual(result["allowed"], bool(expected) and policy == "default", result)

    def test_selector_scope_at_the_command_matches_a_real_child(self):
        host = "git.example"
        target = f"gh pr merge 7 --squash --repo o/r --match-head-commit {HEAD}"
        local = "export GH_HOST=git.example"
        locked = "export GH_HOST=other.example; readonly GH_HOST"
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ):
            env = xt.BenchEnv(Path(tmp))
            os.environ.pop("GH_HOST", None)
            os.environ.pop("GH_REPO", None)
            cases = (
                ("true; GH_HOST=git.example {cmd} && true", host),
                ("unset GH_HOST; GH_HOST=git.example {cmd}", host),
                ("export -n GH_HOST=git.example; {cmd}", ""),
                ("true && " + local + "; {cmd}; unset GH_HOST", host),
                (f"cd {tmp} && " + local + "; {cmd}", host),
                (f"cd {tmp}/missing && " + local + "; {cmd}", ""),
                ("false && " + local + "; {cmd}", ""),
                ("bash -c '" + local + "; {cmd}'", host),
                ('printf %s "$(' + local + '; {cmd})"', host),
                (locked + "; GH_HOST=git.example {cmd}", "other.example"),
                (locked + "; env GH_HOST=git.example {cmd}", host),
                (locked + '; echo "$(' + local + '; {cmd})"', "other.example"),
                (local + "; {cmd}; unset GH_HOST; {cmd}", host),
            )
            for template, expected in cases:
                with self.subTest(template=template):
                    child = subprocess.run(
                        ["bash", "--noprofile", "--norc", "-c", template.format(cmd="printenv GH_HOST")],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(child.stdout.strip(), expected)
                    # Hai lần cùng argv nhận hai môi trường khác nhau: lần cuối không có GH_HOST.
                    bound = expected == host and template.count("{cmd}") == 1
                    for policy in POLICIES:
                        data = {
                            "command": template.format(cmd=target),
                            "policy": policy,
                            "merge_check": merge_result(host=host),
                        }
                        result = xt._bench_guard(data, env)
                        self.assertEqual(result["code"], "OTHER_ASK" if bound else "UNVERIFIED", result)
                        self.assertEqual(result["allowed"], bound and policy == "default", result)

    def test_qualified_inline_repo_and_checkout_inheritance_in_another_directory(self):
        host = "git.example"
        cli = f"gh pr merge 7 --squash --match-head-commit {HEAD}"
        with (
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.dict(os.environ, {"GH_REPO": host + "/o/r", "GH_HOST": host}),
        ):
            root = Path(tmp) / "checkout"
            root.mkdir()
            env = xt.BenchEnv(root)
            for prefix, bound in (
                ("", False),
                ("GH_REPO=o/r ", False),
                ("GH_REPO=git.example/o/r ", True),
                ("env GH_REPO=git.example/o/r ", True),
                ("GH_REPO=git.example/o/r env -u GH_REPO ", False),
            ):
                for policy in POLICIES:
                    with self.subTest(prefix=prefix, policy=policy):
                        data = {
                            "command": f"cd {tmp} && " + prefix + cli,
                            "policy": policy,
                            "merge_check": merge_result(host=host),
                        }
                        result = xt._bench_guard(data, env)
                        self.assertEqual(result["code"], "OTHER_ASK" if bound else "UNVERIFIED", result)
                        self.assertEqual(result["allowed"], bound and policy == "default", result)

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
        target = RepoTarget(host, "org/repo")
        out = bind(
            {"live_host": host, "live_intent": intent._asdict(), "repo": "org/repo"},
            {"action": "merge", "pr": 7, "head": HEAD},
        )
        cmd = xt._steward_command(out, target)[0]
        self.assertIn(f"--hostname {host} repos/org/repo/pulls/7/merge", out["do"])
        self.assertEqual(cmd[cmd.index("--hostname") + 1 :][:2], [host, "repos/org/repo/pulls/7/merge"])
        self.assertIn(f"sha={HEAD}", cmd)
        with_message = xt._steward_command(out, target, "Tiêu đề", "Nội dung")[0]
        self.assertEqual(with_message[-4:], ["-f", "commit_title=Tiêu đề", "-f", "commit_message=Nội dung"])
        fetch = mock.Mock(return_value=[pull])
        self.assertEqual(current(out, target, fetch), "")
        fetch.assert_called_once_with("repos/org/repo/pulls/7", host=host)
        self.assertFalse(xt._steward_command(out, RepoTarget(host, "other/target")))
        for bad in ({"host": "other.example"}, {"repo": "other/target"}, {"pr": 8}, {"expected_head": "b" * 40}):
            with self.subTest(bad=bad):
                changed = {**out, "merge_intent": {**out["merge_intent"], **bad}}
                self.assertTrue(current(changed, target, fetch))
        fetch.return_value = []
        self.assertTrue(current(out, target, fetch))
        fetch.return_value = [False]
        self.assertTrue(current(out, target, fetch))
        self.assertEqual(bind({"live_host": host, "live_intent": None, "repo": "org/repo"}, out)["action"], "wait")
        for fields in ({"host": None}, {"repo": ".."}, {"pr": True}, {"expected_head": 1}):
            self.assertIsNone(
                MergeIntent.from_action({**out, "merge_intent": {**out["merge_intent"], **fields}}, target)
            )
        for fields in (
            {"number": False},
            {"html_url": "https://git.example/other/repo/pull/7"},
            {"head": {"sha": "abcd"}},
        ):
            self.assertIsNone(MergeIntent.from_pull({**pull, **fields}))

    def test_live_read_binds_host_and_rejects_a_different_destination(self):
        checkout = self.init_repo()
        self.git("remote", "add", "origin", "https://git.example/o/r.git")
        self.enterContext(
            mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(checkout), "GH_REPO": "", "GH_HOST": ""})
        )
        selected = []
        pull = {
            "number": 7,
            "html_url": "https://git.example/o/r/pull/7",
            "base": {"repo": {"full_name": "o/r"}},
            "head": {"sha": HEAD},
        }

        def record(repo, number, local, raw, intent):
            selected.append((repo, number, xt.PR_READ_HOST.get()))
            return {}

        with (
            mock.patch.object(xt, "_gh_api", return_value=[pull]) as fetch,
            mock.patch.object(xt, "_pr_rest_details", side_effect=record),
        ):
            xt._pr_rest("https://Git.Example/O/R/pull/7")
            xt._pr_rest("o/r#7")
            with mock.patch.dict(os.environ, {"GH_REPO": "git.example/o/r", "GH_HOST": "git.example"}):
                xt._pr_rest("7")
            for selector in ("a/b#7", "https://github.com/o/r/pull/7", "https://user@git.example/o/r/pull/7"):
                with self.subTest(selector=selector), self.assertRaises(xt.PrInputError):
                    xt._pr_rest(selector)
            with mock.patch.dict(os.environ, {"GH_REPO": "bad/repo/target/shape"}):
                with self.assertRaisesRegex(xt.PrInputError, "GH_REPO"):
                    xt._pr_rest("7")
            with mock.patch.dict(os.environ, {"GH_HOST": "https://git.example"}):
                with self.assertRaisesRegex(xt.PrInputError, "GH_HOST"):
                    xt._pr_rest("o/r#7")
            self.assertEqual(fetch.call_args_list, [mock.call("repos/o/r/pulls/7")] * 3)
        self.assertEqual(selected, [("repos/o/r", "7", "git.example")] * 3)
        for repo, number, host in (
            ("repos/a/b", "7", "git.example"),
            ("repos/o/r", "8", "git.example"),
            ("repos/o/r", "7", "other.example"),
        ):
            with self.assertRaises(xt.PrInputError):
                verified(pull, repo, number, host, xt.PrInputError)

    def test_pr_next_and_steward_do_not_emit_merge_for_ineligible_verdict(self):
        target = RepoTarget("github.com", "o/r")
        for verdict in VERDICTS:
            with self.subTest(verdict=verdict):
                decision = {**merge_result(verdict), "pr": 7, "lane": "nhanh", "review_optional": True}
                action = xt.pr_next(decision, False, {})
                self.assertNotEqual(action["action"], "merge", action)
                commands = xt._steward_command(action, target)
                self.assertFalse(any("--match-head-commit" in command for command in commands), commands)
                self.assertFalse(
                    any(any("/merge" in argument for argument in command) for command in commands), commands
                )
        decision = {**merge_result(), "pr": 7, "lane": "nhanh", "review_optional": True}
        action = xt.pr_next(decision, False, {})
        self.assertEqual(action["action"], "merge", action)
        self.assertEqual(xt._steward_command(action, target), [])
        action["merge_intent"] = {"host": "github.com", "repo": "o/r", "pr": 7, "expected_head": HEAD}
        commands = xt._steward_command(action, target)
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
