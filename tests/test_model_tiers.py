"""ADR-0098: bảng bậc model theo nhà cung cấp là nguồn duy nhất cho vai của agent; agent Claude, gương Codex, tài liệu và
mẫu cho dự án đích phải khớp bảng."""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import xt

TIERS = json.loads((ROOT / "framework" / "templates" / "harness" / "model-tiers.json").read_text(encoding="utf-8"))
AGENTS = {p.stem: p.read_text(encoding="utf-8") for p in sorted((ROOT / ".claude" / "agents").glob("*.md"))}


def frontmatter(text: str) -> dict[str, str]:
    block = text.split("---", 2)[1]
    return dict(line.split(": ", 1) for line in block.strip().splitlines() if ": " in line)


class ModelTiersTest(unittest.TestCase):
    def test_shape_and_order(self):
        self.assertEqual(TIERS["schema"], 1)
        self.assertEqual(TIERS["tiers"], ["bottom", "top-2", "top-1", "top"])
        self.assertRegex(TIERS["as_of"], r"^\d{4}-\d{2}-\d{2}$")
        for vendor in ("anthropic", "openai"):
            for tier in TIERS["tiers"]:
                with self.subTest(vendor=vendor, tier=tier):
                    self.assertTrue(TIERS["vendors"][vendor][tier]["id"])
        self.assertTrue(TIERS["vendors"]["anthropic"]["verified"])
        self.assertFalse(TIERS["vendors"]["openai"]["verified"])  # thứ bậc suy từ docs, chưa chính thức

    def test_anthropic_order_matches_the_machine_ranking(self):
        ranks = [xt.MODEL_TIER[TIERS["vendors"]["anthropic"][t]["alias"]] for t in TIERS["tiers"]]
        self.assertEqual(ranks, sorted(ranks))
        self.assertEqual(len(set(ranks)), len(ranks))
        for t in TIERS["tiers"]:
            entry = TIERS["vendors"]["anthropic"][t]
            self.assertEqual(xt.model_family(entry["id"]), entry["alias"])

    def test_every_agent_has_a_role_and_its_model_matches_the_tier(self):
        self.assertEqual(set(TIERS["roles"]), set(AGENTS), "agent và bảng vai phải cùng tập")
        for name, text in AGENTS.items():
            with self.subTest(agent=name):
                tier = TIERS["roles"][name]
                self.assertEqual(frontmatter(text)["model"], TIERS["vendors"]["anthropic"][tier]["alias"])

    def test_review_agents_are_top_minus_one_and_explore_is_read_only_bottom(self):
        for name in ("reviewer", "reviewer-alt"):
            self.assertEqual(TIERS["roles"][name], "top-1")  # D-558, D-559
        self.assertEqual(TIERS["roles"]["explore"], "bottom")
        tools = {t.strip() for t in frontmatter(AGENTS["explore"])["tools"].split(",")}
        self.assertEqual(tools, {"Read", "Glob", "Grep"})  # chỉ đọc, không Bash

    def test_reviewers_are_pinned_to_opus_high_with_120_turns(self):
        # ADR-0110 (D-623, D-625): trần effort `high`, opus, 120 lượt một lần chạy; không dặn giao model/effort của phiên chính
        for name in ("reviewer", "reviewer-alt"):
            with self.subTest(agent=name):
                meta = frontmatter(AGENTS[name])
                self.assertEqual(meta["model"], "opus")
                self.assertEqual(meta["effort"], "high")
                self.assertEqual(meta["maxTurns"], "120")
                self.assertNotIn("effort cao nhất", AGENTS[name])
                self.assertNotIn("giao kèm `model`", AGENTS[name])
        skills = [
            (ROOT / d / "skills" / "review" / "SKILL.md").read_text(encoding="utf-8") for d in (".claude", ".agents")
        ]
        self.assertEqual(skills[0], skills[1])
        orch = (ROOT / "framework" / "11-autonomous-loop" / "orchestration-and-subagents.md").read_text(
            encoding="utf-8"
        )
        for text in (*skills, orch):
            self.assertNotIn("giao kèm `model: fable`", text)
            self.assertNotIn("effort `max`)", text)
            self.assertIn("ADR-0110", text)
        for text in skills:
            self.assertIn("--inconclusive", text)
            self.assertIn("--author-effort medium", text)
        self.assertTrue((ROOT / "docs" / "adr" / "0110-reviewer-effort-ceiling-and-routing.md").is_file())

    def test_deep_executor_defaults_to_opus_medium_and_pairs_with_reviewer_high(self):
        # D-627: mặc định của vai là medium (không phải tham số lần gọi); cặp (medium, high) hợp lệ, (high, high) bị từ chối
        meta = frontmatter(AGENTS["executor-deep"])
        self.assertEqual((meta["model"], meta["effort"], meta["maxTurns"]), ("opus", "medium", "160"))
        reviewer = frontmatter(AGENTS["reviewer-alt"])
        self.assertIsNone(
            xt.review_capability_error(reviewer["model"], meta["model"], reviewer["effort"], meta["effort"])
        )
        self.assertIsNotNone(xt.review_capability_error("opus", "opus", "high", "high"))

    def test_main_session_rule(self):
        self.assertEqual(
            TIERS["main_session"],
            {
                "plan_spec_decision": "top-1",  # D-605: lập PLAN/SPEC ở Opus; Fable chỉ khi chủ dự án bật
                "write_code": "top-1",
                "write_code_max_effort": "xhigh",
                "top_opt_in": TIERS["main_session"]["top_opt_in"],
            },
        )
        self.assertIn("D-605", TIERS["main_session"]["top_opt_in"])
        self.assertLess(
            xt.EFFORTS.index("xhigh"), xt.EFFORTS.index("max")
        )  # thang effort: `max` vẫn trên `xhigh` (reviewer không dùng, ADR-0110)

    def test_mechanical_executor_is_bottom_with_a_capped_budget(self):
        # D-605: việc cơ học có Gate ở bậc nhẹ nhất; đỏ một lần chuyển `executor`, turn thấp để prompt dưới 100K.
        self.assertEqual(TIERS["roles"]["executor-mech"], "bottom")
        meta = frontmatter(AGENTS["executor-mech"])
        self.assertLessEqual(int(meta["maxTurns"]), 40)
        self.assertNotIn("effort", meta)
        body = AGENTS["executor-mech"]
        for phrase in ("Gate", "`executor`", "không thử sửa lần hai"):
            self.assertIn(phrase, body)
        rank = xt.MODEL_TIER
        self.assertLess(rank[meta["model"]], rank[frontmatter(AGENTS["reviewer"])["model"]])  # LOOP-ORCH-005

    def test_every_agent_declares_a_positive_turn_cap(self):
        # LOOP-ORCH-008 (MUST@L), AUD-HAR-563: install.py chép mọi agent sang dự án đích; agent có Write/Edit cần trần turn
        for name, text in AGENTS.items():
            with self.subTest(agent=name):
                self.assertRegex(frontmatter(text).get("maxTurns", ""), r"^[1-9][0-9]*$")

    def test_four_agents_pin_the_two_prevention_lines(self):
        # T-5045 (C11): guard chặn lệnh vừa ghi vừa đọc cùng một tệp; lệnh chạy dài chia lượt ≤ 4 phút (TTL cache 5 phút)
        for name in ("executor", "executor-deep", "reviewer", "reviewer-alt"):
            with self.subTest(agent=name):
                self.assertIn("hai lệnh Bash riêng", AGENTS[name])
                self.assertIn("lượt ≤ 4 phút", AGENTS[name])

    def test_codex_mirror_has_every_agent(self):
        mirror = {p.stem for p in (ROOT / ".codex" / "agents").glob("*.toml")}
        self.assertEqual(mirror, set(AGENTS))

    def test_docs_and_templates_are_in_sync(self):
        orch = (ROOT / "framework" / "11-autonomous-loop" / "orchestration-and-subagents.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("ADR-0098", orch)
        self.assertNotIn("giao `reviewer-alt` với `model: fable`", orch)  # câu cũ trái D-558
        for path in ("AGENTS.md", "framework/templates/AGENTS.md"):
            self.assertIn("`explore`", (ROOT / path).read_text(encoding="utf-8"), path)
        readme = (ROOT / "framework" / "templates" / "harness" / "README.md").read_text(encoding="utf-8")
        for vendor in ("anthropic", "openai"):
            for tier in ("bottom", "top-1", "top"):
                self.assertIn(TIERS["vendors"][vendor][tier]["id"], readme, f"README thiếu {vendor}/{tier}")
        self.assertTrue(re.search(r"top-1.*rà code", readme))
        for vendor in TIERS["unverified_vendors"]:
            self.assertTrue(TIERS["unverified_vendors"][vendor])


if __name__ == "__main__":
    unittest.main()
