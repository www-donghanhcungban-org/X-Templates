"""PreCompact in checkpoint ra stdout làm chỉ dẫn tóm tắt nén (T-5040, D-613; docs hooks §PreCompact output, đọc
2026-11-26): exit 0, chữ thường (không JSON `decision` — sẽ chặn nén), ≤ 10 000 ký tự, chỉ in checkpoint của lần chạy này."""

from __future__ import annotations

import concurrent.futures
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from git_fixture import init_git_fixture, isolated_git_environment

HOOK = ROOT / ".claude" / "hooks" / "pre-compact.sh"
PAYLOAD = json.dumps({"hook_event_name": "PreCompact", "trigger": "auto", "custom_instructions": None})


def run_pre_compact(project: Path, payload: str = PAYLOAD) -> tuple[int, str, str]:
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(project))
    r = subprocess.run(["bash", str(HOOK)], input=payload, capture_output=True, text=True, env=env, timeout=120)
    return r.returncode, r.stdout, r.stderr


@unittest.skipIf(shutil.which("bash") is None, "cần bash")
class PreCompactOutputTest(unittest.TestCase):
    def project(self, loop: bool = True, decisions: str | None = "### D-001 · a · b\n\n### D-042 · c · d\n") -> Path:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "scripts").mkdir()
        shutil.copy(ROOT / "scripts" / "xt.py", tmp / "scripts" / "xt.py")
        (tmp / "docs" / "autopilot").mkdir(parents=True)
        (tmp / "docs" / "autopilot" / "PLAN.md").write_text("- [ ] `T-001` việc — Gate: `true`\n", encoding="utf-8")
        if decisions is not None:
            (tmp / "docs" / "autopilot" / "DECISIONS.md").write_text(decisions, encoding="utf-8")
        if loop:
            env = dict(os.environ, CLAUDE_PROJECT_DIR=str(tmp))
            cmd = [sys.executable, str(tmp / "scripts" / "xt.py"), "loop", "init", "--single-session"]
            subprocess.run(cmd, check=True, env=env, capture_output=True)
        return tmp

    def evidence(self, tmp: Path, cmd: str, code: int) -> None:
        ev = tmp / ".autopilot" / "evidence"
        ev.mkdir(parents=True, exist_ok=True)
        rec = {"task": "T-001", "cmd": cmd, "exit_code": code, "finished": "2026-11-26T00:00:00+00:00"}
        (ev / "T-001.json").write_text(json.dumps(rec), encoding="utf-8")

    def assert_plain(self, out: str) -> None:
        self.assertFalse(out.lstrip().startswith("{"), out)  # chữ thường: JSON có `decision` sẽ chặn nén
        self.assertNotIn('"decision"', out)
        self.assertLessEqual(len(out), 10000)

    def test_prints_task_gate_dirty_and_latest_decision(self):
        tmp = self.project()
        self.evidence(tmp, "python3 -m unittest tests.test_x", 1)
        with isolated_git_environment():
            init_git_fixture(tmp)
        (tmp / "ghi-chú.txt").write_text("x", encoding="utf-8")
        code, out, err = run_pre_compact(tmp)
        self.assertEqual((code, err), (0, ""))
        self.assert_plain(out)
        self.assertIn("Task đang làm: T-001", out)
        self.assertIn("Gate cuối: T-001 `python3 -m unittest tests.test_x` exit 1.", out)
        self.assertIn("ghi-chú.txt", out)
        self.assertIn("mới nhất trong sổ: D-042.", out)
        self.assertIn("PR đang mở", out)
        st = json.loads((tmp / ".autopilot" / "state.json").read_text(encoding="utf-8"))
        self.assertIn(st["checkpoint"]["at"], out)  # đúng checkpoint vừa ghi

    def test_without_evidence_git_or_decision_log(self):
        tmp = self.project(decisions=None)
        code, out, _ = run_pre_compact(tmp)
        self.assertEqual(code, 0)
        self.assert_plain(out)
        self.assertIn("Gate cuối: chưa có bằng chứng.", out)
        self.assertIn("Tệp chưa commit: không.", out)
        self.assertIn("mới nhất trong sổ: —.", out)

    def test_evidence_without_exit_code_and_long_command_capped(self):
        tmp = self.project()
        ev = tmp / ".autopilot" / "evidence"
        ev.mkdir(parents=True, exist_ok=True)
        rec = {"task": "T-001", "cmd": "echo " + "ạ" * 20000, "finished": "2026-11-26T00:00:00+00:00"}
        (ev / "T-001.json").write_text(json.dumps(rec), encoding="utf-8")
        code, out, _ = run_pre_compact(tmp)
        self.assertEqual(code, 0)
        self.assert_plain(out)
        self.assertLessEqual(len(out), 9001)
        self.assertTrue(out.startswith("Chỉ dẫn tóm tắt"), out[:80])
        self.assertIn("Gate cuối: T-001 `echo ạạ", out)
        self.assertIn(" […]` exit —.", out)  # lệnh cắt ở 500 ký tự, exit code thiếu ghi —
        self.assertIn("PR đang mở", out)  # các dòng sau lệnh dài vẫn còn
        self.assertTrue(out.rstrip().endswith("để nạp lại vị trí."), out[-80:])

    def test_no_loop_prints_nothing(self):
        # T-1711: chưa `loop init` → không khởi động python, không in gì.
        tmp = self.project(loop=False)
        self.assertEqual(run_pre_compact(tmp), (0, "", ""))

    def test_stale_checkpoint_not_printed_when_write_fails(self):
        # Khoá hỏng → checkpoint không ghi được; checkpoint cũ trong state không được in (dẫn sai chỗ).
        tmp = self.project()
        sf = tmp / ".autopilot" / "state.json"
        st = json.loads(sf.read_text(encoding="utf-8"))
        st["checkpoint"] = {"at": "2000-01-01T00:00:00+00:00", "task": "T-CU"}
        sf.write_text(json.dumps(st), encoding="utf-8")
        lock = tmp / ".autopilot" / "state.lock"
        lock.unlink()
        lock.mkdir()
        code, out, _ = run_pre_compact(tmp)
        self.assertEqual((code, out), (0, ""))

    def test_garbage_state_or_checkpoint_types_print_nothing_or_safe_text(self):
        tmp = self.project()
        sf = tmp / ".autopilot" / "state.json"
        sf.write_text("không phải json", encoding="utf-8")
        self.assertEqual(run_pre_compact(tmp)[:2], (0, ""))
        sf.write_text(json.dumps([1, 2]), encoding="utf-8")  # không phải object
        self.assertEqual(run_pre_compact(tmp)[:2], (0, ""))

    def test_bad_field_types_in_checkpoint(self):
        # checkpoint do máy ghi, nhưng state sửa tay/hỏng kiểu không được làm hook lỗi hay in JSON.
        tmp = self.project()
        sf = tmp / ".autopilot" / "state.json"
        st = json.loads(sf.read_text(encoding="utf-8"))
        st["checkpoint"] = {"at": "2999-01-01T00:00:00+00:00", "last_evidence": "x", "dirty": "y", "task": None}
        sf.write_text(json.dumps(st), encoding="utf-8")
        lock = tmp / ".autopilot" / "state.lock"
        lock.unlink()
        lock.mkdir()  # checkpoint mới không ghi được → giữ bản (tương lai) ở trên
        code, out, _ = run_pre_compact(tmp)
        self.assertEqual(code, 0)
        self.assert_plain(out)
        self.assertIn("Task đang làm: —", out)
        self.assertIn("Gate cuối: chưa có bằng chứng.", out)
        self.assertIn("Tệp chưa commit: không.", out)

    def test_concurrent_compactions_never_block(self):
        # Phiên chính và subagent nén cùng lúc: mỗi hook exit 0, in chữ thường, state vẫn là JSON hợp lệ.
        tmp = self.project()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: run_pre_compact(tmp), range(4)))
        for code, out, _ in results:
            self.assertEqual(code, 0)
            self.assert_plain(out)
        st = json.loads((tmp / ".autopilot" / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(st["checkpoint"]["trigger"], "auto")


class CompactSettingsTest(unittest.TestCase):
    """Sai kiểu giá trị làm Claude Code loại cả tệp settings dự án (hook guard tắt theo) — docs settings §Fix a broken
    settings file, đọc 2026-11-26. Ghim kiểu các khoá T-5040 thêm."""

    def test_auto_compact_window_integer_and_env_strings(self):
        s = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
        w = s["autoCompactWindow"]
        self.assertIs(type(w), int)  # không chuỗi, không bool, không "400k"
        self.assertGreaterEqual(w, 100000)
        self.assertEqual(w, 400000)  # D-613
        self.assertTrue(all(isinstance(v, str) for v in s["env"].values()), s["env"])
        self.assertEqual(s["env"]["CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"], "1")  # LOOP-ORCH-001
        self.assertNotIn("CLAUDE_CODE_AUTO_COMPACT_WINDOW", s["env"])  # biến thắng cả --autocompact (LOOP-CTX-016)

    def test_fresh_install_target_gets_keys_and_hook(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import install

        target = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, target, True)
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(install.main([str(target), "--label", "test"]), 0)
        s = json.loads((target / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual((s["autoCompactWindow"], s["env"]), (400000, {"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1"}))
        hook = target / ".claude" / "hooks" / "pre-compact.sh"
        self.assertEqual(hook.read_bytes(), HOOK.read_bytes())


if __name__ == "__main__":
    unittest.main()
