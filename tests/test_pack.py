"""P1 (ADR-0097): artefact `.pyz` dựng tất định, kiểm được, chạy được từ zip."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
import xt_pack


class PackTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def fake_scripts(self) -> Path:
        s = self.tmp / "scripts"
        (s / "xt_app").mkdir(parents=True)
        (s / "xt.py").write_text("def main():\n    return 0\n", encoding="utf-8")
        (s / "xt_flow.py").write_text("X = 1\n", encoding="utf-8")
        (s / "xt_app" / "__init__.py").write_text("", encoding="utf-8")
        (s / "xt_app" / "server.py").write_text("Y = 2\n", encoding="utf-8")
        (s / "install.py").write_text("# không vào artefact\n", encoding="utf-8")
        return s

    def test_two_builds_have_the_same_sha256_and_bytes(self):
        s = self.fake_scripts()
        a = xt_pack.build(s, self.tmp / "a" / "xt.pyz")
        b = xt_pack.build(s, self.tmp / "b" / "xt.pyz")
        self.assertEqual(a, b)
        self.assertEqual(a, hashlib.sha256((self.tmp / "a" / "xt.pyz").read_bytes()).hexdigest())
        self.assertEqual((self.tmp / "a" / "xt.pyz").read_bytes(), (self.tmp / "b" / "xt.pyz").read_bytes())

    def test_layout_is_sorted_stored_and_fixed(self):
        s = self.fake_scripts()
        out = self.tmp / "xt.pyz"
        xt_pack.build(s, out)
        data = out.read_bytes()
        self.assertTrue(data.startswith(xt_pack.SHEBANG))
        with zipfile.ZipFile(out) as z:
            names = [i.filename for i in z.infolist()]
            self.assertEqual(names, sorted(names))
            self.assertEqual(names, ["__main__.py", "xt.py", "xt_app/__init__.py", "xt_app/server.py", "xt_flow.py"])
            for i in z.infolist():
                self.assertEqual((i.compress_type, i.date_time), (zipfile.ZIP_STORED, xt_pack.FIXED_TIME))
                self.assertEqual(i.external_attr, xt_pack.FILE_MODE)
        self.assertTrue(out.stat().st_mode & 0o111)

    def test_missing_xt_py_is_an_error(self):
        s = self.tmp / "empty"
        s.mkdir()
        with self.assertRaises(FileNotFoundError):
            xt_pack.build_bytes(s)

    def test_verify_accepts_the_build_and_pin_and_rejects_a_changed_byte(self):
        s = self.fake_scripts()
        out = self.tmp / "xt.pyz"
        pin = xt_pack.build(s, out)
        self.assertEqual(xt_pack.verify(out, s, pin), [])
        raw = bytearray(out.read_bytes())
        raw[-30] ^= 0x01  # một byte trong thư mục trung tâm của zip
        out.write_bytes(bytes(raw))
        errors = xt_pack.verify(out, s, pin)
        self.assertEqual(len(errors), 2)
        self.assertIn("sha256", errors[0])
        self.assertEqual(len(xt_pack.verify(out, s)), 1)

    def test_cli_build_and_verify(self):
        s = self.fake_scripts()
        out = self.tmp / "dist" / "xt.pyz"
        self.assertEqual(xt_pack.main(["--scripts", str(s), "build", "--out", str(out)]), 0)
        self.assertEqual(xt_pack.main(["--scripts", str(s), "verify", str(out)]), 0)
        out.write_bytes(out.read_bytes() + b"x")
        self.assertEqual(xt_pack.main(["--scripts", str(s), "verify", str(out), "--sha256", "0" * 64]), 1)

    def test_runs_as_a_script(self):
        s = self.fake_scripts()
        out = self.tmp / "xt.pyz"
        r = subprocess.run(
            [sys.executable, "-I", str(SCRIPTS / "xt_pack.py"), "--scripts", str(s), "build", "--out", str(out)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual((r.returncode, r.stdout.strip()), (0, hashlib.sha256(out.read_bytes()).hexdigest()))

    def test_real_scripts_build_and_run_from_the_zip(self):
        out = self.tmp / "xt.pyz"
        xt_pack.build(SCRIPTS, out)
        r = subprocess.run(
            [sys.executable, "-I", str(out), "--version"], capture_output=True, text=True, check=False, cwd=ROOT
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("xt.py", r.stdout)
        r = subprocess.run(
            [sys.executable, "-I", str(out), "guard-check", "--help"],
            capture_output=True,
            text=True,
            check=False,
            cwd=ROOT,
        )
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_artifact_scripts_match_what_install_copies(self):
        text = (SCRIPTS / "install.py").read_text(encoding="utf-8")
        start = text.index("optional_scripts = (")
        block = text[start : text.index(")", start)]
        listed = {line.strip().strip('",') for line in block.splitlines()[1:] if line.strip().startswith('"')}
        self.assertEqual(set(xt_pack.ARTIFACT_SCRIPTS) - {"xt.py"}, listed)


if __name__ == "__main__":
    unittest.main()
