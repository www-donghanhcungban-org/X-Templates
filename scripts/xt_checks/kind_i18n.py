"""Loại `i18n` (XC-I18N-009): catalog bản dịch JSON (phẳng hoặc lồng) phải khớp tệp nguồn. `--opt source=<tệp>` bắt buộc; mỗi
tệp còn lại là locale đích. Báo: `LOC000` không đọc được/không phải JSON object, `LOC001` thiếu khoá so với nguồn, `LOC002`
khoá thừa, `LOC003` cú pháp ICU hỏng (ngoặc `{}` không cân, dấu `'` chưa đóng), `LOC004` tập tham số khác nguồn, `LOC005` giá
trị có thẻ script/trình xử lý sự kiện/URI script mà nguồn không có, `LOC006` mức đầy đủ dưới `--opt min=<0-100>` (mặc định
100), `LOC007` lá không phải chuỗi. Khoá lồng làm phẳng bằng dấu chấm; mọi bước lặp tường minh (không đệ quy)."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

from . import CheckError, Finding, read_text

HELP = "catalog i18n JSON: thiếu/thừa khoá so với nguồn, ICU hỏng, tham số lệch, thẻ lạ, độ đầy đủ"
SUFFIXES = (".json",)
OPTS = ("ignore", "source", "min")
LIST_LIMIT = 20
KEY_SHOW = 80
BOM = chr(0xFEFF)
ELLIPSIS = chr(0x2026)

Flat = dict[str, object]
NAME_RE = re.compile(r"[^,{}]*+")
RISKY_RE = re.compile(
    r"(?P<script><script)|(?P<handler>(?<![\w-])on[a-z]{2,30}\s{0,5}=)|(?P<jsuri>javascript:)",
    re.IGNORECASE,
)


def sniff(text: str) -> bool:
    """Nhận JSON object (gốc là `{`) khi quét thư mục; mảng/số/văn bản khác không phải catalog."""
    return text.lstrip(BOM + " \t\r\n").startswith("{")


SNIFF = sniff


def _flatten(root: dict[str, object]) -> Flat:
    """Làm phẳng object lồng bằng dấu chấm; lặp bằng ngăn xếp tường minh. Mảng và giá trị khác là lá."""
    out: Flat = {}
    stack: list[tuple[str | None, dict[str, object]]] = [(None, root)]
    while stack:
        prefix, node = stack.pop()
        for key, value in node.items():
            path = key if prefix is None else f"{prefix}.{key}"
            if isinstance(value, dict):
                stack.append((path, value))
            else:
                out[path] = value
    return out


def _load(path: Path) -> tuple[Flat | None, str]:
    """(catalog phẳng, "") hoặc (None, lý do) — không bao giờ văng vì nội dung tệp."""
    text = read_text(path)
    if text is None:
        return None, "không đọc được dưới dạng UTF-8 (hoặc quá lớn, không phải tệp thường)"
    try:
        data = json.loads(text)
    except RecursionError:
        return None, "JSON lồng quá sâu"
    except ValueError:
        return None, "không phải JSON hợp lệ"
    if not isinstance(data, dict):
        return None, "gốc JSON không phải object"
    return _flatten(data), ""


def _close_quote(text: str, start: int) -> int:
    """Vị trí dấu `'` đóng đoạn trích ICU (bỏ qua `''` là dấu nháy thường); -1 nếu chưa đóng. Tuyến tính nhờ `find`."""
    pos = text.find("'", start)
    while pos >= 0 and text[pos + 1 : pos + 2] == "'":
        pos = text.find("'", pos + 2)
    return pos


def _skip_quote(text: str, pos: int) -> int:
    """Vị trí sau đoạn dấu `'` bắt đầu ở `pos`; -1 nếu đoạn trích `'{`/`'}` chưa đóng."""
    follow = text[pos + 1 : pos + 2]
    if follow == "'":
        return pos + 2
    if follow in ("{", "}"):
        end = _close_quote(text, pos + 2)
        return end + 1 if end >= 0 else -1
    return pos + 1


def scan_icu(text: str) -> tuple[str, frozenset[str]]:
    """Quét ICU một lượt bằng đếm độ sâu: (lỗi hoặc "", tên tham số cấp cao nhất). `'{`/`'}` mở đoạn trích tới `'` kế,
    `''` là dấu nháy thường, `'` đứng trước ký tự khác là chữ thường."""
    depth = 0
    names: set[str] = set()
    pos = 0
    size = len(text)
    while pos < size:
        char = text[pos]
        if char == "'":
            pos = _skip_quote(text, pos)
            if pos < 0:
                return "dấu ' chưa đóng", frozenset(names)
            continue
        if char == "{":
            if depth == 0:
                name = next(NAME_RE.finditer(text, pos + 1)).group().strip()
                if not name:
                    return "tham số rỗng", frozenset(names)
                names.add(name)
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                return "dấu } thừa", frozenset(names)
        pos += 1
    if depth > 0:
        return f"thiếu {depth} dấu }}", frozenset(names)
    return "", frozenset(names)


def _risky(text: str) -> frozenset[str]:
    """Loại dấu hiệu nguy hiểm trong giá trị: script, handler (`onclick=`), uri script."""
    return frozenset(m.lastgroup or "" for m in RISKY_RE.finditer(text))


def _show(key: str) -> str:
    return key if len(key) <= KEY_SHOW else key[: KEY_SHOW - 1] + ELLIPSIS


def _min_opt(opts: dict[str, str]) -> float:
    raw = opts.get("min", "100")
    try:
        value = float(raw)
    except ValueError:
        raise CheckError(f"--opt min nhận số từ 0 đến 100, không phải {raw!r}") from None
    if not math.isfinite(value) or not 0 <= value <= 100:
        raise CheckError(f"--opt min nhận số từ 0 đến 100, không phải {raw!r}")
    return value


def _source(opts: dict[str, str]) -> tuple[Path, Flat]:
    raw = opts.get("source")
    if not raw:
        raise CheckError("loại i18n cần --opt source=<tệp catalog nguồn>")
    path = Path(raw)
    if path.is_symlink() or not path.is_file():
        raise CheckError(f"--opt source: không thấy tệp thường {raw!r}")
    flat, reason = _load(path)
    if flat is None:
        raise CheckError(f"--opt source {raw!r}: {reason}")
    return path, flat


def _per_key(path: str, code: str, items: list[str]) -> list[Finding]:
    """Mỗi mục một phát hiện, tối đa `LIST_LIMIT` rồi một dòng 'và N khoá nữa'."""
    found = [Finding(path, 0, code, text) for text in items[:LIST_LIMIT]]
    if len(items) > LIST_LIMIT:
        found.append(Finding(path, 0, code, f"và {len(items) - LIST_LIMIT} khoá nữa"))
    return found


def _key_list(path: str, code: str, label: str, keys: list[str]) -> list[Finding]:
    """Một phát hiện cho cả tệp, nêu tối đa `LIST_LIMIT` khoá (đã sắp)."""
    if not keys:
        return []
    shown = ", ".join(_show(k) for k in keys[:LIST_LIMIT])
    extra = f" và {len(keys) - LIST_LIMIT} khoá nữa" if len(keys) > LIST_LIMIT else ""
    return [Finding(path, 0, code, f"{label} {len(keys)} khoá: {shown}{extra}")]


def _compare(
    path: Path, src: Flat, tgt: Flat, minimum: float, cache: dict[str, tuple[str, frozenset[str]]]
) -> list[Finding]:
    name = str(path)
    found = _key_list(name, "LOC001", "thiếu so với nguồn", sorted(src.keys() - tgt.keys()))
    found += _key_list(name, "LOC002", "thừa so với nguồn", sorted(tgt.keys() - src.keys()))
    icu: list[str] = []
    params: list[str] = []
    html: list[str] = []
    nonstr: list[str] = []
    for key in sorted(tgt):
        value = tgt[key]
        if not isinstance(value, str):
            nonstr.append(f"{_show(key)}: giá trị không phải chuỗi")
            continue
        error, names = scan_icu(value)
        if error:
            icu.append(f"{_show(key)}: ICU hỏng ({error})")
        source_value = src.get(key)
        if not isinstance(source_value, str):
            source_info: tuple[str, frozenset[str]] | None = None
            source_risk: frozenset[str] = frozenset()
        else:
            source_info = cache.get(key)
            if source_info is None:
                source_info = cache[key] = scan_icu(source_value)
            source_risk = _risky(source_value)
        if not error and source_info is not None and not source_info[0] and names != source_info[1]:
            lost = sorted(source_info[1] - names)
            gained = sorted(names - source_info[1])
            detail = "; ".join(
                part
                for part in (f"mất {', '.join(lost)}" if lost else "", f"thêm {', '.join(gained)}" if gained else "")
                if part
            )
            params.append(f"{_show(key)}: tham số khác nguồn ({detail})")
        new_risk = sorted(_risky(value) - source_risk)
        if new_risk:
            html.append(f"{_show(key)}: có {', '.join(new_risk)} mà nguồn không có")
    found += _per_key(name, "LOC003", icu)
    found += _per_key(name, "LOC004", params)
    found += _per_key(name, "LOC005", html)
    found += _per_key(name, "LOC007", nonstr)
    total = sum(1 for v in src.values() if isinstance(v, str))
    have = sum(1 for k, v in src.items() if isinstance(v, str) and isinstance(tgt.get(k), str))
    if total and have * 100 < minimum * total:
        found.append(
            Finding(name, 0, "LOC006", f"locale {path.name} đủ {100 * have / total:.1f}% (cần ít nhất {minimum:g}%)")
        )
    return found


def check(files: list[Path], opts: dict[str, str]) -> list[Finding]:
    ignore = {code for code in opts.get("ignore", "").split(",") if code}
    minimum = _min_opt(opts)
    source_path, src = _source(opts)
    resolved = source_path.resolve()
    cache: dict[str, tuple[str, frozenset[str]]] = {}
    found: list[Finding] = []
    for path in files:
        if path.resolve() == resolved:
            continue
        tgt, reason = _load(path)
        if tgt is None:
            found.append(Finding(str(path), 0, "LOC000", reason))
            continue
        found.extend(_compare(path, src, tgt, minimum, cache))
    return [f for f in found if f.code not in ignore]
