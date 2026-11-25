"""Starter web-api-ts giao lệnh nghiệm thu UI cho dự án mới; cài lại hoặc vào brownfield giữ quyền dự án."""

import json
import os
import runpy
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests_e2e"))
import install
import pack_ui

PACK = ROOT / install.PACKS_DIR / "web-api-ts"
STARTER = PACK / "starter"
WORKFLOW = ".github/workflows/dev-preview.yml"
JOURNEY = "tests_e2e/pack_preview.py"
MATRIX = "tests_e2e/pack_ui_matrix.py"
COMMAND = "tests_e2e/preview.sh"
BROWSER = "tests_e2e/prepare-chromium.sh"
LOCK = "tests_e2e/requirements.txt"
TOOLS = ".github/actions/xt-ci-tools/action.yml"
TEST_DB = "scripts/test-with-postgres.sh"


class PackUiTest(unittest.TestCase):
    def test_fresh_starter_owns_browser_ci_and_brownfield_stays_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(StringIO()):
            root = Path(tmp)
            copied = install.install_pack_starter(root, "web-api-ts", "fresh")
            for rel in (JOURNEY, MATRIX, COMMAND, BROWSER, LOCK, WORKFLOW, TOOLS, TEST_DB, pack_ui.PAIRS):
                self.assertIn(rel, copied)
                self.assertEqual((root / rel).read_bytes(), (STARTER / rel).read_bytes())
            (root / JOURNEY).write_text("# Luồng riêng của dự án\n", encoding="utf-8")
            self.assertEqual(install.install_pack_starter(root, "web-api-ts", "upgrade"), [])
            self.assertIn("Luồng riêng", (root / JOURNEY).read_text(encoding="utf-8"))
            brown = root / "existing"
            brown.mkdir()
            own = '{"scripts":{"test":"make my-test"}}'
            (brown / "package.json").write_text(own, encoding="utf-8")
            config = "setup: make my-setup\ntest: make my-test\n"
            (brown / "xt.yaml").write_text(config)
            mode = install.pack_mode(brown, "web-api-ts")
            self.assertEqual(install.install_pack_starter(brown, "web-api-ts", mode), [])
            install.install_pack_yaml(
                brown, "web-api-ts", mode, json.loads((PACK / "pack.json").read_text())["xt_yaml"]
            )
            self.assertEqual((brown / "package.json").read_text(), own)
            self.assertEqual((brown / "xt.yaml").read_text(), config)
            self.assertFalse((brown / TOOLS).exists())
            self.assertFalse((brown / TEST_DB).exists())
            self.assertFalse((brown / WORKFLOW).exists())
            self.assertFalse((brown / JOURNEY).exists())

    def test_browser_preview_restricts_fixture_login_and_redirects(self):
        # Mô phỏng Playwright: bộ unittest không cần tải Chromium hoặc mở kết nối mạng.
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": MagicMock()}):
            preview = runpy.run_path(str(STARTER / JOURNEY))
        origin = preview["PREVIEW_ORIGIN"]
        other = "http://127.0.0.1:4320"
        for target, status in ((origin + "/", 200), (origin + "/", 302), (other + "/", 200)):
            with self.subTest(target=target, status=status):
                route = MagicMock()
                route.request.url = target
                response = route.fetch.return_value
                response.status = status
                preview["preview_request"](route)
                if target.startswith(other):
                    route.fetch.assert_not_called()
                else:
                    route.fetch.assert_called_once_with(max_redirects=0)
                    response.dispose.assert_called_once()
                if target.startswith(other) or status == 302:
                    route.abort.assert_called_once()
                    route.fulfill.assert_not_called()
                else:
                    route.fulfill.assert_called_once_with(response=response)

        browser = MagicMock()
        context = preview["preview_context"](browser)
        browser.new_context.assert_called_once_with(service_workers="block")
        context.route.assert_called_once_with("**/*", preview["preview_request"])
        socket = MagicMock()
        pattern, reject = context.route_web_socket.call_args.args
        self.assertEqual(pattern, "**/*")
        reject(socket)
        socket.close.assert_called_once()
        health_url = origin + "/healthz"
        health = context.request.get.return_value
        health.url = health_url
        health.status = 302
        with self.assertRaisesRegex(ValueError, "healthz"):
            preview["served_digest"](context, "digest")
        context.request.get.assert_called_once_with(health_url, max_redirects=0)
        health.json.assert_not_called()
        health.status = 200
        health.json.return_value = {"digest": "digest"}
        self.assertEqual(preview["served_digest"](context, "digest"), "digest")
        ledger = {"envs": {"dev": {"unknown": False, "current": {"result": "deployed", "url": other}}}}
        with (
            patch.object(Path, "read_text", return_value=json.dumps(ledger)),
            self.assertRaisesRegex(ValueError, "origin"),
        ):
            preview["confirmed_candidate"]()
        page = MagicMock()
        page.url = other + "/"
        with self.assertRaisesRegex(ValueError, "origin"):
            preview["login"](page, {"email": "fixture", "password": "fixture"})
        page.locator.assert_not_called()

    def test_ci_runs_target_command_and_browser_lock_matches_audited_pins(self):
        workflow = (STARTER / WORKFLOW).read_text(encoding="utf-8")
        self.assertIn("\n  pull_request:\n", workflow)
        self.assertIn("\n  workflow_dispatch:\n", workflow)
        self.assertIn(f"run: bash {COMMAND} --output", workflow)
        self.assertIn("docs/ops/DEPLOYS.json", workflow)
        shared_e2e = json.loads((PACK / "pack.json").read_text(encoding="utf-8"))["xt_yaml"].get("e2e", "")
        self.assertNotIn(COMMAND, shared_e2e)

        def pins(path):
            return [line for line in path.read_text(encoding="utf-8").splitlines() if line and not line.startswith("#")]

        self.assertEqual(pins(STARTER / LOCK), pins(ROOT / "requirements-e2e.txt"))
        self.assertIn(f'bash {BROWSER} "$python"', (STARTER / COMMAND).read_text())
        self.assertIn(f"bash {BROWSER} python", (ROOT / ".github/workflows/pack-web-api.yml").read_text())
        app_job = (ROOT / ".github/workflows/ci.yml").read_text().split("\n  app-e2e:\n")[1].split("\n  quality:\n")[0]
        setup = app_job.index(f"run: bash {(STARTER / BROWSER).relative_to(ROOT).as_posix()} python")
        self.assertLess(app_job.index("--require-hashes -r requirements-e2e.txt"), setup)
        self.assertLess(setup, app_job.index("python -m unittest discover -s tests_e2e -t ."))
        self.assertNotIn("--with-deps", app_job)

    def test_starter_scaffold_keeps_declared_contrast_and_vendored_axe_stays_in_framework(self):
        axe = pack_ui.pinned_axe()
        self.assertEqual(axe, ROOT / "tests_e2e/vendor/axe/axe.min.js")
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / "app"
            pack_ui.scaffold(app)
            for filename in (MATRIX, JOURNEY, pack_ui.CSS, pack_ui.PAIRS):
                self.assertEqual((app / filename).read_bytes(), (STARTER / filename).read_bytes())
            self.assertFalse(any(app.rglob("axe.min.js")))

            css = app / pack_ui.CSS
            original = css.read_text(encoding="utf-8")
            self.assertNotRegex(original.split("}", 1)[1], r"#[0-9a-fA-F]{3,8}\b")
            rows = pack_ui.measure_contrast(app)
            self.assertEqual(len(rows), 25)
            for damaged in (
                original.replace("--primary-foreground: #fff;", "--primary-foreground: #175b42;"),
                original.replace("--surface-field:", "--undeclared-field:"),
            ):
                self.assertNotEqual(damaged, original)
                css.write_text(damaged, encoding="utf-8")
                with self.assertRaisesRegex(pack_ui.PackUiFailure, "Tương phản không đạt"):
                    pack_ui.measure_contrast(app)

    def test_browser_matrix_mode_is_explicit_and_keeps_receipt_mode(self):
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": MagicMock()}):
            preview = runpy.run_path(str(STARTER / JOURNEY))
        entry = preview["main"]
        receipt, matrix = MagicMock(), MagicMock(return_value=0)
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.dict(entry.__globals__, {"preview_receipt": receipt, "ui_matrix": matrix}),
        ):
            output = Path(tmp) / "result"
            with patch.object(sys, "argv", [JOURNEY, "--output", str(output)]):
                self.assertEqual(entry(), 0)
            receipt.assert_called_once_with(output)
            matrix.assert_not_called()
            with patch.object(sys, "argv", [JOURNEY, "--ui-matrix", str(output), "--axe", str(pack_ui.AXE)]):
                self.assertEqual(entry(), 0)
            matrix.assert_called_once_with(pack_ui.AXE, output)
            for flags in (
                ["--ui-matrix", str(output)],
                ["--ui-matrix", str(output), "--axe", str(output)],
                ["--output", str(output), "--axe", str(pack_ui.AXE)],
                ["--output", str(output), "--ui-matrix", str(output)],
            ):
                with self.subTest(flags=flags), patch.object(sys, "argv", [JOURNEY, *flags]):
                    with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as rejected:
                        entry()
                    self.assertEqual(rejected.exception.code, 2)
            receipt.assert_called_once()
            matrix.assert_called_once()

    def test_root_ci_reuses_bootstrapped_browser_and_uploads_the_same_matrix(self):
        workflow = (ROOT / ".github/workflows/pack-web-api.yml").read_text(encoding="utf-8")
        root_command = "python3 -m unittest tests.test_pack_ui tests.test_packs && python3 tests_e2e/pack_ui.py"
        self.assertEqual(workflow.count(root_command), 1)
        self.assertEqual(workflow.count("      - tests_e2e/pack_ui.py\n"), 2)
        self.assertEqual(workflow.count("      - tests_e2e/vendor/axe/**\n"), 2)
        self.assertLess(workflow.index("bash tests_e2e/prepare-chromium.sh python"), workflow.index(root_command))
        self.assertIn(
            "if: matrix.case == 'clean'\n"
            "        env:\n"
            "          TMPDIR: ${{ runner.temp }}/starter-ui\n"
            "        run: |\n"
            '          mkdir -p "$TMPDIR"\n'
            f"          {root_command}\n",
            workflow,
        )
        self.assertIn("path: ${{ runner.temp }}/starter-ui/", workflow)
        self.assertIn("name: pack-starter-ui", workflow)
        self.assertIn('python tests_e2e/pack_preview.py --output "$RUNNER_TEMP/preview-browser.json"', workflow)

    def test_missing_browser_report_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            with self.assertRaises(FileNotFoundError):
                pack_ui.require_matrix(output)
            (output / "matrix.json").write_text('{"schema":1,"result":"passed","states":[]}', encoding="utf-8")
            with self.assertRaisesRegex(pack_ui.PackUiFailure, "thiếu các viewport"):
                pack_ui.require_matrix(output)

    def test_controls_must_fail_at_the_expected_browser_check(self):
        def result(code, message):
            return subprocess.CompletedProcess(["browser"], code, "", message)

        pack_ui.require_control(result(1, "pack-ui: 320px/login/overflow: document 640"), "320px/login/overflow")
        pack_ui.require_control(result(1, "pack-ui: 1280px/login/axe: label"), "1280px/login/axe", "label")
        for code, message in (
            (0, "pack-ui: 1280px/login/axe: label"),
            (2, "pack-ui: 1280px/login/axe: label"),
            (1, "pack-ui: 1280px/login/axe-unmeasured: label"),
            (1, "pack-ui: 320px/login/axe: label"),
            (1, "pack-ui: 1280px/login/axe: color-contrast"),
            (1, "pack-ui: chưa đo đủ ma trận trình duyệt"),
        ):
            with self.subTest(code=code, message=message), self.assertRaisesRegex(pack_ui.PackUiFailure, "Ca sai"):
                pack_ui.require_control(result(code, message), "1280px/login/axe", "label")

    def test_chromium_installs_system_packages_only_for_missing_libraries_on_ci(self):
        install = "-m playwright install --only-shell chromium"
        deps = "-m playwright install-deps chromium"
        missing = "error while loading shared libraries: libnss3.so"
        for error, ci, custom, again, expected, success in [
            ("", "true", "", "", [install, "-"], True),
            (missing, "true", "", "", [install, "-", deps, "-"], True),
            ("Host system is missing dependencies", "true", "", "still missing", [install, "-", deps, "-"], False),
            ("target crashed", "true", "", "", [install, "-"], False),
            (missing, "false", "", "", [install, "-"], False),
            (missing, "true", "/custom/chrome", "", ["-"], False),
        ]:
            with self.subTest(error=error, ci=ci, custom=custom, again=again), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                fake = root / "python"
                fake.write_text(
                    '#!/bin/sh\necho "$*" >> "$TRACE"\n'
                    'if [ "$1" = "-" ]; then\n'
                    "  cat >/dev/null\n"
                    '  if [ -f "$TRACE.probed" ]; then ERROR=$AGAIN; fi\n'
                    '  touch "$TRACE.probed"\n'
                    '  if [ -n "$ERROR" ]; then echo "$ERROR" >&2; exit 1; fi\n'
                    "fi\n"
                )
                fake.chmod(0o755)
                trace = root / "calls"
                env = {
                    **os.environ,
                    "TRACE": str(trace),
                    "ERROR": error,
                    "AGAIN": again,
                    "GITHUB_ACTIONS": ci,
                    "XT_E2E_CHROMIUM": custom,
                }
                result = subprocess.run(["bash", str(STARTER / BROWSER), str(fake)], env=env, capture_output=True)
                self.assertEqual(result.returncode == 0, success, result.stderr)
                self.assertEqual(trace.read_text().splitlines(), expected)

    def test_failed_prerequisite_preserves_previous_proof_under_separate_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            proof = Path(tmp) / "report.json"
            old = '{"result":"passed"}'
            proof.write_text(old, encoding="utf-8")
            run = subprocess.run(
                ["bash", str(STARTER / COMMAND), "--output", str(proof)],
                env={**os.environ, "XT_FRAMEWORK_PYTHON": "false"},
                cwd=tmp,
                capture_output=True,
            )
            self.assertNotEqual(run.returncode, 0)
            self.assertFalse(proof.exists())
            previous = list(proof.parent.glob("report.json.previous.*"))
            self.assertEqual(len(previous), 1)
            self.assertEqual(previous[0].read_text(encoding="utf-8"), old)
