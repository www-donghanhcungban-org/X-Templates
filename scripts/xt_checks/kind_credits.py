"""Loại `credits` (UX-VISUAL-007, CMP-LIC-026): mọi tệp media (ảnh, âm thanh, video, font) phải có một dòng trong bảng
`assets/CREDITS.md` ghi nguồn và license. Báo: `CRD000` không đọc được tệp credits, `CRD001` media không có dòng, `CRD002`
dòng thiếu nguồn, `CRD003` license ngoài danh sách cho phép, `CRD004` dòng trỏ tới tệp không còn (chỉ khi tệp đó nằm cùng cây
với các tệp được kiểm). Khai `--opt credits=ĐƯỜNG` và `--opt allow=MIT,CC0-1.0,…` (license SPDX, so không phân biệt hoa thường)."""

from __future__ import annotations

import os
from pathlib import Path

from . import Finding, read_text

HELP = "tệp media thiếu dòng nguồn/license trong assets/CREDITS.md, license ngoài danh sách cho phép"
SUFFIXES = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".avif",
    ".svg",
    ".ico",
    ".mp3",
    ".wav",
    ".ogg",
    ".flac",
    ".m4a",
    ".mp4",
    ".webm",
    ".mov",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
)
ALLOW = (
    "CC0-1.0,CC-BY-4.0,CC-BY-SA-4.0,MIT,Apache-2.0,BSD-2-Clause,BSD-3-Clause,ISC,OFL-1.1,Unlicense,LicenseRef-Project"
)
OPTS = ("credits", "allow")
SRC_WORDS = ("nguồn", "source", "tác giả", "author")
LIC_WORDS = ("license", "licence", "giấy phép")
EMPTY = frozenset({"", "-", "?", "tbd", "todo", "n/a"})
RuleRow = tuple[int, list[str], int, int]


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_sep(cells: list[str]) -> bool:
    return all(set(c) <= set("-: ") for c in cells) and "-" in "".join(cells)


def _col(header: list[str], words: tuple[str, ...], default: int) -> int:
    return next((i for i, c in enumerate(header) if any(w in c.lower() for w in words)), default)


def _rows(text: str) -> list[RuleRow]:
    """Dòng dữ liệu của các bảng: (số dòng, ô, cột nguồn, cột license); tiêu đề và dòng kẻ bị bỏ."""
    table = [(n, _cells(s)) for n, s in enumerate(text.splitlines(), 1) if s.lstrip().startswith("|")]
    out: list[RuleRow] = []
    src, lic = 1, 2
    for i, (number, cells) in enumerate(table):
        if _is_sep(cells):
            continue
        if i + 1 < len(table) and _is_sep(table[i + 1][1]):
            src, lic = _col(cells, SRC_WORDS, 1), _col(cells, LIC_WORDS, 2)
            continue
        out.append((number, cells, src, lic))
    return out


def _at(cells: list[str], index: int) -> str:
    return cells[index].strip("`").strip() if index < len(cells) else ""


def _key(cells: list[str]) -> str:
    return _at(cells, 0).removeprefix("./")


def _hits(path: Path, key: str) -> bool:
    posix = path.as_posix()
    return posix == key or posix.endswith("/" + key)


def _is_missing(key: str, credits: Path, files: list[Path]) -> bool:
    """Tệp `key` không còn mà vị trí dự kiến nằm cùng cây với các tệp được kiểm."""
    root = Path(os.path.commonpath([str(p.resolve().parent) for p in files]))
    bases = (credits.parent, credits.parent.parent, Path("."))
    try:
        spots = [(base / key).resolve() for base in bases]
        present = any(s.exists() for s in spots)  # `exists` cũng ném OSError với tên quá dài trên CPython 3.13
    except (OSError, ValueError):  # tên không hợp lệ (NUL, quá dài): không thể tồn tại → coi là không còn
        return True
    return not present and any(s.is_relative_to(root) for s in spots)


def check(files: list[Path], opts: dict[str, str]) -> list[Finding]:
    media = [p for p in files if p.suffix.lower() in SUFFIXES]
    if not media:
        return []
    credits = Path(opts.get("credits", "assets/CREDITS.md"))
    text = read_text(credits)
    if text is None:
        return [Finding(str(credits), 0, "CRD000", "không đọc được tệp credits (UTF-8)")]
    allow = {s.strip().lower() for s in opts.get("allow", ALLOW).split(",") if s.strip()}
    rows = [r for r in _rows(text) if Path(_key(r[1])).suffix.lower() in SUFFIXES]
    found: list[Finding] = []
    keys = [_key(r[1]) for r in rows]
    for path in media:
        if not any(_hits(path, k) for k in keys):
            found.append(Finding(str(path), 0, "CRD001", "tệp media chưa có dòng trong bảng credits"))
    for number, cells, src, lic in rows:
        name = str(credits)
        if _at(cells, src).lower() in EMPTY:
            found.append(Finding(name, number, "CRD002", f"{_key(cells)}: thiếu nguồn (URL hoặc tác giả)"))
        if _at(cells, lic).lower() not in allow:
            found.append(Finding(name, number, "CRD003", f"{_key(cells)}: license không thuộc danh sách cho phép"))
        if not any(_hits(p, _key(cells)) for p in media) and _is_missing(_key(cells), credits, media):
            found.append(Finding(name, number, "CRD004", f"{_key(cells)}: tệp không còn tồn tại"))
    return found
