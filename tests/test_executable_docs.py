"""Nợ review từ các lệnh thực thi ở hai cây Git (AUD-HAR-460, AUD-HAR-478)."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unicodedata
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
    '- [x] `BASE-X-001` **MUST** Mô tả ban đầu. → Kiểm: đọc kết quả. — Kiểm: `python3 -c "print(1)"`\n'
    "- [ ] `BASE-X-002` **SHOULD** Việc khác.\n"
)
PLAN = (
    "# PLAN\n\n"
    "- [ ] `T-9001` Làm việc A (files: src/) — Gate: `python3 -m unittest tests.test_a`\n"
    "- grant: deploy | env=staging\n"
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

    def commit_file(self, rel, text):
        self.write(rel, text)
        self.git("add", "--", rel)
        if self.git("diff", "--cached", "--name-only"):
            self.git("commit", "-qm", f"fixture {rel}")
        return self.git("rev-parse", "HEAD")

    def debt_since(self, sha):
        rows = {n: ("đã quét", sha, "2026-11-23", "quét") for n, _, _ in xt.AUDIT_GROUPS}
        self.status.write_text(audit_status_text(rows), encoding="utf-8")
        return xt.review_debt(self.repo, self.status)[0]

    def check_edit(self, rel, before, after, expected):
        sha = self.commit_file(rel, before)
        self.commit_file(rel, after)
        self.assertEqual(self.debt_since(sha), expected)

    def test_gate_pairing_and_duplicate_task_order(self):
        rel = "docs/specs/PLAN-y.md"
        for ids in (("T-101", "T-102"), ("T-101", "T-101")):
            with self.subTest(ids=ids):
                rows = [f"- [ ] `{task}` — Gate: " for task in ids]
                before = rows[0] + "`true`\n" + rows[1] + "`false`\n"
                after = rows[0] + "`false`\n" + rows[1] + "`true`\n"
                self.check_edit(rel, before, after, [rel])
        without, with_gate = "- [ ] `T-101` Việc khác\n", "- [ ] `T-101` — Gate: `true`\n"
        self.check_edit(rel, without + with_gate, with_gate + without, [rel])
        self.check_edit(rel, PLAN, PLAN.replace("tests.test_a", "tests.test_b"), [rel])
        rel = "docs/autopilot/PLAN-x.md"
        start = "- [ ] `T-101` — Gate: `true`\n- [ ] `T-102` — Gate: `false`\n"
        self.check_edit(
            rel, start, start.replace("T-101", "T-103").replace("T-102", "T-101").replace("T-103", "T-102"), [rel]
        )

    def test_grants_respect_case_fences_and_last_definition(self):
        rel = "docs/autopilot/PLAN-x.md"
        active = PLAN.replace("grant:", "Grant:")
        self.check_edit(rel, active, active.replace("env=staging", "env=other"), [rel])
        for before in ("~~~\n" + active + "~~~\n", active + "- grant: deploy | env=final\n"):
            with self.subTest(before=before):
                self.check_edit(rel, before, before.replace("env=staging", "env=local"), [])

    def test_blueprint_and_plan_prose_are_not_executable(self):
        bp = "BLUEPRINT.md"
        self.check_edit(bp, BLUEPRINT, BLUEPRINT.replace("đọc kết quả", "xem báo cáo"), [])
        note = BLUEPRINT.replace("[ ] `BASE-X-002`", "[x] `BASE-X-002`").replace(
            "Việc khác.", "Việc khác. — Bằng chứng: log"
        )
        self.check_edit(bp, BLUEPRINT, note, [])
        self.check_edit("docs/autopilot/PLAN-x.md", PLAN, PLAN + "- Timeout Gate: `note`\n- [ ] `T-999` Việc sau\n", [])
        self.check_edit(bp, "# one\n", "# two\n", [])

    def test_commands_match_runtime_normalization_and_git_binary_classification(self):
        for source in (
            BLUEPRINT.replace("— Kiểm:", "— Kiểm :"),
            unicodedata.normalize("NFD", BLUEPRINT),
            BLUEPRINT + "\x00\n",
            BLUEPRINT.replace("\n", "\r\n"),
        ):
            with self.subTest(source=source):
                self.check_edit("BLUEPRINT.md", source, source.replace("print(1)", "print(2)"), ["BLUEPRINT.md"])
        invalid = BLUEPRINT.replace("print(1)", r"print(\`one\`)")
        self.assertEqual(xt._scan_checks(invalid, "BLUEPRINT.md")[0][0]["cmd"], "")
        self.check_edit("BLUEPRINT.md", BLUEPRINT, invalid, ["BLUEPRINT.md"])
        self.check_edit("BLUEPRINT.md", invalid, invalid.replace("one", "two"), [])

    def test_bound_backlog_and_changed_binding_are_debt(self):
        bp, path = "BLUEPRINT.md", "extra/checks.md"
        self.commit_file(path, BLUEPRINT)
        self.commit_file("empty.md", "# Backlog\n")
        before = "---\nbacklog: empty.md\n---\n" + BLUEPRINT
        after = before.replace("empty.md", path)
        self.check_edit(bp, before, after, [bp])
        self.check_edit(path, BLUEPRINT, BLUEPRINT.replace("print(1)", "print(2)"), [path])
        # Chỉ bản quét còn liên kết. Xoá cả hai vẫn phải ghi nhận lệnh cũ của backlog.
        sha = self.git("rev-parse", "HEAD")
        self.git("rm", bp, path)
        self.git("commit", "-qm", "remove")
        self.assertEqual(self.debt_since(sha), [bp, path])

    def test_empty_or_unreadable_sources(self):
        docs = {"docs/note.md"}
        self.assertEqual(xt._changed_exec_docs(self.repo, self.base, set()), set())
        with unittest.mock.patch.object(xt, "sibling_exists", side_effect=lambda name: name != "xt_distribution.py"):
            self.assertEqual(xt._changed_exec_docs(self.repo, self.base, docs), docs)
        self.assertTrue(xt._exec_doc_edited(self.repo, "missing-revision", "docs/note.md"))
        self.git("rm", "BLUEPRINT.md")
        (self.repo / "BLUEPRINT.md").symlink_to("docs/note.md")
        self.git("add", "BLUEPRINT.md")
        self.git("commit", "-qm", "link")
        self.assertEqual(xt._changed_exec_docs(self.repo, self.base, docs), docs)

    def test_unresolved_backlog_path_keeps_document_for_review(self):
        bp = "BLUEPRINT.md"
        self.commit_file(bp, "---\nbacklog: missing.md\n---\n" + BLUEPRINT)
        self.check_edit("docs/note.md", "one", "two", [])
        self.commit_file("examples/note.md", BLUEPRINT)
        (self.repo / "via").symlink_to("examples", target_is_directory=True)
        self.git("add", "via")
        self.git("commit", "-qm", "alias")
        self.commit_file(bp, "---\nbacklog: via/note.md\n---\n" + BLUEPRINT)
        self.check_edit("examples/note.md", BLUEPRINT, BLUEPRINT.replace("print(1)", "print(2)"), ["examples/note.md"])

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
