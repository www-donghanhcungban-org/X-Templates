"""T-4011: `dev-task.sh bootstrap` dựng CPython ≥ 3.13 + công cụ cổng vào `.venv`; `doctor` cảnh báo bản tiền phát hành.
Trình thông dịch và `uv` là giả: không tải mạng, không dựng venv thật."""

from __future__ import annotations

import collections
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import xt

Info = collections.namedtuple("Info", "major minor micro releaselevel serial")

# Trình thông dịch giả: `-c` (kiểm sàn) theo OK; `-V` in phiên bản; `-m venv D` dựng D/bin/python3 ghi lại lời gọi pip.
FAKE_PY = """#!/bin/bash
case "$1" in
  -c) exit {rc} ;;
  -V) echo "Python {ver}" ;;
  -m) mkdir -p "$3/bin"; printf '#!/bin/bash\\necho "$@" >> "%s/pip.log"\\n' "$LOG" > "$3/bin/python3"; chmod +x "$3/bin/python3" ;;
esac
"""
FAKE_UV = """#!/bin/bash
echo "uv $*" >> "$LOG/uv.log"
[ "$2" = find ] && echo "$UV_PY"
exit 0
"""


class BootstrapTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.proj = self.tmp / "proj"
        self.proj.mkdir()
        self.bin = self.tmp / "bin"
        self.bin.mkdir()

    def tool(self, name: str, text: str) -> Path:
        path = self.bin / name
        path.write_text(text, encoding="utf-8")
        path.chmod(0o755)
        return path

    def run_bootstrap(self, python: Path, **env: str) -> subprocess.CompletedProcess[str]:
        base = {
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "HOME": str(self.tmp),
            "CLAUDE_PROJECT_DIR": str(self.proj),
            "XT_PYTHON": str(python),
            "LOG": str(self.tmp),
        }
        return subprocess.run(
            ["bash", str(ROOT / "scripts" / "dev-task.sh"), "bootstrap"],
            env={**base, **env},
            capture_output=True,
            text=True,
            timeout=120,
        )

    def test_good_python_creates_venv_and_installs_pinned_tools(self):
        good = self.tool("py-good", FAKE_PY.format(rc=0, ver="3.13.5"))
        r = self.run_bootstrap(good)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.proj / ".venv" / "bin" / "python3").is_file())
        self.assertIn("export PATH=", r.stderr)
        self.assertFalse((self.tmp / "pip.log").exists())  # không có requirements-dev.txt: không cài gì
        (self.proj / "requirements-dev.txt").write_text("ruff==1 --hash=sha256:00\n", encoding="utf-8")
        r = self.run_bootstrap(good)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("-m venv", r.stderr)  # venv đã có: giữ nguyên
        log = (self.tmp / "pip.log").read_text(encoding="utf-8")
        self.assertIn("--require-hashes", log)

    def test_old_python_without_uv_stops_with_guidance(self):
        old = self.tool("py-old", FAKE_PY.format(rc=1, ver="3.11.9"))
        r = self.run_bootstrap(old)
        self.assertEqual(r.returncode, 3)
        self.assertIn("cần CPython ≥ 3.13", r.stderr)
        self.assertIn("3.11.9", r.stderr)
        self.assertFalse((self.proj / ".venv").exists())

    def test_old_python_uses_uv_with_pinned_version(self):
        old = self.tool("py-old", FAKE_PY.format(rc=1, ver="3.11.9"))
        good = self.tool("py-good", FAKE_PY.format(rc=0, ver="3.15.2"))
        self.tool("uv", FAKE_UV)
        (self.proj / ".python-version").write_text("3.15.2\n", encoding="utf-8")
        r = self.run_bootstrap(old, UV_PY=str(good))
        self.assertEqual(r.returncode, 0, r.stderr)
        uv_log = (self.tmp / "uv.log").read_text(encoding="utf-8").splitlines()
        self.assertEqual(uv_log, ["uv python install 3.15.2", "uv python find 3.15.2"])
        self.assertTrue((self.proj / ".venv" / "bin" / "python3").is_file())

    def test_uv_default_version_and_bad_result(self):
        old = self.tool("py-old", FAKE_PY.format(rc=1, ver="3.12.1"))
        self.tool("uv", FAKE_UV)
        r = self.run_bootstrap(old, UV_PY=str(old))
        self.assertEqual(r.returncode, 3)
        self.assertIn("không đạt CPython ≥ 3.13", r.stderr)
        self.assertIn("uv python install 3.13", (self.tmp / "uv.log").read_text(encoding="utf-8"))

    def test_doctor_warns_on_prerelease_only(self):
        self.assertIsNone(xt._python_prerelease_warning(Info(3, 15, 2, "final", 0)))
        warn = xt._python_prerelease_warning(Info(3, 15, 0, "beta", 4))
        self.assertEqual((warn.code, warn.level), ("runtime", "warn"))
        self.assertIn("3.15.0", warn.msg)
        self.assertIn("beta", warn.msg)
        self.assertIn("bootstrap", warn.msg)
        self.assertIsNone(xt._python_prerelease_warning((3, 13, 0)))  # tuple thường: coi như bản chính thức
        current = xt._python_prerelease_warning()
        self.assertEqual(current is None, sys.version_info.releaselevel == "final")


if __name__ == "__main__":
    unittest.main()
