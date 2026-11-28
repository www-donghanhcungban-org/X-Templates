"""Installed CLI contracts for owner setup, localhost rehearsal and offline operations feedback."""

import base64
import datetime as dt
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from threading import Thread
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_deploy_receipt import receipt
from test_xt_cli import TmpRepoCase, run_main, xt
from test_admin_plan import GithubFixture
import xt_release_ops as release_ops


class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.seen.append((self.path, self.headers.get("Authorization")))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "digest": self.server.digest}).encode())

    def log_message(self, *_):
        pass


class RehearsalTest(GithubFixture, TmpRepoCase):
    def setUp(self):
        super().setUp()
        self.init_repo()
        self.enterContext(mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.repo)}))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Health)
        self.addCleanup(self.server.server_close)
        t = Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        t.start()
        self.addCleanup(t.join)
        self.addCleanup(self.server.shutdown)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        head = self.commit_files(
            {
                "xt.yaml": f"deploy_envs: dev\ndeploy_env_pass:\nrelease_artifacts: package.bin\nurl_dev: {self.url}\n",
                ".gitignore": "package.bin\n",
                "VERSION": "1.2.0\n",
                "app.txt": "version A",
            },
            1,
        )
        (self.repo / "package.bin").write_bytes(b"artifact A")
        _, artifacts = xt._release_artifacts(self.repo)
        candidate, why = xt._release_subject(self.repo, artifacts, head, tree_readable=True)
        self.assertFalse(why)
        self.subject = {key: candidate[key] for key in ("content", "digest", "head")}
        self.server.seen = []
        self.server.digest = self.subject["digest"]
        at = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=4)).isoformat()
        self.record = receipt(
            started=at,
            finished=at,
            subject=self.subject,
            served_digest=self.server.digest,
            url=self.url,
            artifacts=[{k: v for k, v in a.items() if k in ("path", "sha256")} for a in artifacts],
        )
        self.ledger = self.repo / "docs/ops/DEPLOYS.json"
        self.ledger.parent.mkdir(parents=True)
        self.ledger.write_text(
            json.dumps(
                {
                    "schema": 1,
                    "envs": {"dev": {"current": self.record, "previous": None, "unknown": False}},
                    "events": [self.record],
                }
            )
        )

    def drill(self, *flags):
        rc, text, _ = run_main("rollout-drill", "--env", "prod", "--json", *flags)
        return rc, json.loads(text)

    def test_real_http_and_target_readiness_are_distinct(self):
        original = self.ledger.read_bytes()
        code, doc = self.drill()
        self.assertEqual(code, 0, doc)
        self.assertTrue(doc["dev_verified"])
        self.assertEqual(doc["handoff"], "pending")
        self.assertFalse(doc["deployed_to_target"])
        self.assertEqual(self.server.seen, [("/healthz", None)])
        self.assertEqual(self.drill("--require-ready")[0], 1)
        self.assertEqual(self.ledger.read_bytes(), original)
        self.server.digest = "a" * 64
        self.assertEqual(self.drill()[0], 1)
        self.assertEqual(self.ledger.read_bytes(), original)

    def test_protected_handoff_and_remote_negative_cases(self):
        signature = "docs/ops/GO-NO-GO-v1.2.0.md"
        signed = (
            "# GO/NO-GO v1.2.0\n\n"
            + "\n".join(xt.subject_lines(self.subject))
            + "\n\n## 5. Ký\n\n| Vai trò | Tên | Quyết định | Ngày |\n|---|---|---|---|\n"
            f"| Chủ repo | Fixture signer | GO | {dt.datetime.now(dt.timezone.utc).date()} |\n"
        )
        (self.repo / signature).write_text(signed)
        self.git("add", ".")
        self.git("commit", "-qm", "Lưu receipt và chữ ký mẫu trong fixture")
        self.fake_github()
        routes = self.tmp / "routes.json"
        cfg = json.loads(routes.read_text())
        head = self.git("rev-parse", "HEAD")
        compare = f"compare/{head}...{head}"
        plan = f"contents/docs/autopilot/PLAN.md?ref={head}"
        rules = f"contents/xt.yaml?ref={head}"
        encode = lambda text: {"encoding": "base64", "content": base64.b64encode(text.encode()).decode()}
        cfg[compare] = {"status": "identical"}
        cfg[f"contents/{signature}?ref={head}"] = encode(signed)
        report = self.tmp / "release.json"
        artifact_row, artifacts = xt._release_artifacts(self.repo)
        tree, _, readable = xt._release_tree(self.repo)
        subject, why = xt._release_subject(self.repo, artifacts, head, tree_readable=readable, tree_clean=True)
        self.assertFalse(why)
        gates = {key: {"id": key, "result": "PASS", "level": "BLOCKER"} for key in xt.RELEASE_ROWS}
        for gate in (
            artifact_row,
            tree,
            xt._release_verify(self.repo),
            xt._release_stage(self.repo),
            *xt._release_deploy(self.repo, subject),
        ):
            gates[gate["id"]] = gate
        good = {
            "schema": xt.RELEASE_SCHEMA,
            "go": True,
            "head": head,
            "fails": [],
            "human": [],
            "subject": subject,
            "artifacts": artifacts,
            "promotion": {"state": "approved"},
            "at": xt.now_iso(),
            "verdict": "GO",
            "rows": list(gates.values()),
        }
        report.write_text(json.dumps(good))

        def check(changes=None):
            routes.write_text(json.dumps({**cfg, **(changes or {})}))
            return self.drill("--require-ready", "--release", str(report))

        code, doc = check()
        self.assertEqual((code, doc["handoff"]), (0, "ready_for_pipeline_review"), doc)
        self.assertFalse(doc["deployed_to_target"])
        adapter = "deploy_envs: dev prod\n" + "".join(
            f"{key}_prod: ./adapter {key}\n" for key in ("deploy", "smoke", "digest", "rollback")
        )
        for key, changes in [
            ("ancestor", {compare: {"status": "diverged"}}),
            ("remote_grant", {plan: encode("- grant: deploy | env=staging")}),
            ("protected_signoff", {f"contents/{signature}?ref={head}": encode(signed.replace("| GO |", "| NO-GO |"))}),
            ("declared_secret_names", {"actions/secrets?per_page=100&page=1": {"secrets": []}}),
            ("target_adapter", {rules: encode(adapter)}),
            ("target_adapter", {rules: encode(adapter + "deploy_env_pass: null\n")}),
            ("target_env_pass_matches", {rules: encode(adapter + "deploy_env_pass: EXAMPLE_SETTING\n")}),
            (
                "target_adapter",
                {
                    rules: encode(
                        "deploy_envs: dev prod\ndeploy_prod: deploy\nrollback_prod: undo\nsmoke_prod: true\ndigest_prod: :"
                    )
                },
            ),
        ]:
            rc, result = check(changes)
            self.assertEqual(rc, 1, key)
            self.assertFalse(result["preflight"][key], key)
        # Gate state can change without a git change: a snapshot that was valid above no longer binds.
        machine = self.repo / ".autopilot/state.json"
        machine.parent.mkdir(exist_ok=True)
        machine.write_text("{invalid")
        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        rc, changed = check()
        self.assertEqual(rc, 1)
        self.assertFalse(changed["preflight"]["release_report"])
        machine.unlink()
        report.write_text(json.dumps({**good, "head": "0" * 40}))
        rc, result = check()
        self.assertEqual(rc, 1)
        self.assertFalse(result["preflight"]["release_report"])
        report.write_text(json.dumps(good))
        (self.repo / "PROGRESS.md").write_text("excluded from subject but uncommitted")
        rc, result = check()
        self.assertEqual(rc, 1)
        self.assertFalse(result["preflight"]["clean_checkout"])

    def test_rollback_starts_new_observation_window(self):
        doc = json.loads(self.ledger.read_text())
        confirmed = dt.datetime.fromisoformat(self.record["finished"]) + dt.timedelta(hours=1)
        event = {
            **self.record,
            "result": "rolled_back",
            "previous_digest": self.subject["digest"],
            "rollback": self.record["deploy"],
            "finished": confirmed.isoformat(),
        }
        doc["events"].append(event)
        self.ledger.write_text(json.dumps(doc))
        self.assertEqual(release_ops.confirmed_after(xt, self.repo, "dev", self.subject["digest"]), confirmed)
        for offset, allowed in [(-30, False), (1, True)]:
            start = confirmed + dt.timedelta(minutes=offset)
            data = {
                "env": "dev",
                "digest": self.subject["digest"],
                "source": "metrics",
                "started": start.isoformat(),
                "finished": (start + dt.timedelta(seconds=5)).isoformat(),
                "exported_at": (start + dt.timedelta(seconds=6)).isoformat(),
                "requests": 1,
                "errors": 0,
                "p95_ms": 1,
            }
            path = self.tmp / "sample.json"
            path.write_text(json.dumps(data))
            rc, out, _ = run_main(
                "ops-check", "--env", "dev", "--field", str(path), "--max-p95-ms", "1", "--max-error-pct", "0", "--json"
            )
            self.assertEqual(rc, int(not allowed), out)

    def test_stale_artifact_and_stale_source(self):
        for path in ("package.bin", "app.txt"):
            p = self.repo / path
            original = p.read_bytes()
            p.write_bytes(b"B")
            self.assertEqual(self.drill()[0], 1, path)
            p.write_bytes(original)
        self.assertFalse(self.server.seen)

    def test_probe_rejects_nonlocal_origin_and_credentials(self):
        for url in (
            "https://service.example",
            "http://admin:invisible@127.0.0.1",
            self.url + "/admin",
            self.url + "?token=demo",
        ):
            self.assertIsNone(release_ops.dev_health(url))
        self.assertFalse(self.server.seen)

    def test_field_exit_codes_redaction_and_rollout_window(self):
        start = dt.datetime.fromisoformat(self.record["finished"])
        data = {
            "env": "dev",
            "digest": self.server.digest,
            "started": start.isoformat(),
            "finished": (start + dt.timedelta(seconds=60)).isoformat(),
            "requests": 200,
            "source": "prometheus",
            "exported_at": (start + dt.timedelta(seconds=61)).isoformat(),
            "errors": 1,
            "p95_ms": 40,
            "private_header": "do-not-log",
        }
        file = self.tmp / "field.json"
        args = (
            "ops-check",
            "--env",
            "dev",
            "--field",
            str(file),
            "--max-p95-ms",
            "50",
            "--max-error-pct",
            "0.5",
            "--json",
        )
        for patch, expect in [
            ({}, "pass"),
            ({"errors": 2}, "regression"),
            ({"source": True}, "invalid_evidence"),
            ({"exported_at": start.isoformat()}, "invalid_evidence"),
            ({"p95_ms": 51}, "regression"),
            ({"digest": "a" * 64}, "invalid_evidence"),
            ({"requests": 0}, "invalid_evidence"),
            ({"started": (start - dt.timedelta(seconds=5)).isoformat()}, "invalid_evidence"),
        ]:
            file.write_text(json.dumps({**data, **patch}))
            rc, text, _ = run_main(*args)
            self.assertEqual(rc, int(expect != "pass"))
            self.assertEqual(json.loads(text)["verdict"], expect)
            self.assertNotIn("do-not-log", text)

    def test_ancestor_inventory_detects_missing_and_additional_remote_refusal(self):
        origin = mock.Mock(sha="a" * 40, tree_sha=None, prefix="apps/web/")
        root = self.repo / "apps/web"
        doc = "apps/web/docs/ops/GO-NO-GO-1.md"
        head = self.commit_files({doc: "signed", "outside.md": "other"}, 2)
        self.assertFalse(release_ops.signature_inventory(xt, root, origin, head))
        sha = self.git("rev-parse", f"{head}:{doc}")
        origin.tree_sha = self.git("rev-parse", "HEAD^{tree}")
        origin.get.return_value = {"truncated": True, "tree": []}
        self.assertFalse(release_ops.signature_inventory(xt, root, origin, head))
        tree = [{"path": doc, "sha": sha}, {"path": "other-repo/GO-NO-GO.md", "sha": sha}]
        origin.get.return_value = {"truncated": False, "tree": tree}
        self.assertTrue(release_ops.signature_inventory(xt, root, origin, head))
        self.assertFalse(release_ops.signature_inventory(xt, root, origin, "1" * 40))
        tree.append({"path": "apps/web/GO-NO-GO-other.md", "sha": sha})
        self.assertFalse(release_ops.signature_inventory(xt, root, origin, head))
        tree.append({"path": False})
        self.assertFalse(release_ops.signature_inventory(xt, root, origin, head))

    def test_missing_authorization_source_and_invalid_commands(self):
        self.assertEqual(run_main("rollout-drill", "--env", "dev")[0], 2)
        self.assertEqual(
            run_main(
                "ops-check", "--env", "invalid!", "--field", "unused", "--max-p95-ms", "10", "--max-error-pct", "1"
            )[0],
            2,
        )
        self.assertEqual(
            run_main("ops-check", "--env", "dev", "--field", "unused", "--max-p95-ms", "0", "--max-error-pct", "1")[0],
            2,
        )
        (self.repo / "package.bin").unlink()
        rc, text, _ = run_main("rollout-drill", "--env", "prod")
        self.assertEqual(rc, 1)
        self.assertIn("release_artifacts", text)
        (self.repo / "package.bin").write_bytes(b"artifact A")
        with mock.patch.object(xt, "_release_subject", return_value=({}, "unreadable")):
            self.assertEqual(self.drill()[0], 1)
        rc, text, _ = run_main("rollout-drill", "--env", "prod")
        self.assertEqual(rc, 0)
        self.assertIn("preflight:", text)
        bad = self.tmp / "evidence.json"
        for content in (b"[]", b"1" * (2 * 1024 * 1024 + 1)):
            bad.write_bytes(content)
            self.assertFalse(release_ops.release_report(self.repo, str(bad), self.subject))

    def test_failed_agent_or_outdated_signer_is_not_approval(self):
        origin = mock.Mock(sha=self.subject["head"], cfg={})
        for decision, signer, date in (
            ("GO", "fixture", "2000-01-01"),
            ("GO", "agent", dt.datetime.now(dt.timezone.utc).date().isoformat()),
        ):
            path = "docs/ops/GO-NO-GO-v1.2.0.md"
            body = (
                "# GO/NO-GO v1.2.0\n\n"
                + "\n".join(xt.subject_lines(self.subject))
                + "\n\n## 5. Ký\n\n"
                + f"| Vai trò | Tên | Quyết định | Ngày |\n|---|---|---|---|\n| Chủ repo | {signer} | {decision} | {date} |\n"
            )
            (self.repo / path).write_text(body)
            origin.file.return_value = body
            self.assertFalse(release_ops.protected_signoff(xt, self.repo, origin, self.subject))

    def test_unhealthy_runtime_unobserved_state_and_stale_field_window(self):
        with mock.patch.object(Health, "do_GET", lambda handler: handler.send_error(503)):
            self.assertIsNone(release_ops.dev_health(self.url))
        self.assertIsNone(release_ops.dev_health("http://127.0.0.1:99999"))
        data = json.loads(self.ledger.read_text())
        data["events"] = []
        self.ledger.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            release_ops.confirmed_after(xt, self.repo, "dev", self.subject["digest"])
        data["envs"]["dev"].update(current=None, unknown=True)
        self.ledger.write_text(json.dumps(data))
        self.assertIsNone(release_ops.current(xt, self.repo, "dev"))
        with self.assertRaises(ValueError):
            release_ops.field_metrics({"requests": 2, "errors": 0, "p95_ms": -1})
        with self.assertRaises(ValueError):
            release_ops.field_window(
                xt,
                {"started": self.record["finished"], "finished": xt.now_iso(), "exported_at": xt.now_iso()},
                dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc),
                0,
            )
        field = self.tmp / "bad-field.json"
        field.write_text('{"source":"prometheus","env":"dev","digest":false}')
        self.assertEqual(
            run_main("ops-check", "--env", "dev", "--field", str(field), "--max-p95-ms", "10", "--max-error-pct", "1")[
                0
            ],
            1,
        )
