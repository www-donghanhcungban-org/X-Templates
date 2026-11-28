"""ADR-0105 với dữ liệu PR, ruleset và đồng hồ giả."""

from __future__ import annotations

import argparse
import io
import json
import sys
from contextlib import redirect_stdout
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import TestCase, main, mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import xt_merge_queue as queue
import xt
from xt_merge_intent import RepoTarget

REPO = RepoTarget("github.example", "owner/repo")
NOW = datetime(2026, 11, 28, 6, tzinfo=timezone.utc)
OURS = 40


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW


class InputError(Exception):
    pass


def sha(number):
    return f"{number:040x}"


def at(minutes=0):
    return (NOW - timedelta(minutes=minutes)).isoformat()


def summary(number, *, minutes=0, ref="main", head_repo=REPO.repo, base_repo=REPO.repo, **kwargs):
    return {
        "number": number,
        "base": {"ref": ref, "repo": {"full_name": base_repo}},
        "head": {"sha": sha(number), "repo": {"full_name": head_repo}},
        "updated_at": at(minutes),
        **kwargs,
    }


def details(number=OURS, **kwargs):
    return {
        "number": number,
        "headRefOid": sha(number),
        "repo": REPO.repo,
        "headRepo": REPO.repo,
        "baseRefName": "main",
        "live_host": REPO.host,
        "live_intent": {"host": REPO.host, "repo": REPO.repo, "pr": number, "expected_head": sha(number)},
        "state": "OPEN",
        "case": "merge",
        **kwargs,
    }


def decision(pr):
    number = pr["number"]
    verdict = pr["case"]
    if pr.get("mergeStateStatus") == "BEHIND":
        verdict = "update" if verdict == "review" else verdict
    return {
        "pr": number,
        "head": pr["headRefOid"],
        "verdict": verdict,
        "lane": pr.get("lane", "nhanh"),
        "hard": pr.get("hard", []),
        "stacked": pr.get("stacked", False),
        "hard_waived": pr.get("hard_waived", []),
        "eligible": verdict == "merge",
        "reasons": [f"fixture {verdict}"],
        "next": "fixture",
        "next_rest": "fixture",
    }


