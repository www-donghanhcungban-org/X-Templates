"""So đáp án của CLI nguồn, bản cài và gói zipapp trong cùng thư mục làm việc."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import xt_pack
import test_check_design_outcome
import test_check_eval_evidence


class EvalSurfaceParityTest(unittest.TestCase):
    def test_installed_and_packed_cli(self):
        outside = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        installed = outside / "project"
        installed.mkdir()
        archive = outside / "xt.pyz"
        xt_pack.build(ROOT / "scripts", archive)
        install = self.run_cli(
            outside,
            ROOT / "scripts/install.py",
            str(installed),
            "--no-harness",
            "--no-git-hooks",
        )
        self.assertEqual(install.returncode, 0, install.stderr or install.stdout)
        paths = (
            ROOT / "scripts/xt.py",
            installed / ".xtemplates/scripts/xt.py",
            archive,
        )
        fixture = test_check_eval_evidence.EvalEvidenceTest()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.report_path.write_text(json.dumps(fixture.report))
        fixture.policy_path.write_text(json.dumps(fixture.policy))
        policy_options = {k: v for k, v in fixture.options.items() if k != "artifacts"}
        invalid = outside / "invalid.json"
        invalid.write_text("{}")
        design = test_check_design_outcome.DesignOutcomeTests()
        design.setUp()
        self.addCleanup(design.doCleanups)
        self.assertFalse(design.run_check().findings)
        cases = [
            ("eval-report", fixture.report_path, {}, 0),
            ("eval-report", invalid, {}, 1),
            ("eval-report", fixture.report_path, {"mode": "gate", **policy_options}, 0),
            ("eval-evidence", fixture.report_path, fixture.options, 0),
            ("eval-evidence", fixture.report_path, fixture.options | {"revision": "b" * 40}, 1),
            ("design-outcome", design.path, design.opts, 0),
            ("design-outcome", design.path, policy_options, 1),
        ]
        for kind, path, options, code in cases:
            with self.subTest(kind=kind, path=path.name, code=code):
                args = ["static-check", kind, str(path), "--json"]
                for name, value in options.items():
                    args.extend(("--opt", f"{name}={value}"))
                results = [self.run_cli(outside, entry, *args) for entry in paths]
                for result in results:
                    self.assertEqual(result.returncode, code, result.stderr or result.stdout)
                source, target, packed = (json.loads(result.stdout) for result in results)
                self.assertEqual(source, target)
                self.assertEqual(source, packed)

    @staticmethod
    def run_cli(outside, entry, *args):
        env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
        return subprocess.run(
            [sys.executable, "-I", "-S", str(entry), *args],
            cwd=outside,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
