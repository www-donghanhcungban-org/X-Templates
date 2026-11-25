"""Configured project adapter and production authorization at the normal CLI entry point, without credentials."""

import base64
import datetime as dt
import json
import os
import subprocess
from pathlib import Path
import sys
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_admin_plan import GithubFixture
from test_release_contract import ReleaseCase
from test_xt_cli import run_main, xt


ADAPTER = """import hashlib, os, sys
from pathlib import Path
state = Path(os.environ['XT_DEPLOY_STATE'])
step = sys.argv[1]
if os.environ['XT_DEPLOY_ENV'] != 'dev':
    assert 'DEPLOY_TEST_HOST_ONLY' not in os.environ
with (state / 'calls').open('a') as log:
    print(step, file=log)
live = state / 'live.bin'
if step in ('deploy','rollback'):
    saved = Path(os.environ['XT_DEPLOY_ARTIFACT_ROOT']) / os.environ['XT_DEPLOY_ARTIFACTS']
    assert saved.is_relative_to(state)
    live.write_bytes(saved.read_bytes())
elif step == 'smoke':
    sys.exit(int(os.environ['XT_DEPLOY_ENV'] == 'prod' and (live.read_bytes() == b'unhealthy' or (state / 'smoke-fail').exists())))
elif step == 'digest':
    assert set(os.environ).isdisjoint({'XT_DEPLOY_DIGEST','XT_DEPLOY_PREVIOUS','XT_DEPLOY_ARTIFACT_ROOT'})
    digest = hashlib.sha256(live.read_bytes()).hexdigest()
    print(hashlib.sha256(('dist/app.bin' + chr(0) + digest + chr(10)).encode()).hexdigest())
"""


