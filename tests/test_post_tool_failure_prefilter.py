"""T-5042: tiền lọc regex bash của `.claude/hooks/post-tool-failure.sh` là TẬP CHA của `TRIAGE_LOCAL_GATE_RE`
(scripts/xt.py) — payload khớp bộ lọc thật thì không bao giờ bị tiền lọc loại; payload không khớp thoát trước khi gọi
python."""

from __future__ import annotations

import itertools
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import xt

HOOK = ROOT / ".claude" / "hooks" / "post-tool-failure.sh"

# Khoảng trắng mà `\s` của Python khớp: thường, tab, xuống dòng, VT/FF, FS–US, NEL, NBSP, khoảng Unicode.
SPACES = (" ", "  ", "\t", "\n", "\r", "\x0b", "\x0c", "\x1c", "\x1f", "\x85", " ", " ", "　", " \t\n ")
# Mỗi nhánh của TRIAGE_LOCAL_GATE_RE; `{s}` là chỗ khoảng trắng.
TEMPLATES = (
    "dev-task.sh gate",
    "x dev-task.sh",
    "xt.py{s}loop{s}record --task T",
    "python3 scripts/xt.py{s}loop{s}verify",
    "python3 -m unittest tests.x",
    "python -m pytest -q",
    "npm{s}test",
    "npm{s}run{s}test",
    "pnpm{s}test",
    "pnpm{s}run{s}test",
    "yarn{s}test",
    "yarn{s}run{s}test",
    "bun{s}test",
    "bun{s}run{s}test",
    "go{s}test ./...",
    "cargo{s}test",
    "make{s}test",
    "ruff check .",
    "mypy --strict",
    "shellcheck a.sh",
    "tsc --noEmit",
    "eslint .",
    "echo hi && pytest",
    ";ruff",
    "(mypy)",
)


def _prefilter_re() -> re.Pattern[str]:
    m = re.search(r"^PREFILTER_RE='(.*)'$", HOOK.read_text(encoding="utf-8"), re.M)
    assert m, "không thấy PREFILTER_RE"
    # ERE → Python: chỉ lớp POSIX `[:alnum:]` cần dịch.
    return re.compile(m.group(1).replace("[:alnum:]", "A-Za-z0-9"))


def _fill(template: str, seps: tuple[str, ...]) -> str:
    parts = template.split("{s}")
    return parts[0] + "".join(s + p for s, p in zip(seps, parts[1:], strict=True))


def _variants() -> list[str]:
    out = []
    for t in TEMPLATES:
        n = t.count("{s}")
        for seps in itertools.product(SPACES, repeat=n):
            out.append(_fill(t, seps))
    return out


class PrefilterSupersetTest(unittest.TestCase):
    def test_every_triage_match_passes_prefilter(self):
        pre = _prefilter_re()
        hit = 0
        for cmd in _variants():
            for ascii_only in (True, False):
                payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}, ensure_ascii=ascii_only)
                if xt.TRIAGE_LOCAL_GATE_RE.search(cmd):
                    hit += 1
                    self.assertTrue(pre.search(payload), f"tiền lọc bỏ sót {cmd!r} ({payload!r})")
        self.assertGreater(hit, 300)  # không rỗng: phần lớn biến thể phải khớp bộ lọc thật

    def test_prefilter_rejects_plain_commands(self):
        pre = _prefilter_re()
        for cmd in ("ls -la", "git status", "echo hello", "cat README.md", "npm install", "go build ./..."):
            payload = json.dumps({"tool_input": {"command": cmd}, "error": "Exit code 1"})
            self.assertIsNone(pre.search(payload), cmd)


class PrefilterHookTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        bash = shutil.which("bash")
        assert bash
        for tool in ("bash", "cat", "dirname"):
            found = shutil.which(tool)
            assert found
            (self.bin / tool).symlink_to(found)
        self.marker = self.tmp / "python-called"
        # Python giả chỉ đánh dấu đã bị gọi (redirection là builtin; PATH giả không có `touch`).
        fake = self.bin / "python3"
        fake.write_text(f"#!{bash}\n: > {self.marker}\n", encoding="utf-8")
        fake.chmod(0o755)
        (self.tmp / "scripts").mkdir()
        shutil.copy(ROOT / "scripts" / "xt.py", self.tmp / "scripts" / "xt.py")

    def _run(self, cmd: str) -> int:
        env = {"PATH": str(self.bin), "CLAUDE_PROJECT_DIR": str(self.tmp)}
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}, "error": "Exit code 1\nboom"})
        r = subprocess.run(
            ["bash", str(HOOK)], input=payload, capture_output=True, text=True, env=env, timeout=60, check=False
        )
        return r.returncode

    def test_nonmatching_payload_does_not_call_python(self):
        for cmd in ("ls -la", "git status", "npm install"):
            self.assertEqual(self._run(cmd), 0)
            self.assertFalse(self.marker.exists(), cmd)

    def test_matching_payload_calls_python(self):
        for cmd in ("pytest -q", "make\ttest", "python3 scripts/xt.py\nloop  record --task T"):
            self.marker.unlink(missing_ok=True)
            self.assertEqual(self._run(cmd), 0)
            self.assertTrue(self.marker.exists(), cmd)


if __name__ == "__main__":
    unittest.main()
