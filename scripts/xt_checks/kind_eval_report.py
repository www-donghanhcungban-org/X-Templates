"""Validate evaluation report snapshots and apply an independently supplied policy."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from . import CheckError, CheckReport, Finding, read_text

HELP = "Kiểm cấu trúc báo cáo eval hoặc áp chính sách nghiệm thu độc lập"
SUFFIXES = (".json",)
OPTS = ("mode", "policy", "revision", "at")

LIMIT = 100_000
STATUSES = {"pass", "fail", "infra_failure", "error", "unscored", "skipped"}
CLAIMS = {"real-path", "faithful-fixture", "asserted-not-measured", "synthetic-fixture"}
MODES = {"fresh", "replay"}
CACHES = {"off", "provider", "replay"}
IDENTITY = {"suite", "eval_version", "dataset_sha256", "scorer_sha256", "config_sha256", "environment_sha256"}
RUNTIME = {"implementation", "version", "platform"}
REPORT = {
    "schema",
    "kind",
    "identity",
    "run_id",
    "timestamp",
    "revision",
    "dirty",
    "content_sha256",
    "runtime",
    "claim",
    "execution",
    "cases",
    "counts",
}
POLICY = {
    "schema",
    "kind",
    "policy_id",
    "identity",
    "content_sha256",
    "runtime",
    "case_ids",
    "critical_ids",
    "clusters",
    "attempts_per_case",
    "min_success_rate",
    "max_infra_rate",
    "max_age_seconds",
    "allowed_claims",
    "allowed_execution_modes",
    "cache",
    "infra_exclusions",
}


class Invalid(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Invalid(message)


def obj(value: Any, keys: set[str], name: str) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == keys, f"{name}: keys")
    return cast(dict[str, Any], value)


def string(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def integer(value: Any, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def digest(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def revision_ok(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", value) is not None


def timestamp(value: Any) -> datetime:
    require(
        isinstance(value, str)
        and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)", value)
        is not None
        and not value.endswith("-00:00"),
        "timestamp",
    )
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Invalid("timestamp") from exc


def identity(value: Any) -> None:
    data = obj(value, IDENTITY, "identity")
    require(
        string(data["suite"])
        and isinstance(data["eval_version"], str)
        and re.fullmatch(r"[1-9][0-9]*-[A-Z]+", data["eval_version"]) is not None,
        "identity",
    )
    require(all(digest(data[k]) for k in IDENTITY if k.endswith("_sha256")), "identity digest")


def runtime(value: Any) -> None:
    data = obj(value, RUNTIME, "runtime")
    require(all(string(v) for v in data.values()), "runtime")


def common(data: dict[str, Any], kind: str) -> None:
    require(type(data["schema"]) is int and data["schema"] == 1 and data["kind"] == kind, "schema/kind")
    identity(data["identity"])
    runtime(data["runtime"])
    require(digest(data["content_sha256"]), "content digest")


def sequence(value: Any, name: str, nonempty: bool = False) -> list[Any]:
    require(isinstance(value, list) and len(value) <= LIMIT and (not nonempty or bool(value)), name)
    return cast(list[Any], value)


def strings(value: Any, name: str, nonempty: bool = False) -> set[str]:
    items = sequence(value, name, nonempty)
    require(all(string(v) for v in items), name)
    result = set(items)
    require(len(result) == len(items), name)
    return result


def execution(value: Any) -> dict[str, Any]:
    data = obj(value, {"mode", "cache", "attempts_per_case"}, "execution")
    require(
        data["mode"] in MODES
        and data["cache"] in CACHES
        and (data["mode"] == "replay") == (data["cache"] == "replay")
        and integer(data["attempts_per_case"], 1, 1000),
        "execution",
    )
    return data


def report_schema(value: Any, checked: dict[str, int]) -> dict[str, Any]:
    data = obj(value, REPORT, "report")
    common(data, "eval-report")
    require(string(data["run_id"]) and revision_ok(data["revision"]) and type(data["dirty"]) is bool, "run identity")
    timestamp(data["timestamp"])
    require(data["claim"] in CLAIMS, "claim")
    run = execution(data["execution"])
    require(
        not (data["claim"] == "real-path" and run["mode"] != "fresh")
        and not (data["claim"] == "faithful-fixture" and run["mode"] != "replay"),
        "claim/mode",
    )
    cases = sequence(data["cases"], "cases", True)
    checked["case_records"] = len(cases)
    pairs: set[tuple[str, int]] = set()
    counts: Counter[str] = Counter()
    for item in cases:
        require(isinstance(item, dict), "case")
        status = item.get("status")
        case = obj(
            item,
            {"id", "attempt", "cluster", "status", "evidence_sha256"}
            | ({"infra_confirmation"} if status == "infra_failure" else set()),
            "case",
        )
        require(
            string(case["id"])
            and integer(case["attempt"], 1, 1000)
            and string(case["cluster"])
            and status in STATUSES
            and digest(case["evidence_sha256"]),
            "case fields",
        )
        pair = (case["id"], case["attempt"])
        require(pair not in pairs, "duplicate case")
        pairs.add(pair)
        counts[status] += 1
        if status == "infra_failure":
            conf = obj(case["infra_confirmation"], {"confirmed", "reason", "evidence_sha256"}, "infra confirmation")
            require(
                type(conf["confirmed"]) is bool and string(conf["reason"]) and digest(conf["evidence_sha256"]),
                "infra confirmation",
            )
    totals = obj(data["counts"], {"total", "eligible"} | STATUSES, "counts")
    expected = dict(counts)
    expected.update(total=len(cases), eligible=len(cases) - counts["infra_failure"])
    require(all(integer(totals[k], 0, LIMIT) and totals[k] == expected.get(k, 0) for k in totals), "counts")
    return data


def rate(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1


def policy_schema(value: Any) -> dict[str, Any]:
    data = obj(value, POLICY, "policy")
    common(data, "eval-policy")
    require(string(data["policy_id"]), "policy id")
    ids = strings(data["case_ids"], "case ids", True)
    critical = strings(data["critical_ids"], "critical ids")
    require(critical <= ids, "critical ids")
    clusters = obj(data["clusters"], ids, "clusters")
    require(all(string(v) for v in clusters.values()), "clusters")
    attempts = data["attempts_per_case"]
    require(integer(attempts, 1, 1000) and len(ids) * attempts <= LIMIT, "attempts")
    require(
        rate(data["min_success_rate"])
        and rate(data["max_infra_rate"])
        and integer(data["max_age_seconds"], 1, 31_536_000),
        "threshold",
    )
    require(strings(data["allowed_claims"], "claims", True) <= CLAIMS - {"asserted-not-measured"}, "claims")
    require(strings(data["allowed_execution_modes"], "modes", True) <= MODES and data["cache"] in CACHES, "modes/cache")
    pairs: set[tuple[str, int]] = set()
    for entry in sequence(data["infra_exclusions"], "infra exclusions"):
        item = obj(entry, {"id", "attempt", "reason", "evidence_sha256"}, "infra exclusion")
        require(
            string(item["id"])
            and item["id"] in ids
            and integer(item["attempt"], 1, attempts)
            and string(item["reason"])
            and digest(item["evidence_sha256"]),
            "infra exclusion",
        )
        pair = (item["id"], item["attempt"])
        require(pair not in pairs, "duplicate exclusion")
        pairs.add(pair)
    return data


def apply_gate(report: dict[str, Any], policy: dict[str, Any], revision: str, at: str) -> None:
    require(revision_ok(revision), "revision option")
    now = timestamp(at)
    require(
        all(report[k] == policy[k] for k in ("identity", "content_sha256", "runtime")),
        "identity/content/runtime mismatch",
    )
    require(report["revision"] == revision and not report["dirty"], "revision/dirty")
    age = (now - timestamp(report["timestamp"])).total_seconds()
    require(0 <= age <= policy["max_age_seconds"], "age")
    run = report["execution"]
    require(
        report["claim"] in policy["allowed_claims"]
        and run["mode"] in policy["allowed_execution_modes"]
        and run["cache"] == policy["cache"]
        and run["attempts_per_case"] == policy["attempts_per_case"],
        "claim/execution",
    )
    cases = report["cases"]
    ids = set(policy["case_ids"])
    critical = set(policy["critical_ids"])
    attempts = policy["attempts_per_case"]
    # Schema đã loại cặp trùng. Đủ số lượng và từng cặp thuộc miền thì tập khớp.
    require(
        len(cases) == len(ids) * attempts and all(c["id"] in ids and c["attempt"] <= attempts for c in cases),
        "case manifest",
    )
    require(all(c["cluster"] == policy["clusters"][c["id"]] for c in cases), "cluster")
    require(all(c["status"] == "pass" for c in cases if c["id"] in critical), "critical case")
    require(all(c["status"] not in {"error", "unscored", "skipped"} for c in cases), "unusable result")
    exclusions = {(e["id"], e["attempt"], e["reason"], e["evidence_sha256"]) for e in policy["infra_exclusions"]}
    actual = {
        (c["id"], c["attempt"], c["infra_confirmation"]["reason"], c["infra_confirmation"]["evidence_sha256"])
        for c in cases
        if c["status"] == "infra_failure" and c["infra_confirmation"]["confirmed"]
    }
    infra = report["counts"]["infra_failure"]
    require(exclusions == actual and len(actual) == infra, "infra confirmation")
    eligible = report["counts"]["eligible"]
    require(
        eligible > 0
        and infra / len(cases) <= policy["max_infra_rate"]
        and report["counts"]["pass"] / eligible >= policy["min_success_rate"],
        "quality threshold",
    )


def evaluate(
    report: object, policy: object | None = None, revision: str | None = None, at: str | None = None
) -> tuple[list[tuple[str, str]], dict[str, int], dict[str, object] | None]:
    """Check already-decoded snapshots; return findings, counters, and valid report."""
    gate = revision is not None or at is not None or policy is not None
    checked = {"case_records": 0, "quality_gates": 0, "schema_only": int(not gate)}
    try:
        data = report_schema(report, checked)
        if gate:
            policy_data = policy_schema(policy)
            require(revision is not None and at is not None and revision_ok(revision), "gate options")
            timestamp(at)
    except (Invalid, TypeError, OverflowError) as exc:
        return [("EVR000", str(exc))], checked, None
    if gate:
        try:
            assert revision is not None and at is not None
            apply_gate(data, policy_data, revision, at)
        except (Invalid, TypeError, OverflowError) as exc:
            return [("EVR001", str(exc))], checked, None
        checked["quality_gates"] = 1
    return [], checked, data


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    data = dict(pairs)
    require(len(data) == len(pairs), "JSON có khóa trùng")
    return data


def reject_constant(value: str) -> None:
    raise Invalid(f"Giá trị JSON không hữu hạn {value}")


def read_payload(path: Path) -> object:
    text = read_text(path)
    if text is None:
        raise Invalid("Không đọc được tệp JSON UTF-8 trong giới hạn")
    try:
        return json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant)
    except RecursionError as error:
        raise Invalid("JSON lồng quá sâu") from error


def check_report(files: list[Path], opts: dict[str, str]) -> CheckReport:
    mode = opts.get("mode", "validate")
    if mode == "gate":
        required = {"mode", "policy", "revision", "at"}
        if len(files) != 1 or set(opts) != required or not all(opts.values()):
            raise CheckError("mode=gate cần một report và policy, revision, at")
        if not revision_ok(opts["revision"]):
            raise CheckError("revision phải là SHA Git đầy đủ")
        try:
            timestamp(opts["at"])
        except Invalid as error:
            raise CheckError("at phải là thời điểm RFC 3339") from error
    elif mode != "validate" or set(opts) - {"mode"}:
        raise CheckError("mode phải là validate hoặc gate cùng tùy chọn của chế độ đó")

    checked = {"files": 0, "case_records": 0, "quality_gates": 0, "schema_only": int(mode == "validate")}
    findings = []
    if not files:
        findings.append(Finding(".", 1, "EVR000", "Không có tệp report"))
    for path in files:
        try:
            report = read_payload(path)
            policy = read_payload(Path(opts["policy"])) if mode == "gate" else None
        except (OSError, ValueError) as error:
            findings.append(Finding(str(path), 1, "EVR000", str(error)))
            continue
        issues, counts, _ = evaluate(report, policy, opts.get("revision"), opts.get("at"))
        checked["files"] += 1
        checked["case_records"] += counts["case_records"]
        checked["quality_gates"] = counts["quality_gates"]
        findings.extend(Finding(str(path), 1, code, message) for code, message in issues)
    return CheckReport(findings, checked)


def check(files: list[Path], opts: dict[str, str]) -> list[Finding]:
    return check_report(files, opts).findings
