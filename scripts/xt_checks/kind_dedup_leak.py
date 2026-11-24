"""Loại `dedup-leak` (AI-DATA-007, PRF-DATA-007): tập train và eval không được trùng mẫu — kiểm bằng băm sau chuẩn hoá
(NFKC, hạ chữ, gộp khoảng trắng). Đầu vào là tập dữ liệu JSONL/CSV (tên tập = tên tệp bỏ đuôi); `--opt train=` và
`--opt eval=` bắt buộc; `--opt fewshot=<tệp>` (mỗi dòng không rỗng là một mẫu), `--opt field=<trường>`, `--opt near=<0-1>`
(bật so near-duplicate MinHash + LSH). CSV: hàng đầu là tiêu đề (bỏ qua; `field` chọn cột theo tiêu đề), mỗi hàng còn lại là
một mẫu; JSONL: mỗi dòng không rỗng là một bản ghi. Báo: `DDL000` không đọc được/sai định dạng/quá lớn, `DDL001` eval trùng
train, `DDL002` thiếu trường, `DDL003` few-shot trùng eval hoặc train, `DDL004` trùng trong eval, `DDL005` gần trùng."""

from __future__ import annotations

import csv
import hashlib
import json
import random
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from . import CheckError, Finding, read_text

HELP = "tập train/eval trùng mẫu (băm sau chuẩn hoá), few-shot lọt vào eval, near-duplicate (MinHash)"
SUFFIXES = (".jsonl", ".csv")
OPTS = ("train", "eval", "fewshot", "field", "near")
MAX_RECORDS = 1_000_000
MAX_PAIRS = 20
SEP = chr(0x1F)
BOM = chr(0xFEFF)
HASHES = 64
BANDS = 16
ROWS = 4
SHINGLE = 5
MAX_BUCKET = 64
PRIME = (1 << 61) - 1
_RNG = random.Random(0x5EED)
COEFS = tuple((_RNG.randrange(1, PRIME), _RNG.randrange(PRIME)) for _ in range(HASHES))
UNREADABLE = "không đọc được dưới dạng UTF-8 (hoặc quá lớn)"


class _Missing(Exception):
    """Bản ghi không có trường cần lấy."""


@dataclass(frozen=True)
class _Dataset:
    samples: list[tuple[int, str]]  # (số dòng, mẫu đã chuẩn hoá)
    findings: list[Finding]
    fatal: bool = False


@dataclass(frozen=True)
class _Config:
    train: Path
    evaluation: Path
    fewshot: Path | None
    field: str | None
    near: float | None


def _norm(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).lower().split())


def _digest(norm: str) -> bytes:
    return hashlib.sha256(norm.encode("utf-8", "surrogatepass")).digest()


def _fatal(path: str, line: int, message: str) -> _Dataset:
    return _Dataset([], [Finding(path, line, "DDL000", message)], True)


def _report(path: str, code: str, entries: list[tuple[int, str]], total: str) -> list[Finding]:
    """Tối đa `MAX_PAIRS` phát hiện chi tiết rồi một dòng tổng (dòng 0); không có mục nào thì không báo gì."""
    if not entries:
        return []
    found = [Finding(path, line, code, message) for line, message in entries[:MAX_PAIRS]]
    found.append(Finding(path, 0, code, total))
    return found


def _pick(record: object, field: str | None) -> str:
    if field is not None:
        if not isinstance(record, dict):
            raise _Missing("bản ghi không phải object")
        if field not in record:
            raise _Missing(f"thiếu trường {field!r}")
        record = record[field]
    return record if isinstance(record, str) else json.dumps(record, sort_keys=True, ensure_ascii=False)


def _parse_jsonl(path: str, text: str, field: str | None) -> _Dataset:
    samples: list[tuple[int, str]] = []
    bad: list[tuple[int, str]] = []
    for number, raw in enumerate(text.split("\n"), 1):
        line = raw.removesuffix("\r")
        if not line.strip():
            continue
        try:
            value = _pick(json.loads(line), field)
        except _Missing as exc:
            bad.append((number, str(exc)))
            continue
        except (ValueError, RecursionError, TypeError):
            return _fatal(path, number, "dòng không phải JSON hợp lệ (hoặc lồng quá sâu)")
        samples.append((number, _norm(value)))
        if len(samples) > MAX_RECORDS:
            return _fatal(path, number, f"quá lớn: hơn {MAX_RECORDS} bản ghi")
    return _Dataset(samples, _report(path, "DDL002", bad, f"tổng {len(bad)} bản ghi thiếu trường"))


