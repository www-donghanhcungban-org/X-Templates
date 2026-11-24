"""Loại `vex` (SEC-SUPPLY-031/030): kiểm tệp OpenVEX JSON. Báo: `VEX000` không phải JSON/OpenVEX hợp lệ, `VEX001` thiếu
author/timestamp/version ở mức tài liệu, `VEX002` statement thiếu vulnerability (name hoặc @id) hay products, `VEX003` status
ngoài tập hợp lệ, `VEX004` `not_affected` thiếu justification hợp lệ lẫn impact_statement, `VEX005` `affected` thiếu
action_statement."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from . import Finding, read_text

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


def _has_vuln(stmt: dict[str, Any]) -> bool:
    vuln = stmt.get("vulnerability")
    return isinstance(vuln, dict) and bool(vuln.get("name") or vuln.get("@id"))


def _statement(path: str, index: int, stmt: dict[str, Any]) -> list[Finding]:
    tag = f"statement #{index}"
    found: list[Finding] = []
    if not _has_vuln(stmt) or not stmt.get("products"):
        found.append(Finding(path, 0, "VEX002", f"{tag} thiếu vulnerability (name/@id) hoặc products"))
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
    return found


def _doc(path: str, data: dict[str, Any]) -> list[Finding]:
    found: list[Finding] = []
    miss = [key for key in ("author", "timestamp", "version") if data.get(key) in (None, "")]
    if miss:
        found.append(Finding(path, 0, "VEX001", f"tài liệu thiếu: {', '.join(miss)}"))
    statements = data.get("statements")
    for index, raw in enumerate(statements if isinstance(statements, list) else [], 1):
        found.extend(_statement(path, index, raw if isinstance(raw, dict) else {}))
    return found


def check(files: list[Path], opts: dict[str, str]) -> list[Finding]:
    found: list[Finding] = []
    for path in files:
        text = read_text(path)
        data = None if text is None else _load(text)
        if data is None:
            found.append(Finding(str(path), 0, "VEX000", "không phải JSON OpenVEX hợp lệ (hoặc quá lớn)"))
        else:
            found.extend(_doc(str(path), data))
    return found
