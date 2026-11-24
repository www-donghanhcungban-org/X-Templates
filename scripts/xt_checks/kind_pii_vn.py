"""Loại `pii-vn` (CMP-PRIV-010, PM-METRIC-005, AI-GUARD-004, PRF-DATA-009): dữ liệu cá nhân Việt Nam chưa che trong tệp mẫu/log/fixture.
`PII000` tệp không đọc được (không phải UTF-8, quá 2 MiB, lỗi đọc: không được bỏ qua im lặng), `PII001` số CCCD 12 chữ số, `PII002` số di động, `PII003` email, `PII004` khoá/cột nhạy cảm có giá trị chưa che. Giả định CCCD
(heuristic, không phải kiểm số thật): 3 số đầu trong 001–096 (không đối chiếu từng mã tỉnh), số thứ 4 trong 0–3 (thế kỷ/giới
tính 1900–2099), 2 số kế là năm sinh; biên không dính chữ/số/gạch nối để khỏi bắt timestamp, UUID, ID dài. Email bỏ miền tài liệu
(example.*, .test, .invalid, localhost) và `--opt allow_domains=a.vn,b.vn`. Dòng có `xt-allow: PII00N` bỏ mã đó; `--opt ignore=…`
bỏ toàn cục. Thông điệp che toàn bộ giá trị dài ≤ 8 ký tự, giá trị dài hơn giữ 2 ký tự đầu và cuối."""

from __future__ import annotations

import csv
import re
from pathlib import Path

from . import Finding, read_text

HELP = "dữ liệu cá nhân Việt Nam chưa che (CCCD, SĐT, email, khoá nhạy cảm) trong tệp mẫu/log/fixture"
SUFFIXES = (".csv", ".json", ".jsonl", ".ndjson", ".sql", ".log", ".txt", ".tsv")
OPTS = ("allow_domains", "ignore")
_B = r"(?<![\w-])"
_E = r"(?![\w-])"
CCCD = re.compile(_B + r"(?:00[1-9]|0[1-8]\d|09[0-6])[0-3]\d{8}" + _E)
PHONE = re.compile(_B + r"(?:\+?84|0)[35789]\d{8}" + _E)
# Phần trước `@` chặn ở 64 ký tự (giới hạn RFC 5321): mỗi vị trí chỉ quét tối đa 64 nên dòng dài base64/hex vẫn tuyến tính mà
# không cần neo lookbehind (neo làm mất email dính liền sau ký tự khác — rà #776 lượt hai).
EMAIL = re.compile(r"[\w.+-]{1,64}+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*)")
PAIR = re.compile(r"""(?<![\w-])["']?([\w-]++)["']?\s*[:=]\s*("[^"]*"|'[^']*'|[^\s,;}]+)""")
ALLOW = re.compile(r"xt-allow:([\sA-Z0-9,]*)")
LINE_BREAK = re.compile(r"\r\n|\r|\n")
DOC_DOMAINS = ("example.com", "example.org", "example.net", "test", "invalid", "localhost")
SENSITIVE = frozenset({"cccd", "cmnd", "sodienthoai", "sdt", "phone", "email", "hoten", "diachi", "ngaysinh"})
HIDDEN = re.compile(r"x{3,}|\*|\[redacted\]", re.IGNORECASE)


def _mask(value: str) -> str:
    return value[:2] + "*" * (len(value) - 4) + value[-2:] if len(value) > 8 else "*" * len(value)


def _norm(name: str) -> str:
    return name.lower().replace("_", "").replace("-", "")


def _unmasked(value: str) -> bool:
    text = value.strip().strip("\"'").strip()
    return bool(text) and text.lower() not in {"null", "none"} and not HIDDEN.search(text)


def _domain_ok(domain: str, allowed: tuple[str, ...]) -> bool:
    low = domain.lower()
    return any(low == a or low.endswith("." + a) for a in DOC_DOMAINS + allowed)


def _hits(line: str, allowed: tuple[str, ...]) -> list[tuple[str, str]]:
    found = [("PII001", "số CCCD 12 chữ số chưa che: " + _mask(m.group())) for m in CCCD.finditer(line)]
    found += [("PII002", "số di động chưa che: " + _mask(m.group())) for m in PHONE.finditer(line)]
    for m in EMAIL.finditer(line):
        if not _domain_ok(m.group(1), allowed):
            found.append(("PII003", "email chưa che: " + _mask(m.group())))
    for m in PAIR.finditer(line):
        if _norm(m.group(1)) in SENSITIVE and _unmasked(m.group(2)):
            found.append(
                ("PII004", f"khoá nhạy cảm '{m.group(1)}' có giá trị chưa che: " + _mask(m.group(2).strip("\"'")))
            )
    return found


def _columns(line: str, delim: str, cols: list[int] | None) -> tuple[list[int], list[tuple[str, str]]]:
    """Dòng đầu tệp bảng là tiêu đề: nhớ cột nhạy cảm; các dòng sau kiểm giá trị ở cột đó."""
    try:
        cells = next(csv.reader([line], delimiter=delim), [])
    except csv.Error:  # ô lớn hơn giới hạn của `csv` (131072): tách thô theo dấu phân cách thay vì văng traceback
        cells = line.split(delim)
    if cols is None:
        return [i for i, c in enumerate(cells) if _norm(c) in SENSITIVE], []
    return cols, [
        ("PII004", f"cột nhạy cảm #{i + 1} có giá trị chưa che: " + _mask(cells[i]))
        for i in cols
        if i < len(cells) and _unmasked(cells[i])
    ]


def check(files: list[Path], opts: dict[str, str]) -> list[Finding]:
    ignore = {c.strip() for c in opts.get("ignore", "").split(",") if c.strip()}
    allowed = tuple(d.strip().lower() for d in opts.get("allow_domains", "").split(",") if d.strip())
    found: list[Finding] = []
    for path in files:
        text = read_text(path)
        if text is None:
            if "PII000" not in ignore:
                found.append(
                    Finding(
                        str(path),
                        0,
                        "PII000",
                        "không đọc được dưới dạng UTF-8 (hoặc quá lớn) — chưa kiểm dữ liệu cá nhân",
                    )
                )
            continue
        delim = "\t" if path.suffix.lower() == ".tsv" else ","
        cols: list[int] | None = None
        # Ngắt dòng `\r\n`, `\r` hoặc `\n` (CSV xuất từ Mac cũ chỉ có `\r`: tách theo `\n` làm cả tệp thành một dòng và bỏ lọt
        # cột nhạy cảm — rà #776 lượt hai 🟠); U+2028/form feed không tách dòng như editor và `grep -n`.
        for number, line in enumerate(LINE_BREAK.split(text), 1):
            hits = _hits(line, allowed)
            if path.suffix.lower() in (".csv", ".tsv") and line.strip():
                cols, extra = _columns(line, delim, cols)
                hits += extra
            skip = ignore | set(re.findall(r"PII\d{3}", "".join(ALLOW.findall(line))))
            found += [Finding(str(path), number, c, m) for c, m in hits if c not in skip]
    return found
