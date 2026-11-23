"""T-4004 (AUD-HAR-460, D-535): tài liệu có lệnh chạy được tính nợ review theo DÒNG ĐỔI — sửa mô tả thuần không sinh nợ,
đổi lệnh `Kiểm:` / Gate / `- grant:` / lệnh trong mẫu thì tính như mã."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import xt
from test_xt import audit_status_text

BLUEPRINT = (
    "# Blueprint\n\n"
    '- [x] `BASE-X-001` **MUST** Mô tả ban đầu. — Kiểm: `python3 -c "print(1)"`\n'
    "- [ ] `BASE-X-002` **SHOULD** Việc khác.\n"
)
PLAN = (
    "# PLAN\n\n"
    "- [ ] `T-9001` Làm việc A (files: src/) — Gate: `python3 -m unittest tests.test_a`\n"
    "- grant: deploy env=staging\n"
    "Ghi chú tự do.\n"
)
TEMPLATE = "# Mẫu\n\nChạy `<XT> loop status` để xem trạng thái.\nVăn xuôi giải thích.\n"


class ExecutableDocsDebtTest(unittest.TestCase):
    def setUp(self):
        self.repo = Path(self.enterContext(tempfile.TemporaryDirectory(ignore_cleanup_errors=True))).resolve()
        self.enterContext(unittest.mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.repo)}))
        self.git("init", "-q", "-b", "main")
        for rel, text in {
            "BLUEPRINT.md": BLUEPRINT,
            "docs/autopilot/PLAN-x.md": PLAN,
            "framework/templates/PLAN.md": TEMPLATE,
            "docs/note.md": "ghi chú\n",
        }.items():
            self.write(rel, text)
        self.status = self.repo / "docs" / "ops" / "AUDIT-STATUS.md"
        self.write("docs/ops/AUDIT-STATUS.md", audit_status_text())
        self.git("add", "-A")
        self.git("commit", "-qm", "c0")
        self.base = self.git("rev-parse", "HEAD")
        rows = {1: ("đã quét", self.base, "2026-11-23", "quét"), 9: ("đã quét", self.base, "2026-11-23", "quét")}
        self.status.write_text(audit_status_text(rows), encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", "sổ")

    def git(self, *args: str) -> str:
        cfg = ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false"]
        cfg += ["-c", "maintenance.auto=false", "-c", "gc.auto=0"]
        r = subprocess.run(["git", "-C", str(self.repo), *cfg, *args], capture_output=True, text=True, check=True)
        return r.stdout.strip()

    def write(self, rel: str, text: str) -> None:
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def debt(self, rel: str, text: str) -> list[str]:
        self.write(rel, text)
        self.git("add", "-A")
        self.git("commit", "-qm", f"đổi {rel}")
        return xt.review_debt(self.repo, self.status)[0]

    def test_prose_only_edit_creates_no_debt(self):
        self.assertEqual(self.debt("BLUEPRINT.md", BLUEPRINT.replace("Mô tả ban đầu", "Mô tả đã viết lại")), [])
        self.assertEqual(self.debt("docs/autopilot/PLAN-x.md", PLAN.replace("Ghi chú tự do", "Ghi chú khác")), [])

    def test_changed_check_command_is_debt(self):
        text = BLUEPRINT.replace("print(1)", "print(2)")
        self.assertEqual(self.debt("BLUEPRINT.md", text), ["BLUEPRINT.md"])

    def test_removed_or_added_check_line_is_debt(self):
        text = BLUEPRINT + "- [x] `BASE-X-003` **MUST** Mới. — Kiểm: `true`\n"
        self.assertEqual(self.debt("BLUEPRINT.md", text), ["BLUEPRINT.md"])

    def test_plan_gate_and_grant_lines_are_debt(self):
        self.assertEqual(
            self.debt("docs/autopilot/PLAN-x.md", PLAN.replace("tests.test_a", "tests.test_b")),
            ["docs/autopilot/PLAN-x.md"],
        )

    def test_plan_grant_line_is_debt(self):
        self.assertEqual(
            self.debt("docs/autopilot/PLAN-x.md", PLAN.replace("env=staging", "env=prod")),
            ["docs/autopilot/PLAN-x.md"],
        )

    def test_template_command_is_debt(self):
        self.assertEqual(
            self.debt("framework/templates/PLAN.md", TEMPLATE.replace("loop status", "loop next-step")),
            ["framework/templates/PLAN.md"],
        )

    def test_other_docs_never_count(self):
        self.assertEqual(self.debt("docs/note.md", "ghi chú — Kiểm: `rm -rf /`\n"), [])

    def test_untouched_exec_doc_is_not_debt_and_unrelated_plan_name_is_doc(self):
        self.assertEqual(xt.review_debt(self.repo, self.status)[0], [])
        self.assertEqual(self.debt("docs/autopilot/NOTES.md", "- Gate: `x`\n"), [])


if __name__ == "__main__":
    unittest.main()