def _csv_rows(text: str) -> list[tuple[int, list[str]]]:
    """Hàng CSV không rỗng kèm dòng bắt đầu; `csv.Error` nổi lên cho nơi gọi (kèm `args` mang số dòng gần đúng)."""
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
        raise csv.Error(previous + 1, str(exc)) from exc
    return rows


def _csv_samples(
    rows: list[tuple[int, list[str]]], field: str | None
) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    header_line, header = rows[0]
    column = header.index(field) if field is not None and field in header else -1
    if field is not None and column < 0:
        return [], [(header_line, f"thiếu cột {field!r} ở tiêu đề")]
    samples: list[tuple[int, str]] = []
    bad: list[tuple[int, str]] = []
    for number, row in rows[1:]:
        if field is None:
            samples.append((number, SEP.join(_norm(cell) for cell in row)))
        elif column < len(row):
            samples.append((number, _norm(row[column])))
        else:
            bad.append((number, f"hàng thiếu cột {field!r}"))
    return samples, bad


def _parse_csv(path: str, text: str, field: str | None) -> _Dataset:
    try:
        rows = _csv_rows(text)
    except csv.Error as exc:
        line, reason = exc.args
        return _fatal(path, line, f"CSV sai định dạng: {reason}")
    if not rows:
        return _Dataset([], [])
    samples, bad = _csv_samples(rows, field)
    if len(samples) > MAX_RECORDS:
        return _fatal(path, 0, f"quá lớn: hơn {MAX_RECORDS} bản ghi")
    return _Dataset(samples, _report(path, "DDL002", bad, f"tổng {len(bad)} bản ghi thiếu trường"))


def _load(path: Path, field: str | None) -> _Dataset:
    text = read_text(path)
    if text is None:
        return _fatal(str(path), 0, UNREADABLE)
    text = text.removeprefix(BOM)  # BOM đầu tệp (Excel) không dính vào tiêu đề CSV hay dòng JSONL đầu
    if path.suffix.lower() == ".csv":
        return _parse_csv(str(path), text, field)
    return _parse_jsonl(str(path), text, field)


def _option_near(opts: dict[str, str]) -> float | None:
    raw = opts.get("near")
    if raw is None:
        return None
    try:
        value = float(raw)
    except ValueError:
        raise CheckError(f"--opt near cần số trong khoảng 0–1, không phải {raw!r}") from None
    if not 0.0 <= value <= 1.0:
        raise CheckError(f"--opt near cần số trong khoảng 0–1, không phải {raw!r}")
    return value


def _dataset_path(opts: dict[str, str], key: str, names: dict[str, Path]) -> Path:
    name = opts.get(key)
    if not name:
        raise CheckError(f"thiếu --opt {key}=<tên tập> (tên tệp bỏ đuôi)")
    if name not in names:
        raise CheckError(
            f"--opt {key}={name}: không có tập này trong đầu vào — có: {', '.join(sorted(names)) or '(không)'}"
        )
    return names[name]


def _config(files: list[Path], opts: dict[str, str]) -> _Config:
    names: dict[str, Path] = {}
    for path in files:
        if path.stem in names:
            raise CheckError(f"hai tệp cùng tên tập {path.stem!r}")
        names[path.stem] = path
    train = _dataset_path(opts, "train", names)
    evaluation = _dataset_path(opts, "eval", names)
    if train == evaluation:
        raise CheckError("--opt train và eval phải là hai tập khác nhau")
    field = opts.get("field")
    if field == "":
        raise CheckError("--opt field không được rỗng")
    fewshot = opts.get("fewshot")
    if fewshot is not None and not Path(fewshot).is_file():
        raise CheckError(f"--opt fewshot: không thấy tệp {fewshot!r}")
    return _Config(train, evaluation, Path(fewshot) if fewshot is not None else None, field, _option_near(opts))


def _signature(norm: str) -> tuple[int, ...]:
    words = norm.split(" ")
    shingles = {" ".join(words[i : i + SHINGLE]) for i in range(max(1, len(words) - SHINGLE + 1))}
    bases = [
        int.from_bytes(hashlib.blake2b(s.encode("utf-8", "surrogatepass"), digest_size=8).digest()) for s in shingles
    ]
    return tuple(min((a * x + b) % PRIME for x in bases) for a, b in COEFS)


