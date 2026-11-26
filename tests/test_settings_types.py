"""Kiểm kiểu các khoá ĐÃ BIẾT của `.claude/settings.json` (T-5035). Một khoá sai kiểu làm Claude Code bỏ cả tệp
hoặc bỏ hook im lặng, mà `json.tool` vẫn xanh. Khoá lạ không làm đỏ. `install.py` chỉ cài chính tệp này (không có bản
settings mẫu riêng cho Claude Code), nên một nguồn là đủ.

`onFailure`: chỉ giá trị `"block"` đã xác minh từ tài liệu hooks (mức a, 2026-11-26); `"allow"` chưa xác minh nên
không được khẳng định."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / ".claude" / "settings.json"
ON_FAILURE = {"block"}
MIN_COMPACT_WINDOW = 100000


def is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def check_env(s: Dict[str, Any]) -> List[str]:
    env = s.get("env")
    if env is None:
        return []
    if not isinstance(env, dict):
        return ["env: phải là object"]
    return [f"env.{k}: giá trị phải là chuỗi" for k, v in env.items() if not isinstance(v, str)]


def check_compact(s: Dict[str, Any]) -> List[str]:
    if "autoCompactWindow" not in s:
        return []
    v = s["autoCompactWindow"]
    if not is_int(v) or v < MIN_COMPACT_WINDOW:
        return [f"autoCompactWindow: phải là số nguyên >= {MIN_COMPACT_WINDOW}"]
    return []


def check_permissions(s: Dict[str, Any]) -> List[str]:
    perms = s.get("permissions")
    if perms is None:
        return []
    if not isinstance(perms, dict):
        return ["permissions: phải là object"]
    errs: List[str] = []
    for key in ("allow", "deny", "ask"):
        if key not in perms:
            continue
        v = perms[key]
        if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            errs.append(f"permissions.{key}: phải là danh sách chuỗi")
    return errs


def check_hook(where: str, h: Any) -> List[str]:
    if not isinstance(h, dict):
        return [f"{where}: phải là object"]
    errs = [f"{where}.{k}: phải là chuỗi" for k in ("type", "command") if not isinstance(h.get(k), str)]
    if "timeout" in h and (not is_num(h["timeout"]) or h["timeout"] <= 0):
        errs.append(f"{where}.timeout: phải là số > 0 (không bool)")
    if "onFailure" in h and h["onFailure"] not in ON_FAILURE:
        errs.append(f"{where}.onFailure: ngoài tập {sorted(ON_FAILURE)}")
    return errs


def check_hook_entry(where: str, e: Any) -> List[str]:
    if not isinstance(e, dict):
        return [f"{where}: phải là object"]
    errs: List[str] = []
    if "matcher" in e and not isinstance(e["matcher"], str):
        errs.append(f"{where}.matcher: phải là chuỗi")
    hooks = e.get("hooks")
    if not isinstance(hooks, list):
        return errs + [f"{where}.hooks: phải là danh sách"]
    for i, h in enumerate(hooks):
        errs += check_hook(f"{where}.hooks[{i}]", h)
    return errs


def check_hooks(s: Dict[str, Any]) -> List[str]:
    hooks = s.get("hooks")
    if hooks is None:
        return []
    if not isinstance(hooks, dict):
        return ["hooks: phải là object"]
    errs: List[str] = []
    for event, entries in hooks.items():
        if not isinstance(entries, list):
            errs.append(f"hooks.{event}: phải là danh sách")
            continue
        for i, e in enumerate(entries):
            errs += check_hook_entry(f"hooks.{event}[{i}]", e)
    return errs


def check_settings(s: Any) -> List[str]:
    """Thuần: nhận dict settings, trả danh sách lỗi kiểu (rỗng = đạt)."""
    if not isinstance(s, dict):
        return ["settings: phải là object"]
    return check_env(s) + check_compact(s) + check_permissions(s) + check_hooks(s)


def hook_doc(**over: Any) -> Dict[str, Any]:
    h: Dict[str, Any] = {"type": "command", "command": "x", "timeout": 5, "onFailure": "block"}
    h.update(over)
    return {"hooks": {"Stop": [{"matcher": "Bash", "hooks": [h]}]}}


class RealSettingsTest(unittest.TestCase):
    def test_repo_settings_types(self):
        data = json.loads(SETTINGS.read_text(encoding="utf-8"))
        self.assertEqual(check_settings(data), [])

    def test_repo_has_hooks_to_check(self):
        data = json.loads(SETTINGS.read_text(encoding="utf-8"))
        self.assertTrue(any(h for es in data["hooks"].values() for e in es for h in e["hooks"]))


class PureCheckerTest(unittest.TestCase):
    def test_valid_and_unknown_keys_pass(self):
        doc = hook_doc()
        doc.update(
            {
                "env": {"A": "1"},
                "autoCompactWindow": 100000,
                "khoaLa": [1, {"x": None}],
                "permissions": {"allow": ["Bash"], "deny": [], "ask": ["x"], "lạ": 1},
            }
        )
        doc["hooks"]["Stop"][0]["hooks"][0]["khoaLa"] = True
        self.assertEqual(check_settings(doc), [])
        self.assertEqual(check_settings({}), [])
        self.assertEqual(check_settings(hook_doc(timeout=0.5)), [])

    def assert_caught(self, doc: Any, needle: str) -> None:
        errs = check_settings(doc)
        self.assertTrue(any(needle in e for e in errs), (needle, errs))

    def test_root_not_object(self):
        self.assert_caught([], "settings")

    def test_env(self):
        self.assert_caught({"env": {"A": 1}}, "env.A")
        self.assert_caught({"env": {"A": None}}, "env.A")
        self.assert_caught({"env": ["A"]}, "env:")

    def test_timeout(self):
        for bad in ("5", True, 0, -1, None, [1]):
            with self.subTest(bad=bad):
                self.assert_caught(hook_doc(timeout=bad), "timeout")

    def test_on_failure(self):
        for bad in ("allow", "BLOCK", True, None, 1):
            with self.subTest(bad=bad):
                self.assert_caught(hook_doc(onFailure=bad), "onFailure")

    def test_auto_compact_window(self):
        for bad in (99999, "100000", True, 150000.5, None):
            with self.subTest(bad=bad):
                self.assert_caught({"autoCompactWindow": bad}, "autoCompactWindow")

    def test_permissions(self):
        for key in ("allow", "deny", "ask"):
            self.assert_caught({"permissions": {key: "Bash"}}, f"permissions.{key}")
            self.assert_caught({"permissions": {key: ["a", 1]}}, f"permissions.{key}")
        self.assert_caught({"permissions": []}, "permissions:")

    def test_hook_type_command(self):
        for k in ("type", "command"):
            self.assert_caught(hook_doc(**{k: 1}), f".{k}")
            self.assert_caught(hook_doc(**{k: None}), f".{k}")

    def test_hook_missing_fields(self):
        doc = {"hooks": {"Stop": [{"hooks": [{}]}]}}
        errs = check_settings(doc)
        self.assertEqual(len(errs), 2, errs)

    def test_matcher(self):
        doc = hook_doc()
        doc["hooks"]["Stop"][0]["matcher"] = ["Bash"]
        self.assert_caught(doc, "matcher")

    def test_structure(self):
        self.assert_caught({"hooks": []}, "hooks:")
        self.assert_caught({"hooks": {"Stop": {}}}, "hooks.Stop")
        self.assert_caught({"hooks": {"Stop": ["x"]}}, "hooks.Stop[0]")
        self.assert_caught({"hooks": {"Stop": [{"matcher": "a"}]}}, ".hooks")
        self.assert_caught({"hooks": {"Stop": [{"hooks": ["x"]}]}}, "hooks[0]")


if __name__ == "__main__":
    unittest.main()
