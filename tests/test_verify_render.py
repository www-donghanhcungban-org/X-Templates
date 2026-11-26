"""T-5034 (D-516, D-608): bất biến THẬT quanh cổng `verify-render.mjs` và bài e2e `verify_render.test.mjs` — workflow
chạy bài e2e phủ cả hai tệp theo `paths:`, có lệnh `node --test`, README ui-gates liệt kê mọi cờ CLI của mã. Nhờ đó
`xt.py test-select` ánh xạ hai tệp này tới lớp test hẹp thay vì cả suite."""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent
GATE = "framework/templates/ui-gates/verify-render.mjs"
E2E = "tests_e2e/verify_render.test.mjs"
WORKFLOW = ROOT / ".github" / "workflows" / "pack-web-api.yml"
README = ROOT / "framework" / "templates" / "ui-gates" / "README.md"
# Khai báo cờ trong `parseArgs({ options: { <tên>: { type: … } } })`: một khối options, mỗi cờ một dòng.
_OPTIONS_BLOCK = re.compile(r"options:\s*\{\n(.*?)\n\s*\},\n\s*\}\);", re.S)
_OPTION_NAME = re.compile(r"^\s*(\w+):\s*\{\s*type:\s*'(?:string|boolean)'", re.M)


def _glob_re(pattern: str) -> "re.Pattern[str]":
    """Glob của `on.<event>.paths` GitHub: `**` qua thư mục, `*` trong một cấp."""
    out = ""
    i = 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(out)


def _paths(event: str) -> List[str]:
    """Các mục `paths:` của sự kiện `event` (pull_request/push) đọc thẳng từ văn bản workflow."""
    text = WORKFLOW.read_text(encoding="utf-8")
    block = re.search(rf"^  {event}:\n(.*?)(?=^  \w|^\w)", text, re.S | re.M)
    assert block, event
    listed = re.search(r"^    paths:\n((?:      - .*\n)+)", block[1], re.M)
    assert listed, event
    return [ln.strip()[2:].strip() for ln in listed[1].splitlines()]


def gate_flags() -> List[str]:
    text = (ROOT / GATE).read_text(encoding="utf-8")
    block = _OPTIONS_BLOCK.search(text)
    assert block, "không thấy khối options của parseArgs"
    return sorted(f"--{name}" for name in _OPTION_NAME.findall(block[1]))


class VerifyRenderWorkflowTest(unittest.TestCase):
    def test_paths_cover_gate_and_e2e_in_both_events(self):
        for event in ("pull_request", "push"):
            paths = _paths(event)
            for f in (GATE, E2E):
                with self.subTest(event=event, file=f):
                    self.assertTrue(any(_glob_re(p).fullmatch(f) for p in paths), f"{event}: paths: không phủ {f}")

    def test_glob_helper_is_not_vacuous(self):
        self.assertIsNotNone(_glob_re("a/**").fullmatch("a/b/c.mjs"))
        self.assertIsNone(_glob_re("a/*").fullmatch("a/b/c.mjs"))
        self.assertIsNone(_glob_re("tests_e2e/x.mjs").fullmatch("tests_e2e/y.mjs"))

    def test_workflow_runs_node_test_on_e2e_file(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertRegex(text, rf"node --test {re.escape(E2E)}\b")
        self.assertTrue((ROOT / E2E).is_file())
        self.assertTrue((ROOT / GATE).is_file())


class VerifyRenderReadmeFlagsTest(unittest.TestCase):
    def test_flag_extraction_finds_known_flags(self):
        flags = gate_flags()
        self.assertTrue({"--widths", "--themes", "--limit", "--tags", "--strict", "--exceptions"} <= set(flags), flags)

    def test_readme_lists_every_cli_flag_of_gate(self):
        readme = README.read_text(encoding="utf-8")
        listed = set(re.findall(r"^\| `(--[a-z][a-z-]*)", readme, re.M))
        missing = [f for f in gate_flags() if f not in listed]
        self.assertEqual(missing, [], f"README ui-gates thiếu cờ của {GATE}: {missing}")


if __name__ == "__main__":
    unittest.main()