class ProductionDeployTest(GithubFixture, ReleaseCase):
    def setUp(self):
        super().setUp()
        self.sign = "docs/ops/GO-NO-GO-v1.2.0.md"
        self.ledger = self.repo / xt.DEPLOY_LEDGER
        self.artifact = self.repo / "dist/app.bin"
        self.artifact.parent.mkdir()
        self.artifact.write_bytes(b"A")
        (self.repo / "adapter.py").write_text(ADAPTER)
        (self.repo / "VERSION").write_text("1.2.0\n")
        plan = self.repo / "docs/autopilot/PLAN.md"
        plan.parent.mkdir(parents=True, exist_ok=True)
        plan.write_text("- grant: deploy | env=prod\n")
        self.setup_xt(
            deploy_envs="dev prod",
            deploy_env_pass="",
            release_artifacts="dist/app.bin",
            **{
                f"{action}_{env}": f"python3 adapter.py {action}"
                for env in ("dev", "prod")
                for action in xt.DEV_ACTIONS
            },
        )
        self.fixture_routes = self.tmp / "routes.json"
        self.state = self.repo / ".git/xt-preview/prod"
        self.fake_github()

    def call(self, env="prod", op="run", rc=0):
        code, out, err = run_main("deploy", op, "--env", env, "--json")
        self.assertEqual(code, rc, f"{out}\n{err}")
        return json.loads(out) if out else err

    def publish_fixture(self, **overrides):
        self.commit()
        head = self.git("rev-parse", "HEAD")
        docs = {
            "": {"default_branch": "main"},
            "commits/main": {"sha": head},
            f"compare/{head}...{head}": {"status": "identical"},
        }
        for path in ["xt.yaml", self.sign, xt.DEPLOY_LEDGER, "docs/autopilot/PLAN.md"]:
            if (self.repo / path).is_file():
                docs[f"contents/{path}?ref={head}"] = {
                    "encoding": "base64",
                    "content": base64.b64encode((self.repo / path).read_bytes()).decode(),
                }
        docs.update(overrides)
        self.fixture_routes.write_text(json.dumps(docs))
        return head

    def candidate(self, data):
        self.artifact.write_bytes(data)
        receipt = self.call("dev")
        date = dt.datetime.now(dt.timezone.utc).date()
        (self.repo / self.sign).write_text(
            "# GO/NO-GO v1.2.0\n"
            + "\n".join(xt.subject_lines(receipt["subject"]))
            + f"\n\n## 5. Ký\n\n| Vai trò | Tên | Quyết định | Ngày |\n|---|---|---|---|\n| QA | Fixture | GO | {date} |\n"
        )
        self.publish_fixture()
        return receipt

    def test_approved_run_and_verified_saved_rollback(self):
        self.enterContext(mock.patch.dict(os.environ, {"DEPLOY_TEST_HOST_ONLY": "fixture"}))
        a = self.candidate(b"A")
        self.assertEqual(self.call()["served_digest"], a["served_digest"])
        self.candidate(b"B")
        self.assertEqual(self.call()["result"], "deployed")
        self.publish_fixture()
        self.artifact.unlink()
        self.assertEqual(self.call(op="rollback")["served_digest"], a["served_digest"])
        self.assertEqual((self.state / "live.bin").read_bytes(), b"A")

    def test_any_production_target_requires_explicit_allowlist_before_lock(self):
        config = self.repo / "xt.yaml"
        original = config.read_text()
        for env in ("prod", "edge"):
            config.write_text(original.replace("deploy_env_pass: \n", "").replace("prod", env))
            for op in ("run", "rollback"):
                with (
                    self.subTest(env=env, op=op),
                    mock.patch.object(xt, "_dev_lock", side_effect=AssertionError("lock")),
                ):
                    self.assertIn("deploy_env_pass", self.call(env, op, rc=2))
                self.assertFalse((self.repo / ".git/xt-preview" / env).exists())
        self.assertFalse(self.ledger.exists())

    def test_invalid_production_allowlist_is_rejected_before_lock(self):
        config = self.repo / "xt.yaml"
        original = config.read_text()
        for raw in ("null", "GIT_EXEC_PATH"):
            config.write_text(original.replace("deploy_env_pass: \n", f"deploy_env_pass: {raw}\n"))
            with self.subTest(raw=raw), mock.patch.object(xt, "_dev_lock", side_effect=AssertionError("lock")):
                self.assertIn(raw, self.call(rc=2))
        self.assertFalse(self.ledger.exists())

    def test_allowlist_must_match_the_authorized_configuration(self):
        self.candidate(b"A")
        before = self.ledger.read_bytes()
        # Mô phỏng cấu hình đọc trước khi kiểm HEAD đã cũ.
        self.state.mkdir(parents=True)  # thư mục đã được _dev_lock tạo ở lối vào CLI
        config = xt._xt_keys(self.repo)
        for stale in (
            {**config, "deploy_env_pass": "LANG"},
            {k: v for k, v in config.items() if k != "deploy_env_pass"},
        ):
            with (
                self.subTest(env_pass=stale.get("deploy_env_pass")),
                self.assertRaisesRegex(xt.DeployError, "cấu hình"),
            ):
                xt._dev_execute(self.repo, self.state, 30, False, "prod", stale)
        self.assertFalse((self.state / "calls").exists())
        self.assertEqual(self.ledger.read_bytes(), before)

    def test_preconditions_leave_target_and_receipt_untouched(self):
        self.candidate(b"A")
        head = self.git("rev-parse", "HEAD")
        unchanged = self.ledger.read_bytes()
        for override, why in [
            ({f"contents/docs/autopilot/PLAN.md?ref={head}": None}, "grant"),
            ({f"compare/{head}...{head}": {"status": "diverged"}}, "nhánh chính"),
            ({f"contents/{self.sign}?ref={head}": None}, "chữ ký"),
            ({f"contents/xt.yaml?ref={head}": None}, "adapter"),
            ({f"contents/{xt.DEPLOY_LEDGER}?ref={head}": None}, "sổ triển khai"),
        ]:
            with self.subTest(why=why):
                valid = self.fixture_routes.read_text()
                self.fixture_routes.write_text(json.dumps({**json.loads(valid), **override}))
                self.assertIn(why, self.call(rc=2))
                self.fixture_routes.write_text(valid)
        (self.repo / "dirty").write_text("changed")
        self.assertIn("sạch", self.call(rc=2))
        (self.repo / "dirty").unlink()
        self.artifact.write_bytes(b"B")
        self.assertIn("dev.current", self.call(rc=2))
        self.assertFalse((self.state / "calls").exists())
        self.assertEqual(self.ledger.read_bytes(), unchanged)

    def test_failed_smoke_restores_old_bytes_and_failed_restore_blocks(self):
        a = self.candidate(b"A")
        self.call()
        self.candidate(b"unhealthy")
        event = self.call(rc=1)
        self.assertEqual((event["result"], event["served_digest"]), ("rolled_back", a["served_digest"]))
        self.assertEqual((self.state / "live.bin").read_bytes(), b"A")
        self.publish_fixture()
        (self.state / "smoke-fail").touch()
        self.assertEqual(self.call(rc=1)["result"], "rollback_failed")
        self.assertEqual(json.loads(self.ledger.read_text())["envs"]["prod"]["current"], None)
        self.assertTrue(xt.read_state(self.repo)["blocked"])

    def test_snapshot_inputs_and_receipt_addresses(self):
        import xt_deploy

        self.assertEqual(xt_deploy.receipt_url("https://service.example.test"), "https://service.example.test")
        with self.assertRaises(ValueError):
            xt_deploy.receipt_url("https://service.example.test/?field=value")
        self.state.mkdir(parents=True)
        scratch = self.tmp / "copies"
        scratch.mkdir()
        (self.state / "artifacts").symlink_to(scratch, target_is_directory=True)
        digest = "f" * 64
        with self.assertRaisesRegex(ValueError, "symlink"):
            xt_deploy.artifact_root(self.state, digest)
        (self.state / "artifacts").unlink()
        for name in ("../copy", ".git/index", str(self.artifact)):
            with self.subTest(name=name), self.assertRaises(ValueError):
                xt_deploy.artifact_file(self.repo, name)
        with self.assertRaisesRegex(ValueError, "nguồn"):
            xt_deploy.retain_artifacts(self.repo, self.state, digest, [{"path": "missing", "sha256": digest}])
        with self.assertRaisesRegex(ValueError, "thiếu"):
            xt_deploy.verify_artifacts(scratch, digest, [{"path": "missing", "sha256": digest}])
        with self.assertRaisesRegex(ValueError, "receipt"):
            xt_deploy.verify_artifacts(scratch, digest, [])

    def test_corrupt_saved_artifact_or_revoked_grant_prevents_rollback(self):
        a = self.candidate(b"A")
        self.call()
        self.candidate(b"B")
        self.call()
        head = self.publish_fixture()
        calls = (self.state / "calls").read_bytes()
        ledger = self.ledger.read_bytes()
        original = self.fixture_routes.read_text()
        routes = json.loads(original)
        del routes[f"contents/docs/autopilot/PLAN.md?ref={head}"]
        self.fixture_routes.write_text(json.dumps(routes))
        self.assertIn("grant", self.call(op="rollback", rc=2))
        self.fixture_routes.write_text(original)
        saved = self.state / "artifacts" / a["served_digest"] / "dist/app.bin"
        saved.write_bytes(b"damaged")
        self.assertIn("SHA-256", self.call(op="rollback", rc=2))
        self.assertEqual((self.state / "calls").read_bytes(), calls)
        self.assertEqual(self.ledger.read_bytes(), ledger)

    def test_cli_refuses_unsigned_subject_and_honors_signed_fixture(self):
        self.call("dev")
        self.publish_fixture()
        cmd = [sys.executable, "-I", str(Path(xt.__file__).resolve()), "deploy", "run", "--env", "prod", "--json"]

        def cli():
            return subprocess.run(
                cmd,
                env={**os.environ, "CLAUDE_PROJECT_DIR": str(self.repo)},
                cwd=self.repo,
                capture_output=True,
                text=True,
                check=False,
                timeout=45,
            )

        missing = cli()
        self.assertEqual(missing.returncode, 2, missing)
        self.assertIn("promotion", missing.stderr)
        self.assertFalse((self.state / "calls").exists())
        signed = self.candidate(b"A")
        deployed = cli()
        self.assertEqual(deployed.returncode, 0, deployed)
        self.assertEqual(json.loads(deployed.stdout)["served_digest"], signed["subject"]["digest"])

    def test_preflight_detects_concurrent_changes_and_records_unusable_snapshot(self):
        import xt_deploy

        self.state.mkdir(parents=True)
        alias = self.state.parent / "dev"
        alias.symlink_to(self.tmp, target_is_directory=True)
        with self.assertRaisesRegex(xt.DeployError, "symlink"), xt._dev_lock(self.repo, "prod"):
            self.fail("coordinator did not refuse the changed lock directory")
        alias.unlink()
        commands = {action: f"python3 adapter.py {action}" for action in xt.DEV_ACTIONS}
        clean = mock.Mock(cfg={})
        with (
            mock.patch.object(xt_deploy, "production_authority", return_value=clean),
            self.assertRaisesRegex(xt.DeployError, "cấu hình"),
        ):
            xt._deploy_authorized_head(self.repo, "prod", commands, {}, ())
        driver = xt.DevPreview(
            self.repo, self.state, 1, {"head": "b" * 40, "digest": "a" * 64}, "", approved_head="c" * 40
        )
        with self.assertRaisesRegex(xt.DeployError, "HEAD"):
            xt._prepare_configured(driver, {}, None, [], "prod", commands, False, "")
        driver.commands = commands
        result, served = driver.invoke("deploy")
        self.assertNotEqual(result["exit_code"], 0)
        self.assertIsNone(served)
        self.assertFalse((self.state / "calls").exists())

    def test_production_rechecks_authority_at_each_target_mutation(self):
        import xt_deploy

        self.candidate(b"A")
        head = self.git("rev-parse", "HEAD")
        baseline = self.fixture_routes.read_bytes()
        before = self.ledger.read_bytes()
        materialize = xt_deploy.materialize_artifacts

        def revoke_after_copy(*args):
            materialize(*args)
            data = json.loads(self.fixture_routes.read_bytes())
            del data[f"contents/docs/autopilot/PLAN.md?ref={head}"]
            self.fixture_routes.write_text(json.dumps(data))

        with mock.patch.object(xt_deploy, "materialize_artifacts", side_effect=revoke_after_copy):
            self.assertIn("grant", self.call(rc=2))
        self.assertFalse((self.state / "calls").exists())
        self.assertEqual(self.ledger.read_bytes(), before)

        def unsign_after_copy(*args):
            materialize(*args)
            data = json.loads(self.fixture_routes.read_bytes())
            del data[f"contents/{self.sign}?ref={head}"]
            self.fixture_routes.write_text(json.dumps(data))

        self.fixture_routes.write_bytes(baseline)
        with mock.patch.object(xt_deploy, "materialize_artifacts", side_effect=unsign_after_copy):
            self.assertIn("chữ ký GO đã đổi trước khi triển khai", self.call(rc=2))
        self.assertFalse((self.state / "calls").exists())
        self.assertEqual(self.ledger.read_bytes(), before)
        self.fixture_routes.write_bytes(baseline)
        self.call()
        self.candidate(b"unhealthy")
        head = self.git("rev-parse", "HEAD")
        calls_before = (self.state / "calls").read_text().splitlines()

        def revoke_before_restore(saved, checkout, paths):
            if (saved / paths[0]).read_bytes() == b"A":
                revoke_after_copy(saved, checkout, paths)
            else:
                materialize(saved, checkout, paths)

        with mock.patch.object(xt_deploy, "materialize_artifacts", side_effect=revoke_before_restore):
            result = self.call(rc=1)
        self.assertEqual(result["result"], "rollback_failed")
        self.assertEqual((self.state / "calls").read_text().splitlines()[len(calls_before) :], ["deploy", "smoke"])
        self.assertTrue(json.loads(self.ledger.read_text())["envs"]["prod"]["unknown"])
        self.assertTrue(xt.read_state(self.repo)["blocked"])
