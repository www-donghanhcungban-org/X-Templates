"""Run the field and incident commands with local reports and Git refs controlled by each test."""

import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_xt_cli import TmpRepoCase, run_main, xt
from test_deploy_receipt import DIGEST, receipt
import xt_field as field


class FieldTriggerTest(TmpRepoCase):
    def setUp(self):
        super().setUp()
        self.init_repo()
        self.enterContext(mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.repo)}))
        self.now = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)
        self.doc = {
            "source": "rum",
            "exported_by": "field-job",
            "exported_at": self.now.isoformat(),
            "window": {"from": (self.now - dt.timedelta(minutes=10)).isoformat(), "to": self.now.isoformat()},
            "metrics": [{"name": "LCP", "percentile": 75, "segment": "mobile", "value_ms": 3100, "budget_ms": 2500}],
        }
        self.path = self.tmp / "field.json"

    def check(self, data, *opts):
        self.path.write_text(json.dumps(data))
        return run_main("perf", "field-check", "--file", str(self.path), *opts)

    def test_stdin_and_canonical_exit_codes(self):
        r = subprocess.run(
            [sys.executable, "-I", str(xt.SCRIPT_DIR / "xt.py"), "perf", "field-check", "--file", "-"],
            input=json.dumps(self.doc),
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual((r.returncode, r.stdout.strip()), (1, "LCP p75 3100 > 2500 ms"), r.stderr)
        self.assertEqual(json.loads(self.check(self.doc, "--json")[1])["verdict"], "regression")
        self.doc["metrics"][0]["budget_ms"] = 3100
        self.assertEqual(self.check(self.doc)[0], 0)
        self.doc["metrics"][0].pop("budget_ms")
        self.assertEqual(self.check(self.doc, "--json")[0], 0)
        self.assertEqual(self.check({"private": "never-echo"})[0], 2)
        self.assertNotIn("never-echo", self.check({"private": "never-echo"})[2])

    def test_reject_bad_evidence(self):
        old = (self.now - dt.timedelta(days=32)).isoformat()
        for patch in (
            {"source": None},
            {"exported_by": "!bad"},
            {"exported_at": old},
            {"exported_at": None},
            {"window": {"from": old, "to": old}},
            {"exported_at": "2025-01-01T00:00:00"},
            {"window": None},
            {"metrics": []},
            {"metrics": [1]},
            {"metrics": [{"name": "x", "value_ms": 8, "budget_pct": 1}]},
            {"metrics": [{"name": "x", "value_ms": True}]},
            {"metrics": [{"name": "x", "value_ms": 1, "percentile": 0}]},
            {"metrics": [{"name": "x", "value_ms": float("nan")}]},
            {"metrics": [{"name": "x", "value_bad$unit": 1}]},
            {"observation": []},
        ):
            with self.subTest(patch=patch):
                self.assertEqual(self.check({**self.doc, **patch})[0], 2)
        self.assertEqual(self.check([])[0], 2)
        self.assertIn("source", self.check({**self.doc, "source": ""})[2])
        for raw in (b"{", b" " * (field.MAX + 1)):
            self.path.write_bytes(raw)
            self.assertEqual(run_main("perf", "field-check", "--file", str(self.path))[0], 2)
        self.assertEqual(run_main("perf", "field-check", "--file", str(self.tmp / "absent"))[0], 2)

    def test_export_omit_private_data_and_setup_skip(self):
        cfg = self.repo / "xt.yaml"
        self.assertEqual(run_main("perf", "field-export")[0], 3)
        self.commit_files(
            {
                "xt.yaml": "field_export: python3 read_window.py\n",
                "read_window.py": "from pathlib import Path\nprint(Path('sample.json').read_text())\n",
                "sample.json": json.dumps({**self.doc, "private_header": "example-private"}),
            },
            1,
        )
        rc, out, err = run_main("perf", "field-export")
        self.assertEqual(rc, 0, err)
        self.assertEqual(json.loads(out)["metrics"], self.doc["metrics"])
        self.assertNotIn("private", out)
        (self.repo / "sample.json").write_text("bad")
        self.assertEqual(run_main("perf", "field-export")[0], 2)
        cfg.write_text("field_export: python3 missing.py\n")
        self.assertEqual(run_main("perf", "field-export")[0], 2)
        cfg.write_text("field_export: true\n")
        self.assertEqual(run_main("perf", "field-export")[0], 2)

    def test_raw_metrics_bind_receipt_and_revalidate_before_publication(self):
        start = (self.now - dt.timedelta(hours=2)).isoformat()
        record = receipt(started=start, finished=start)
        self.commit_files(
            {
                "xt.yaml": "field_env: dev\nfield_max_p95_ms: 50\nfield_max_error_pct: 0.5\n",
                "docs/ops/DEPLOYS.json": json.dumps(
                    {
                        "schema": 1,
                        "envs": {"dev": {"current": record, "previous": None, "unknown": False}},
                        "events": [record],
                    }
                ),
            },
            1,
        )
        raw = {
            "source": "telemetry",
            "env": "dev",
            "digest": DIGEST,
            "requests": 100,
            "errors": 1,
            "p95_ms": 45,
            "started": start,
            "finished": self.now.isoformat(),
            "exported_at": self.now.isoformat(),
            "private": "never-echo",
        }
        rc, text, err = self.check(raw, "--normalize")
        self.assertEqual(rc, 1, err)
        doc = json.loads(text)
        self.assertEqual(doc["observation"]["digest"], DIGEST)
        self.assertNotIn("private", text)
        self.assertEqual(self.check(doc, "--normalize")[1], text)
        self.assertEqual(self.check({**raw, "digest": "a" * 64})[0], 2)
        self.assertEqual(self.check({**raw, "env": "prod"})[0], 2)
        self.assertEqual(self.check({**raw, "requests": 0})[0], 2)
        (self.repo / "xt.yaml").write_text("field_env: dev\nfield_max_p95_ms: 0\nfield_max_error_pct: 0.5\n")
        self.assertEqual(self.check(raw)[0], 2)

    def test_loop_uses_newest_default_commit_and_deduplicates_plan(self):
        day = self.now.date().isoformat()
        # Ngày trong tên file phải trùng ngày UTC của `exported_at` (committed_field loại file lệch ngày).
        # Bản cũ xuất ở giữa đoạn từ 00:00 UTC tới `self.now`, không lùi một khoảng cố định:
        # lùi 10 phút làm test đỏ ngay sau nửa đêm.
        day_start = self.now.replace(hour=0, minute=0, second=0, microsecond=0)
        earlier = day_start + (self.now - day_start) / 2
        old = {
            **self.doc,
            "exported_at": earlier.isoformat(),
            "window": {"from": (earlier - dt.timedelta(hours=1)).isoformat(), "to": earlier.isoformat()},
            "metrics": [{"name": "LCP", "value_ms": 100, "budget_ms": 100}],
        }
        path = f"docs/ops/FIELD-{day}-235959Z.json"
        self.commit_files({f"docs/ops/FIELD-{day}.json": json.dumps(old), path: json.dumps(self.doc)}, 1)

        def next_step():
            rc, out, err = run_main("loop", "next-step", "--json", "--prs", "-", stdin="[]")
            self.assertEqual(rc, 0, err)
            return json.loads(out)

        self.assertEqual(next_step()["action"], "optimize")
        self.assertIn(path, next_step()["reason"])
        self.git("checkout", "-qb", "feature")
        self.commit_files({path: json.dumps(old)}, 2)
        self.assertEqual(next_step()["action"], "optimize")
        plan = self.repo / "docs/autopilot/PLAN.md"
        plan.parent.mkdir(parents=True)
        plan.write_text("- [ ] `T-001` Giảm LCP — Gate: `pytest`\n")
        self.assertNotEqual(next_step()["action"], "optimize")
        self.git("remote", "add", "origin", "https://example.invalid/project.git")
        self.assertEqual(field.committed_field(xt, self.repo, ""), {})
        self.git("update-ref", "refs/remotes/origin/main", self.git("rev-parse", "main"))
        self.assertIn("field", field.committed_field(xt, self.repo, ""))
        self.assertIn("field", xt._field_facts(self.repo, ""))
        with mock.patch.object(xt, "SCRIPT_DIR", self.tmp):  # minimal framework install without xt_field.py
            self.assertEqual(xt._field_facts(self.repo, ""), {})
        self.git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        self.assertIn("field", field.committed_field(xt, self.repo, ""))

    def test_incident_requires_visible_defined_test(self):
        put = self.repo / "post.md"
        cases = self.repo / "x.test.ts"
        cases.write_text(
            "/*\nit('hidden', () => 0);\n*/\nconst sample = `\nit('example', () => 0);\n`;\nit.skip('skipped', () => 0);\nit('renders', () => 1);\n"
        )
        header = "## 6. Hành động\n| Hành động | Loại |\n|---|---|\n"
        for ref, expected in (
            ("x.test.ts::renders", 0),
            ("x.test.ts::skipped", 1),
            ("x.test.ts::hidden", 1),
            ("x.test.ts::example", 1),
            ("../absent.ts::renders", 1),
        ):
            put.write_text(header + f"| `{ref}` | phòng ngừa |\n")
            rc, out, err = run_main("incident", "check", "post.md", "--json")
            self.assertEqual(rc, expected, err + out)
            self.assertEqual(json.loads(out)["missing_lines"], [4] if expected else [])
        for reason, expected in (("Mất kết nối nhà cung cấp chỉ diễn tập tại chỗ", 0), ("<lý do>", 1)):
            put.write_text(header + f"| không kiểm thử được — {reason} | phòng tái diễn |\n")
            self.assertEqual(run_main("incident", "check", "post.md")[0], expected)
        put.write_text(header + "| điều tra | vá |\n")
        self.assertEqual(run_main("incident", "check", "post.md")[0], 0)
        put.write_text("```md\n" + header + "| x | vá |\n```\n")
        self.assertEqual(run_main("incident", "check", "post.md")[0], 2)

    def test_field_inventory_rejects_non_report_or_bad_newest(self):
        day = self.now.date().isoformat()
        valid = f"docs/ops/FIELD-{day}.json"
        self.commit_files({"docs/ops/notes.json": "{}"}, 1)
        self.assertEqual(field.committed_field(xt, self.repo, ""), {})
        self.commit_files({"docs/ops/FIELD-2001-01-01.json": "{}", valid: json.dumps(self.doc)}, 2)
        self.assertIn("field", field.committed_field(xt, self.repo, ""))
        self.commit_files(
            {f"docs/ops/FIELD-{day}-231500Z.json": json.dumps({**self.doc, "exported_at": self.doc["window"]["from"]})},
            3,
        )
        self.assertEqual(field.committed_field(xt, self.repo, ""), {})
        self.commit_files({"docs/ops/FIELD-2999-01-01.json": json.dumps(self.doc)}, 4)
        self.assertEqual(field.committed_field(xt, self.repo, ""), {})

    def test_incident_matches_python_and_go_declarations(self):
        py = self.repo / "test_cases.py"
        py.write_text("async def test_async(): pass\nclass Case:\n    def test_x(self): pass\n")
        for name in ("test_async", "Case.test_x", "Case::test_x"):
            self.assertTrue(field.test_exists(self.repo, py.name, name))
        for name in ("test_absent", "Case.Test.Test_x", "Case.some"):
            self.assertFalse(field.test_exists(self.repo, py.name, name))
        py.write_text("def invalid(")
        self.assertFalse(field.test_exists(self.repo, py.name, "test_x"))
        go = self.repo / "ops_test.go"
        go.write_text("package ops\n/*\nfunc TestHidden(t *testing.T) {}\n*/\nfunc TestRetry(t *testing.T) {}\n")
        self.assertTrue(field.test_exists(self.repo, go.name, "TestRetry"))
        self.assertFalse(field.test_exists(self.repo, go.name, "TestHidden"))
        self.assertFalse(field.test_exists(self.repo, go.name, "Example"))
        other = self.repo / "plain.md"
        other.write_text("# Test")
        self.assertFalse(field.test_exists(self.repo, other.name, "Test"))

    def test_incident_diagnostics_preserve_original_lines(self):
        path = self.repo / "post.md"
        intro = "intro\n\n```\nexample\n```\n## 6. Hành động\n\n"
        header = "| Việc | Loại |\n|---|---|\n"
        path.write_text(intro + header + "| mất test | phòng ngừa |\n")
        self.assertIn("10", run_main("incident", "check", path.name)[1])
        path.write_text(intro + header + "| typo | phòng ngừ |\n")
        self.assertEqual(run_main("incident", "check", path.name)[0], 2)
        self.assertEqual(run_main("incident", "check", "../outside.md")[0], 2)
        self.assertEqual(run_main("incident", "check", "absent.md")[0], 2)

    def test_workflow_separates_read_secret_and_pr_writer(self):
        src = (xt.SCRIPT_DIR.parent / "framework/templates/xt-field.yml").read_text()
        reader, publisher = src.split("  publish:")
        self.assertIn("cron:", reader)
        self.assertIn("environment: xt-field-read", reader)
        self.assertIn("XT_FIELD_READ_TOKEN", reader)
        self.assertNotIn("XT_FIELD_READ_TOKEN", publisher)
        self.assertIn("perf field-check", publisher)
        self.assertIn("git diff --quiet", publisher)
        self.assertIn("gh pr create", publisher)
        # Audit delta 3.35.0: a PR opened with github.token starts no CI and may get 403; the scheduled payload has no
        # `repository`, so the base comes from the ref the reader job was restricted to.
        self.assertIn("GH_TOKEN: ${{ secrets.XT_STEWARD_TOKEN }}", publisher)
        for stale in ("${{ github.token }}", "pull-requests: write", "contents: write", "github.event.repository"):
            self.assertNotIn(stale, publisher)
        self.assertIn("BASE: ${{ github.ref_name }}", publisher)

    def test_field_report_pr_needs_the_steward_token(self):
        src = (xt.SCRIPT_DIR.parent / "framework/templates/xt-field.yml").read_text()
        script = "\n".join(line.removeprefix(" " * 10) for line in src.split("        run: |\n")[-1].splitlines())
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        log = self.tmp / "calls"
        fakes = {"gh": 'echo "gh $*" >> "$LOG"\n', "git": 'echo "git $*" >> "$LOG"\n[ "$1" != ls-remote ] || exit 2\n'}
        for name, body in fakes.items():
            (bin_dir / name).write_text("#!/bin/sh\n" + body)
            (bin_dir / name).chmod(0o755)
        env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "LOG": str(log), "BASE": "trunk", "STAMP": "s"}

        def publish(value):
            return subprocess.run(
                ["bash", "-eo", "pipefail", "-c", script],
                env={**env, "GH_TOKEN": value},
                capture_output=True,
                text=True,
                timeout=30,
            )

        denied = publish("")
        self.assertEqual(denied.returncode, 1)
        self.assertIn("::error::", denied.stdout)
        self.assertFalse(log.exists())
        self.assertEqual(publish("steward").returncode, 0)
        calls = log.read_text().splitlines()
        self.assertIn("git push origin HEAD:refs/heads/xt-field/s", calls)
        self.assertIn("gh pr create --base trunk --head xt-field/s", calls[-1])
