"""Đánh giá kết quả thử theo policy được ghim độc lập."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path

from . import CheckError, CheckReport, Finding, JsonShape, read_text
from . import kind_design_evidence as evidence
from .kind_eval_report import Invalid, timestamp

HELP = "đánh giá kết quả thử tác vụ theo policy độc lập"
SUFFIXES = (".json",)
NAMES = frozenset({"DESIGN-EVIDENCE.json"})
OPTS = ("policy", "revision", "at")
POLICY_FIELDS = frozenset(
    (
        "schema",
        "kind",
        "policy_id",
        "revision",
        "evidence_sha256",
        "observed_at",
        "max_age_seconds",
        "participant_ids",
        "required_completed_ids",
        "min_completion_rate",
        "min_unassisted_rate",
        "max_error_rate",
        "max_p95_duration_seconds",
    )
)
LIMIT = 100000


def _date(value: object) -> datetime | None:
    try:
        return timestamp(value)
    except Invalid:
        return None


def _json(path: Path) -> tuple[str, dict[str, object]] | None:
    text = read_text(path)
    if text is None:
        return None
    try:
        data = json.loads(text, object_pairs_hook=evidence._unique_object, parse_constant=_bad_constant)
    except (ValueError, RecursionError):
        return None
    return (text, data) if isinstance(data, dict) else None


def _bad_constant(value: str) -> None:
    raise ValueError(value)


def _fields(shape: JsonShape, where: str, data: dict[str, object], fields: frozenset[str]) -> None:
    if set(data) != fields:
        shape.error(where, "đúng các trường hợp đồng")


def _ids(shape: JsonShape, field: str, value: object, nonempty: bool) -> set[str]:
    if not isinstance(value, list) or len(value) > LIMIT or (nonempty and not value):
        shape.error(field, "mảng ID trong giới hạn")
        return set()
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip() or item in seen:
            shape.error(field, "ID khác rỗng và duy nhất")
        else:
            seen.add(item)
    return seen


def _number(value: object, low: float, high: float, *, positive: bool = False) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value) and low <= value <= high and (not positive or value > 0)
    except OverflowError:
        return False


def _policy_header(shape: JsonShape, data: dict[str, object]) -> None:
    if type(data.get("schema")) is not int or data.get("schema") != 1 or data.get("kind") != "design-outcome-policy":
        shape.error("policy.schema/kind", "schema 1 và kind design-outcome-policy")
    if not isinstance(data.get("policy_id"), str) or not str(data["policy_id"]).strip():
        shape.error("policy_id", "ID khác rỗng")
    for key, pattern in (("revision", r"(?:[0-9a-f]{40}|[0-9a-f]{64})"), ("evidence_sha256", r"[0-9a-f]{64}")):
        if not isinstance(data.get(key), str) or not re.fullmatch(pattern, str(data[key])):
            shape.error(key, "digest hex thường hợp lệ")
    if _date(data.get("observed_at")) is None:
        shape.error("observed_at", "thời điểm có múi giờ")
    age = data.get("max_age_seconds")
    if type(age) is not int or not 1 <= age <= 31536000:
        shape.error("max_age_seconds", "số nguyên từ 1 đến 31536000")


def _policy(shape: JsonShape, data: dict[str, object]) -> tuple[set[str], set[str]]:
    _fields(shape, "policy", data, POLICY_FIELDS)
    _policy_header(shape, data)
    ids = _ids(shape, "participant_ids", data.get("participant_ids"), True)
    required = _ids(shape, "required_completed_ids", data.get("required_completed_ids"), False)
    if not required <= ids:
        shape.error("required_completed_ids", "tập con participant_ids")
    for key in ("min_completion_rate", "min_unassisted_rate", "max_error_rate"):
        if not _number(data.get(key), 0, 1):
            shape.error(key, "số hữu hạn trong [0, 1]")
    if not _number(data.get("max_p95_duration_seconds"), 0, float("inf"), positive=True):
        shape.error("max_p95_duration_seconds", "số hữu hạn dương")
    return ids, required


def _strict_trial(shape: JsonShape, trial: dict[str, object]) -> None:
    participants = trial.get("participants")
    if isinstance(participants, list):
        for obj in participants:
            if isinstance(obj, dict):
                _fields(
                    shape,
                    "trial.participants",
                    obj,
                    frozenset(("id", "completed", "duration_seconds", "errors", "help_count")),
                )
    summary = trial.get("summary")
    if isinstance(summary, dict):
        _fields(shape, "trial.summary", summary, frozenset(("participants", "completed")))


def _strict(shape: JsonShape, data: dict[str, object]) -> None:
    _fields(shape, "hồ sơ", data, frozenset(("schema", "brief", "options", "decision", "trial")))
    fields = {
        "brief": evidence.BRIEF_FIELDS,
        "decision": ("selected", "reason"),
        "trial": ("status", "participants", "summary"),
    }
    for key, allowed in fields.items():
        obj = data.get(key)
        if isinstance(obj, dict):
            _fields(shape, key, obj, frozenset(allowed))
    options = data.get("options")
    if isinstance(options, list):
        for obj in options:
            if isinstance(obj, dict):
                _fields(shape, "options", obj, frozenset(("id", "approach", "tradeoffs")))
    trial = data.get("trial")
    if isinstance(trial, dict):
        _strict_trial(shape, trial)


def _quality(
    report: CheckReport,
    path: Path,
    data: dict[str, object],
    policy: dict[str, object],
    ids: set[str],
    required: set[str],
    text: str,
    revision: str,
    at: datetime,
) -> None:
    trial = data["trial"]
    assert isinstance(trial, dict)
    participants = trial["participants"]
    assert isinstance(participants, list)
    actual = {p["id"] for p in participants}
    completed = sum(p["completed"] for p in participants)
    unassisted = sum(p["completed"] and p["help_count"] == 0 for p in participants)
    errors = sum(p["errors"] > 0 for p in participants)
    durations = sorted(p["duration_seconds"] for p in participants)
    report.checked.update(participants=len(participants), completed=completed, unassisted=unassisted, errors=errors)
    observed = _date(policy["observed_at"])
    assert observed is not None
    age = policy["max_age_seconds"]
    completion_rate = policy["min_completion_rate"]
    unassisted_rate = policy["min_unassisted_rate"]
    error_rate = policy["max_error_rate"]
    duration_limit = policy["max_p95_duration_seconds"]
    assert isinstance(age, int)
    assert isinstance(completion_rate, (int, float))
    assert isinstance(unassisted_rate, (int, float))
    assert isinstance(error_rate, (int, float))
    assert isinstance(duration_limit, (int, float))
    elapsed = (at - observed).total_seconds()
    conditions = (
        actual == ids,
        required <= {p["id"] for p in participants if p["completed"]},
        policy["revision"] == revision,
        policy["evidence_sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest(),
        0 <= elapsed <= age,
        completed / len(participants) >= completion_rate,
        unassisted / len(participants) >= unassisted_rate,
        errors / len(participants) <= error_rate,
        durations[math.ceil(0.95 * len(durations)) - 1] <= duration_limit,
    )
    if all(conditions):
        report.checked["quality_gates"] = 1
    else:
        report.findings.append(Finding(str(path), 0, "DSO001", "ngưỡng hoặc provenance không khớp policy"))


def check_report(files: list[Path], opts: dict[str, str]) -> CheckReport:
    if len(files) != 1 or set(opts) != set(OPTS) or not all(opts.values()):
        raise CheckError("cần đúng một hồ sơ và policy, revision, at")
    if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", opts["revision"]) or (at := _date(opts["at"])) is None:
        raise CheckError("revision hoặc at không hợp lệ")
    report = CheckReport([], dict(files=0, participants=0, completed=0, unassisted=0, errors=0, quality_gates=0))
    policy_path = Path(opts["policy"])
    parsed_policy = _json(policy_path)
    parsed = _json(files[0])
    for path, item in ((policy_path, parsed_policy), (files[0], parsed)):
        if item is None:
            JsonShape(str(path), "DSO000", report.findings).error("tệp", "object JSON UTF-8 hợp lệ")
    if parsed_policy is None or parsed is None:
        return report
    policy = parsed_policy[1]
    shape = JsonShape(str(policy_path), "DSO000", report.findings)
    ids, required = _policy(shape, policy)
    text, data = parsed
    shape = JsonShape(str(files[0]), "DSO000", report.findings)
    trial = data.get("trial")
    if isinstance(trial, dict) and isinstance(trial.get("participants"), list) and len(trial["participants"]) > LIMIT:
        shape.error("trial.participants", "không quá 100000 người")
        return report
    _strict(shape, data)
    counts = dict(briefs=0, options=0, decisions=0, trials=0, participants=0, summaries=0)
    evidence._doc(shape, data, counts, "pilot")
    trial = data.get("trial")
    if isinstance(trial, dict) and trial.get("status") != "tested":
        shape.error("trial.status", "tested")
    if report.findings:
        return report
    report.checked["files"] = 1
    _quality(report, files[0], data, policy, ids, required, text, opts["revision"], at)
    return report


def check(files: list[Path], opts: dict[str, str]) -> list[Finding]:
    return check_report(files, opts).findings
