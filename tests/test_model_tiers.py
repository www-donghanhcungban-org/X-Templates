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

    def test_main_session_rule(self):
        self.assertEqual(
            TIERS["main_session"],
            {"plan_spec_decision": "top", "write_code": "top-1", "write_code_max_effort": "xhigh"},
        )
        self.assertLess(xt.EFFORTS.index("xhigh"), xt.EFFORTS.index("max"))  # reviewer `max` cao hơn người viết ≤ xhigh

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
