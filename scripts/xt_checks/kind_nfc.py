"""Loại `nfc` (UX-CONTENT-002, BASE-DATA-*, FE-FORM-013): văn bản tiếng Việt phải ở dạng Unicode NFC — dấu dạng tổ hợp nhìn giống
nhau nhưng khác mã nên làm hỏng tìm kiếm, so khớp và khoá duy nhất ("Việt" ≠ "Việt"). Báo: `NFC000` không đọc được UTF-8 (hay
quá lớn; mã hoá cũ như TCVN3/VNI thường rơi vào đây), `NFC001` dòng chưa NFC, `NFC002` ký tự thay thế U+FFFD (đã mất chữ),
`NFC003` ký tự ẩn (BOM, ký tự không độ rộng). Khai `--opt ignore=NFC003,…` để bỏ mã không áp dụng."""

from __future__ import annotations

import unicodedata
from pathlib import Path

from . import Finding, read_text

HELP = "văn bản không ở dạng NFC, ký tự thay thế U+FFFD, ký tự ẩn (BOM, zero-width)"
SUFFIXES = (
    ".md",
    ".txt",
    ".json",
    ".csv",
    ".sql",
    ".yaml",
    ".yml",
    ".html",
    ".css",
    ".po",
    ".srt",
    ".vtt",
    ".xlf",
    ".xliff",
    ".properties",
)
HIDDEN = frozenset(
    chr(code) for code in (0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF)
)  # ký tự ẩn: viết bằng mã, không bằng chữ
OPTS = ("ignore",)
REPLACEMENT = chr(0xFFFD)


def _line_findings(path: str, number: int, line: str, ignore: set[str]) -> list[Finding]:
    found: list[Finding] = []
    if "NFC001" not in ignore and not unicodedata.is_normalized("NFC", line):
        found.append(Finding(path, number, "NFC001", "chuỗi không ở dạng NFC (dấu tổ hợp) — chuẩn hoá về NFC"))
    if "NFC002" not in ignore and REPLACEMENT in line:
        found.append(Finding(path, number, "NFC002", "có ký tự thay thế U+FFFD — chữ đã mất khi đổi mã hoá"))
    if "NFC003" not in ignore and any(ch in HIDDEN for ch in line):
        found.append(Finding(path, number, "NFC003", "có ký tự ẩn (BOM hoặc ký tự không độ rộng)"))
    return found


def check(files: list[Path], opts: dict[str, str]) -> list[Finding]:
    ignore = {code for code in opts.get("ignore", "").split(",") if code}
    found: list[Finding] = []
    for path in files:
        text = read_text(path)
        if text is None:
            if "NFC000" not in ignore:
                found.append(Finding(str(path), 0, "NFC000", "không đọc được dưới dạng UTF-8 (hoặc quá lớn)"))
            continue
        for number, line in enumerate(text.split("\n"), 1):
            found.extend(_line_findings(str(path), number, line.removesuffix("\r"), ignore))
    return found