class MergeQueueTests(TestCase):
    def setUp(self):
        self.host = mock.Mock()
        self.host.PrInputError = InputError
        self.host.MERGE_WAIT_NEXT = "wait command"
        self.host.PR_BEHIND_REASON = "behind"
        self.host.PR_READ_HOST = ContextVar("test_host", default="")
        self.host.project_dir.return_value = Path("/mock/repo")
        self.host._pr_policy_ref.return_value = "committed-base"
        self.host._committed_xt_keys.return_value = {}
        self.host._pr_open.return_value = []
        self.host._pr_rest.side_effect = self.read_pr
        self.host._merge_eval.side_effect = lambda pr: (decision(pr), [])
        self.host.steward_untrusted.side_effect = lambda pr: pr.get("outside", "")
        self.host._waived_notes.return_value = ["waived"]
        self.host._pr_update_next.return_value = "update pinned head"
        self.rows = {}
        self.ours = details()
        self.out = {"pr": OURS, "head": sha(OURS), "action": "merge"}
        patcher = mock.patch.object(queue, "datetime", Clock)
        patcher.start()
        self.addCleanup(patcher.stop)

    def read_pr(self, number, *, local_check, target):
        self.assertIs(local_check, False)
        self.assertEqual(target, REPO)
        candidate = self.rows[int(number)]
        if isinstance(candidate, Exception):
            raise candidate
        return candidate

    def gate(self, action="", *, fresh=False):
        return queue.gate(self.host, self.ours, decision(self.ours), action, fresh=fresh)

    def before_action(self, action="merge"):
        return queue.before_action(self.host, {**self.out, "action": action}, REPO, "main")

    def assert_waits_for(self, result, expected):
        self.assertEqual(result["verdict"], "wait")
        self.assertFalse(result["eligible"])
        self.assertNotIn("next_rest", result)
        self.assertEqual(result["next"], "wait command")
        self.assertIn(f"#{expected} đứng đầu hàng", result["reasons"][0])

    def test_only_same_repo_and_branch_open_unready_head_waits(self):
        self.rows.update({12: details(12, case="wait"), 18: details(18)})
        self.host._pr_open.return_value = [
            summary(18),
            summary(11, state="closed"),
            summary(10, draft=True),
            summary(9, head_repo="someone/fork"),
            summary(8, base_repo="someone/fork"),
            summary(7, ref="release"),
            {**summary(6), "head": {"sha": sha(6), "repo": None}},
            summary(0),
            summary(True),
            summary(OURS),
            summary(12, head_repo=REPO.repo.upper()),
        ]
        for verdict, action in (
            ("merge", ""),
            ("merge", "merge"),
            ("update", "update"),
            ("update", "disable-auto-merge"),
        ):
            with self.subTest(verdict=verdict, action=action):
                self.ours["case"] = verdict
                self.assert_waits_for(self.gate(action), 12)
        self.assertEqual(self.host._pr_rest.call_args_list, [mock.call("12", local_check=False, target=REPO)] * 4)
        self.host._pr_policy_ref.assert_called_with(Path("/mock/repo"), "main")
        self.host._committed_xt_keys.assert_called_with(Path("/mock/repo"), "committed-base")

    def test_review_holds_until_head_leaves_then_only_next_pr_proceeds(self):
        self.rows.update({12: details(12, case="review"), 18: details(18)})
        self.host._pr_open.return_value = [summary(18), summary(12)]
        with queue.queue_scope():
            self.assert_waits_for(self.gate(), 12)
            self.host._pr_open.return_value = [summary(18)]
            self.assert_waits_for(self.gate(), 18)
            self.ours = details(18)
            self.assertEqual(self.gate()["verdict"], "merge")

    def test_live_classification_drops_candidates_that_can_no_longer_proceed(self):
        self.rows.update(
            {
                1: details(1, state="MERGED"),
                2: details(2, isDraft=True),
                3: details(3, baseRefName="other"),
                4: details(4, headRepo="someone/fork"),
                5: details(5, case="fix"),
                6: details(6, case="human"),
                7: details(7, case="closed"),
                8: details(8, hard=["fixture hard"]),
                9: details(9, stacked=True),
                10: details(10, case="wait", outside="outside"),
                11: details(11, case="wait", lane="derived", outside="outside"),
            }
        )
        self.host._pr_open.return_value = [summary(n) for n in self.rows]
        self.assert_waits_for(self.gate(), 11)

    def test_oldest_started_check_and_listing_age_control_stall_boundary(self):
        self.rows.update(
            {
                2: details(
                    2,
                    case="wait",
                    statusCheckRollup=[{"startedAt": at(2)}, {"startedAt": at(121)}, {"startedAt": "broken"}, None],
                ),
                3: details(3, case="review"),
                4: details(4, case="review", statusCheckRollup=[{"startedAt": at(120)}]),
            }
        )
        self.host._committed_xt_keys.return_value = {
            "merge_queue": "misspelled",
            "merge_queue_stall_minutes": "-1",
        }
        self.host._pr_open.return_value = [summary(2), summary(3, minutes=121), summary(4, minutes=200)]
        self.assert_waits_for(self.gate(), 4)
        self.host._committed_xt_keys.return_value = {"merge_queue_stall_minutes": "0"}
        self.assertEqual(self.gate()["verdict"], "merge")
        self.rows[4]["statusCheckRollup"] = [{"startedAt": "2026-11-28T06:00:00"}]
        self.host._pr_open.return_value[-1] = summary(4)
        self.assert_waits_for(self.gate(), 4)
        self.assertIsNone(queue.stall_minutes("9" * 5000))
        self.assertIsNone(queue.stall_minutes("٤"))

    def test_merge_candidate_that_needs_update_never_stalls(self):
        self.rows[2] = details(2, case="review", mergeStateStatus="BEHIND")
        self.host._pr_open.return_value = [summary(2, minutes=200)]
        self.assert_waits_for(self.gate(), 2)
        self.assertEqual(self.rows[2]["mergeStateStatus"], "BEHIND")
        self.rows[2]["hard"] = ["held out"]
        self.assertEqual(self.gate()["verdict"], "merge")
        self.rows[2].update(hard=[], case="wait")
        self.assertEqual(self.gate()["verdict"], "merge")

    def test_errors_fail_closed_until_listing_ttl_and_scan_cap(self):
        self.rows.update({1: InputError("fixture"), 2: OSError("fixture"), 3: details(3, headRefOid=sha(4))})
        self.host._pr_open.return_value = [summary(1, minutes=121), summary(2, minutes=120), summary(3, minutes=80)]
        self.assert_waits_for(self.gate(), 2)
        self.rows[2] = details(2, case="fix")
        self.assert_waits_for(self.gate(), 3)
        self.host._pr_open.return_value[2]["updated_at"] = None
        self.assert_waits_for(self.gate(), 3)
        self.rows[3] = details(3, baseRefName=None)
        self.assert_waits_for(self.gate(), 3)
        self.host._pr_rest.reset_mock()
        self.rows = {number: details(number, case="fix") for number in range(1, queue.SCAN_LIMIT + 2)}
        self.host._pr_open.return_value = [summary(number) for number in self.rows]
        result = self.gate()
        self.assertEqual(result["verdict"], "wait")
        self.assertIn("chưa xác minh", result["reasons"][0])
        self.assertEqual(self.host._pr_rest.call_count, queue.SCAN_LIMIT)
        self.host._pr_open.side_effect = InputError("fixture")
        self.assertEqual(self.gate()["verdict"], "wait")

    def test_ineligible_snapshot_and_committed_off_do_not_read_queue(self):
        self.ours["case"] = "review"
        self.assertEqual(self.gate()["verdict"], "review")
        self.ours["case"] = "merge"
        self.assertEqual(self.gate("review")["verdict"], "merge")
        self.ours["live_intent"] = None
        self.assertEqual(self.gate()["verdict"], "merge")
        self.ours = details()
        self.host._committed_xt_keys.return_value = {"merge_queue": "off"}
        self.assertEqual(self.gate()["verdict"], "merge")
        self.host._pr_open.assert_not_called()
        self.ours["baseRefName"] = None
        self.assertEqual(self.gate()["verdict"], "wait")
        self.ours = details(live_intent={"pr": OURS})
        self.assertEqual(self.gate()["verdict"], "wait")
        self.ours = details()
        self.host._committed_xt_keys.side_effect = OSError("không đọc được nhánh đích")
        self.host._pr_open.return_value = [summary(2, minutes=120)]
        self.rows[2] = details(2, case="review")
        self.assert_waits_for(self.gate(), 2)

    def test_strict_base_uses_live_host_after_queue_and_only_for_merge(self):
        self.ours["strictBaseRepo"] = REPO.path

        def base_distance(path, branch, head):
            self.assertEqual(self.host.PR_READ_HOST.get(), REPO.host)
            self.assertEqual((path, branch, head), (REPO.path, "main", sha(OURS)))
            return next(distances)

        distances = iter([0, None, 2])
        self.host._live_base_distance.side_effect = base_distance
        self.assertEqual(self.gate("update")["verdict"], "merge")
        self.assertEqual(self.gate("merge")["verdict"], "merge")
        self.assertIn("ruleset", self.gate("merge")["reasons"][0])
        updated = self.gate("merge")
        self.assertEqual(updated["verdict"], "update")
        self.assertEqual(updated["reasons"], ["behind", "waived"])
        self.assertEqual(updated["next"], "update pinned head")
        self.assertFalse(updated["eligible"])
        self.assertNotIn("next_rest", updated)
        self.ours["case"] = "update"
        self.assertEqual(self.gate()["verdict"], "update")
        self.assertEqual(self.host._live_base_distance.call_count, 3)

    def test_same_sha_can_change_queue_eligibility_during_steward_pass(self):
        self.rows.update({2: details(2, case="fix"), OURS: self.ours})
        self.host._pr_open.return_value = [summary(2)]
        with queue.queue_scope():
            self.assertEqual(self.gate()["verdict"], "merge")
            self.rows[2]["case"] = "wait"
            self.assertEqual(self.gate()["verdict"], "merge")
            self.assertIn("#2 đứng đầu hàng", self.before_action())
            self.assert_waits_for(self.gate(), 2)
        self.rows[2]["case"] = "fix"
        self.assertEqual(self.gate()["verdict"], "merge")
        self.host._pr_open.return_value = [{"number": 2}]
        with queue.queue_scope():
            self.assertEqual(self.gate()["verdict"], "merge")

    def test_before_action_rejects_retarget_head_drift_and_revoked_checks(self):
        for changes, reason in (
            ({"baseRefName": "other"}, "nhánh đích"),
            ({"live_intent": {**self.ours["live_intent"], "expected_head": sha(1)}}, "head đổi"),
            ({"case": "wait"}, "fixture wait"),
            ({"case": "review"}, "fixture review"),
            ({"outside": "outside"}, "outside"),
            ({"state": "MERGED"}, "đã đóng/merge"),
            ({"hard": ["fixture hard"]}, "cổng vừa đổi"),
            ({"stacked": True}, "cổng vừa đổi"),
        ):
            with self.subTest(changes=changes):
                self.rows[OURS] = details(**changes)
                self.assertIn(reason, self.before_action())
        self.rows[OURS] = details(case="update", autoMergeRequest=True)
        self.assertIn("auto-merge đang bật", self.before_action("update"))
        self.rows[OURS] = details(case="update")
        self.assertEqual(self.before_action("update"), "")
        self.rows[OURS] = details(case="update", hard=["fixture unwaivable"])
        self.assertIn("cổng vừa đổi", self.before_action("update"))
        self.rows[OURS] = details()
        self.assertEqual(self.before_action(), "")
        self.rows[OURS] = details(hard_waived=["fixture waived"])
        self.assertEqual(self.before_action(), "")
        self.rows[OURS] = details(lane="derived", outside="outside")
        self.assertEqual(self.before_action(), "")
        self.rows[OURS] = InputError("fixture")
        self.assertIn("không đọc lại", self.before_action())

    def test_before_action_confirms_strict_base_even_when_expected_update(self):
        self.host._live_base_distance.side_effect = [1, 0]
        self.rows[OURS] = details(strictBaseRepo=REPO.path)
        self.assertEqual(self.before_action("update"), "")
        self.assertIn("cổng vừa đổi", self.before_action("update"))

    def test_event_advances_only_after_confirmed_merge_and_to_one_candidate(self):
        self.rows.update(
            {
                OURS: details(),
                41: details(41, case="human"),
                42: details(42, case="review"),
                43: details(43),
            }
        )
        self.host._pr_open.return_value = [summary(43), summary(42), summary(41), summary(1, ref="release")]
        self.assertEqual(queue.event_successors(self.host, self.out, REPO), [])
        self.host._pr_open.assert_not_called()
        self.rows[OURS]["state"] = "MERGED"
        self.assertEqual(queue.event_successors(self.host, self.out, REPO), ["42"])
        self.host._committed_xt_keys.return_value = {"merge_queue": "off"}
        self.assertEqual(queue.event_successors(self.host, self.out, REPO), [])
        self.rows[OURS] = InputError("fixture error")
        self.assertEqual(queue.event_successors(self.host, self.out, REPO), [])

    def test_followup_update_stops_when_live_queue_changes(self):
        self.rows.update({OURS: details(case="update"), 12: details(12, case="wait")})
        self.host._pr_open.return_value = [summary(12)]
        out = {**self.out, "action": "disable-auto-merge"}
        self.assertIs(queue.followup_update(self.host, out, REPO, "main"), out)
        self.host._add_note.assert_called_once()
        self.assertIn("#12 đứng đầu hàng", self.host._add_note.call_args.args[1])
        self.host._steward_run.assert_not_called()

    def test_summary_reports_head_and_missing_required_checks(self):
        results = [
            {"pr": 1, "action": "merge", "applied": True, "_queue_branch": "main"},
            {"pr": 2, "action": "wait", "why": "fixture", "_queue_branch": "main", "_queue_checks_absent": True},
            {"pr": 3, "action": "wait", "_queue_branch": "main"},
            {"pr": 4, "action": "closed", "_queue_branch": "other"},
            {"pr": 5, "action": "error"},
        ]
        self.assertEqual(
            queue.queue_summary(results),
            [
                "⚠ main: nhánh đích không có check bắt buộc (LOOP-STOP-033)",
                "main · hàng: đầu #2 (fixture) · rời hàng: #1 · sau: #3",
                "other · hàng: đầu — · rời hàng: #4 · sau: —",
            ],
        )
        self.assertNotIn("_queue_branch", results[1])
        self.assertNotIn("_queue_checks_absent", results[1])

    def test_event_summary_uses_the_earlier_pr_named_by_the_gate(self):
        why = "chờ tới lượt: #12 đứng đầu hàng (LOOP-STOP-031)"
        result = {"pr": 18, "action": "wait", "why": why, "_queue_branch": "main"}
        self.assertEqual(queue.queue_summary([result]), [f"main · hàng: đầu #12 ({why}) · rời hàng: — · sau: #18"])


