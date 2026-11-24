"""Loại `sbom` (SEC-SUPPLY-012/028, CMP-LIC-003): kiểm tệp SBOM CycloneDX JSON (1.4–1.7). Báo: `SBM000` không phải JSON/CycloneDX
hợp lệ, `SBM001` thiếu metadata (timestamp, công cụ tạo, component gốc), `SBM002` thành phần thiếu name/version, `SBM003` thiếu
định danh (purl/cpe/swid), `SBM004` thiếu hashes (chỉ khi `--opt hashes=require`), `SBM005` tỷ lệ thành phần có licenses dưới
`--opt license_ratio=` (mặc định 0.99), `SBM006` AI-BOM: model thiếu version/hashes/licenses, `SBM007` không có dependencies."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from . import CheckError, CheckReport, Finding, JsonShape, read_text

HELP = "SBOM CycloneDX thiếu metadata, name/version, định danh, hash, license, AI-BOM hay dependencies"
SUFFIXES = (".json",)
DEFAULT_RATIO = 0.99
OPTS = ("hashes", "license_ratio")
HASH_MODES = ("require", "ignore")


def sniff(text: str) -> bool:
    """Nhận diện sơ bộ tệp CycloneDX khi duyệt thư mục."""
    return '"bomFormat"' in text


SNIFF = sniff


def _load(text: str) -> dict[str, Any] | None:
    try:
        data = json.loads(text)
    except (ValueError, RecursionError):
        return None
    if isinstance(data, dict) and data.get("bomFormat") == "CycloneDX":
        return data
    return None


def _components(shape: JsonShape, field: str, items: object) -> Iterator[tuple[str, dict[str, Any]]]:
    stack = list(reversed(shape.entries(field, items, dict)))
    while stack:
        where, comp = stack.pop()
        yield where, comp
        if "components" in comp:
            stack.extend(reversed(shape.entries(f"{where}.components", comp["components"], dict)))


def _component_fields(shape: JsonShape, where: str, comp: dict[str, Any]) -> None:
    if "swid" in comp:
        shape.mapping(f"{where}.swid", comp["swid"])
    shape.entries(f"{where}.hashes", comp.get("hashes", []), dict)
    for field, choice in shape.entries(f"{where}.licenses", comp.get("licenses", []), dict):
        if "license" in choice:
            shape.mapping(f"{field}.license", choice["license"])


def _ratio(opts: dict[str, str]) -> float:
    raw = opts.get("license_ratio", str(DEFAULT_RATIO))
    try:
        value = float(raw)
    except ValueError:
        raise CheckError(f"--opt license_ratio phải là số 0..1 (nhận {raw!r})") from None
    if not 0 <= value <= 1:
        raise CheckError(f"--opt license_ratio phải nằm trong 0..1 (nhận {raw!r})")
    return value


def _need_hashes(opts: dict[str, str]) -> bool:
    mode = opts.get("hashes", "ignore")
    if mode not in HASH_MODES:
        raise CheckError(f"--opt hashes chỉ nhận require hoặc ignore (nhận {mode!r})")
    return mode == "require"


def _meta(shape: JsonShape, data: dict[str, Any]) -> None:
    meta = shape.mapping("metadata", data.get("metadata", {}))
    miss = [key for key in ("timestamp", "tools", "component") if not meta.get(key)]
    if miss:
        shape.findings.append(Finding(shape.path, 0, "SBM001", f"metadata thiếu: {', '.join(miss)}"))
    if "component" in meta:
        root = shape.mapping("metadata.component", meta["component"])
        _component_fields(shape, "metadata.component", root)
        for field, comp in _components(shape, "metadata.component.components", root.get("components", [])):
            _component_fields(shape, field, comp)
    tools = meta.get("tools", [])
    if isinstance(tools, dict):
        for field, comp in _components(shape, "metadata.tools.components", tools.get("components", [])):
            _component_fields(shape, field, comp)
        shape.entries("metadata.tools.services", tools.get("services", []), dict)
    else:
        shape.entries("metadata.tools", tools, dict)


def _dependencies(shape: JsonShape, data: dict[str, Any]) -> None:
    deps = data.get("dependencies", [])
    if deps == []:
        shape.findings.append(Finding(shape.path, 0, "SBM007", "không có dependencies (quan hệ phụ thuộc)"))
    for field, dep in shape.entries("dependencies", deps, dict):
        for key in ("dependsOn", "provides"):
            shape.entries(f"{field}.{key}", dep.get(key, []), str)


def _ai(path: str, label: str, comp: dict[str, Any]) -> list[Finding]:
    if comp.get("type") != "machine-learning-model":
        return []
    miss = [key for key in ("version", "hashes", "licenses") if not comp.get(key)]
    if not miss:
        return []
    return [Finding(path, 0, "SBM006", f"model AI {label} thiếu: {', '.join(miss)}")]


def _component(path: str, comp: dict[str, Any], need_hashes: bool) -> list[Finding]:
    label = str(comp.get("name") or comp.get("bom-ref") or "?")
    found: list[Finding] = []
    miss = [key for key in ("name", "version") if not comp.get(key)]
    if miss:
        found.append(Finding(path, 0, "SBM002", f"thành phần {label} thiếu: {', '.join(miss)}"))
    if not any(comp.get(key) for key in ("purl", "cpe", "swid")):
        found.append(Finding(path, 0, "SBM003", f"thành phần {label} không có purl/cpe/swid"))
    if need_hashes and not comp.get("hashes"):
        found.append(Finding(path, 0, "SBM004", f"thành phần {label} thiếu hashes"))
    return found + _ai(path, label, comp)


def _bom(shape: JsonShape, data: dict[str, Any], need_hashes: bool, ratio: float) -> int:
    _meta(shape, data)
    count = with_license = 0
    for field, comp in _components(shape, "components", data.get("components", [])):
        count += 1
        _component_fields(shape, field, comp)
        shape.findings.extend(_component(shape.path, comp, need_hashes))
        with_license += bool(comp.get("licenses"))
    if count and with_license / count < ratio:
        shape.findings.append(
            Finding(shape.path, 0, "SBM005", f"chỉ {with_license}/{count} thành phần có licenses (cần ≥ {ratio})")
        )
    _dependencies(shape, data)
    return count


def check_report(files: list[Path], opts: dict[str, str]) -> CheckReport:
    report = CheckReport([], {"files": len(files), "components": 0})
    need_hashes, ratio = _need_hashes(opts), _ratio(opts)
    for path in files:
        text = read_text(path)
        data = None if text is None else _load(text)
        if data is None:
            report.findings.append(Finding(str(path), 0, "SBM000", "không phải JSON CycloneDX hợp lệ (hoặc quá lớn)"))
        else:
            shape = JsonShape(str(path), "SBM000", report.findings)
            report.checked["components"] += _bom(shape, data, need_hashes, ratio)
    return report


def check(files: list[Path], opts: dict[str, str]) -> list[Finding]:
    return check_report(files, opts).findings
