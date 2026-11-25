"""Loại `motion` (UX-VISUAL-001..003, UX-A11Y-015, UX-STATE-020, FE-TEST-014): chuyển động CSS phải tôn trọng
`prefers-reduced-motion`, không chớp quá 3 lần/giây và dừng được. Quét bằng regex (heuristic: bỏ chú thích `/* */`, không
phân tích @import, biến `var()`, hay khai báo trải nhiều tệp). Báo: `MOT001` `transition: all`; `MOT002` tệp có chuyển động
nhưng không có khối `@media (prefers-reduced-motion: reduce)` (một phát hiện ở dòng chuyển động đầu tiên); `MOT003` hoạt ảnh
`infinite` có thời lượng < 0,34 giây (đọc `animation-duration` trong cùng khối quy tắc, không có thì thời lượng đầu tiên của
shorthand `animation:`; đơn vị s, ms); `MOT004` hoạt ảnh `infinite` mà tệp không có `animation-play-state`. Bỏ một mã cho
một dòng bằng `/* xt-allow: MOT00N */`; `--opt ignore=MOT002,…` bỏ mã toàn cục."""

from __future__ import annotations

import bisect
import re
from pathlib import Path

from . import Finding, read_text

HELP = (
    "chuyển động CSS: transition all, thiếu prefers-reduced-motion, hoạt ảnh lặp vô hạn chớp nhanh hoặc không dừng được"
)
OPTS = ("ignore",)
SUFFIXES = (".css", ".scss")
MIN_SECONDS = 0.34
LOOKAHEAD = 2000  # khối khai báo dài hơn mức này không xét: giữ thời gian quét tuyến tính theo cỡ tệp (rà #776)
ALLOW = re.compile(r"xt-allow:\s*([A-Z0-9, ]+)")
TRANSITION_ALL = re.compile(r"\btransition(?:-property)?\s*:[^;}]{0,300}\ball\b")
# Neo lookbehind (cho phép tiền tố nhà cung cấp `-webkit-`): chỉ thử ở đầu mỗi tên thuộc tính; `\b` khớp sau mỗi dấu `-` nên
# `animation-animation-…` từng bậc hai (rà #776 lượt hai).
MOTION = re.compile(
    r"@keyframes\b|(?<![\w-])(?:-[a-z]+-)?(?:(?:animation|transition)[\w-]*+|view-transition-name)\s*:", re.IGNORECASE
)
REDUCED = re.compile(r"@media[^{]{0,300}prefers-reduced-motion\s*:\s*reduce")
INFINITE = re.compile(r"\banimation(?:-iteration-count)?\s*:[^;}]{0,300}\binfinite\b")
DURATION = re.compile(r"animation-duration\s*:\s*(\d++(?:\.\d++)?|\.\d++)(ms|s)\b")
TIME = re.compile(r"(?<![\w.-])(\d++(?:\.\d++)?|\.\d++)(ms|s)\b")


def _blank_comments(text: str) -> str:
    """Thay nội dung bình luận `/* … */` bằng khoảng trắng (giữ xuống dòng để số dòng không lệch); bình luận không đóng kéo
    tới hết tệp như CSS. Vòng `find` tuyến tính — regex `.*?` thử lại từ mỗi `/*` nên bậc hai với tệp nhiều `/*` không đóng."""
    parts: list[str] = []
    pos = 0
    while (start := text.find("/*", pos)) != -1:
        end = text.find("*/", start + 2)
        stop = len(text) if end == -1 else end + 2
        parts.append(text[pos:start])
        parts.append(re.sub(r"[^\n]", " ", text[start:stop]))
        pos = stop
    parts.append(text[pos:])
    return "".join(parts)


def _seconds(match: re.Match[str]) -> float:
    value = float(match.group(1))
    return value / 1000 if match.group(2) == "ms" else value


def _duration(clean: str, hit: re.Match[str]) -> float | None:
    low = max(0, hit.start() - LOOKAHEAD)
    opener = clean.rfind("{", low, hit.start())
    start = opener + 1 if opener >= 0 else low
    high = min(len(clean), hit.end() + LOOKAHEAD)
    closer = clean.find("}", hit.end(), high)
    block = clean[start : closer if closer >= 0 else high]
    found = DURATION.search(block) or TIME.search(hit.group())
    return _seconds(found) if found else None


def _check_text(path: str, text: str, ignore: set[str]) -> list[Finding]:
    allow: dict[int, set[str]] = {}
    for number, raw in enumerate(text.split("\n"), 1):
        marker = ALLOW.search(raw)
        if marker:
            allow[number] = {c.strip() for c in marker.group(1).split(",")}
    clean = _blank_comments(text)
    seen: dict[tuple[int, str], Finding] = {}
    newlines = [m.start() for m in re.finditer("\n", clean)]  # một lần: đếm lại từ đầu tệp cho mỗi phát hiện là bậc hai
    pausable = "animation-play-state" in clean

    def add(offset: int, code: str, message: str) -> None:
        line = bisect.bisect_right(newlines, offset - 1) + 1  # số `\n` đứng trước offset
        if code not in ignore and code not in allow.get(line, set()):
            seen.setdefault((line, code), Finding(path, line, code, message))

    for hit in TRANSITION_ALL.finditer(clean):
        add(hit.start(), "MOT001", "`transition: all` — nêu rõ thuộc tính cần chuyển")
    first = MOTION.search(clean)
    if first and not REDUCED.search(clean):
        add(first.start(), "MOT002", "có chuyển động nhưng thiếu @media (prefers-reduced-motion: reduce)")
    for hit in INFINITE.finditer(clean):
        seconds = _duration(clean, hit)
        if seconds is not None and seconds < MIN_SECONDS:
            add(hit.start(), "MOT003", "hoạt ảnh lặp vô hạn dưới 0,34 giây — nguy cơ chớp quá 3 lần/giây")
        if not pausable:
            add(hit.start(), "MOT004", "hoạt ảnh lặp vô hạn không có animation-play-state — không dừng được")
    return list(seen.values())


def check(files: list[Path], opts: dict[str, str]) -> list[Finding]:
    ignore = {code for code in opts.get("ignore", "").split(",") if code}
    found: list[Finding] = []
    for path in files:
        text = read_text(path)
        if text is not None:
            found.extend(_check_text(str(path), text, ignore))
    return found
