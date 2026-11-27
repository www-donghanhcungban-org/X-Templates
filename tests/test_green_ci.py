"""Trả nợ review 🟢 nhóm CI/phụ thuộc (T-3921): AUD-DEP-023, AUD-DEP-025, AUD-DEP-028."""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GITHUB = ROOT / ".github"


class GreenCiTest(unittest.TestCase):
    def test_pack_npm_audit_is_required_check_and_a_real_job(self):
        """AUD-DEP-023: người merge tay trên giao diện cũng bị chặn khi `pnpm audit` đỏ; tên context = `name:` của job."""
        rules = json.loads((GITHUB / "rulesets" / "main.json").read_text(encoding="utf-8"))["rules"]
        status = next(r for r in rules if r["type"] == "required_status_checks")["parameters"]
        contexts = [c["context"] for c in status["required_status_checks"]]
        self.assertIn("pack-npm-audit", contexts)
        workflow = (GITHUB / "workflows" / "dep-audit.yml").read_text(encoding="utf-8")
        self.assertRegex(workflow, r"(?m)^  pack-npm-audit:\n    name: pack-npm-audit$")

    def test_dependabot_cooldown_is_at_least_seven_days(self):
        """AUD-DEP-025: zizmor `dependabot-cooldown` đòi ≥ 7 ngày ở mọi khối (đo bằng zizmor 1.32.0: 3 khối đều cảnh báo)."""
        text = (GITHUB / "dependabot.yml").read_text(encoding="utf-8")
        days = [int(d) for d in re.findall(r"(?m)^\s+default-days:\s*(\d+)\s*$", text)]
        self.assertEqual(len(days), text.count("package-ecosystem:"))
        self.assertTrue(days and min(days) >= 7, days)

    def test_scope_reason_names_pnpm_audit(self):
        """AUD-DEP-028: lý do của nhóm "CI, ruleset, phụ thuộc" nêu đủ lớp đỡ của AUD-DEP-021."""
        scope = json.loads((ROOT / "tests" / "fixtures" / "autonomy" / "scope.json").read_text(encoding="utf-8"))
        groups = scope["out_of_scope"]
        reason = next(g["reason"] for g in groups if g["reason"].startswith("CI, ruleset, phụ thuộc"))
        self.assertIn("`pnpm audit`", reason)
        self.assertIn("pack-npm-audit", reason)

    def test_all_non_pushing_checkouts_disable_persist_credentials(self):
        """AUD-CI-007: chỉ hai job `tag` và `tag-app` của release-tag.yml giữ credential để đẩy tag."""
        for wf in sorted((GITHUB / "workflows").glob("*.yml")):
            text = wf.read_text(encoding="utf-8")
            checkouts = len(re.findall(r"uses:\s+actions/checkout@", text))
            disabled = len(re.findall(r"persist-credentials:\s+false\b", text))
            expected = checkouts - (2 if wf.name == "release-tag.yml" else 0)
            self.assertEqual(disabled, expected, f"{wf.name}: {disabled}/{expected} persist-credentials: false")


if __name__ == "__main__":
    unittest.main()
