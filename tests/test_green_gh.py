"""T-3917 (PLAN-harden-2026-11-17 đợt 3, ADR-0080, D-415): nợ review 🟢 của luật lệnh `gh` trong guard.

Mỗi ID một lớp: ca DENY (lỗ hổng bị chặn như dạng trơn tương ứng, hay đối chứng vẫn chặn) và ca ALLOW đối chứng (dạng
trợ giúp/lệnh lành gh thật chạy vô hại không bị chặn oan)."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
import unittest.mock as mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

os.environ.setdefault("XT_GUARD_PHASE", "harden")
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
import guard

SHA = "a" * 40
MARK = "<!-- xt-review v1 head=" + SHA + " verdict=clean -->"
MERGE_OK = {
    "host": "github.com",
    "repo": "o/r",
    "pr": 7,
    "verdict": "merge",
    "hard": [],
    "head": SHA,
    "eligible": True,
    "reasons": ["ok"],
}


def decide(cmd: str, cwd: str = str(ROOT)) -> dict:
    # Nhánh hiện tại ghim về `feat` như tests/test_guard_strict.py: quyết định không phụ thuộc nhánh checkout
    with (
        mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(ROOT), "XT_GUARD_POLICY": ""}),
        mock.patch.object(guard, "_current_branch", return_value="feat"),
    ):
        return guard.apply_policy(guard.bash_decision(cmd, str(ROOT), cwd))


class _Case(unittest.TestCase):
    def setUp(self) -> None:
        # AUD-TEST-109: merge-check giả (xanh, như MergeDeleteBranchTest) — không gọi `xt.py merge-check`/`gh` thật của
        # repo đang checkout; quyết định không phụ thuộc mạng hay trạng thái PR thật.
        patcher = mock.patch.object(guard, "merge_check", return_value=MERGE_OK)
        self.merge_check = patcher.start()
        self.enterContext(mock.patch.dict(os.environ, {"GH_REPO": "github.com/o/r", "GH_HOST": "github.com"}))
        self.addCleanup(patcher.stop)

    def assert_code(self, cmds: tuple, code: str, cwd: str = str(ROOT)) -> None:
        for cmd in cmds:
            with self.subTest(cmd=cmd):
                result = decide(cmd, cwd)
                self.assertEqual((result["decision"], result["code"]), ("deny", code), result["reason"])

    def assert_runs(self, cmds: tuple, cwd: str = str(ROOT)) -> None:
        for cmd in cmds:
            with self.subTest(cmd=cmd):
                result = decide(cmd, cwd)
                self.assertNotEqual(result["decision"], "deny", result["reason"])


class ReleaseSignHelpTest(_Case):  # AUD-HAR-342
    def setUp(self) -> None:
        super().setUp()
        # Repo khung bật `release_signoff: agent` (#625): ghim khoá tắt để test xét luật GO_SIGN, không phụ thuộc xt.yaml thật
        patcher = mock.patch.object(guard, "agent_release_signoff", return_value=False)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_deny_sign_forms(self):
        self.assert_code(
            (
                "python3 scripts/xt.py release-sign",
                "python3 scripts/xt.py release-sign --he",  # viết tắt argparse: không miễn (chặt)
                "python3 scripts/xt.py release-sign -- --help",
                "python3 scripts/xt.py release-sign --help --bogus",
                'python3 "$XT" release-sign --help',  # xt mờ
            ),
            "GO_SIGN",
        )

    def test_allow_help(self):
        self.assert_runs(
            (
                "python3 scripts/xt.py release-sign --help",
                "python3 scripts/xt.py release-sign -h",
                "python3 scripts/xt.py release-sign --note x --help",
            )
        )
        self.assertFalse(guard._release_sign_help(["python3", "scripts/xt.py", "release-sign"], str(ROOT), str(ROOT)))


class RefSingularTest(_Case):  # AUD-SEC-562
    def test_deny(self):
        self.assert_code(
            (
                "gh api -X DELETE repos/o/r/git/ref/heads/x",
                "gh api -X DELETE repos/o/r/git/ref/tags/v1",
                'gh api graphql -f query=\'mutation { updateRef(input: {refId: "x", oid: "a", force: true}) { a } }\'',
            ),
            "REMOTE_DELETE",
        )
        self.assert_code(("gh api -X DELETE repos/o/r/git/ref/heads/main",), "DESTROY")
        self.assert_code(("gh api -X PATCH repos/o/r/git/ref/heads/main -F sha=" + SHA,), "PUSH_MAIN")

    def test_allow(self):
        # nhánh phiên trên repo `origin` (AUD-SEC-560)
        with mock.patch.object(guard, "_origin_repo", return_value="o/r"):
            self.assert_runs(("gh api repos/o/r/git/ref/heads/x", "gh api -X DELETE repos/o/r/git/ref/heads/feat"))


class MergeDeleteBranchTest(_Case):  # AUD-SEC-565
    def test_deny(self):
        with mock.patch.object(guard, "merge_check", return_value=MERGE_OK):
            self.assert_code(
                (
                    "gh pr merge 12 --delete-branch",
                    "gh pr merge 12 -sd",
                    "gh pr merge 12 --squash --delete-branch=false",  # mọi giá trị tính — như `pr close`
                    "gh pr -R o/r merge 12 -d",
                    f"gh pr merge 12 --squash --match-head-commit {SHA} -d",
                    "gh pr merge 12 -d -b --help",  # `--help` là thân commit, không phải trợ giúp
                ),
                "REMOTE_DELETE",
            )

    def test_allow(self):
        with mock.patch.object(guard, "merge_check", return_value={**MERGE_OK, "pr": 12}):
            result = decide(f"gh pr merge 12 --squash --match-head-commit {SHA}")
            self.assertEqual(result["decision"], "allow", result["reason"])
            self.assert_runs(("gh pr merge 12 -d --help", f"gh pr merge 12 -b -d --squash --match-head-commit {SHA}"))
        self.assertNotIn("--delete-branch", guard.MERGE_ALLOW_FLAGS)


class ShortHelpEqualsTest(_Case):  # AUD-HAR-356
    def test_deny(self):
        self.assert_code(
            ("gh pr close 12 -d", "gh pr close 12 -d=h", "gh pr close 12 -d -c -h=false", "gh pr close 12 -dc -h=x"),
            "REMOTE_DELETE",
        )

    def test_allow(self):
        self.assert_runs(("gh pr close 12 -d -h=false", "gh pr close 12 -dh=false", "gh pr close 12 -h= -d"))


class FlagMergeHelpTest(_Case):  # AUD-HAR-357
    def test_deny(self):
        self.assert_code(("gh pr -R o/r merge 12", "gh pr -R o/r merge 12 -b --help"), "UNVERIFIED")
        self.assert_code(("gh pr -R o/r merge 12 --auto --help=false",), "AUTO_MERGE_ENABLE")

    def test_allow(self):
        self.assert_runs(("gh pr -R o/r merge 12 --help", "gh pr -R o/r merge 12 -h", "gh -R o/r pr merge 12 -sh"))


class LeadingHelpTest(_Case):  # AUD-HAR-360
    def test_deny(self):
        self.assert_code(
            (
                "gh -X DELETE api repos/o/r",
                "gh -H --help -X DELETE api repos/o/r",  # `--help` là giá trị của `-H`
                "gh repo --help=false edit --visibility public",
                "gh repo edit -h --help --visibility public",  # `-h` của `repo edit` là homepage, ăn `--help`
            ),
            "DESTROY",
        )
        # X=-H lúc chạy: `--help` thành giá trị header — không miễn trợ giúp (đường api có biến: BUDGET)
        self.assert_code(('gh api -X DELETE repos/o/r "$X" --help',), "BUDGET")
        self.assertFalse(guard._gh_help_reading(["api", "-X", "DELETE", "repos/o/r", "$X", "--help"]))
        self.assert_code(('gh pr -R o/r merge 12 "$X" --help',), "UNVERIFIED")
        self.assert_code(("gh auth token --help",), "RULE_DENY")  # lệnh không có bảng cờ: không miễn

    def test_allow(self):
        self.assert_runs(
            (
                "gh --help -X DELETE api repos/o/r",
                "gh repo --help edit --visibility public",
                "gh api -X DELETE repos/o/r --help",
                "gh cache delete --all -h",
                "gh auth status --show-token --help",
            )
        )
        self.assertFalse(guard._gh_help_reading(["alias", "set", "x", "y", "--help"]))


class CommitMessageMentionsGhTest(_Case):  # AUD-HAR-364
    def setUp(self) -> None:
        super().setUp()
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        Path(self.d, "r.md").write_text(MARK + "\n", encoding="utf-8")

    def test_deny(self):
        self.assert_code(
            (
                "git commit -m ok && gh pr comment 5 --body-file r.md",
                "gh pr list --search review && gh pr comment 5 --body-file r.md",
                'git commit -m "x $(gh pr comment 5 --body-file r.md)"',  # thay lệnh trong message vẫn xét
            ),
            "REVIEW_FORGE",
            self.d,
        )
        # lệnh bọc `gh` (AUD-SEC-180) và cờ toàn cục của git vẫn là chữ xét; chỉ message bị bỏ
        self.assertTrue(guard._gh_wrapped(["sh", "-c", "gh pr comment 5 -F -"]))
        self.assertTrue(guard._gh_wrapped(["git", "-c", "alias.x=!gh pr comment 5 -F -", "commit", "-m", "x"]))
        self.assertEqual(
            guard._commit_text_dropped(["git", "-c", "alias.x=!gh pr comment 5", "commit", "-m", "gh pr review"]),
            ["git", "-c", "alias.x=!gh pr comment 5", "commit"],
        )

    def test_allow(self):
        self.assert_runs(
            (
                'git commit -m "docs: gh pr flow, reviewer must review (#$PR)"',
                'git commit -m "fix: gh -F field before api ($N)"',
                'git commit --message="fix: gh -F field before api ($N)"',
                'git commit -am "fix: gh -F field before api ($N)" < r.md',
                'gh pr list --search "review:approved author:$U" < r.md',  # lệnh chỉ đọc: giá trị cờ không đăng
                "gh pr view 5 --comments --jq '.body | test(\"review\")' < r.md",
            ),
            self.d,
        )
        self.assertTrue(guard._gh_read_only_cmd(["gh", "-R", "o/r", "issue", "list", "--search", "comment"]))
        self.assertFalse(guard._gh_read_only_cmd(["gh", "pr", "list$Z", "--search", "review"]))
        self.assertFalse(guard._gh_wrapped(["git", "commit", "-m", "docs: gh pr flow, reviewer must review (#$PR)"]))
        self.assertEqual(guard._commit_text_dropped(["echo", "gh pr review"]), ["echo", "gh pr review"])


class QuotedSeparatorHeredocTest(_Case):  # AUD-HAR-365
    def test_deny(self):
        self.assert_code(
            (
                "gh pr --title 'feat: a; b' create --body-file - <<'EOF'\nClaude-Session: x\nEOF",
                "gh pr --title \"feat: a | b\" create --body-file - <<'EOF'\nClaude-Session: x\nEOF",
                'gh pr --title "a \\" && b" create --body-file - <<\'EOF\'\nClaude-Session: x\nEOF',
            ),
            "RULE_DENY",
        )

    def test_allow(self):
        self.assert_runs(
            (
                "gh pr --title 'feat: a; b' create --body-file - <<'EOF'\nok\nEOF",
                "echo 'gh; pr' ; cat <<'EOF'\nClaude-Session: x\nEOF",
                # heredoc của lệnh khác cùng chuỗi với `gh pr create`: không phải thân PR
                "gh pr create --title 'feat: a; b' -b ok; cat <<'EOF'\nClaude-Session: x\nEOF",
            )
        )
        self.assertEqual(guard._blank_quoted_seps('a;\'b;c\'\\;"d|e\\"&"'), 'a;\'b c\'\\;"d e\\" "')


class RedirectReadingTest(_Case):  # AUD-HAR-366 (dạng `gh 2>&1 pr view`)
    def test_deny(self):
        self.assert_code(("gh 2>&1 alias set x y", 'gh ">" pr view', "gh 2>/dev/null close"), "BUDGET")
        self.assert_code(("gh 2>&1 pr close 12 -d",), "REMOTE_DELETE")

    def test_allow(self):
        self.assert_runs(("gh 2>&1 pr view", "gh 2>/dev/null pr view", "gh pr view 2>&1"))
        # AUD-SEC-016 + AUD-TEST-109: merge-check xanh → merge trơn ghim head được allow; có chuyển hướng thì không còn
        # là dạng trơn — hỏi (OTHER_ASK), không allow theo luật merge, không bị chặn oan.
        plain = decide(f"gh pr merge 7 --squash --match-head-commit {SHA}")
        self.assertEqual((plain["decision"], plain["code"]), ("allow", "RULE_ALLOW"), plain["reason"])
        redirected = decide(f"gh pr merge 7 --squash --match-head-commit {SHA} >/dev/null")
        self.assertEqual(redirected["code"], "OTHER_ASK", redirected["reason"])
        self.assertNotIn(redirected["decision"], ("allow", "deny"), redirected["reason"])
        self.assertEqual(self.merge_check.call_count, 2)  # cả hai đi qua merge-check giả, không gọi GitHub


class TokenPrintTest(_Case):  # AUD-SEC-589
    def test_deny(self):
        self.assert_code(
            (
                "gh auth git-credential get",
                "gh auth git-credential",
                "gh config get oauth_token -h github.com",
                "gh config get -h github.com oauth_token",
            ),
            "RULE_DENY",
        )

    def test_allow(self):
        self.assert_runs(("gh config get editor", "gh config get git_protocol -h github.com", "gh auth status"))


class LabelSlashTest(_Case):  # AUD-SEC-601
    def test_deny(self):
        self.assert_code(
            ("gh api -X DELETE repos/o/r/labels/kind%2Fbug", "gh api --method DELETE repos/o/r/labels/a%2Fb%2Fc"),
            "DESTROY",
        )

    def test_allow(self):
        self.assert_runs(
            ("gh api repos/o/r/labels/kind%2Fbug", "gh api -X PATCH repos/o/r/labels/kind%2Fbug -f color=fff")
        )


class SuspectedPathsTest(_Case):  # AUD-SEC-603
    def test_deny(self):
        self.assert_code(
            ("gh api -X DELETE repositories/123", "gh api -X PATCH repositories/9 -F archived=true"), "DESTROY"
        )
        self.assert_code(("gh api -X DELETE repositories/123/git/refs/heads/x",), "REMOTE_DELETE")
        self.assert_code(
            (
                "gh api -X PATCH repositories/123/git/refs/heads/x -F sha=a -F force=true",
                "gh api -X PATCH repos/o/r/git/refs/heads/x?force=true -F sha=a",
                "gh api -X PATCH 'repos/o/r/git/refs/heads/x?a=1&force=false#f' -F sha=a",
                "gh api -X PATCH repos/o/r/git/refs/heads/x -F sha=a -f force=false",
                "gh api -X PATCH repos/o/r/git/refs/heads/x -F sha=a --raw-field=force=false",
                "gh api -X PATCH repos/o/r/git/refs/heads/x -F sha=a -F force=False",
                "gh api -X PATCH repos/o/r/git/refs/heads/x -F sha=a -F 'force= false'",
            ),
            "RULE_DENY",
        )

    def test_allow(self):
        self.assert_runs(
            (
                "gh api repositories/123",
                "gh api repositories/123/git/refs/heads/x",
                "gh api -X PATCH repos/o/r/git/refs/heads/x -F sha=a",
                "gh api -X PATCH repos/o/r/git/refs/heads/x -F sha=a -F force=false",
                "gh api -X PATCH repos/o/r/git/refs/heads/x?a=1 -F sha=a --field=force=false",
            )
        )


if __name__ == "__main__":
    unittest.main()
