"""T-4000 / AUD-HAR-454: quyết định merge giữ mã qua hook và adapter (D-547).

Chỉ giả lập kết quả máy đọc PR; đường phân tích lệnh, gom lý do và chính sách chạy thật.
Không gọi GitHub hay thực hiện một lệnh merge nào.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
import guard

HEAD = "a" * 40
OTHER_HEAD = "b" * 40
VERDICTS = ("wait", "fix", "update", "human", "closed")
ENTRIES = ("cli", "rest", "mcp", "core")
BOUND_ENTRIES = ("cli", "rest", "core")
POLICIES = ("default", "strict")
CLI = f"gh pr merge 7 --squash --match-head-commit {HEAD}"
REST = f"gh api -X PUT repos/{{owner}}/{{repo}}/pulls/7/merge -f sha={HEAD} -f merge_method=squash"
MCP = {
    "owner": "o",
    "repo": "r",
    "pullNumber": 7,
    "expectedHeadSha": HEAD,
    "merge_method": "squash",
}


def merge_result(verdict: str = "merge", **changes: object) -> dict:
    return {
        "verdict": verdict,
        "host": "github.com",
        "pr": 7,
        "hard": [],
        "head": HEAD,
        "repo": "o/r",
        "reasons": ["Kết quả kiểm PR"],
        "eligible": verdict == "merge",
        "review": "optional",
        "autonomy": 3,
        **changes,
    }


class MergeVerdictCodesTest(unittest.TestCase):
    def setUp(self):
        self.root = self.enterContext(tempfile.TemporaryDirectory(prefix="xt-merge-verdict-"))
        self.enterContext(
            mock.patch.dict(
                os.environ,
                {
                    "CLAUDE_PROJECT_DIR": self.root,
                    "XT_GUARD_PHASE": "harden",
                    "GH_REPO": "github.com/o/r",
                    "GH_HOST": "github.com",
                },
            )
        )

    def raw(self, entry: str, result: dict, command: str | None = None, tool_input: dict | None = None) -> dict:
        with mock.patch.object(guard, "merge_check", return_value=result):
            if entry == "core":
                return guard._core_decision(
                    {"tool": "exec_command", "command": command or CLI, "project_dir": self.root, "cwd": self.root}
                )
            if entry == "mcp":
                return guard._rule_decision(
                    "mcp",
                    {
                        "tool_name": "mcp__github__merge_pull_request",
                        "tool_input": MCP if tool_input is None else tool_input,
                    },
                    self.root,
                )
            return guard._rule_decision(
                "bash",
                {"tool_input": {"command": command or (REST if entry == "rest" else CLI)}, "cwd": self.root},
                self.root,
            )

    def check(self, entry: str, result: dict, policy: str, code: str, **kwargs: object) -> None:
        with mock.patch.dict(os.environ, {"XT_GUARD_POLICY": policy}):
            raw = self.raw(entry, result, **kwargs)
            self.assertEqual(guard.decide(raw).code, code, raw)
            if code in ("MERGE_INELIGIBLE", "MERGE_HEAD_MISMATCH"):
                self.assertEqual(json.loads(json.dumps(raw)).get("code"), code, raw)
            final = raw if policy == "strict" else guard.apply_policy(raw)
        self.assertEqual(final["decision"], "ask" if policy == "strict" else "deny", final)

    def test_every_ineligible_verdict_across_entry_points_and_policies(self):
        for verdict in VERDICTS:
            for entry in ENTRIES:
                for policy in POLICIES:
                    with self.subTest(verdict=verdict, entry=entry, policy=policy):
                        self.check(entry, merge_result(verdict), policy, "MERGE_INELIGIBLE")

    def test_valid_pinned_merge_still_allowed(self):
        for entry in BOUND_ENTRIES:
            for policy in POLICIES:
                with self.subTest(entry=entry, policy=policy), mock.patch.dict(os.environ, {"XT_GUARD_POLICY": policy}):
                    raw = self.raw(entry, merge_result())
                    final = raw if policy == "strict" else guard.apply_policy(raw)
                    self.assertEqual(final["decision"], "allow", final)
                    self.assertEqual(guard.decide(raw).code, "RULE_ALLOW", raw)

    def test_pinned_mcp_merge_still_requires_a_verified_host(self):
        for policy in POLICIES:
            for head in (HEAD, OTHER_HEAD):
                with self.subTest(policy=policy, head=head):
                    self.check("mcp", merge_result(head=head), policy, "UNVERIFIED")
            self.check(
                "mcp",
                merge_result(head=OTHER_HEAD),
                policy,
                "UNVERIFIED",
                tool_input={**MCP, "merge_method": "unsupported"},
            )

    def test_head_changed_since_pin_is_not_replaced_with_latest_head(self):
        for entry in BOUND_ENTRIES:
            for policy in POLICIES:
                for head in (OTHER_HEAD, ""):
                    with self.subTest(entry=entry, policy=policy, head=head):
                        self.check(
                            entry, merge_result(head=head), policy, "MERGE_HEAD_MISMATCH" if head else "UNVERIFIED"
                        )

    def test_existing_review_hard_and_unverified_blocks_keep_their_codes(self):
        cases = (
            (merge_result("review", review="missing"), "REVIEW_MISSING"),
            (merge_result("human", hard=["quyền người merge"]), "HARD_EXCEPTION"),
            ({"verdict": "lỗi", "reasons": ["không đọc được PR"]}, "UNVERIFIED"),
        )
        for result, code in cases:
            for entry in ENTRIES:
                for policy in POLICIES:
                    with self.subTest(code=code, entry=entry, policy=policy):
                        self.check(entry, result, policy, code)

    def test_ineligible_merge_without_supported_pin_is_still_blocked(self):
        entries = (
            ("cli", {"command": "gh pr merge 7 --squash"}),
            ("cli", {"command": CLI + " --body notes"}),
            ("rest", {"command": "gh api -X PUT repos/o/r/pulls/7/merge"}),
            ("rest", {"command": REST + " -H Accept:application/json"}),
            ("mcp", {"tool_input": {k: v for k, v in MCP.items() if k != "expectedHeadSha"}}),
        )
        for verdict in VERDICTS:
            for entry, kwargs in entries:
                for policy in POLICIES:
                    with self.subTest(verdict=verdict, entry=entry, policy=policy, kwargs=kwargs):
                        self.check(entry, merge_result(verdict), policy, "MERGE_INELIGIBLE", **kwargs)

    def test_eligible_unpinned_merge_requires_a_pin(self):
        """ADR-0102: thiếu pin vẫn chặn ở head đủ điều kiện."""
        entries = (
            ("cli", {"command": "gh pr merge 7 --squash"}),
            ("rest", {"command": "gh api -X PUT repos/o/r/pulls/7/merge"}),
            ("mcp", {"tool_input": {k: v for k, v in MCP.items() if k != "expectedHeadSha"}}),
        )
        for entry, kwargs in entries:
            with self.subTest(entry=entry):
                raw = self.raw(entry, merge_result(), **kwargs)
                self.assertEqual((raw["decision"], guard.decide(raw).code), ("ask", "UNVERIFIED"), raw)
                self.assertEqual(guard.apply_policy(raw)["decision"], "deny")

    def test_extra_flags_and_duplicate_pins_cannot_hide_head_mismatch(self):
        """Dạng không auto-allow vẫn kiểm tất cả pin, không chỉ giá trị cuối của cờ/field trùng."""
        entries = (
            ("cli", {"command": CLI + " --body notes"}),
            ("cli", {"command": CLI + " -R o/r"}),
            ("cli", {"command": CLI.replace("--match-head-commit ", "--match-head-commit=") + " --body notes"}),
            ("cli", {"command": CLI + f" --match-head-commit {OTHER_HEAD}"}),
            ("cli", {"command": CLI.replace(HEAD, OTHER_HEAD) + f" --match-head-commit {HEAD}"}),
            ("rest", {"command": REST + " -H Accept:application/json"}),
            ("rest", {"command": REST + f" -f sha={OTHER_HEAD}"}),
            ("rest", {"command": REST.replace(HEAD, OTHER_HEAD) + f" -f sha={HEAD}"}),
        )
        for entry, kwargs in entries:
            for policy in POLICIES:
                with self.subTest(entry=entry, policy=policy, kwargs=kwargs):
                    self.check(entry, merge_result(head=OTHER_HEAD), policy, "MERGE_HEAD_MISMATCH", **kwargs)

    def test_pin_like_body_values_are_not_read_as_merge_pins(self):
        """Dữ liệu của cờ và đối số sau -- không tạo pin giả; pin thiếu vẫn không auto-allow."""
        commands = (
            CLI + " --body --match-head-commit=example",
            CLI + " --body=--match-head-commit=example",
            CLI.replace("--match-head-commit ", "--match-head-commit=") + " --body --match-head-commit=example",
            CLI + " -sb --match-head-commit=example",
            CLI + " -- --match-head-commit=example",
            "gh pr merge 7 --squash --match-head-commit",
        )
        for command in commands:
            with self.subTest(command=command):
                raw = self.raw("cli", merge_result(), command=command)
                unverified = command.endswith(" --match-head-commit") or " -- " in command
                self.assertEqual(
                    (raw["decision"], guard.decide(raw).code), ("ask", "UNVERIFIED" if unverified else "OTHER_ASK"), raw
                )
                self.assertEqual(guard.apply_policy(raw)["decision"], "deny" if unverified else "", raw)

    def test_new_codes_are_carried_from_source_not_reason_text(self):
        codes = {"MERGE_INELIGIBLE", "MERGE_HEAD_MISMATCH"}
        self.assertFalse(codes & {code for _, code in guard.REASON_CODES})
        for result, code, entries in (
            (merge_result("wait", reasons=["CI pending"]), "MERGE_INELIGIBLE", ENTRIES),
            (
                merge_result(head=OTHER_HEAD, reasons=["Nội dung giải thích đã đổi"]),
                "MERGE_HEAD_MISMATCH",
                BOUND_ENTRIES,
            ),
        ):
            for entry in entries:
                with (
                    self.subTest(entry=entry, code=code),
                    mock.patch.object(guard, "REASON_CODES", ()),
                    mock.patch.object(guard, "EXTERNAL_ASK", "Thông báo đã đổi ngôn ngữ"),
                ):
                    self.check(entry, result, "default", code)

    def test_nested_shell_and_container_preserve_code(self):
        commands = (
            f"bash -c '{CLI}'",
            f"sh -c '{CLI}'",
            f"echo $({CLI})",
            f"bash <<'EOF'\n{CLI}\nEOF",
            f"true && {CLI}",
            f"{CLI}; printf done",
            f"docker exec app {CLI}",
            f"docker exec app sh -c '{CLI}'",
            f"docker run --rm alpine {CLI}",
        )
        for command in commands:
            for result, code in (
                (merge_result("wait"), "MERGE_INELIGIBLE"),
                (merge_result(head=OTHER_HEAD), "MERGE_HEAD_MISMATCH"),
            ):
                for policy in POLICIES:
                    with self.subTest(command=command, code=code, policy=policy):
                        self.check("cli", result, policy, code, command=command)

    def test_existing_deny_wins_over_new_merge_ask(self):
        denied = "gh pr merge 7 --auto --squash"
        for command in (f"{CLI}; {denied}", f"{denied}; {CLI}"):
            for policy in POLICIES:
                with self.subTest(command=command, policy=policy):
                    raw = self.raw("cli", merge_result("wait"), command=command)
                    final = raw if policy == "strict" else guard.apply_policy(raw)
                    self.assertEqual(final["decision"], "deny", final)
                    self.assertEqual(guard.decide(raw).code, "AUTO_MERGE_ENABLE", raw)

    def test_new_merge_ask_does_not_weaken_existing_shell_budget_deny(self):
        """Lỗi cú pháp độc lập vẫn deny ở strict, dù merge đã có một mã chặn mặc định."""
        for result in (merge_result("wait"), merge_result(head=OTHER_HEAD)):
            with mock.patch.object(guard, "merge_check", return_value=result):
                _, reason = guard.gh_pr_merge_rule(["7", "--match-head-commit", HEAD], self.root)
            with (
                self.subTest(result=result),
                mock.patch.object(guard, "_argv_shell_why", return_value="cú pháp chưa xác minh"),
                self.assertRaises(guard.ScanTooComplex),
            ):
                guard._argv_shell_check("printf ok", ["printf", "ok"], True, [reason], {}, self.root, self.root)
            raw = self.raw("cli", result)
            rough = guard._rough_budget(raw, "printf ok")
            self.assertEqual((rough["decision"], rough["code"]), ("deny", "BUDGET"))

    def test_existing_block_code_wins_when_independent_merge_reasons_are_combined(self):
        other = CLI.replace("merge 7 ", "merge 8 ")
        for command in (f"{CLI}; {other}", f"{other}; {CLI}"):
            with (
                self.subTest(command=command),
                mock.patch.object(
                    guard,
                    "merge_check",
                    side_effect=lambda selector, root: (
                        merge_result("wait") if selector == ["7"] else merge_result("review", review="missing")
                    ),
                ),
            ):
                raw = guard.bash_decision(command, self.root)
                self.assertEqual(guard.decide(raw).code, "REVIEW_MISSING", raw)
                self.assertEqual(guard.apply_policy(raw)["decision"], "deny", raw)

    def test_code_does_not_leak_to_following_command(self):
        for entry in ENTRIES:
            with self.subTest(entry=entry):
                self.check(entry, merge_result("wait"), "default", "MERGE_INELIGIBLE")
                safe = self.raw("core", merge_result(), command="printf done")
                self.assertEqual(guard.apply_policy(safe)["decision"], "", safe)
                self.assertEqual(guard.decide(safe).code, "NONE", safe)
                following = self.raw(entry, merge_result())
                expected = ("ask", "UNVERIFIED") if entry == "mcp" else ("allow", "RULE_ALLOW")
                self.assertEqual((following["decision"], guard.decide(following).code), expected)

    def test_unknown_verdict_is_ineligible_when_pr_is_verified(self):
        for verdict in ("future-state", ""):
            with self.subTest(verdict=verdict):
                self.check("cli", merge_result(verdict), "default", "MERGE_INELIGIBLE")

    def test_core_adapter_outputs_deny_even_when_host_requests_strict(self):
        """Adapter không có ask; core giữ hợp đồng deny/exit 2 ở cả hai biến môi trường."""
        for policy in POLICIES:
            for verdict in VERDICTS:
                payload = {"tool": "exec_command", "command": CLI, "project_dir": self.root}
                out, err = io.StringIO(), io.StringIO()
                with (
                    self.subTest(policy=policy, verdict=verdict),
                    mock.patch.dict(os.environ, {"XT_GUARD_POLICY": policy}),
                    mock.patch.object(guard, "merge_check", return_value=merge_result(verdict)),
                    mock.patch.object(sys, "argv", ["guard.py", "core"]),
                    mock.patch.object(sys, "stdin", io.StringIO(json.dumps(payload))),
                    mock.patch.object(sys, "stdout", out),
                    mock.patch.object(sys, "stderr", err),
                ):
                    rc = guard.main()
                result = json.loads(out.getvalue())
                self.assertEqual((rc, result["decision"], result["code"]), (2, "deny", "MERGE_INELIGIBLE"))
                self.assertTrue(err.getvalue())


if __name__ == "__main__":
    unittest.main()
