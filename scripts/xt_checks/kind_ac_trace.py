"""Loại `ac-trace` (WF-SDD-003, WF-SDD-008): mỗi tiêu chí chấp nhận `AC-<số>` định nghĩa trong spec phải được ít nhất một test nhắc
(tên test, docstring, chú thích). Mã đứng đầu dòng spec (sau `-`, `*`, `#`, `|`, `**`, khoảng trắng) là định nghĩa; chỗ khác chỉ
là nhắc. Báo: `ACT000` thư mục test không có/không đọc được, `ACT001` AC chưa test nào nhắc, `ACT002` test nhắc AC không spec nào
định nghĩa, `ACT003` AC định nghĩa hai nơi. Khai `--opt tests=<thư mục>` (mặc định `tests`), `--opt test_suffixes=.py,.go,…`."""

from __future__ import annotations

import re
from pathlib import Path

from . import CheckError, Finding, collect, read_text

HELP = "tiêu chí AC-<số> trong spec chưa có test nhắc tới, test nhắc AC lạ, AC định nghĩa hai nơi"
SUFFIXES = (".md",)
OPTS = ("tests", "test_suffixes")
TEST_SUFFIXES = ".py,.js,.jsx,.ts,.tsx,.go,.rs,.java,.rb,.feature"
DEFINE = re.compile(r"^[\s\-*#|]*(AC-\d+)(?!\w|-\w)")
MENTION = re.compile(r"(?<![\w-])AC-\d+(?!\w|-\w)")


def _definitions(files: list[Path]) -> tuple[dict[str, tuple[str, int]], list[Finding]]:
    first: dict[str, tuple[str, int]] = {}
    found: list[Finding] = []
    for path in files:
        text = read_text(path)
        for number, line in enumerate((text or "").splitlines(), 1):
            match = DEFINE.match(line)
            if match is None:
                continue
            code = match.group(1)
            if code in first:
                where = f"{first[code][0]}:{first[code][1]}"
                found.append(Finding(str(path), number, "ACT003", f"{code} đã định nghĩa ở {where}"))
            else:
                first[code] = (str(path), number)
    return first, found


def check(files: list[Path], opts: dict[str, str]) -> list[Finding]:
    folder = opts.get("tests", "tests")
    suffixes = tuple(s.strip().lower() for s in opts.get("test_suffixes", TEST_SUFFIXES).split(",") if s.strip())
    try:
        tests = collect([folder], suffixes) if Path(folder).is_dir() else None
    except CheckError:
        tests = None
    if tests is None:
        return [Finding(folder, 0, "ACT000", "thư mục test không có hoặc không đọc được")]
    defined, found = _definitions(files)
    mentioned: set[str] = set()
    for path in tests:
        text = read_text(path)
        for number, line in enumerate((text or "").splitlines(), 1):
            for code in sorted(set(MENTION.findall(line))):
                mentioned.add(code)
                if code not in defined:
                    found.append(Finding(str(path), number, "ACT002", f"test nhắc {code} nhưng spec không định nghĩa"))
    for code, (where, number) in defined.items():
        if code not in mentioned:
            found.append(Finding(where, number, "ACT001", f"{code} chưa có test nào nhắc tới"))
    return found