class StewardQueueIntegrationTests(TestCase):
    def test_cli_and_steward_hold_candidates_through_ci_and_review(self):
        rows = {12: details(12, case="wait"), 18: details(18, case="update"), 40: details(40)}

        def read(number, **_kwargs):
            return rows[int(number)]

        def evaluate(pr, **_kwargs):
            if pr["case"] == "update" and pr.get("mergeStateStatus") == "CLEAN":
                pr = {**pr, "case": "wait"}
            return {**decision(pr), "review_optional": True}, []

        def opened(_target):
            return [summary(n) for n, pr in reversed(rows.items()) if pr["state"] == "OPEN"]

        output = io.StringIO()
        self.enterContext(redirect_stdout(output))
        self.enterContext(mock.patch.object(queue, "datetime", Clock))
        self.enterContext(mock.patch.object(xt, "_pr_checkout", return_value=REPO))
        self.enterContext(mock.patch.object(xt, "_pr_rest", side_effect=read))
        self.enterContext(mock.patch.object(xt, "_pr_open", side_effect=opened))
        self.enterContext(mock.patch.object(xt, "_merge_eval", side_effect=evaluate))
        self.enterContext(mock.patch.object(xt, "_committed_xt_keys", return_value={}))
        self.enterContext(mock.patch.object(xt, "steward_untrusted", return_value=""))
        self.enterContext(mock.patch.object(xt, "_steward_can_update", return_value=True))
        self.enterContext(mock.patch.object(xt, "_steward_stale", return_value=""))
        self.enterContext(mock.patch.object(xt, "_steward_command", side_effect=self.commands))
        writes = self.enterContext(
            mock.patch.object(xt, "_steward_run", side_effect=lambda cmds: self.write(rows, cmds))
        )

        def run():
            output.seek(0)
            output.truncate()
            args = argparse.Namespace(pr=None, event=None, repo=None, apply=True, json=True)
            self.assertEqual(xt.cmd_pr_steward(args), 0)
            return {r["pr"]: r for r in json.loads(output.getvalue())}

        for waiting in ("wait", "review"):
            with self.subTest(waiting=waiting):
                rows[12]["case"] = waiting
                candidate = rows[18]
                _, step = xt._eval_pr_next(candidate, evaluate(candidate)[0], {}, Path("/mock/repo"))
                self.assertEqual(step["action"], "wait")
                result = run()
                for number in (18, 40):
                    self.assertEqual(result[number]["action"], "wait")
                    self.assertIn("#12 đứng đầu hàng", result[number]["why"])
                writes.assert_not_called()

        rows[12]["case"] = "merge"
        rows[18]["mergeStateStatus"] = "BEHIND"
        result = run()
        self.assertTrue(result[12]["applied"])
        self.assertTrue(result[18]["applied"])
        self.assertFalse(result[40]["applied"])
        self.assertEqual(writes.call_args_list, [mock.call([["/merge"]]), mock.call([["/update"]])])

    @staticmethod
    def write(rows, commands):
        if ["/merge"] in commands:
            rows[12]["state"] = "MERGED"
        if ["/update"] in commands:
            rows[18] = details(18, case="wait")
        return ""

    @staticmethod
    def commands(out, *_args):
        return [[f"/{out['action']}"]] if out["action"] in ("merge", "update") else []


if __name__ == "__main__":
    main()
