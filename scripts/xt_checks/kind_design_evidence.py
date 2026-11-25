"""Kiểm cấu trúc bằng chứng thiết kế schema 1 (T-5015, D-584)."""

from __future__ import annotations

import json
import math
from pathlib import Path

from . import CheckError, CheckReport, Finding, JsonShape, read_text

HELP = "brief, phương án và biên bản thử tác vụ hợp lệ; mode=pilot yêu cầu kết quả đo"
SUFFIXES = (".json",)
NAMES = frozenset({"DESIGN-EVIDENCE.json"})
OPTS = ("mode",)
BRIEF_FIELDS = ("primary_user", "task", "device", "long_data", "empty_data", "success_criteria")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    data: dict[str, object] = {}
    for key, value in pairs:
        if key in data:
            raise ValueError("JSON có khoá lặp")
        data[key] = value
    return data


def _read(path: Path) -> dict[str, object] | None:
    text = read_text(path)
    if text is None:
        return None
    try:
        data = json.loads(text, object_pairs_hook=_unique_object)
    except (ValueError, RecursionError):
        return None
    return data if isinstance(data, dict) else None


def _text(shape: JsonShape, field: str, value: object) -> str | None:
    if isinstance(value, str) and (clean := value.strip()):
        return clean
    shape.error(field, "chuỗi khác rỗng")
    return None


def _object(shape: JsonShape, field: str, value: object) -> dict[str, object] | None:
    if isinstance(value, dict):
        return value
    shape.error(field, "object")
    return None


def _count(shape: JsonShape, field: str, value: object) -> int | None:
    if type(value) is int and value >= 0:
        return value
    shape.error(field, "số nguyên không âm")
    return None


def _id(shape: JsonShape, field: str, value: object, seen: set[str]) -> None:
    cleaned = _text(shape, field, value)
    if cleaned is None:
        return
    if cleaned in seen:
        shape.error(field, "ID duy nhất")
    seen.add(cleaned)


def _options(shape: JsonShape, data: dict[str, object], checked: dict[str, int]) -> set[str]:
    raw = data.get("options")
    entries = shape.entries("options", raw, dict)
    checked["options"] += len(entries)
    seen: set[str] = set()
    for field, option in entries:
        _id(shape, f"{field}.id", option.get("id"), seen)
        _text(shape, f"{field}.approach", option.get("approach"))
        _text(shape, f"{field}.tradeoffs", option.get("tradeoffs"))
    if isinstance(raw, list) and len(seen) < 2:
        shape.error("options", "ít nhất hai phương án có ID khác nhau")
    return seen


def _decision(shape: JsonShape, decision: dict[str, object], options: set[str]) -> None:
    selected = _text(shape, "decision.selected", decision.get("selected"))
    if selected is not None and selected not in options:
        shape.error("decision.selected", "ID của một phương án trong options")
    _text(shape, "decision.reason", decision.get("reason"))


def _nonnegative_duration(value: object) -> bool:
    if type(value) is int:
        return value >= 0
    return isinstance(value, float) and math.isfinite(value) and value >= 0


def _participant(shape: JsonShape, field: str, data: dict[str, object], seen: set[str]) -> bool | None:
    _id(shape, f"{field}.id", data.get("id"), seen)
    if not _nonnegative_duration(data.get("duration_seconds")):
        shape.error(f"{field}.duration_seconds", "số giây hữu hạn không âm")
    _count(shape, f"{field}.errors", data.get("errors"))
    _count(shape, f"{field}.help_count", data.get("help_count"))
    completed = data.get("completed")
    if isinstance(completed, bool):
        return completed
    shape.error(f"{field}.completed", "boolean")
    return None


def _tested(shape: JsonShape, trial: dict[str, object], checked: dict[str, int]) -> None:
    raw = trial.get("participants")
    entries = shape.entries("trial.participants", raw, dict)
    checked["participants"] += len(entries)
    if raw == []:
        shape.error("trial.participants", "ít nhất một người thử")
    seen: set[str] = set()
    outcomes: list[bool] = []
    for field, entry in entries:
        result = _participant(shape, field, entry, seen)
        if result is not None:
            outcomes.append(result)
    total = len(raw) if isinstance(raw, list) else None
    completed = sum(outcomes) if len(outcomes) == total else None
    summary = _object(shape, "trial.summary", trial.get("summary"))
    if summary is None:
        return
    checked["summaries"] += 1
    for key, measured in (("participants", total), ("completed", completed)):
        field = f"trial.summary.{key}"
        declared = _count(shape, field, summary.get(key))
        if declared is not None and measured is not None and declared != measured:
            shape.error(field, "tổng khớp trial.participants")


def _untested(shape: JsonShape, trial: dict[str, object], mode: str) -> None:
    if mode == "pilot":
        shape.findings.append(Finding(shape.path, 0, "DES001", "trial.status: mode=pilot cần kết quả thử tác vụ"))
    _text(shape, "trial.reason", trial.get("reason"))
    _text(shape, "trial.next_step", trial.get("next_step"))
    for key in ("participants", "summary"):
        if key in trial:
            shape.error(f"trial.{key}", "bỏ trường này khi status=not_tested")


def _trial(shape: JsonShape, trial: dict[str, object], checked: dict[str, int], mode: str) -> None:
    status = trial.get("status")
    if status == "tested":
        _tested(shape, trial, checked)
    elif status == "not_tested":
        _untested(shape, trial, mode)
    else:
        shape.error("trial.status", "tested hoặc not_tested")


def _doc(shape: JsonShape, data: dict[str, object], checked: dict[str, int], mode: str) -> None:
    schema = data.get("schema")
    if type(schema) is not int or schema != 1:
        shape.error("schema", "số nguyên 1")
        return
    brief = _object(shape, "brief", data.get("brief"))
    if brief is not None:
        checked["briefs"] += 1
        for key in BRIEF_FIELDS:
            _text(shape, f"brief.{key}", brief.get(key))
    options = _options(shape, data, checked)
    decision = _object(shape, "decision", data.get("decision"))
    if decision is not None:
        checked["decisions"] += 1
        _decision(shape, decision, options)
    trial = _object(shape, "trial", data.get("trial"))
    if trial is not None:
        checked["trials"] += 1
        _trial(shape, trial, checked, mode)


def check_report(files: list[Path], opts: dict[str, str]) -> CheckReport:
    mode = opts.get("mode", "draft")
    if mode not in ("draft", "pilot"):
        raise CheckError("--opt mode nhận draft hoặc pilot")
    if mode == "pilot" and not files:
        raise CheckError("mode=pilot cần ít nhất một tệp bằng chứng thiết kế")
    checked = dict(files=len(files), briefs=0, options=0, decisions=0, trials=0, participants=0, summaries=0)
    report = CheckReport([], checked)
    for path in files:
        shape = JsonShape(str(path), "DES000", report.findings)
        data = _read(path)
        if data is None:
            shape.error("tệp", "object JSON UTF-8 đọc được, trong giới hạn kích thước và không lặp khoá")
        else:
            _doc(shape, data, checked, mode)
    return report


def check(files: list[Path], opts: dict[str, str]) -> list[Finding]:
    return check_report(files, opts).findings
