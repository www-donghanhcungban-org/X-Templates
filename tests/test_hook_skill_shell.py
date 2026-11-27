"""`pre-bash-guard.sh` với payload `PreSkillShellCommand` (lệnh chèn `!`…`` khi skill nạp — PreToolUse không chạy cho
chúng; docs hooks §PreSkillShellCommand, Claude Code ≥ 2.1.332, đọc 2026-11-27). Cùng script dùng được cho cả hai sự
kiện: guard không đọc `hook_event_name`/`tool_name`, trả JSON PreToolUse (`hookEventName: PreToolUse` — docs cho phép khi
dùng chung script) hoặc exit 2. Trên sự kiện này `ask`/`defer`/`updatedInput` bị Claude Code coi như `deny` (T-5040).
Đăng ký sự kiện ở settings còn chờ (harness-files.md §Giới hạn đã biết); `RegistrationTest` ghim điều kiện khi đăng ký."""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "hooks"
sys.path.insert(0, str(ROOT / "scripts"))
import install


def skill_payload(cmd: str, tool: str = "Bash") -> str:
    return json.dumps(
        {
            "session_id": "s-1",
            "hook_event_name": "PreSkillShellCommand",
            "permission_mode": "bypassPermissions",
            "tool_name": tool,
            "tool_input": {"command": cmd},
            "tool_use_id": "inj-1",
            "command_name": "my-plugin:deploy",
            "command_source": "plugin",
            "invoked_by": "claude",
        }
    )


def run_guard(cmd: str, tool: str = "Bash", policy: str = "", hooks: Path = HOOKS) -> tuple[int, str]:
    env = {k: v for k, v in os.environ.items() if k != "XT_GUARD_POLICY"}
    env.update(CLAUDE_PROJECT_DIR=str(ROOT), XT_GUARD_PHASE="harden", **({"XT_GUARD_POLICY": policy} if policy else {}))
    r = subprocess.run(
        ["bash", str(hooks / "pre-bash-guard.sh")],
        input=skill_payload(cmd, tool),
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    return r.returncode, r.stdout


def decision(out: str) -> str | None:
    if not out.strip():
        return None
    d = json.loads(out)["hookSpecificOutput"]
    assert d["hookEventName"] == "PreToolUse", d  # một script cho cả hai sự kiện (docs)
    return str(d["permissionDecision"])


@unittest.skipIf(shutil.which("bash") is None, "cần bash")
class SkillShellGuardTest(unittest.TestCase):
    def test_dangerous_injected_commands_denied(self):
        for tool, cmd in (
            ("Bash", "git push --force origin main"),
            ("Bash", "rm -rf /"),
            ("Bash", "git push origin main"),
            ("PowerShell", "rm -rf ~"),
            ("Bash", "echo xin chào\ngit push --force origin main"),  # khối ```! nhiều dòng: dòng sau vẫn bị xét
        ):
            with self.subTest(tool=tool, cmd=cmd):
                code, out = run_guard(cmd, tool)
                self.assertEqual((code, decision(out)), (0, "deny"))

    def test_safe_injected_commands_pass(self):
        for cmd in ("git status --short", "echo hello", "git log --oneline -3"):
            with self.subTest(cmd=cmd):
                self.assertEqual(run_guard(cmd), (0, ""))

    def test_strict_policy_ask_is_not_silent_allow(self):
        # strict: guard trả `ask` — trên PreSkillShellCommand Claude Code chặn như `deny` (fail-closed), không cho chạy.
        code, out = run_guard("git push origin main", policy="strict")
        self.assertEqual((code, decision(out)), (0, "ask"))
        self.assertEqual(run_guard("git status --short", policy="strict"), (0, ""))

    def test_missing_guard_fails_closed(self):
        # ADR-0002: guard.py vắng → chặn mọi lệnh trừ lệnh xem/khôi phục một dòng, cả khi đến từ skill.
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        hooks = tmp / "hooks"
        shutil.copytree(HOOKS, hooks)
        (hooks / "guard.py").unlink()
        code, out = run_guard("rm -rf build", hooks=hooks)
        self.assertEqual((code, decision(out)), (0, "deny"))
        self.assertEqual(run_guard("git status", hooks=hooks), (0, ""))

    def test_concurrent_injected_commands_each_decided(self):
        # Skill có nhiều lệnh chèn: Claude Code gọi hook cho từng lệnh, có thể song song — mỗi lệnh quyết riêng.
        cmds = ["rm -rf /", "echo a", "git push --force origin main", "git status --short"] * 2
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            got = list(pool.map(lambda c: decision(run_guard(c)[1]), cmds))
        self.assertEqual(got, ["deny", None, "deny", None] * 2)

    def test_empty_or_broken_payload_does_not_hang(self):
        # Fail-open về luồng (ADR-0002): payload rỗng/hỏng không có lệnh để chạy → exit 0, không in, không treo.
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(ROOT))
        env.pop("XT_GUARD_POLICY", None)
        for raw in (
            "",
            "không phải json",
            "{}",
            "[1, 2]",
            '{"hook_event_name": "PreSkillShellCommand", "tool_input": {}}',
        ):
            with self.subTest(raw=raw):
                r = subprocess.run(
                    ["bash", str(HOOKS / "pre-bash-guard.sh")],
                    input=raw,
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=120,
                )
                self.assertEqual((r.returncode, r.stdout), (0, ""))


