"""Loại `srm` (PM-METRIC-018, PM-METRIC-011): hợp lệ dữ liệu thí nghiệm — Sample Ratio Mismatch. Đầu vào là CSV (hàng đầu
là tiêu đề), JSON (mảng object hoặc object có khoá `records` là mảng) hay JSONL (mỗi dòng một object); mỗi bản ghi gán một
đơn vị vào một biến thể. `--opt variant=<trường>` (mặc định `variant`), `--opt unit=<trường>` (mặc định `unit_id`; không có
trường này ở mọi bản ghi thì bỏ qua kiểm đơn vị, trừ khi người dùng nêu rõ), `--opt exposed=<trường 0/1/true/false>`,
`--opt ratio=a:b[:c…]` (thứ tự theo tên biến thể sắp tăng dần; mặc định chia đều), `--opt alpha=<0-1>` (mặc định 0,001).
Báo: `SRM000` không đọc được/sai định dạng/thiếu trường, `SRM001` chi-bình-phương Pearson lệch tỷ lệ gán, `SRM002` đơn vị
trùng, `SRM003` đơn vị ở nhiều biến thể, `SRM004` thiếu/sai giá trị trường, `SRM005` phơi nhiễm lệch giữa các biến thể
(kiểm định đồng nhất bảng exposed/không exposed × biến thể), `SRM006` chưa đủ bằng chứng (ô kỳ vọng < 5). Với JSON, "dòng"
là số thứ tự bản ghi (từ 1). BOM UTF-8 đầu tệp được bỏ. Quét thư mục giữ tệp có bản ghi mang trường `--opt variant=`."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from . import CheckError, Finding, read_text

HELP = "Sample Ratio Mismatch: chi-bình-phương tỷ lệ gán biến thể, đơn vị trùng/rò randomization, phơi nhiễm lệch"
SUFFIXES = (".csv", ".json", ".jsonl")
OPTS = ("variant", "unit", "exposed", "ratio", "alpha")
DEFAULT_ALPHA = 0.001
MIN_VARIANTS = 2
MIN_PER_VARIANT = 5
MAX_EXAMPLES = 5
MAX_ITER = 100_000
EPS = 1e-15
TINY = 1e-300
TRUE_TEXT = frozenset({"1", "true"})
FALSE_TEXT = frozenset({"0", "false"})
UNREADABLE = "không đọc được dưới dạng UTF-8 (hoặc quá lớn)"
BOM = chr(0xFEFF)


def sniff(text: str, opts: dict[str, str]) -> bool:
    """Nhận diện tệp gán biến thể khi duyệt thư mục: có bản ghi mang trường `--opt variant=` (mặc định `variant`) — cột ở
    tiêu đề CSV, khoá của object trong mảng/`records` JSON hay dòng JSONL. Object đơn kiểu `{"variant": "primary"}` (cấu
    hình UI) không phải tệp bản ghi; dòng JSONL hỏng mà mang tên trường vẫn được giữ để `check` báo SRM000."""
    name = _field(opts, "variant", "variant")
    body = text.removeprefix(BOM).lstrip()
    if not body:
        return False
    return (body[0] in "[{" and _json_has(body, name)) or _csv_has(body, name)


def _json_has(body: str, name: str) -> bool:
    try:
        data = json.loads(body)
    except (ValueError, RecursionError):
        return _jsonl_has(body, name)
    if isinstance(data, dict):
        data = data.get("records")
    return isinstance(data, list) and any(isinstance(item, dict) and name in item for item in data)


def _jsonl_has(body: str, name: str) -> bool:
    quoted = json.dumps(name)
    for line in body.split("\n"):
        try:
            item = json.loads(line)
        except (ValueError, RecursionError):
            if quoted in line:
                return True
            continue
        if isinstance(item, dict) and name in item:
            return True
    return False


def _csv_has(body: str, name: str) -> bool:
    first = body.partition("\n")[0].removesuffix("\r")
    try:
        header = next(csv.reader([first]), [])
    except csv.Error:  # ô vượt field_size_limit: nhận theo chuỗi để `check` tự báo
        return name in first
    return name in header


SNIFF = sniff


class _Bad(Exception):
    """Tệp sai định dạng: (dòng, thông điệp) cho `SRM000`."""

    def __init__(self, line: int, message: str) -> None:
        super().__init__(message)
        self.line = line
        self.message = message


class _Rec(NamedTuple):
    line: int
    variant: str | None
    unit: str | None
    exposed: str | None


@dataclass(frozen=True)
class _Config:
    variant: str
    unit: str
    unit_explicit: bool
    exposed: str | None
    ratio: tuple[float, ...] | None
    alpha: float


# ---------------------------------------------------------------- toán: p-value chi-bình-phương


def _series_p(a: float, x: float) -> float:
    """P(a, x) chính quy bằng chuỗi (x < a + 1)."""
    ap = a
    term = total = 1.0 / a
    for _ in range(MAX_ITER):
        ap += 1.0
        term *= x / ap
        total += term
        if abs(term) < abs(total) * EPS:
            break
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _fraction_q(a: float, x: float) -> float:
    """Q(a, x) chính quy bằng phân số liên tục (Lentz; x ≥ a + 1)."""
    b = x + 1.0 - a
    c = 1.0 / TINY
    d = 1.0 / b
    h = d
    for i in range(1, MAX_ITER):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        d = d if abs(d) > TINY else TINY
        c = b + an / c
        c = c if abs(c) > TINY else TINY
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < EPS:
            break
    return h * math.exp(-x + a * math.log(x) - math.lgamma(a))


def chi2_pvalue(chi2: float, df: int) -> float:
    """P(X ≥ chi2) với X ~ chi-bình-phương `df` bậc tự do = Q(df/2, chi2/2), hàm gamma không hoàn chỉnh chính quy."""
    a = df / 2.0
    x = chi2 / 2.0
    if df < 1 or not x > 0.0:  # gồm NaN, âm và chi2 dưới chuẩn mà chi2/2 làm tròn về 0 (log(0) sẽ văng)
        return 1.0
    if math.isinf(x):
        return 0.0
    p = 1.0 - _series_p(a, x) if x < a + 1.0 else _fraction_q(a, x)
    return min(1.0, max(0.0, p))


def _chi_square(observed: list[int], weights: list[float]) -> tuple[float, float]:
    scale = sum(observed) / sum(weights)
    chi2 = sum((o - w * scale) ** 2 / (w * scale) for o, w in zip(observed, weights))
    return chi2, chi2_pvalue(chi2, len(observed) - 1)


def _homogeneity(hit: list[int], miss: list[int]) -> tuple[float, float]:
    """Chi-bình-phương đồng nhất bảng 2×k (exposed/không exposed × biến thể), bậc k−1; mọi ô kỳ vọng > 0."""
    seen, unseen = sum(hit), sum(miss)
    total = seen + unseen
    chi2 = 0.0
    for h, m in zip(hit, miss):
        size = h + m
        for value, share in ((h, seen), (m, unseen)):
            want = size * share / total
            chi2 += (value - want) ** 2 / want
    return chi2, chi2_pvalue(chi2, len(hit) - 1)


# ---------------------------------------------------------------- đọc bản ghi


def _scalar(value: object) -> str | None:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value.strip() or None
    return None


def _record(line: int, fields: dict[str, object], cfg: _Config) -> _Rec:
    exposed = _scalar(fields.get(cfg.exposed)) if cfg.exposed is not None else None
    return _Rec(
        line,
        _scalar(fields.get(cfg.variant)),
        _scalar(fields.get(cfg.unit)),
        exposed.lower() if exposed is not None else None,
    )


def _as_fields(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _parse_json(text: str, cfg: _Config) -> list[_Rec]:
    try:
        data = json.loads(text)
    except (ValueError, RecursionError):
        raise _Bad(0, "không phải JSON hợp lệ (hoặc lồng quá sâu)") from None
    if isinstance(data, dict):
        data = data.get("records")
    if not isinstance(data, list):
        raise _Bad(0, "cần mảng bản ghi (hoặc object có khoá 'records' là mảng)")
    return [_record(n, _as_fields(item), cfg) for n, item in enumerate(data, 1)]


def _parse_jsonl(text: str, cfg: _Config) -> list[_Rec]:
    out: list[_Rec] = []
    for number, raw in enumerate(text.split("\n"), 1):
        line = raw.removesuffix("\r")
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except (ValueError, RecursionError):
            raise _Bad(number, "dòng không phải JSON hợp lệ (hoặc lồng quá sâu)") from None
        out.append(_record(number, _as_fields(item), cfg))
    return out


def _csv_rows(text: str) -> list[tuple[int, list[str]]]:
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    reader = csv.reader((line.removesuffix("\r") + "\n" for line in lines), strict=True)
    rows: list[tuple[int, list[str]]] = []
    previous = 0
    try:
        for row in reader:
            if row:
                rows.append((previous + 1, row))
            previous = reader.line_num
    except csv.Error as exc:
        raise _Bad(previous + 1, f"CSV sai định dạng: {exc}") from None
    return rows


def _parse_csv(text: str, cfg: _Config) -> list[_Rec]:
    rows = _csv_rows(text)
    if not rows:
        return []
    header = rows[0][1]
    if cfg.variant not in header:
        raise _Bad(rows[0][0], f"thiếu cột {cfg.variant!r} ở tiêu đề")
    return [_record(number, dict(zip(header, row)), cfg) for number, row in rows[1:]]


def _parse(path: Path, text: str, cfg: _Config) -> list[_Rec]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _parse_csv(text, cfg)
    if suffix == ".json":
        return _parse_json(text, cfg)
    return _parse_jsonl(text, cfg)


# ---------------------------------------------------------------- phân tích


def _examples(lines: list[int]) -> str:
    shown = ", ".join(str(n) for n in lines[:MAX_EXAMPLES])
    return f"vd dòng {shown}"


def _bad_exposed(value: str | None) -> bool:
    return value not in TRUE_TEXT and value not in FALSE_TEXT


def _missing(path: str, recs: list[_Rec], cfg: _Config, unit_used: bool) -> list[Finding]:
    gaps = [r.line for r in recs if r.variant is None or (unit_used and r.unit is None)]
    found: list[Finding] = []
    if gaps:
        what = f"{cfg.variant!r} hoặc {cfg.unit!r}"
        found.append(Finding(path, gaps[0], "SRM004", f"{len(gaps)} bản ghi thiếu trường {what} ({_examples(gaps)})"))
    if cfg.exposed is not None:
        bad = [r.line for r in recs if _bad_exposed(r.exposed)]
        if bad:
            what = f"{cfg.exposed!r} thiếu hoặc không phải 0/1/true/false"
            found.append(Finding(path, bad[0], "SRM004", f"{len(bad)} bản ghi có {what} ({_examples(bad)})"))
    return found


def _units(recs: list[_Rec]) -> dict[str, list[object]]:
    """đơn vị → [dòng đầu, số bản ghi, biến thể đầu, thấy ở ≥ 2 biến thể]; tuyến tính theo băm."""
    stats: dict[str, list[object]] = {}
    for rec in recs:
        if rec.unit is None:
            continue
        stat = stats.get(rec.unit)
        if stat is None:
            stats[rec.unit] = [rec.line, 1, rec.variant, False]
            continue
        stat[1] = int(str(stat[1])) + 1
        if rec.variant is None:
            continue
        if stat[2] is None:
            stat[2] = rec.variant
        elif stat[2] != rec.variant:
            stat[3] = True
    return stats


def _shown(unit: str) -> str:
    return repr(unit if len(unit) <= 40 else unit[:40] + "…")


def _unit_findings(path: str, recs: list[_Rec]) -> list[Finding]:
    stats = _units(recs)
    dup = [(unit, s) for unit, s in stats.items() if int(str(s[1])) >= 2]
    leak = [(unit, s) for unit, s in stats.items() if s[3]]
    found: list[Finding] = []
    for code, items, what in (
        ("SRM002", dup, "đơn vị xuất hiện ở ≥ 2 bản ghi"),
        ("SRM003", leak, "đơn vị nằm ở ≥ 2 biến thể (rò randomization)"),
    ):
        if items:
            sample = ", ".join(f"{_shown(u)} (dòng {s[0]})" for u, s in items[:MAX_EXAMPLES])
            found.append(Finding(path, int(str(items[0][1][0])), code, f"{len(items)} {what}: {sample}"))
    return found


def _counts(recs: list[_Rec]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for rec in recs:
        if rec.variant is not None:
            counts[rec.variant] = counts.get(rec.variant, 0) + 1
    return counts


def _describe(names: list[str], values: list[int]) -> str:
    """Tối đa `MAX_EXAMPLES` cặp `'tên'=số`; tên escape như `_shown` (surrogate, ESC, xuống dòng không lọt vào thông điệp)."""
    shown = ", ".join(f"{_shown(n)}={v}" for n, v in zip(names[:MAX_EXAMPLES], values))
    more = len(names) - MAX_EXAMPLES
    return shown + (f" và {more} biến thể nữa" if more > 0 else "")


def _weights(path: str, names: list[str], cfg: _Config) -> list[float] | Finding:
    """Trọng số kỳ vọng theo `names` (đã sắp); không dùng được → Finding giải thích (SRM000/SRM006)."""
    k = len(names)
    if cfg.ratio is None:
        if k < MIN_VARIANTS:
            return Finding(path, 0, "SRM006", f"chưa đủ bằng chứng: chỉ thấy {k} biến thể, cần ≥ {MIN_VARIANTS}")
        return [1.0] * k
    if k > len(cfg.ratio):
        return Finding(path, 0, "SRM000", f"thấy {k} biến thể nhưng --opt ratio chỉ có {len(cfg.ratio)} phần")
    if k < len(cfg.ratio):
        return Finding(
            path, 0, "SRM006", f"chưa đủ bằng chứng: chỉ thấy {k}/{len(cfg.ratio)} biến thể (có biến thể 0 bản ghi)"
        )
    return list(cfg.ratio)


def _srm_findings(path: str, recs: list[_Rec], cfg: _Config) -> list[Finding]:
    counts = _counts(recs)
    names = sorted(counts)
    observed = [counts[n] for n in names]
    weights = _weights(path, names, cfg)
    if isinstance(weights, Finding):
        return [weights]
    k = len(names)
    total = sum(observed)
    least = min(weights) * total / sum(weights)
    if least < MIN_PER_VARIANT:
        message = (
            f"chưa đủ bằng chứng: kỳ vọng nhỏ nhất {least:.3g} < {MIN_PER_VARIANT} (tổng {total} mẫu, {k} biến thể)"
        )
        return [Finding(path, 0, "SRM006", message)]
    found: list[Finding] = []
    chi2, p = _chi_square(observed, weights)
    if p < cfg.alpha:
        message = f"SRM: chi2={chi2:.4g}, bậc {k - 1}, p={p:.3g} < {cfg.alpha:g}; số đếm {_describe(names, observed)}"
        found.append(Finding(path, 0, "SRM001", message))
    if cfg.exposed is not None:
        found.extend(_exposure_findings(path, recs, cfg, names))
    return found


def _exposure_findings(path: str, recs: list[_Rec], cfg: _Config, names: list[str]) -> list[Finding]:
    """SRM005: tỷ lệ exposed khác nhau giữa các biến thể — kiểm định đồng nhất bảng 2×k trên bản ghi có giá trị exposed
    hợp lệ. Không ai hay ai cũng exposed → bỏ qua (không có gì để so); ô kỳ vọng < 5 → SRM006."""
    hit = dict.fromkeys(names, 0)
    miss = dict.fromkeys(names, 0)
    for rec in recs:
        if rec.variant is not None and rec.exposed in TRUE_TEXT:
            hit[rec.variant] += 1
        elif rec.variant is not None and rec.exposed in FALSE_TEXT:
            miss[rec.variant] += 1
    exposed = [hit[n] for n in names]
    unexposed = [miss[n] for n in names]
    seen, unseen = sum(exposed), sum(unexposed)
    if seen == 0 or unseen == 0:
        return []
    k = len(names)
    least = min(e + u for e, u in zip(exposed, unexposed)) * min(seen, unseen) / (seen + unseen)
    if least < MIN_PER_VARIANT:
        message = f"chưa đủ bằng chứng về phơi nhiễm: ô kỳ vọng nhỏ nhất của bảng exposed×biến thể {least:.3g} < 5"
        return [Finding(path, 0, "SRM006", message)]
    chi2, p = _homogeneity(exposed, unexposed)
    if p >= cfg.alpha:
        return []
    message = (
        f"phơi nhiễm lệch giữa các biến thể (bảng 2×{k}): chi2={chi2:.4g}, bậc {k - 1}, p={p:.3g} < {cfg.alpha:g}; "
        f"exposed {_describe(names, exposed)}"
    )
    return [Finding(path, 0, "SRM005", message)]


def _file_findings(path: Path, cfg: _Config) -> list[Finding]:
    name = str(path)
    text = read_text(path)
    if text is None:
        return [Finding(name, 0, "SRM000", UNREADABLE)]
    try:
        recs = _parse(path, text.removeprefix(BOM), cfg)
    except _Bad as bad:
        return [Finding(name, bad.line, "SRM000", bad.message)]
    if not any(r.variant is not None for r in recs):
        return [Finding(name, 0, "SRM000", f"không có bản ghi nào mang trường {cfg.variant!r}")]
    unit_used = any(r.unit is not None for r in recs)
    if cfg.unit_explicit and not unit_used:
        return [Finding(name, 0, "SRM000", f"không có bản ghi nào mang trường {cfg.unit!r}")]
    if cfg.exposed is not None and all(r.exposed is None for r in recs):
        return [Finding(name, 0, "SRM000", f"không có bản ghi nào mang trường {cfg.exposed!r}")]
    found = _missing(name, recs, cfg, unit_used)
    if unit_used:
        found.extend(_unit_findings(name, recs))
    return [*found, *_srm_findings(name, recs, cfg)]


# ---------------------------------------------------------------- tuỳ chọn


def _field(opts: dict[str, str], key: str, default: str) -> str:
    value = opts.get(key, default)
    if value == "":
        raise CheckError(f"--opt {key} không được rỗng")
    return value


def _ratio(raw: str | None) -> tuple[float, ...] | None:
    if raw is None:
        return None
    try:
        parts = tuple(float(p) for p in raw.split(":"))
    except ValueError:
        raise CheckError(f"--opt ratio cần dạng a:b[:c…] gồm số dương, không phải {raw!r}") from None
    if len(parts) < MIN_VARIANTS or not all(0.0 < p < math.inf for p in parts) or math.isinf(sum(parts)):
        raise CheckError(f"--opt ratio cần ≥ 2 số dương hữu hạn (tổng không tràn) dạng a:b[:c…], không phải {raw!r}")
    return parts


def _alpha(raw: str | None) -> float:
    if raw is None:
        return DEFAULT_ALPHA
    try:
        value = float(raw)
    except ValueError:
        raise CheckError(f"--opt alpha cần số trong khoảng (0, 1], không phải {raw!r}") from None
    if not 0.0 < value <= 1.0:
        raise CheckError(f"--opt alpha cần số trong khoảng (0, 1], không phải {raw!r}")
    return value


def _config(opts: dict[str, str]) -> _Config:
    return _Config(
        variant=_field(opts, "variant", "variant"),
        unit=_field(opts, "unit", "unit_id"),
        unit_explicit="unit" in opts,
        exposed=_field(opts, "exposed", "") if "exposed" in opts else None,
        ratio=_ratio(opts.get("ratio")),
        alpha=_alpha(opts.get("alpha")),
    )


def check(files: list[Path], opts: dict[str, str]) -> list[Finding]:
    cfg = _config(opts)
    found: list[Finding] = []
    for path in files:
        found.extend(_file_findings(path, cfg))
    return found
