"""Dò drift lệnh trong tài liệu cho agent (ý "drift AGENTS.md" của catalog stored, §6.4): mọi cờ `--xxx` nhắc sau
`xt.py <lệnh…>` hoặc `<XT> <lệnh…>` ở AGENTS.md, CLAUDE.md, README, skill, agent và `framework/` phải có thật ở lệnh đó
(parser của `xt.py` là nguồn). Đổi tên hay xoá cờ mà quên sửa skill thì test đỏ — agent đọc skill rồi gọi lệnh không tồn tại."""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import xt

REF = re.compile(r"(?:xt\.py|<XT>)\s+([a-z][a-z0-9-]*)([^`|;&)]*)")
FLAG = re.compile(r"(?<![\w-])(--[a-z][a-z0-9-]*)")
TOKEN = re.compile(r"[a-z][a-z0-9-]*")
# Cờ nhắc có chủ ý mà không (còn) tồn tại: `(lệnh, cờ)` → lý do. Rỗng = không có ngoại lệ.
ALLOWED: dict[tuple[str, str], str] = {}


def subcommands(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return dict(action.choices)
    return {}


def options(parser: argparse.ArgumentParser) -> set[str]:
    return {opt for action in parser._actions for opt in action.option_strings}


def resolve(
    top: dict[str, argparse.ArgumentParser], first: str, rest: str
) -> tuple[argparse.ArgumentParser, str] | None:
    """Parser của lệnh con sâu nhất mà `first rest…` gọi tên (đi theo từ liền kề là lệnh con); lệnh không biết → None."""
    node = top.get(first)
    if node is None:
        return None
    label = first
    for token in TOKEN.findall(rest.split("--")[0]):
        nested = subcommands(node)
        if token not in nested:
            break
        node, label = nested[token], f"{label} {token}"
    return node, label


def doc_files() -> list[Path]:
    files = [ROOT / "AGENTS.md", ROOT / "CLAUDE.md", ROOT / "README.md"]
    return files + sorted((ROOT / ".claude").rglob("*.md")) + sorted((ROOT / "framework").rglob("*.md"))


def drift(files: list[Path]) -> tuple[int, list[str]]:
    """(số cờ đã kiểm, danh sách `đường:dòng: lệnh cờ` lệch)."""
    top = subcommands(xt.build_parser())
    checked, bad = 0, []
    for path in files:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in REF.finditer(line):
                found = resolve(top, match[1], match[2])
                if found is None:
                    continue
                node, label = found
                for flag in FLAG.findall(match[2]):
                    checked += 1
                    if flag not in options(node) | {"--help"} and (label, flag) not in ALLOWED:
                        bad.append(f"{path.relative_to(ROOT)}:{number}: `{label}` không có cờ {flag}")
    return checked, bad


class DocCommandDriftTest(unittest.TestCase):
    def test_flags_cited_in_agent_docs_exist(self):
        checked, bad = drift(doc_files())
        self.assertGreater(checked, 100)  # bộ dò thật sự đọc được tham chiếu, không rỗng vì đổi định dạng
        self.assertEqual(bad, [], "tài liệu nhắc cờ không tồn tại — sửa tài liệu hoặc khai ALLOWED kèm lý do")

    def test_detector_reports_a_planted_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            planted = Path(tmp) / "x.md"
            planted.write_text(
                "`python3 scripts/xt.py pr next --pr 3 --khong-co-co`\n`xt.py loop record --task T-1 --no-tick`\n",
                encoding="utf-8",
            )
            with unittest.mock.patch.object(sys.modules[__name__], "ROOT", Path(tmp)):
                checked, bad = drift([planted])
        self.assertEqual(checked, 4)
        self.assertEqual(len(bad), 1)
        self.assertIn("`pr next` không có cờ --khong-co-co", bad[0])

    def test_resolve_descends_nested_subcommands_and_ignores_unknown(self):
        top = subcommands(xt.build_parser())
        node, label = resolve(top, "perf", " trial start --hypothesis x") or (None, "")
        self.assertEqual(label, "perf trial start")
        self.assertIn("--hypothesis", options(node))
        self.assertIsNone(resolve(top, "khong-co-lenh", " --x"))
        leaf = resolve(top, "validate", " --json") or (None, "")
        self.assertEqual(leaf[1], "validate")


if __name__ == "__main__":
    unittest.main()