def min_version(text: str) -> tuple[int, ...] | None:
    m = re.search(r"""^claude_min_version:[ \t]*["']?(\d+)\.(\d+)\.(\d+)["']?[ \t]*(?:#.*)?$""", text, re.M)
    return tuple(int(x) for x in m.groups()) if m else None


class RegistrationTest(unittest.TestCase):
    """Bản < 2.1.332 chạy lệnh chèn mà không gọi hook và mở hộp thoại `Unknown hook event` (changelog 2.1.332): sàn
    phiên bản ghim ở `xt.yaml` (doctor cảnh báo — LOOP-HARNESS-026). Đã đăng ký thì phải đúng lệnh guard Bash; chưa đăng
    ký thì giới hạn phải ghi ở harness-files.md."""

    SKILL_SHELL_MIN = (2, 1, 332)

    def test_min_version_covers_skill_shell_hook(self):
        got = min_version((ROOT / "xt.yaml").read_text(encoding="utf-8"))
        self.assertIsNotNone(got, "xt.yaml thiếu claude_min_version")
        self.assertGreaterEqual(got, self.SKILL_SHELL_MIN)
        self.assertIsNone(min_version("claude_min_version: 2.1\n"))
        self.assertEqual(min_version('claude_min_version: "2.1.400" # x\n'), (2, 1, 400))

    def test_registered_entry_reuses_bash_guard_or_limit_documented(self):
        hooks = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))["hooks"]
        doc = (ROOT / "framework" / "11-autonomous-loop" / "harness-files.md").read_text(encoding="utf-8")
        if "PreSkillShellCommand" not in hooks:
            limit = doc.split("**Lệnh chèn trong skill**", 1)[-1].split("\n- **", 1)[0]
            self.assertIn("PreSkillShellCommand", limit)
            self.assertIn("**chưa đăng ký**", limit)
            self.assertIn("2.1.332", limit)
            return
        bash = [h for e in hooks["PreToolUse"] if e.get("matcher") == "Bash" for h in e["hooks"]]
        (entry,) = hooks["PreSkillShellCommand"]
        self.assertEqual(entry["matcher"], "Bash|PowerShell")
        self.assertEqual(entry["hooks"], bash)  # cùng lệnh, timeout, onFailure: block — không nhân bản luật
        self.assertEqual(bash[0]["onFailure"], "block")
        self.assertNotIn("**chưa đăng ký**", doc)


class InstallMergeSkillShellTest(unittest.TestCase):
    """Khi khung đăng ký sự kiện: `install.py` gộp theo từng sự kiện, nên cùng lệnh guard đã có ở PreToolUse của đích
    không làm mục PreSkillShellCommand bị bỏ qua; `onFailure: block` và matcher đi theo."""

    GUARD = 'bash "${CLAUDE_PROJECT_DIR}/.claude/hooks/pre-bash-guard.sh"'

    def entry(self, matcher: str) -> dict[str, Any]:
        hook = {"type": "command", "command": self.GUARD, "timeout": 1200, "onFailure": "block"}
        return {"matcher": matcher, "hooks": [hook]}

    def test_new_event_with_same_command_is_added(self):
        ours = {"hooks": {"PreToolUse": [self.entry("Bash")], "PreSkillShellCommand": [self.entry("Bash|PowerShell")]}}
        hooks: dict[str, Any] = {"PreToolUse": [self.entry("Bash")]}
        added, synced = install._merge_hook_events(ours, {"hooks": hooks})
        self.assertEqual(
            added, [{"event": "PreSkillShellCommand", "matcher": "Bash|PowerShell", "commands": [self.GUARD]}]
        )
        self.assertEqual(synced, [])
        self.assertEqual(hooks["PreSkillShellCommand"], [self.entry("Bash|PowerShell")])
        self.assertEqual(hooks["PreToolUse"], [self.entry("Bash")])

    def test_target_that_already_has_it_is_not_duplicated(self):
        ours = {"hooks": {"PreSkillShellCommand": [self.entry("Bash|PowerShell")]}}
        hooks: dict[str, Any] = {"PreSkillShellCommand": [self.entry("Bash|PowerShell")]}
        self.assertEqual(install._merge_hook_events(ours, {"hooks": hooks}), ([], []))
        self.assertEqual(hooks["PreSkillShellCommand"], [self.entry("Bash|PowerShell")])


if __name__ == "__main__":
    unittest.main()
