"""Bộ kiểm tĩnh theo loại (ADR-0099): `xt.py static-check <loại> [ĐƯỜNG…]`. Mỗi loại là một module `kind_<tên>.py` có `HELP`,
`SUFFIXES` (đuôi tệp khi quét thư mục; rỗng = mọi tệp) và `check(files, opts) -> list[Finding]`. Chỉ stdlib, tất định, chỉ đọc.
Danh sách `KINDS` là tường minh (không tự dò module) để test kiểm được và zipapp không phụ thuộc cách quét gói."""

from __future__ import annotations

import importlib
import os
import re
import stat
from collections.abc import Callable
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
    """Nội dung UTF-8 của tệp THƯỜNG; liên kết tượng trưng, FIFO/thiết bị, không đọc được, không phải UTF-8 hay quá
    `MAX_BYTES` → None (loại tự báo). Mở `O_NOFOLLOW|O_NONBLOCK` rồi `fstat`: tệp đặc biệt không làm treo hay ăn bộ nhớ
    (rà #776 🟠: `CREDITS.md` là liên kết tới thiết bị, FIFO tên `.md`)."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        return None
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
        os.close(fd)
        return None
    with os.fdopen(fd, "rb") as handle:
        data = handle.read(MAX_BYTES + 1)
    try:
        return data.decode("utf-8") if len(data) <= MAX_BYTES else None
    except UnicodeDecodeError:
        return None


def _walk(folder: Path, suffixes: tuple[str, ...]) -> list[Path]:
    found: list[Path] = []
    for here, dirs, names in os.walk(folder, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not Path(here, d).is_symlink())
        for name in sorted(names):
            path = Path(here, name)
            if (not suffixes or path.suffix.lower() in suffixes) and stat.S_ISREG(os.lstat(path).st_mode):
                found.append(path)  # lstat: liên kết và FIFO/thiết bị bị bỏ, không mở chúng
    return found


def collect(paths: list[str], suffixes: tuple[str, ...], sniff: Callable[[str], bool] | None = None) -> list[Path]:
    """Tệp cần kiểm theo thứ tự ổn định: tệp nêu đích danh (bất kể đuôi) và tệp trong thư mục có đuôi khớp. Khi quét
    thư mục, `sniff` (nếu có) giữ lại tệp mang dấu hiệu đúng định dạng — nên `sbom` không báo mọi `.json` của repo (rà #776).
    Liên kết tượng trưng hoặc đường dẫn không có → `CheckError` (không âm thầm bỏ qua đích người dùng đã nêu)."""
    out: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_symlink():
            raise CheckError(f"{raw}: liên kết tượng trưng — từ chối")
        if path.is_file():
            out.append(path)
        elif path.is_dir():
            found = _walk(path, suffixes)
            out.extend(p for p in found if sniff is None or sniff(read_text(p) or ""))
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


CODE_RE = re.compile(r"[A-Z]{3}[0-9]{3}")


def validate_opts(module: ModuleType, opts: dict[str, str]) -> None:
    """Khoá `--opt` phải thuộc `OPTS` của loại; `ignore` chỉ nhận mã dạng `ABC123`. Gõ nhầm khoá không được âm thầm bỏ qua
    (rà #776 🟠: `hashes=required` tắt kiểm mà vẫn exit 0) — `CheckError`, mã thoát 2."""
    unknown = sorted(set(opts) - set(module.OPTS))
    if unknown:
        valid = ", ".join(module.OPTS) or "(không có)"
        raise CheckError(f"--opt lạ: {', '.join(unknown)} — loại này nhận: {valid}")
    for code in [c for c in opts.get("ignore", "").split(",") if c]:
        if CODE_RE.fullmatch(code) is None:
            raise CheckError(f"--opt ignore nhận mã dạng ABC123, không phải {code!r}")


def run(kind: str, paths: list[str], opts: dict[str, str]) -> list[Finding]:
    """Chạy loại `kind` trên `paths`; kết quả sắp theo (đường dẫn, dòng, mã)."""
    module = load(kind)
    validate_opts(module, opts)
    files = collect(paths, module.SUFFIXES, getattr(module, "SNIFF", None))
    return sorted(module.check(files, opts), key=lambda f: (f.path, f.line, f.code))
