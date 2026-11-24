"""Loại `trace` (AI-OBS-001/008/013, OPS-OBS-002/017): trace OTLP JSON của agent/tool theo OpenTelemetry GenAI phải liền mạch và đủ
thuộc tính `gen_ai.*`. Đầu vào: một tài liệu OTLP hoặc JSON Lines (mỗi dòng một tài liệu). Báo: `TRC000` tệp không phải JSON/OTLP
hợp lệ (lồng quá sâu, quá 200000 span), `TRC001` span mồ côi (cha không có cùng traceId), `TRC002` thiếu thuộc tính `gen_ai.*`
bắt buộc, `TRC003` con khác traceId với cha, `TRC004` traceId/spanId sai dạng hex. `--opt required=a,b|c` thay danh sách mặc định
(`a|b` = một trong)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from . import Finding, read_text

HELP = "trace OTLP của agent: span mồ côi, con khác traceId với cha, thiếu gen_ai.* bắt buộc, id sai hex"
SUFFIXES = (".json", ".jsonl", ".ndjson")
MAX_SPANS = 200000
DEFAULT_REQUIRED = "gen_ai.operation.name,gen_ai.provider.name|gen_ai.system"
OPTS = ("required",)
TRACE_ID = re.compile(r"[0-9a-f]{32}")
SPAN_ID = re.compile(r"[0-9a-f]{16}")

Span = tuple[int, dict[str, Any]]


def sniff(text: str) -> bool:
    """Nhận diện sơ bộ tệp OTLP khi duyệt thư mục."""
    return '"resourceSpans"' in text


SNIFF = sniff


def _items(parent: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = parent.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, dict) for v in value):
        raise ValueError(f"cấu trúc OTLP sai ({key} phải là danh sách đối tượng)")
    return value


def _parse(text: str) -> list[tuple[int, object]]:
    try:
        return [(1, json.loads(text))]
    except json.JSONDecodeError:
        pass
    docs = [(number, json.loads(line)) for number, line in enumerate(text.split("\n"), 1) if line.strip()]
    if not docs:
        raise ValueError("tệp rỗng")
    return docs


def _load(text: str) -> list[Span]:
    spans: list[Span] = []
    for number, doc in _parse(text):
        if not isinstance(doc, dict) or "resourceSpans" not in doc:
            raise ValueError("thiếu resourceSpans")
        for resource in _items(doc, "resourceSpans"):
            for scope in _items(resource, "scopeSpans"):
                spans.extend((number, span) for span in _items(scope, "spans"))
        if len(spans) > MAX_SPANS:
            raise ValueError(f"quá {MAX_SPANS} span")
    return spans


def _text(span: dict[str, Any], key: str) -> str:
    value = span.get(key)
    return value.lower() if isinstance(value, str) else ""


def _bad_hex(value: str, pattern: re.Pattern[str]) -> bool:
    return not pattern.fullmatch(value) or not value.strip("0")


def _keys(span: dict[str, Any]) -> set[str]:
    attrs = span.get("attributes")
    if not isinstance(attrs, list):
        return set()
    return {a["key"] for a in attrs if isinstance(a, dict) and isinstance(a.get("key"), str)}


def _attr_findings(path: str, line: int, span: dict[str, Any], groups: list[list[str]]) -> list[Finding]:
    keys = _keys(span)
    if not any(k.startswith("gen_ai.") for k in keys):
        return []
    missing = ["|".join(g) for g in groups if not keys.intersection(g)]
    if not missing:
        return []
    return [
        Finding(path, line, "TRC002", f"span {_text(span, 'name')!r} thiếu thuộc tính bắt buộc: {', '.join(missing)}")
    ]


def _span_findings(path: str, span: Span, ids: set[tuple[str, str]], traces_of: dict[str, set[str]]) -> list[Finding]:
    line, data = span
    trace, sid, parent = _text(data, "traceId"), _text(data, "spanId"), str(data.get("parentSpanId") or "").lower()
    found: list[Finding] = []
    if _bad_hex(trace, TRACE_ID):
        found.append(Finding(path, line, "TRC004", f"traceId sai dạng (cần 32 hex, không toàn 0): {trace!r}"))
    if _bad_hex(sid, SPAN_ID):
        found.append(Finding(path, line, "TRC004", f"spanId sai dạng (cần 16 hex, không toàn 0): {sid!r}"))
    if parent and (trace, parent) not in ids:
        found.append(Finding(path, line, "TRC001", f"span {sid!r} mồ côi: không có cha {parent!r} cùng traceId"))
    if parent in traces_of and trace not in traces_of[parent]:
        found.append(Finding(path, line, "TRC003", f"span {sid!r} khác traceId với cha {parent!r}"))
    return found


def _file_findings(path: str, spans: list[Span], groups: list[list[str]]) -> list[Finding]:
    ids = {(_text(s, "traceId"), _text(s, "spanId")) for _, s in spans}
    traces_of: dict[str, set[str]] = {}
    for trace, sid in ids:
        traces_of.setdefault(sid, set()).add(trace)
    found: list[Finding] = []
    for span in spans:
        found.extend(_span_findings(path, span, ids, traces_of))
        found.extend(_attr_findings(path, span[0], span[1], groups))
    return found


def check(files: list[Path], opts: dict[str, str]) -> list[Finding]:
    items = [item for item in opts.get("required", DEFAULT_REQUIRED).split(",") if item.strip()]
    groups = [[name.strip() for name in item.split("|")] for item in items]
    found: list[Finding] = []
    for path in files:
        text = read_text(path)
        if text is None:
            found.append(Finding(str(path), 0, "TRC000", "không đọc được dưới dạng UTF-8 (hoặc quá lớn)"))
            continue
        try:
            spans = _load(text)
        except RecursionError:
            found.append(Finding(str(path), 1, "TRC000", "JSON lồng quá sâu"))
            continue
        except ValueError as exc:
            found.append(Finding(str(path), 1, "TRC000", f"không phải JSON/OTLP hợp lệ: {exc}"))
            continue
        found.extend(_file_findings(str(path), spans, groups))
    return found
