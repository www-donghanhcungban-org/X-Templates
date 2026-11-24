"""Bộ kiểm tĩnh theo loại (ADR-0099): `xt.py static-check <loại> [ĐƯỜNG…]`. Mỗi loại là một module `kind_<tên>.py` có `HELP`,
`SUFFIXES` (đuôi tệp khi quét thư mục; rỗng = mọi tệp) và `check(files, opts) -> list[Finding]`. Chỉ stdlib, tất định, chỉ đọc.
Danh sách `KINDS` là tường minh (không tự dò module) để test kiểm được và zipapp không phụ thuộc cách quét gói."""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

KINDS: tuple[str, ...] = ("ac-trace", "credits", "motion", "nfc", "pii-vn", "sbom", "tokens", "trace", "vex")
SKIP_DIRS = frozenset({".git", "node_modules", ".venv", "venv", "__pycache__", ".mypy_cache", ".ruff_cache"})
MAX_BYTES = 2 * 1024 * 1024


class CheckError(Exception):
    """Dùng sai (loại lạ, đường dẫn không có hay là liên kết, `--opt` sai) — mã thoát 2, không phải "có phát hiện"."""


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    code: str
    message: str

    def as_dict(self) -> dict[str, object]:
        return {"path": self.path, "line": self.line, "code": self.code, "message": self.message}


def load(kind: str) -> ModuleType:
    """Module của `kind`; loại không có trong `KINDS` → `CheckError`."""
    if kind not in KINDS:
        raise CheckError(f"loại lạ {kind!r} — có: {', '.join(KINDS)}")
    return importlib.import_module(f"{__name__}.kind_{kind.replace('-', '_')}")


def read_text(path: Path) -> str | None:
    """Nội dung UTF-8 của tệp; không đọc được, không phải UTF-8 hay quá `MAX_BYTES` → None (loại tự báo)."""
    try:
        if path.stat().st_size > MAX_BYTES:
            return None
        return path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _walk(folder: Path, suffixes: tuple[str, ...]) -> list[Path]:
    found: list[Path] = []
    for here, dirs, names in os.walk(folder, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not Path(here, d).is_symlink())
        for name in sorted(names):
            path = Path(here, name)
            if not path.is_symlink() and (not suffixes or path.suffix.lower() in suffixes):
                found.append(path)
    return found


def collect(paths: list[str], suffixes: tuple[str, ...]) -> list[Path]:
    """Tệp cần kiểm theo thứ tự ổn định: tệp nêu đích danh (bất kể đuôi) và tệp trong thư mục có đuôi khớp. Liên kết tượng
    trưng hoặc đường dẫn không có → `CheckError` (không âm thầm bỏ qua đích người dùng đã nêu)."""
    out: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_symlink():
            raise CheckError(f"{raw}: liên kết tượng trưng — từ chối")
        if path.is_file():
            out.append(path)
        elif path.is_dir():
            out.extend(_walk(path, suffixes))
        else:
            raise CheckError(f"không thấy: {raw}")
    return out


def parse_opts(items: list[str]) -> dict[str, str]:
    """`--opt khoá=giá-trị` (lặp được) → dict; thiếu `=`, khoá rỗng hay khoá lặp → `CheckError`."""
    opts: dict[str, str] = {}
    for item in items:
        key, sep, value = item.partition("=")
        if not sep or not key or key in opts:
            raise CheckError(f"--opt cần dạng khoá=giá-trị, khoá không lặp ({item!r})")
        opts[key] = value
    return opts


def run(kind: str, paths: list[str], opts: dict[str, str]) -> list[Finding]:
    """Chạy loại `kind` trên `paths`; kết quả sắp theo (đường dẫn, dòng, mã)."""
    module = load(kind)
    files = collect(paths, module.SUFFIXES)
    return sorted(module.check(files, opts), key=lambda f: (f.path, f.line, f.code))