def _bands(signature: tuple[int, ...]) -> list[int]:
    return [hash((band, *signature[band * ROWS : (band + 1) * ROWS])) for band in range(BANDS)]


def _near_pairs(train: _Dataset, evaluation: _Dataset, threshold: float) -> list[tuple[int, int, float]]:
    """(dòng eval, dòng train, Jaccard ước lượng) — chỉ so các mẫu cùng bucket theo dải, không so mọi cặp."""
    reps: dict[bytes, int] = {}
    for line, norm in train.samples:
        reps.setdefault(_digest(norm), line)
    exact = set(reps)
    signatures: list[tuple[int, ...]] = []
    lines: list[int] = []
    buckets: dict[int, list[int]] = {}
    for line, norm in train.samples:
        if reps.get(_digest(norm)) != line:
            continue
        signatures.append(_signature(norm))
        lines.append(line)
        for key in _bands(signatures[-1]):
            bucket = buckets.setdefault(key, [])
            if len(bucket) < MAX_BUCKET:
                bucket.append(len(lines) - 1)
    pairs: list[tuple[int, int, float]] = []
    for line, norm in evaluation.samples:
        if _digest(norm) in exact:
            continue
        signature = _signature(norm)
        candidates = dict.fromkeys(i for key in _bands(signature) for i in buckets.get(key, ()))
        best = max(
            ((sum(a == b for a, b in zip(signature, signatures[i])) / HASHES, -lines[i]) for i in candidates),
            default=None,
        )
        if best is not None and best[0] >= threshold:
            pairs.append((line, -best[1], best[0]))
    return pairs


def _exact_findings(config: _Config, train: _Dataset, evaluation: _Dataset) -> list[Finding]:
    path = str(config.evaluation)
    first: dict[bytes, int] = {}
    for line, norm in train.samples:
        first.setdefault(_digest(norm), line)
    leaks: list[tuple[int, str]] = []
    seen: dict[bytes, int] = {}
    groups: set[bytes] = set()
    example: tuple[int, int] | None = None
    for line, norm in evaluation.samples:
        digest = _digest(norm)
        if digest in first:
            leaks.append((line, f"eval dòng {line} trùng train dòng {first[digest]}"))
        if digest in seen:
            groups.add(digest)
            example = example or (seen[digest], line)
        seen.setdefault(digest, line)
    found = _report(path, "DDL001", leaks, f"tổng {len(leaks)} mẫu eval trùng train")
    if example is not None:
        found.append(
            Finding(
                path,
                example[1],
                "DDL004",
                f"{len(groups)} nhóm mẫu trùng trong eval (vd dòng {example[0]} và dòng {example[1]})",
            )
        )
    return found


def _fewshot_findings(path: Path, train: _Dataset, evaluation: _Dataset) -> list[Finding]:
    text = read_text(path)
    if text is None:
        return [Finding(str(path), 0, "DDL000", UNREADABLE)]
    text = text.removeprefix(BOM)
    eval_hashes = {_digest(norm) for _, norm in evaluation.samples}
    train_hashes = {_digest(norm) for _, norm in train.samples}
    hits: list[tuple[int, str]] = []
    for number, raw in enumerate(text.split("\n"), 1):
        norm = _norm(raw)
        if not norm:
            continue
        digest = _digest(norm)
        if digest in eval_hashes:
            hits.append((number, f"mẫu few-shot dòng {number} trùng mẫu eval"))
        elif digest in train_hashes:
            hits.append((number, f"mẫu few-shot dòng {number} trùng mẫu train"))
    return _report(str(path), "DDL003", hits, f"tổng {len(hits)} mẫu few-shot trùng eval/train")


def check(files: list[Path], opts: dict[str, str]) -> list[Finding]:
    config = _config(files, opts)
    train = _load(config.train, config.field)
    evaluation = _load(config.evaluation, config.field)
    found = [*train.findings, *evaluation.findings]
    if train.fatal or evaluation.fatal:
        return found
    found.extend(_exact_findings(config, train, evaluation))
    if config.fewshot is not None:
        found.extend(_fewshot_findings(config.fewshot, train, evaluation))
    if config.near is not None:
        pairs = _near_pairs(train, evaluation, config.near)
        entries = [(e, f"eval dòng {e} gần trùng train dòng {t} (Jaccard ước lượng {j:.2f})") for e, t, j in pairs]
        found.extend(_report(str(config.evaluation), "DDL005", entries, f"tổng {len(pairs)} mẫu eval gần trùng train"))
    return found
