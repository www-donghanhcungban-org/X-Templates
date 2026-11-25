"""Loại `vex` (SEC-SUPPLY-031/030): kiểm tệp OpenVEX JSON. Báo: `VEX000` không phải JSON/OpenVEX hợp lệ, `VEX001` thiếu
author/timestamp/version ở mức tài liệu, `VEX002` statement thiếu vulnerability (name hoặc @id) hay products, `VEX003` status
ngoài tập hợp lệ, `VEX004` `not_affected` thiếu justification hợp lệ lẫn impact_statement, `VEX005` `affected` thiếu
action_statement."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from . import CheckReport, Finding, JsonShape, read_text

HELP = "OpenVEX thiếu trường tài liệu, vulnerability/products, status sai, justification hay action_statement"
SUFFIXES = (".json",)
OPTS: tuple[str, ...] = ()
# `@context` hợp lệ: scheme https, host openvex.dev, path bắt đầu /ns (viết từng phần; BASE-CFG-001 cấm URL literal)
CONTEXT_SCHEME = "https"
CONTEXT_HOST = "openvex.dev"
CONTEXT_PATH = "/ns"
STATUSES = ("not_affected", "affected", "fixed", "under_investigation")
JUSTIFICATIONS = (
    "component_not_present",
    "vulnerable_code_not_present",
    "vulnerable_code_not_in_execute_path",
    "vulnerable_code_cannot_be_controlled_by_adversary",
    "inline_mitigations_already_exist",
)


def sniff(text: str) -> bool:
    """Nhận diện sơ bộ tệp OpenVEX khi duyệt thư mục."""
    return '"@context"' in text and "openvex" in text


SNIFF = sniff


def _context_ok(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parts = urlsplit(value)
        host = parts.hostname
    except ValueError:
        return False
    return parts.scheme == CONTEXT_SCHEME and host == CONTEXT_HOST and parts.path.startswith(CONTEXT_PATH)


def _load(text: str) -> dict[str, Any] | None:
    try:
        data = json.loads(text)
    except (ValueError, RecursionError):
        return None
    if isinstance(data, dict) and _context_ok(data.get("@context")):
        return data
    return None


def _product_fields(shape: JsonShape, field: str, product: dict[str, Any]) -> None:
    for key in ("hashes", "identifiers"):
        if key in product:
            shape.mapping(f"{field}.{key}", product[key])


def _targets(shape: JsonShape, field: str, stmt: dict[str, Any]) -> None:
    vuln = shape.mapping(f"{field}.vulnerability", stmt.get("vulnerability", {}))
    shape.entries(f"{field}.vulnerability.aliases", vuln.get("aliases", []), str)
    products = stmt.get("products", [])
    if not (vuln.get("name") or vuln.get("@id")) or products == []:
        shape.findings.append(Finding(shape.path, 0, "VEX002", f"{field} thiếu vulnerability (name/@id) hoặc products"))
    for where, product in shape.entries(f"{field}.products", products, dict):
        _product_fields(shape, where, product)
        for subfield, sub in shape.entries(f"{where}.subcomponents", product.get("subcomponents", []), dict):
            _product_fields(shape, subfield, sub)


def _statement(shape: JsonShape, tag: str, stmt: dict[str, Any]) -> None:
    path, found = shape.path, shape.findings
    _targets(shape, tag, stmt)
    status = stmt.get("status")
    if status not in STATUSES:
        found.append(Finding(path, 0, "VEX003", f"{tag} có status không hợp lệ: {status!r}"))
    if (
        status == "not_affected"
        and stmt.get("justification") not in JUSTIFICATIONS
        and not stmt.get("impact_statement")
    ):
        found.append(Finding(path, 0, "VEX004", f"{tag} not_affected thiếu justification hợp lệ hoặc impact_statement"))
    if status == "affected" and not stmt.get("action_statement"):
        found.append(Finding(path, 0, "VEX005", f"{tag} affected thiếu action_statement"))


def _doc(shape: JsonShape, data: dict[str, Any]) -> int:
    miss = [key for key in ("author", "timestamp", "version") if data.get(key) in (None, "")]
    if miss:
        shape.findings.append(Finding(shape.path, 0, "VEX001", f"tài liệu thiếu: {', '.join(miss)}"))
    statements = data.get("statements")
    if statements == []:
        shape.error("statements", "ít nhất một statement")
    entries = shape.entries("statements", statements, dict)
    for field, stmt in entries:
        _statement(shape, field, stmt)
    return len(entries)


def check_report(files: list[Path], opts: dict[str, str]) -> CheckReport:
    report = CheckReport([], {"files": len(files), "statements": 0})
    for path in files:
        text = read_text(path)
        data = None if text is None else _load(text)
        if data is None:
            report.findings.append(Finding(str(path), 0, "VEX000", "không phải JSON OpenVEX hợp lệ (hoặc quá lớn)"))
        else:
            shape = JsonShape(str(path), "VEX000", report.findings)
            report.checked["statements"] += _doc(shape, data)
    return report


def check(files: list[Path], opts: dict[str, str]) -> list[Finding]:
    return check_report(files, opts).findings
