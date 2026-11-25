"""Exercise merge target binding with real Git checkouts and a local HTTP route double."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from contextlib import chdir
from pathlib import Path
from unittest import main, mock
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_merge import REAL_RUN, mark, pr
from test_xt_cli import TmpRepoCase, run_main, xt

HOST = "git.example"
PUBLIC = "github.com"
SLUG = "o/r"
PR = "7"


def pr_url(host=HOST, slug=SLUG):
    return f"https://{host}/{slug}/pull/{PR}"


class RouteDouble:
    """Duplicate a PR fixture across two hosts so mistaken routes stay visible."""

    def __init__(self, head, base):
        self.head = head
        self.base = base
        self.file = "src/ordinary.py"
        self.comments = []
        self.checks = ["success"]
        self.calls = []
        self.merged = False
        self.merged_sha = "a" * 40
        self.association = "OWNER"
        self.permissions = {PUBLIC: "write", HOST: "read"}
        self.open_prs = [{"number": int(PR)}]

    def pull(self, host, slug):
        merged = self.merged
        return {
            "html_url": pr_url(host, slug),
            "number": int(PR),
            "title": "fix: bind merge target",
            "state": "closed" if merged else "open",
            "merged": merged,
            "merge_commit_sha": self.merged_sha if merged else None,
            "draft": False,
            "mergeable": True,
            "mergeable_state": "clean",
            "head": {"sha": self.head, "repo": {"full_name": slug}},
            "base": {"ref": "main", "sha": self.base, "repo": {"full_name": slug, "default_branch": "main"}},
            "author_association": self.association,
            "user": {"login": "target-binding-fixture-member"},
            "labels": [],
        }

    def check_result(self):
        value = self.checks.pop(0) if len(self.checks) > 1 else self.checks[0]
        return {
            "check_runs": [{"name": "test", "status": "completed" if value else "in_progress", "conclusion": value}]
        }

    def payload(self, host, repo, path, page):
        if page > 1:
            return []
        if path == f"/pulls/{PR}":
            return self.pull(host, repo)
        if path == f"/commits/{self.head}/check-runs":
            return self.check_result()
        if path.endswith("/permission"):
            return {"permission": self.permissions[host]}
        return {
            "/pulls": self.open_prs,
            f"/pulls/{PR}/reviews": [],
            f"/pulls/{PR}/files": [{"filename": self.file, "additions": 1, "deletions": 0}],
            f"/issues/{PR}/comments": self.comments,
            "/rules/branches/main": [],
            "/branches/main": {},
            f"/commits/{self.head}/status": {"statuses": []},
            f"/commits/{self.head}": {"parents": []},
            f"/compare/{self.base}...{self.head}": {"merge_base_commit": {"sha": self.base}},
        }[path]

    def respond(self, argv, **kwargs):
        if argv[0] == "git":
            return REAL_RUN(argv, **kwargs)
        if argv[:2] != ["gh", "api"]:
            raise AssertionError(f"unexpected command: {argv}")
        path = next(arg for arg in argv if arg.startswith("repos/"))
        host = argv[argv.index("--hostname") + 1] if "--hostname" in argv else ""
        method = argv[argv.index("-X") + 1] if "-X" in argv else "GET"
        self.calls.append((method, host, urlsplit(path).path, argv))
        _, owner, repo, suffix = (urlsplit(path).path + "/").split("/", 3)
        repo_name = SLUG if (owner, repo) == ("{owner}", "{repo}") else f"{owner}/{repo}"
        route = "/" + suffix.rstrip("/") if suffix else ""
        if method == "PUT" and route == f"/pulls/{PR}/merge":
            self.merged = True
        if method != "GET":
            return subprocess.CompletedProcess(argv, 0, "{}", "")
        page = int(parse_qs(urlsplit(path).query).get("page", ["1"])[0])
        value = self.payload(host or os.environ.get("GH_HOST") or PUBLIC, repo_name, route, page)
        return subprocess.CompletedProcess(argv, 0, json.dumps(value), "")


class MergeTargetBindingTest(TmpRepoCase):
    CONFIG = "merge_autonomy: L3\nmerge_review: optional\nmerge_hard_exceptions: auto\n"

    def setUp(self):
        super().setUp()
        self.init_repo()
        env = {k: v for k, v in os.environ.items() if not k.startswith(("GH_", "GITHUB_", "XT_STEWARD_", "XT_CI_"))}
        self.enterContext(mock.patch.dict(os.environ, {**env, "CLAUDE_PROJECT_DIR": str(self.repo)}, clear=True))
        self.basis = self.commit_files(
            {"xt.yaml": self.CONFIG, xt.RELEASE_WORKFLOW_FILE: "on: workflow_dispatch\n"}, 1700000000
        )
        self.git("update-ref", "refs/remotes/origin/main", self.basis)
        self.head = self.commit_files({"README.md": "candidate\n"}, 1700000001)
        self.git("remote", "add", "origin", f"https://{HOST}/{SLUG}.git")
        self.gh = RouteDouble(self.head, self.basis)
        self.enterContext(mock.patch.object(xt.subprocess, "run", side_effect=self.gh.respond))

    def assert_target_routes(self, slug=SLUG):
        self.assertTrue(self.gh.calls)
        for _, host, path, _ in self.gh.calls:
            with self.subTest(host=host, path=path):
                self.assertEqual(host, HOST)
                self.assertTrue(path.startswith(f"repos/{slug}/"), path)

    def assert_pinned_next(self, result, slug=SLUG):
        rc, out, err = result
        self.assertEqual(rc, 0, err)
        data = json.loads(out)
        self.assertEqual(data["action"], "merge", data)
        argv = shlex.split(data["do"])
        self.assertEqual(argv[argv.index("--hostname") + 1 :][:2], [HOST, f"repos/{slug}/pulls/{PR}/merge"])
        self.assertIn(f"sha={self.head}", argv)

    def test_numeric_selector_reads_authoritative_enterprise_origin_first(self):
        self.assert_pinned_next(run_main("pr", "next", "--pr", PR, "--json"))
        self.assertEqual(self.gh.calls[0][:3], ("GET", HOST, f"repos/{SLUG}/pulls/{PR}"))
        self.assert_target_routes()

    def test_origin_protocols_accept_and_normalize_checkout_target(self):
        for url in ("https://Git.Example/O/R.git/", "ssh://git@Git.Example/O/R.git", "git@Git.Example:O/R.git"):
            with self.subTest(url=url):
                self.git("remote", "set-url", "origin", url)
                self.gh.calls.clear()
                self.assert_pinned_next(run_main("pr", "next", "--pr", PR, "--json"))
                self.assert_target_routes()

    def test_invalid_origin_syntax_is_rejected_before_reads(self):
        urls = (
            "https://git@git.example/o/r",
            "ssh://git.example/o/r",
            "ssh://alice@git.example/o/r",
            "alice@git.example:o/r",
            "ssh://git:example@git.example/o/r",
            "https://git.example:443/o/r",
            "ssh://git@git.example:22/o/r",
            "https://git.example/o/r?ref=main",
            "https://git.example/o/r#main",
            "https://-git.example/o/r",
            "https://git..example/o/r",
            "https://git.example/o/..",
            "https://git.example/o/.git",
            "https://git.example/o/r/extra",
        )
        for url in urls:
            with self.subTest(url=url):
                self.git("remote", "set-url", "origin", url)
                rc, out, err = run_main("pr", "next", "--pr", PR, "--json")
                self.assertEqual(rc, 2, out + err)
                self.assertIn("không xác minh được host/repo của origin", err)
                self.assertEqual(self.gh.calls, [])

    def test_checkout_policy_does_not_authorize_a_foreign_selector(self):
        for url in (pr_url("another.example"), pr_url(HOST, "o/other")):
            with self.subTest(url=url):
                rc, out, err = run_main("pr", "next", "--pr", url, "--json")
                self.assertEqual(rc, 2, out + err)
                self.assertEqual(self.gh.calls, [])

    def test_checkout_without_origin_cannot_authorize_a_live_selector(self):
        self.git("remote", "remove", "origin")
        rc, out, err = run_main("pr", "next", "--pr", pr_url(), "--json")
        self.assertEqual(rc, 2, out + err)
        self.assertEqual(self.gh.calls, [])

    def test_checkout_with_multiple_origin_values_is_unverified(self):
        self.git("config", "--add", "remote.origin.url", f"https://{PUBLIC}/{SLUG}.git")
        rc, out, err = run_main("pr", "next", "--pr", PR, "--json")
        self.assertEqual(rc, 2, out + err)
        self.assertEqual(self.gh.calls, [])

    def test_numeric_zero_and_detached_branch_require_an_explicit_valid_pr(self):
        rc, out, err = run_main("pr", "next", "--pr", "0", "--json")
        self.assertEqual(rc, 2, out + err)
        self.assertIn("lớn hơn 0", err)
        self.git("checkout", "--detach", self.head)
        rc, out, err = run_main("pr", "next", "--json")
        self.assertEqual(rc, 2, out + err)
        self.assertIn("không có nhánh hiện tại", err)
        self.assertEqual(self.gh.calls, [])

    def test_branch_query_binds_owner_host_and_requires_valid_result_number(self):
        self.assert_pinned_next(run_main("pr", "next", "--pr", "feature/x", "--json"))
        method, host, path, args = self.gh.calls[0]
        self.assertEqual((method, host, path), ("GET", HOST, f"repos/{SLUG}/pulls"))
        self.assertEqual(parse_qs(urlsplit(args[-1]).query)["head"], ["o:feature/x"])
        self.gh.calls.clear()
        self.gh.open_prs = [{"number": False}]
        rc, out, err = run_main("pr", "next", "--pr", "feature/x", "--json")
        self.assertEqual(rc, 2, out + err)
        self.assertIn("số PR của nhánh không hợp lệ", err)
        self.assertTrue(all(path == f"repos/{SLUG}/pulls" for _, _, path, _ in self.gh.calls))

    def test_merge_check_waits_without_a_complete_live_pin(self):
        self.gh.head = "short"
        rc, out, err = run_main("merge-check", "--pr", PR, "--json")
        self.assertEqual(rc, 1, out + err)
        data = json.loads(out)
        self.assertEqual((data["verdict"], data["eligible"], data["next"]), ("wait", False, ""))
        self.assert_target_routes()

    def test_steward_apply_fails_without_a_complete_live_pin(self):
        self.gh.head = "short"
        rc, out, err = run_main("pr", "steward", "--pr", PR, "--apply", "--json")
        self.assertEqual(rc, 1, out + err)
        (data,) = json.loads(out)
        self.assertEqual((data["action"], data["applied"], data["do"]), ("error", False, ""))
        self.assertEqual(data["why"], "chưa xác minh đủ đích và head của PR")
        self.assert_target_routes()
        self.assertTrue(all(method == "GET" for method, _, _, _ in self.gh.calls), self.gh.calls)

    def test_steward_label_merge_ci_and_release_stay_on_bound_host(self):
        policy = self.CONFIG.replace("optional", "required") + "merge_risk_paths: VERSION\n"
        self.basis = self.commit_files({"xt.yaml": policy}, 1700000002)
        self.git("update-ref", "refs/remotes/origin/main", self.basis)
        self.head = self.commit_files({"VERSION": "1.2.3\n"}, 1700000003)
        self.gh.head, self.gh.base = self.head, self.basis
        self.gh.file = "VERSION"
        self.gh.comments = [mark(self.head, "clean", "2026-10-19T02:00:00Z")]
        with mock.patch.dict(os.environ, {"GH_HOST": HOST, "GITHUB_ACTIONS": "true", "XT_STEWARD_UPDATE": "off"}):
            rc, out, err = run_main("pr", "steward", "--repo", SLUG, "--pr", PR, "--apply", "--json")
        self.assertEqual(rc, 0, out + err)
        self.assertTrue(json.loads(out)[0]["applied"], out)
        mutations = [c for c in self.gh.calls if c[0] != "GET"]
        self.assertEqual(
            [(method, path) for method, _, path, _ in mutations],
            [
                ("POST", f"repos/{SLUG}/issues/{PR}/labels"),
                ("PUT", f"repos/{SLUG}/pulls/{PR}/merge"),
                ("POST", f"repos/{SLUG}/actions/workflows/ci.yml/dispatches"),
                ("POST", f"repos/{SLUG}/actions/workflows/release-tag.yml/dispatches"),
            ],
        )
        self.assertEqual(self.gh.calls[-2][:3], ("GET", HOST, f"repos/{SLUG}/pulls/{PR}"))
        self.assertIn(f"sha={self.head}", mutations[1][3])
        self.assertIn(f"inputs[sha]={self.gh.merged_sha}", mutations[-1][3])
        self.assert_target_routes()

    def test_wait_hint_preserves_verified_pr_selector(self):
        self.gh.checks = [None]
        rc, out, err = run_main("pr", "next", "--pr", pr_url(), "--json")
        self.assertEqual(rc, 0, out + err)
        data = json.loads(out)
        self.assertEqual(data["action"], "wait")
        self.assertIn(pr_url(), data["do"])
        self.assert_target_routes()

    def test_watch_reuses_enterprise_selector_at_each_read_and_handoff(self):
        self.gh.checks = [None, "success"]
        with mock.patch.object(xt.time, "sleep"):
            rc, out, err = run_main("merge-watch", "--pr", pr_url())
        self.assertEqual(rc, 0, out + err)
        self.assertIn("WAIT", out)
        self.assertIn("pr next → MERGE", out)
        self.assertIn(f"--hostname {HOST} repos/{SLUG}/pulls/{PR}/merge", out)
        reads = [call[:3] for call in self.gh.calls if call[2] == f"repos/{SLUG}/pulls/{PR}"]
        self.assertEqual(reads, [("GET", HOST, f"repos/{SLUG}/pulls/{PR}")] * 3)
        self.assert_target_routes()

    def test_watch_retries_a_rejected_first_response_on_the_resolved_pr(self):
        reply = self.gh.payload
        first = True

        def payload(host, repo, path, page):
            nonlocal first
            if path == "/pulls/7" and first:
                first = False
                self.gh.open_prs = [{"number": 8}]
                partial = reply(host, repo, path, page)
                partial.pop("html_url")
                return {**partial, "number": 8}
            if path == "/pulls/8":
                return {**reply(host, repo, "/pulls/7", page), "number": 8, "html_url": pr_url()[:-1] + "8"}
            return reply(host, repo, path.replace("/8/", "/7/"), page)

        self.gh.checks = [None, "success"]
        with mock.patch.object(self.gh, "payload", side_effect=payload), mock.patch.object(xt.time, "sleep"):
            rc, out, err = run_main("merge-watch")
        self.assertEqual(rc, 0, out + err)
        self.assertIn("lỗi đọc PR (1/3)", out)
        self.assertIn("WAIT · PR #7", out)
        self.assertIn(f"--hostname {HOST} repos/{SLUG}/pulls/7/merge", out)
        paths = [path for _, _, path, _ in self.gh.calls if path.rsplit("/", 1)[-1] in {"pulls", "7", "8"}]
        self.assertEqual(paths, [f"repos/{SLUG}/pulls", *([f"repos/{SLUG}/pulls/7"] * 4)])
        self.assert_target_routes()

    def test_pr_read_rejects_partial_conflicting_identity_before_details(self):
        self.gh.head = "short"
        for changes in (
            {"html_url": None, "number": 8},
            {"html_url": pr_url("another.example")},
            {"html_url": None, "base": {"repo": {"full_name": "o/other"}}},
            {"html_url": pr_url(slug="o/other") + "/changes"},
        ):
            with self.subTest(changes=changes):
                pull = {**self.gh.pull(HOST, SLUG), **changes}
                self.gh.calls.clear()
                with mock.patch.object(self.gh, "pull", return_value=pull):
                    rc, out, err = run_main("pr", "next", "--pr", PR, "--json")
                self.assertEqual(rc, 2, out + err)
                self.assertIn("Đích PR trả về khác host, repo hoặc số PR", err)
                self.assertEqual([call[:3] for call in self.gh.calls], [("GET", HOST, f"repos/{SLUG}/pulls/{PR}")])

    def test_pending_pr_wait_hint_uses_resolved_route_without_verified_url(self):
        pull = self.gh.pull(HOST, SLUG)
        pull.pop("html_url")
        self.gh.checks = [None]
        with mock.patch.object(self.gh, "pull", return_value=pull):
            rc, out, err = run_main("pr", "next", "--pr", "feature/x", "--json")
        self.assertEqual(rc, 0, err)
        data = json.loads(out)
        self.assertEqual((data["pr"], data["action"]), (7, "wait"))
        self.assertIn(pr_url(), data["do"])
        self.assertNotIn("merge_intent", data)
        self.assert_target_routes()

    def test_member_write_permission_cache_isolated_by_host(self):
        self.gh.association = "MEMBER"
        with mock.patch.dict(xt._WRITER_CACHE, clear=True):
            self.git("remote", "set-url", "origin", f"https://{PUBLIC}/{SLUG}.git")
            rc, out, err = run_main("pr", "steward", "--pr", pr_url(PUBLIC), "--json")
            self.assertEqual(rc, 0, err)
            self.assertEqual(json.loads(out)[0]["action"], "merge")
            self.git("remote", "set-url", "origin", f"https://{HOST}/{SLUG}.git")
            rc, out, err = run_main("pr", "steward", "--pr", pr_url(), "--json")
        self.assertEqual(rc, 0, err)
        self.assertEqual(json.loads(out)[0]["action"], "defer-human")
        self.assertEqual([host for _, host, path, _ in self.gh.calls if path.endswith("/permission")], [PUBLIC, HOST])

    def test_offline_snapshot_cannot_offer_a_mutating_command(self):
        snap = pr(
            headRefOid=self.head,
            live_selector=pr_url("another.example"),
            autoMergeRequest={"enabledBy": {"login": "fixture"}, "mergeMethod": "SQUASH"},
            statusCheckRollup=[{"__typename": "CheckRun", "name": "test", "status": "IN_PROGRESS"}],
        )
        rc, out, err = run_main("pr", "next", "--pr-json", "-", "--json", stdin=json.dumps(snap))
        self.assertEqual(rc, 0, err)
        self.assertEqual(json.loads(out).get("do"), "")
        rc, out, err = run_main("merge-check", "--pr-json", "-", "--json", stdin=json.dumps(snap))
        self.assertEqual(rc, 1, out + err)
        self.assertNotIn("live_selector", json.loads(out))
        self.assertEqual(self.gh.calls, [])
        isolated = REAL_RUN(
            [sys.executable, "-I", "-B", str(xt.SCRIPT_DIR / "xt.py"), "pr", "next", "--pr-json", "-", "--json"],
            input=json.dumps(snap),
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(isolated.returncode, 0, isolated.stderr)
        self.assertEqual(json.loads(isolated.stdout)["do"], "")

    def test_github_profile_repository_is_a_valid_dot_prefixed_slug(self):
        slug = "o/.github"
        self.git("remote", "set-url", "origin", f"https://{HOST}/{slug}.git")
        self.assert_pinned_next(run_main("pr", "next", "--pr", pr_url(slug=slug), "--json"), slug)
        self.assert_target_routes(slug)

    def test_full_matching_selector_works_below_checkout_root(self):
        child = self.repo / "nested"
        self.basis = self.commit_files({"nested/xt.yaml": self.CONFIG}, 1700000002)
        self.git("update-ref", "refs/remotes/origin/main", self.basis)
        self.head = self.commit_files({"nested/README.md": "candidate\n"}, 1700000003)
        self.gh.head, self.gh.base = self.head, self.basis
        with chdir(child), mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(child)}):
            self.assert_pinned_next(run_main("pr", "next", "--pr", pr_url(), "--json"))
        self.assert_target_routes()

    def test_files_tab_and_matching_steward_repo_are_accepted(self):
        for tab in ("/files", "/changes#diff-abcd"):
            with self.subTest(tab=tab):
                self.assert_pinned_next(run_main("pr", "next", "--pr", pr_url() + tab, "--json"))
        selector = pr_url() + "/changes"
        rc, out, err = run_main("pr", "steward", "--repo", f"{HOST}/{SLUG}", "--pr", selector, "--json")
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(json.loads(out)[0]["action"], "merge")
        self.assert_target_routes()
        self.gh.calls.clear()
        rc, out, err = run_main("pr", "steward", "--repo", f"{HOST}/{SLUG}", "--pr", pr_url(slug="o/other"))
        self.assertNotEqual(rc, 0, out + err)
        self.assertEqual(self.gh.calls, [])

    def test_changes_tab_is_not_a_canonical_live_response_url(self):
        pull = {**self.gh.pull(HOST, SLUG), "html_url": pr_url() + "/changes"}
        with mock.patch.object(self.gh, "pull", return_value=pull):
            rc, out, err = run_main("merge-check", "--pr", PR, "--json")
        self.assertEqual(rc, 1, out + err)
        data = json.loads(out)
        self.assertEqual((data["host"], data["verdict"], data["eligible"], data["next"]), ("", "wait", False, ""))
        self.gh.calls.clear()
        rc, out, err = run_main("pr", "next", "--pr", pr_url() + "/changes/not-a-commit", "--json")
        self.assertEqual(rc, 2, out + err)
        self.assertEqual(self.gh.calls, [])

    def test_wrong_review_url_leaves_review_slice_and_cost_unchanged(self):
        review = ("pr", "reviewed", "--head", self.head, "--slice", "PLAN-x/T-1", "--cost", "id=review,usd=0.1")
        rc, out, err = run_main(*review, "--pr", PR, "--inconclusive", "--no-publish")
        self.assertEqual(rc, 0, out + err)
        state = xt.state_dir(self.repo)
        ledger = state / xt.REVIEWS_FILE
        events = state / xt.SLICES_SUBDIR / "PLAN-x__T-1.jsonl"
        before = ledger.read_bytes(), events.read_bytes()
        for selector in (pr_url(PUBLIC), pr_url(slug="o/other")):
            for extra in ((), ("--no-publish",)):
                with self.subTest(selector=selector, extra=extra):
                    rc, out, err = run_main(*review, "--pr", selector, "--blocking", *extra)
                    self.assertEqual((ledger.read_bytes(), events.read_bytes()), before)
                    self.assertEqual(rc, 2, out + err)
                    self.assertIn("URL review", err)
                    self.assertEqual(self.gh.calls, [])

    def test_native_review_publication_uses_the_bound_enterprise_target(self):
        review = ("pr", "reviewed", "--head", self.head, "--blocking", "--pr")
        rc, out, err = run_main(*review, pr_url() + "/files#diff-abcd")
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(self.gh.calls[-1][:3], ("POST", HOST, f"repos/{SLUG}/issues/{PR}/comments"))
        self.assert_target_routes()

    def test_review_publication_without_origin_preserves_review_for_retry(self):
        self.git("remote", "remove", "origin")
        previous = xt.PR_READ_HOST.set(PUBLIC)
        self.addCleanup(xt.PR_READ_HOST.reset, previous)
        review = ("pr", "reviewed", "--pr", PR, "--head", self.head, "--blocking")
        rc, out, err = run_main(*review)
        self.assertEqual(rc, 3, out + err)
        self.assertIn("chưa đăng được review lên PR #7", err)
        self.assertIn("không xác minh được host/repo của origin", err)
        self.assertIn("chạy lại `xt.py pr reviewed", err)
        self.assertNotIn("đã đăng review", out)
        self.assertEqual(self.gh.calls, [])
        self.assertEqual(xt.PR_READ_HOST.get(), PUBLIC)
        reviews = xt.read_reviews(self.repo)[PR]["reviews"]
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["head"], self.head)
        self.assertFalse(reviews[0]["clean"])
        self.assertNotIn("published", reviews[0])

        self.git("remote", "add", "origin", f"https://{HOST}/{SLUG}.git")
        rc, out, err = run_main(*review)
        self.assertEqual(rc, 0, out + err)
        self.assertIn("đã ghi trước đó — không ghi thêm", out)
        self.assertIn("đã đăng review lên PR #7", out)
        self.assert_target_routes()
        self.assertEqual(
            [call[:3] for call in self.gh.calls if call[0] != "GET"],
            [("POST", HOST, f"repos/{SLUG}/issues/{PR}/comments")],
        )
        self.assertEqual(xt.PR_READ_HOST.get(), PUBLIC)
        self.assertEqual(xt.read_reviews(self.repo)[PR]["reviews"], [{**reviews[0], "published": True}])


if __name__ == "__main__":
    main()
