"""Loại `tokens` (UX-DS-002, UX-DS-010, UX-DS-019): mã giao diện chỉ dùng biến thiết kế `var(--x)` từ một tệp khai báo, không
hard-code màu và không bịa tên chưa định nghĩa. Khai `--opt tokens=<tệp css>` (bắt buộc) và `--opt allow=#fff,…` (màu được phép;
`transparent`, `currentColor`, `inherit` luôn được phép). Mã: `TOK000` không đọc được tệp khai báo (thiếu opt → lỗi dùng sai, mã thoát 2); `TOK001` `var(--x)`
chưa định nghĩa (tập tên = mọi `--x:` trong tệp khai báo và trong các tệp được kiểm; có fallback vẫn báo, ghi rõ trong thông
điệp); `TOK002` màu hard-code (#rgb/#rrggbb/#rrggbbaa, rgb(, rgba(, hsl(, hsla(, oklch(, color() ngoài tệp khai báo.
Heuristic theo dòng, không phân tích cú pháp: dòng bắt đầu bằng `//`, `/*` hay `*` coi là chú thích và bị bỏ qua với TOK002; dòng
có `xt-allow: TOK002` được bỏ qua; `#abc` trong href hay nhãn HTML có thể báo nhầm — dùng `xt-allow` hoặc `allow`."""

from __future__ import annotations

import re
from pathlib import Path

from . import CheckError, Finding, read_text

HELP = "mã giao diện dùng var(--x) chưa định nghĩa hoặc màu hard-code ngoài tệp biến thiết kế"
SUFFIXES = (".css", ".scss", ".tsx", ".jsx", ".ts", ".js", ".vue", ".svelte", ".html")
ALWAYS = ("transparent", "currentcolor", "inherit")
DEFINED = re.compile(r"(?<![\w-])(--[\w-]++)\s*:")  # neo + chiếm hữu: chỉ thử ở đầu mỗi chuỗi, tuyến tính (rà #776)
USED = re.compile(r"var\(\s*(--[\w-]+)\s*(,?)")
COLOR = re.compile(
    r"(?<![\w&])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![\w-])|\b(?:rgba?|hsla?|oklch|color)\("
)
OPTS = ("tokens", "allow")
COMMENT_STARTS = ("//", "/*", "*")


def _color_findings(path: str, number: int, line: str, allowed: set[str]) -> list[Finding]:
    if line.lstrip().startswith(COMMENT_STARTS) or "xt-allow: TOK002" in line:
        return []
    return [
        Finding(path, number, "TOK002", f"màu hard-code {m.group(0)} — dùng var(--…) từ tệp biến thiết kế")
        for m in COLOR.finditer(line)
        if m.group(0).lower() not in allowed
    ]


def _file_findings(path: str, text: str, names: set[str], allowed: set[str], is_design_file: bool) -> list[Finding]:
    found: list[Finding] = []
    for number, line in enumerate(text.split("\n"), 1):
        line = line.removesuffix("\r")
        for m in USED.finditer(line):
            if m.group(1) not in names:
                extra = " (có fallback)" if m.group(2) else ""
                found.append(
                    Finding(path, number, "TOK001", f"{m.group(1)} chưa định nghĩa{extra} — tên bịa hoặc gõ sai")
                )
        if not is_design_file:
            found.extend(_color_findings(path, number, line, allowed))
    return found


def check(files: list[Path], opts: dict[str, str]) -> list[Finding]:
    design_path = opts.get("tokens", "")
    if not design_path:
        raise CheckError("cần --opt tokens=<tệp token CSS>")
    design_text = read_text(Path(design_path))
    if design_text is None:
        return [Finding(design_path, 0, "TOK000", "không đọc được tệp biến thiết kế (--opt tokens=…)")]
    allowed = {c.strip().lower() for c in opts.get("allow", "").split(",") if c.strip()} | set(ALWAYS)
    design_resolved = Path(design_path).resolve()
    texts = {path: read_text(path) for path in files}
    names = set(DEFINED.findall(design_text))
    for text in texts.values():
        names.update(DEFINED.findall(text or ""))
    found: list[Finding] = []
    for path, text in texts.items():
        if text is not None:
            found.extend(_file_findings(str(path), text, names, allowed, path.resolve() == design_resolved))
    return found
