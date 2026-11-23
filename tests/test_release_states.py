"""T-4019: `release-check` tách ba trạng thái (kiểm kỹ thuật · nội dung đã ký đúng vân tay · đã phân phối); trạng thái chờ ký
không nói "human" khi agent là người ký; lược đồ 4, bên đọc nhận cả tên cũ `pending_human` và schema 3 một chu kỳ; consumer
chỉ tin `promotion.state == approved`, không tin riêng `go`/exit code."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import xt
import xt_flow
import xt_release_ops
from test_xt import audit_status_text


def row(rid: str, result: str, level: str = "BLOCKER") -> dict:
    return {"id": rid, "result": result, "level": level, "evidence": "x"}


class StatesTest(unittest.TestCase):
    def states(self, rows, fails, state, reasons=("r",)):
        return xt.release_states(rows, fails, {"state": state, "reasons": list(reasons)})

    def test_technical_passed_or_failed_with_ids(self):
        ok = self.states([row("deploy", "PASS")], [], "approved")
        self.assertEqual(ok["technical"], {"state": "passed", "fails": []})
        bad = self.states([row("deploy", "PASS")], ["blueprint", "tree"], "blocked")
        self.assertEqual(bad["technical"], {"state": "failed", "fails": ["blueprint", "tree"]})

    def test_signed_state_follows_promotion_not_exit_code(self):
        for promo, want in (
            ("approved", "signed"),
            ("rejected", "rejected"),
            ("pending_signoff", "pending"),
            ("pending_human", "pending"),  # tên cũ vẫn đọc được
            ("blocked", "not_ready"),
            ("lạ", "not_ready"),  # trạng thái lạ: không bao giờ là signed
        ):
            with self.subTest(promo=promo):
                self.assertEqual(self.states([], [], promo)["signed"]["state"], want)

    def test_distributed_comes_from_the_deploy_row(self):
        for result, want in (("PASS", "deployed"), ("FAIL", "not_distributed"), ("N/A", "not_configured")):
            with self.subTest(result=result):
                self.assertEqual(self.states([row("deploy", result)], [], "approved")["distributed"], want)
        self.assertEqual(self.states([], [], "approved")["distributed"], "not_configured")  # không có hàng deploy

    def test_three_states_are_independent(self):
        got = self.states([row("deploy", "PASS")], ["tree"], "approved")
        self.assertEqual(
            (got["technical"]["state"], got["signed"]["state"], got["distributed"]), ("failed", "signed", "deployed")
        )


class ConstantsTest(unittest.TestCase):
    def test_promotion_names_do_not_shadow_the_loop_verdict_constant(self):
        self.assertEqual(xt.PENDING_HUMAN, "done-pending-human")  # verdict vòng lặp, không phải trạng thái promotion
        self.assertEqual((xt.PROMO_PENDING_SIGNOFF, xt.PROMO_PENDING_HUMAN), ("pending_signoff", "pending_human"))


class PromotionNamingTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.subject = {"head": "a" * 40, "tree": None, "digest": None, "content": "b" * 64}

    def promotion(self, agent: bool, fails=(), human=("go_no_go",)):
        with unittest.mock.patch.object(xt, "release_agent_signoff", return_value=agent):
            return xt._release_promotion(self.base, list(fails), list(human), self.subject)

    def test_agent_signer_names_the_state_signoff_not_human(self):
        got = self.promotion(True)
        self.assertEqual((got["state"], got["signer"]), ("pending_signoff", "agent"))
        self.assertTrue(xt.promotion_pending(got["state"]))

    def test_human_signer_keeps_the_accurate_old_name(self):
        got = self.promotion(False)
        self.assertEqual((got["state"], got["signer"]), ("pending_human", "human"))
        self.assertTrue(xt.promotion_pending(got["state"]))

    def test_agent_is_the_signer_only_when_the_signature_is_the_sole_human_item(self):
        """Review lô B (🟢): `release-sign` từ chối khi còn việc người ngoài chữ ký — khi đó phải gọi là chờ người."""
        self.assertEqual(self.promotion(True, human=("go_no_go",))["signer"], "agent")
        for human in (("prod_switch",), ("go_no_go", "acceptance"), ("acceptance",)):
            with self.subTest(human=human):
                got = self.promotion(True, human=human)
                self.assertEqual((got["state"], got["signer"]), ("pending_human", "human"))

    def test_unsigned_without_human_rows_follows_the_same_rule(self):
        self.assertEqual(self.promotion(True, human=())["state"], "pending_signoff")
        self.assertEqual(self.promotion(False, human=())["state"], "pending_human")

    def test_blocked_unchanged_and_helper_rejects_other_states(self):
        self.assertEqual(self.promotion(True, fails=("tree",))["state"], "blocked")
        for state in ("approved", "rejected", "blocked", "", "pending", None):
            self.assertFalse(xt.promotion_pending(state))


class ReaderCompatibilityTest(unittest.TestCase):
    def setUp(self):
        tmp = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.base, self.main = tmp / "base", tmp / "main"
        for d in (self.base, self.main):
            d.mkdir()
            (d / "VERSION").write_text("9.9.9\n", encoding="utf-8")
            (d / "xt.yaml").write_text("release_signoff: agent\n", encoding="utf-8")
        self.target = "c" * 40

    def check(self, **release):
        doc = {
            "head": self.target,
            "subject": {"head": self.target, "content": "d" * 64},
            "go": True,
            "human": ["go_no_go"],
            "verdict": "GO (chờ người)",
            "promotion": {"state": "pending_signoff", "reasons": ["go_no_go"]},
        } | release
        core = SimpleNamespace(
            _go_no_go_docs=lambda base, version: [],
            release_check=lambda base, blueprint, status: doc,
            promotion_pending=xt.promotion_pending,
            RELEASE_SIGN_BLUEPRINT="BLUEPRINT.md",
            RELEASE_SIGN_STATUS="docs/ops/AUDIT-STATUS.md",
        )
        return xt_release_ops.approved_for_tag(core, self.base, self.main, self.target)

    def test_both_pending_names_wait_for_signoff(self):
        for state in ("pending_signoff", "pending_human"):
            with self.subTest(state=state):
                self.assertFalse(self.check(promotion={"state": state, "reasons": ["go_no_go"]}))

    def test_only_approved_with_go_is_accepted(self):
        approved = {"state": "approved", "reasons": ["GO-NO-GO.md"]}
        self.assertTrue(self.check(promotion=approved, verdict="GO", human=[]))
        with self.assertRaises(ValueError):  # go True nhưng chưa approved: exit 0 không đủ
            self.check(promotion={"state": "pending_signoff", "reasons": ["x"]}, human=["go_no_go", "prod_switch"])
        with self.assertRaises(ValueError):
            self.check(promotion={"state": "rejected", "reasons": ["x"]}, verdict="GO", human=[])
        with self.assertRaises(ValueError):
            self.check(promotion=approved, verdict="GO (chờ người)", human=["prod_switch"])

    def test_release_schema_accepts_current_and_previous_only(self):
        self.assertEqual(xt.RELEASE_SCHEMA, 4)
        self.assertEqual(xt.RELEASE_SCHEMAS, (3, 4))
        for schema, schema_error in ((2, True), (3, False), (4, False), (5, True)):
            with self.subTest(schema=schema):
                with self.assertRaises(ValueError) as ctx:
                    xt_flow.release_rows({"schema": schema, "rows": [], "at": "2026-11-23T00:00:00+00:00"})
                self.assertEqual("cần báo cáo đầy đủ từ release-check" in str(ctx.exception), schema_error)


class ReleaseCheckOutputTest(unittest.TestCase):
    def setUp(self):
        self.repo = Path(self.enterContext(tempfile.TemporaryDirectory(ignore_cleanup_errors=True))).resolve()
        self.enterContext(unittest.mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.repo)}))
        git = ["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
        subprocess.run([*git, "init", "-q", "-b", "main"], check=True)
        (self.repo / "docs" / "ops").mkdir(parents=True)
        (self.repo / "docs" / "ops" / "AUDIT-STATUS.md").write_text(audit_status_text(), encoding="utf-8")
        subprocess.run([*git, "add", "-A"], check=True)
        subprocess.run([*git, "commit", "-qm", "c0"], check=True)

    def test_output_carries_schema_four_states_and_signer(self):
        out = xt.release_check(self.repo, "BLUEPRINT.md", "docs/ops/AUDIT-STATUS.md")
        self.assertEqual(out["schema"], 4)
        self.assertEqual(sorted(out["states"]), ["distributed", "signed", "technical"])
        self.assertEqual(out["states"]["technical"]["state"], "failed")  # chưa có BLUEPRINT.md
        self.assertEqual(out["states"]["signed"]["state"], "not_ready")
        for key in ("go", "verdict", "human", "fails", "promotion"):  # trường cũ giữ nguyên
            self.assertIn(key, out)


if __name__ == "__main__":
    unittest.main()
