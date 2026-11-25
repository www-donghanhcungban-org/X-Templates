"""Giao ước nghiệm thu độc lập của dự án cài và các cổng dùng sổ."""

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import xt

lock = xt.acceptance_module()


class AcceptanceLockTest(unittest.TestCase):
    spec = "docs/specs/SPEC-x.md"
    case = "acceptance/x.py"
    other = "acceptance/y.py"

    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.enterContext(patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.base)}))
        self.git("init", "-q")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "fixture@example.invalid")
        self.write(self.spec, "| Trạng thái | Approved |\n### S-101 đăng nhập\n### S-102 lưu\n")
        self.write(self.case, "# S-101\n")
        self.write(self.other, "# S-102\n")
        self.configure()
        self.write(
            "gate.py",
            "import pathlib,sys\np=pathlib.Path\np('junit.xml').write_bytes(p('input.xml').read_bytes())\nsys.exit(int(p('rc').read_text()))\n",
        )
        self.report()
        self.git("add", ".")
        self.git("commit", "-qm", "Khởi tạo")
        self.parser = xt.build_parser()

    def write(self, name, content):
        p = self.base / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.base), *args], text=True).strip()

    def configure(self, paths="acceptance", command="python3 gate.py", report="junit.xml"):
        self.write("xt.yaml", f'acceptance_paths: "{paths}"\nacceptance: "{command}"\nacceptance_report: "{report}"\n')

    def report(self, failed=True, names=None):
        names = names if names is not None else [self.case, self.other]
        cases = "".join(
            f'<testcase file="{name}" name="case-{i}">' + ("<failure/>" if failed else "") + "</testcase>"
            for i, name in enumerate(names)
        )
        self.write("input.xml", "<testsuite>" + cases + "</testsuite>")
        self.write("rc", str(int(failed)))

    def cli(self, *args, code=0, command="acceptance"):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            parsed = self.parser.parse_args([command, *args])
            actual = parsed.fn(parsed)
        output = stdout.getvalue() + stderr.getvalue()
        self.assertEqual(actual, code, output)
        return output

    def create(self, *args, code=0):
        return self.cli("lock", "--spec", self.spec, "--author", "acceptance-author", *args, code=code)

    def amend(self, did, *, reviewer="reviewer-alt", code=0):
        return self.cli(
            "amend", "--lock", "A-001", "--reviewer", reviewer, "--why", "Đổi tiêu chí", "--decision", did, code=code
        )

    def ledger(self):
        return json.loads((self.base / lock.LEDGER).read_bytes())

    def test_cli_red_then_green_and_real_release_gate(self):
        self.assertIn("chưa có bộ", self.cli("check", code=1))
        self.assertIn("A-001", self.create())
        first = self.ledger()
        self.assertEqual(first["locks"][0]["counts"], {self.case: 1, self.other: 1})
        self.create()
        self.assertEqual(self.ledger(), first)
        self.assertTrue(json.loads(self.cli("check", "--json"))["ok"])
        self.assertIn("khớp", self.cli("check"))
        self.report(False)
        run = xt._release_run(self.base, "BLUEPRINT.md", "acceptance", "nghiệm thu")
        row = lock.release_rows(xt, self.base, run)[0]
        self.assertEqual((row["result"], row["level"]), ("PASS", "BLOCKER"))
        self.assertIn("A-001", row["evidence"])
        self.write(self.case, "# S-101 bị sửa")
        self.assertIn(self.case, lock.release_rows(xt, self.base, run)[0]["evidence"])
        self.write(self.case, "# S-101\n")
        # Tổng vẫn là hai nhưng một file được thay bằng ca thứ hai của file khác.
        self.report(False, [self.case, self.case])
        run = xt._release_run(self.base, "BLUEPRINT.md", "acceptance", "")
        self.assertIn(self.other, lock.release_rows(xt, self.base, run)[0]["evidence"])
        self.write("junit.xml", "<testsuite/>")
        self.assertIn("thay đổi", lock.release_rows(xt, self.base, run)[0]["evidence"])
        self.assertEqual(lock.release_rows(xt, self.base, ({"result": "FAIL"}, None))[0]["result"], "FAIL")

    def test_structural_changes_cannot_green_a_task_or_release(self):
        self.create()
        self.write(self.case, "# S-101 sửa sau khoá")
        ev = self.cli("record", "--task", "T-010", "--", "true", command="loop", code=1)
        self.assertIn("A-001", ev)
        self.assertTrue(json.loads((self.base / ".autopilot/evidence/T-010.json").read_text())["acceptance_lock_red"])
        self.assertEqual(xt.loop_stats(self.base)["acceptance_red_tasks"], 1)
        with patch.object(xt, "read_runs", return_value=[{"executor": "acceptance-author"}]):
            out = json.loads(self.cli("check", "--json", code=1))
            self.assertEqual(out["author_executor_overlap"], ["A-001"])
            self.assertTrue(out["authors"]["A-001"]["session"])
        self.assertIn("amend", self.create(code=1))
        self.write(self.spec, "### S-101\n### S-102\n### S-103\n")
        self.write("acceptance/new.py", "# S-201\n")
        self.configure("", "python3 gate.py --thu-hep")
        check = self.cli("check", code=1)
        for text in ("A-001", "S-103", "acceptance/new.py", "lệnh acceptance"):
            self.assertIn(text, check)
        self.git("add", lock.LEDGER)
        self.git("commit", "-qm", "Khoá")
        self.write(lock.LEDGER, json.dumps({"schema": 1, "locks": [], "events": []}))
        self.assertIn("mất các khoá", self.cli("check", code=1))
        (self.base / lock.LEDGER).unlink()
        self.assertIn("trong Git", self.cli("check", code=1))

    def test_unmerged_lock_does_not_enable_acceptance_on_other_branches(self):
        self.configure("")
        self.git("add", "xt.yaml")
        self.git("commit", "-qm", "Nhánh gốc chưa bật nghiệm thu")
        previous = self.git("branch", "--show-current")
        self.git("switch", "--quiet", "-c", "feature-acceptance")
        self.configure()
        self.create()
        self.git("add", "xt.yaml", lock.LEDGER)
        self.git("commit", "-qm", "Khoá thử nghiệm ở nhánh tính năng")
        self.git("switch", "--quiet", previous)
        self.assertFalse(json.loads(self.cli("check", "--json"))["enabled"])
        self.write(lock.LEDGER, json.dumps({"schema": 1, "locks": [], "events": []}))
        self.assertFalse(json.loads(self.cli("check", "--json"))["enabled"])
        (self.base / lock.LEDGER).unlink()
        self.git("merge", "-q", "--ff-only", "feature-acceptance")
        (self.base / lock.LEDGER).unlink()
        self.assertIn("trong Git", self.cli("check", code=1))

    def test_amend_requires_new_decision_independent_actor_and_audit_trail(self):
        log = "docs/autopilot/DECISIONS.md"
        self.write(log, "### D-001 · 2020-01-01T00:00:00+00:00\nA-001\n")
        self.report(False)
        self.assertIn("phải đỏ", self.create(code=1))
        self.assertIn("D-999", self.create("--existing", "D-999", code=1))
        self.create("--existing", "D-001")
        first = self.ledger()["locks"][0]
        self.write(self.case, "# S-101 sửa có duyệt")
        self.assertIn("sau", self.amend("D-001", code=1))
        self.write(log, "### D-002 · 2099-01-01T00:00:00+00:00\nkhông nhắc khoá\n")
        self.assertIn("sau", self.amend("D-002", code=1))
        self.write(log, f"### D-003 · {xt.now_iso()}\nSửa A-001\n")
        self.assertIn("reviewer", self.amend("D-003", reviewer="acceptance-author", code=1))
        self.amend("D-003")
        self.assertEqual(self.ledger()["events"][-1]["previous"], first)
        self.assertEqual(xt.loop_stats(self.base)["acceptance_amendments"], 1)
        self.cli("check")

    def test_plan_requires_each_approved_spec(self):
        self.create()
        self.write(
            "docs/autopilot/PLAN.md",
            "[x](../specs/SPEC-x.md) [y](../specs/SPEC-y.md#mot) [sổ](README.md) [z](../specs/SPEC-z.md)\n",
        )
        self.write("docs/specs/SPEC-y.md", "| Trạng thái | Approved |\n### S-201\n")
        self.write("docs/specs/SPEC-z.md", "| Trạng thái | Draft |\n")
        self.assertIn("SPEC-y.md", self.cli("check", code=1))
        self.write("acceptance/y-new.py", "# S-201")
        self.report(True, [self.case, self.other, "acceptance/y-new.py"])
        self.cli("lock", "--spec", "docs/specs/SPEC-y.md", "--author", "external")
        self.cli("check")
        self.write("docs/specs/SPEC-z.md", "| Trạng thái | Approved |\n### S-101\n")
        self.assertIn("chỉ thuộc", self.cli("lock", "--spec", "docs/specs/SPEC-z.md", "--author", "external", code=1))
        with patch.object(xt, "read_state", return_value={"active": False}):
            self.cli("check")

    def test_lock_rejects_invalid_inputs_without_writing(self):
        self.assertIn("độc lập", self.cli("lock", "--spec", self.spec, "--author", "self", code=1))
        self.configure("", "")
        self.assertFalse(json.loads(self.cli("check", "--json"))["enabled"])
        self.write(lock.LEDGER, json.dumps({"schema": 1, "locks": [], "events": []}))
        self.assertFalse(json.loads(self.cli("check", "--json"))["enabled"])
        (self.base / lock.LEDGER).unlink()
        self.assertEqual(lock.release_rows(xt, self.base, ({}, None)), [])
        self.configure(command="")
        self.assertIn("Cần khai", self.create(code=1))
        self.configure()
        self.write(self.case, "# X-101")
        self.assertIn("S-101", self.create(code=1))
        self.write(self.spec, "# không có scenario\n")
        self.assertIn("thiếu tiêu đề", self.create(code=1))
        self.write(self.spec, "### S-102\n")
        (self.base / self.other).unlink()
        self.assertIn("S-102", self.create(code=1))
        self.write(self.other, "# S-102\n")
        self.report(True, [])
        self.assertIn("Thiếu ca", self.create(code=1))
        self.report(True, [self.other])
        self.write("rc", "0")
        self.write("docs/autopilot/DECISIONS.md", "### D-001 · 2020-01-01\n")
        self.assertIn("không khớp", self.create("--existing", "D-001", code=1))
        with patch.object(xt, "run_gate_shell", return_value=(126, "")):
            self.assertIn("Guard", self.create(code=126))
        with patch.object(xt, "run_gate_shell", return_value=(1, "")):
            self.assertIn("JUnit mới", self.create(code=1))
        (self.base / self.spec).unlink()
        self.assertIn("SPEC-x", self.create(code=2))
        self.assertFalse((self.base / lock.LEDGER).exists())

    def test_report_attribution_and_skips(self):
        raw = b'<testsuite><testcase classname="acceptance.x.Example"/><testcase classname="acceptance.y"/><testcase><skipped/></testcase></testsuite>'
        self.assertEqual(dict(lock.report_counts(raw, {self.case, self.other})[0]), {self.case: 1, self.other: 1})
        for raw in (
            b"<sarif/>",
            b'<testsuite><testcase classname="x"/></testsuite>',
            b'<testsuite><testcase file="/tmp/x"/></testsuite>',
        ):
            with self.assertRaises(ValueError):
                lock.report_counts(raw, {self.case})

    def test_snapshot_bounds_and_ledger_validation(self):
        (self.base / "acceptance/link").symlink_to("/dev/null")
        self.assertEqual(set(lock.snapshot(self.base, ["acceptance", self.case])), {self.case, self.other})
        with patch.object(lock, "MAX_FILES", 0), self.assertRaisesRegex(ValueError, "2 000"):
            lock.snapshot(self.base, ["acceptance"])
        with self.assertRaisesRegex(ValueError, "symlink"):
            lock.project_file(self.base, "../outside")
        with self.assertRaises(OSError):
            lock.raise_walk_error(OSError())
        self.create()
        doc = self.ledger()
        bad = [
            {},
            {**doc, "locks": []},
            {**doc, "locks": {}},
            {**doc, "locks": [{}]},
            {**doc, "locks": [{**doc["locks"][0], "cases": 0}]},
            {**doc, "locks": doc["locks"] * 2},
            {**doc, "events": [{}]},
            {**doc, "events": []},
        ]
        for item in bad:
            self.write(lock.LEDGER, json.dumps(item))
            self.assertFalse(json.loads(self.cli("check", "--json", code=1))["ok"])

    def test_review_protects_target_ledger_when_config_is_removed(self):
        self.create()
        self.git("add", lock.LEDGER)
        self.git("commit", "-qm", "Khoá")
        files = [self.case, self.spec, lock.LEDGER, "README.md"]
        self.assertEqual(lock.review_paths(xt, self.base, "HEAD", files), files[:-1])
        self.configure("")
        (self.base / lock.LEDGER).unlink()
        self.assertEqual(lock.review_paths(xt, self.base, "HEAD", files), files[:-1])
        self.write(lock.LEDGER, "{}")
        self.assertEqual(lock.review_paths(xt, self.base, "HEAD", files), files)

    def test_review_with_missing_remote_ref_does_not_read_the_index_ledger(self):
        self.create()
        self.git("add", lock.LEDGER)
        self.configure("")
        (self.base / lock.LEDGER).unlink()
        files = [self.case, self.spec, lock.LEDGER, "README.md"]
        self.assertEqual(lock.review_paths(xt, self.base, None, files), [lock.LEDGER])

    def test_gate_review_and_compatibility_for_opted_out_products(self):
        from tests.test_merge_review_source import std

        self.create()
        self.configure()
        with (self.base / "xt.yaml").open("a") as f:
            f.write("merge_autonomy: L3\nmerge_hard_exceptions: auto\nmerge_review: optional\ndelivery_phase: build\n")
        self.git("add", ".")
        self.git("commit", "-qm", "Duyệt thay đổi nghiệm thu")
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        decision, _ = xt._merge_eval(std() | {"files": [{"path": self.case}]})
        self.assertEqual(decision["verdict"], "review", decision)
        unrelated, _ = xt._merge_eval(std() | {"files": [{"path": "README.md"}]})
        self.assertEqual(unrelated["review"], "optional")
        with patch.object(xt, "SCRIPT_DIR", self.base):
            self.assertIsNone(xt.acceptance_module())
            self.assertIsNotNone(xt.build_parser())
        with patch.object(sys, "path", [p for p in sys.path if p != str(xt.SCRIPT_DIR)]):
            self.assertIs(xt.acceptance_module(), lock)
        (self.base / lock.LEDGER).unlink()
        self.assertEqual(self.cli("check", code=1).count("Git"), 1)

    def test_guard_classifies_ledger_as_machine_only(self):
        case = json.loads((ROOT / "tests/fixtures/autonomy/guard.json").read_text())["cases"][0]
        result = xt._bench_guard(case["input"], xt.BenchEnv(self.base))
        self.assertEqual({k: result[k] for k in case["expect"]}, case["expect"])
        guard = xt.BenchEnv(self.base).module("guard")
        self.assertEqual(guard.classify_path(lock.LEDGER), "evidence")
        self.assertEqual(guard.classify_path("docs/autopilot/ACCEPT*.json"), "evidence")

    def test_concurrent_write_and_input_changes_are_not_accepted(self):
        original = xt._state_lock

        @contextlib.contextmanager
        def competing(base):
            with original(base), patch.object(lock, "_ledger", return_value={"schema": 1, "events": [{}], "locks": []}):
                yield

        with patch.object(xt, "_state_lock", competing):
            self.assertIn("vừa đổi", self.create(code=1))
        snapshot = lock.snapshot
        with patch.object(lock, "snapshot", side_effect=[snapshot(self.base, ["acceptance"]), {}]):
            self.assertIn("thay đổi", self.create(code=1))
        with patch.object(xt, "_git_head", return_value=None):
            self.assertIn("commit Git", self.create(code=1))
        self.write("docs/autopilot/DECISIONS.md", "### D-012\nA-002\n")
        self.assertIn(
            "chưa tồn tại",
            self.cli(
                "amend", "--lock", "A-002", "--why", "Lý do", "--decision", "D-012", "--reviewer", "độc lập", code=1
            ),
        )
        self.assertFalse((self.base / lock.LEDGER).exists())
        with tempfile.TemporaryDirectory() as work:
            self.git("worktree", "add", "--quiet", "--detach", work, "HEAD")
            with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": work}):
                self.assertIn("điều phối", self.create(code=2))
