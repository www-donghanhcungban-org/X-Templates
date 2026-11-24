"""Loại `sbom` (SEC-SUPPLY-012/028, CMP-LIC-003): kiểm tệp SBOM CycloneDX JSON (1.4–1.7). Báo: `SBM000` không phải JSON/CycloneDX
hợp lệ, `SBM001` thiếu metadata (timestamp, công cụ tạo, component gốc), `SBM002` thành phần thiếu name/version, `SBM003` thiếu
định danh (purl/cpe/swid), `SBM004` thiếu hashes (chỉ khi `--opt hashes=require`), `SBM005` tỷ lệ thành phần có licenses dưới
`--opt license_ratio=` (mặc định 0.99), `SBM006` AI-BOM: model thiếu version/hashes/licenses, `SBM007` không có dependencies."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import CheckError, Finding, read_text

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


def _flatten(items: object) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    stack = [items]
    while stack:
        cur = stack.pop()
        if isinstance(cur, list):
            for item in cur:
                if isinstance(item, dict):
                    out.append(item)
                    stack.append(item.get("components"))
    return out


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


def _meta(path: str, data: dict[str, Any]) -> list[Finding]:
    meta = data.get("metadata")
    meta = meta if isinstance(meta, dict) else {}
    miss = [key for key in ("timestamp", "tools", "component") if not meta.get(key)]
    if not miss:
        return []
    return [Finding(path, 0, "SBM001", f"metadata thiếu: {', '.join(miss)}")]


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


def _bom(path: str, data: dict[str, Any], opts: dict[str, str]) -> list[Finding]:
    found = _meta(path, data)
    comps = _flatten(data.get("components"))
    need_hashes = _need_hashes(opts)
    for comp in comps:
        found.extend(_component(path, comp, need_hashes))
    with_license = sum(1 for comp in comps if comp.get("licenses"))
    ratio = _ratio(opts)
    if comps and with_license / len(comps) < ratio:
        found.append(
            Finding(path, 0, "SBM005", f"chỉ {with_license}/{len(comps)} thành phần có licenses (cần ≥ {ratio})")
        )
    if not data.get("dependencies"):
        found.append(Finding(path, 0, "SBM007", "không có dependencies (quan hệ phụ thuộc)"))
    return found


def check(files: list[Path], opts: dict[str, str]) -> list[Finding]:
    found: list[Finding] = []
    for path in files:
        text = read_text(path)
        data = None if text is None else _load(text)
        if data is None:
            found.append(Finding(str(path), 0, "SBM000", "không phải JSON CycloneDX hợp lệ (hoặc quá lớn)"))
        else:
            found.extend(_bom(str(path), data, opts))
    return found
