"""Bộ kiểm tĩnh theo loại (ADR-0099): `xt.py static-check <loại> [ĐƯỜNG…]`. Mỗi loại là một module `kind_<tên>.py` có `HELP`,
`SUFFIXES` (đuôi tệp khi quét thư mục; rỗng = mọi tệp), `OPTS`, tuỳ chọn `SNIFF` (`sniff(text)` hay `sniff(text, opts)`) và
`NAMES` (tên tệp được nhận khi quét thư mục), và `check(files, opts) -> list[Finding]`. Chỉ stdlib, tất định, chỉ đọc.
Danh sách `KINDS` là tường minh (không tự dò module) để test kiểm được và zipapp không phụ thuộc cách quét gói."""

from __future__ import annotations

import importlib
import inspect
import os
import re
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, TypeVar

KINDS: tuple[str, ...] = (
    "ac-trace",
    "credits",
    "dedup-leak",
    "design-evidence",
    "i18n",
    "llms-txt",
    "motion",
    "nfc",
    "pii-vn",
    "sbom",
    "srm",
    "tokens",
    "trace",
    "vex",
)
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


@dataclass
class CheckReport:
    findings: list[Finding]
    checked: dict[str, int]


_Item = TypeVar("_Item")


@dataclass
class JsonShape:
    """Ghi lỗi cấu trúc ở đúng trường, giữ các phần tử cùng mảng còn kiểm được."""

    path: str
    code: str
    findings: list[Finding]

    def error(self, field: str, expected: str) -> None:
        self.findings.append(Finding(self.path, 0, self.code, f"{field}: cần {expected}"))

    def mapping(self, field: str, value: object) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        self.error(field, "object")
        return {}

    def entries(self, field: str, value: object, item_type: type[_Item]) -> list[tuple[str, _Item]]:
        if not isinstance(value, list):
            self.error(field, "mảng")
            return []
        result = []
        for index, item in enumerate(value):
            where = f"{field}[{index}]"
            if isinstance(item, item_type):
                result.append((where, item))
            else:
                self.error(where, "object" if item_type is dict else "chuỗi")
        return result


def load(kind: str) -> ModuleType:
    """Module của `kind`; loại không có trong `KINDS` → `CheckError`."""
    if kind not in KINDS:
        raise CheckError(f"loại lạ {kind!r} — có: {', '.join(KINDS)}")
    return importlib.import_module(f"{__name__}.kind_{kind.replace('-', '_')}")


def read_text(path: Path) -> str | None:
    """Nội dung UTF-8 của tệp THƯỜNG; liên kết tượng trưng, FIFO/thiết bị, không đọc được, không phải UTF-8 hay quá
    `MAX_BYTES` → None (loại tự báo). Mở `O_NOFOLLOW|O_NONBLOCK` rồi `fstat`: tệp đặc biệt không làm treo hay ăn bộ nhớ
    (rà #776 🟠: `CREDITS.md` là liên kết tới thiết bị, FIFO tên `.md`)."""
    data = _read_prefix(path, MAX_BYTES + 1)
    try:
        return data.decode("utf-8") if data is not None and len(data) <= MAX_BYTES else None
    except UnicodeDecodeError:
        return None


def _read_prefix(path: Path, limit: int) -> bytes | None:
    """Tối đa `limit` byte đầu của tệp THƯỜNG (không theo liên kết, không mở FIFO/thiết bị); mọi lỗi mở hay đọc → None."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        return None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return None
        with os.fdopen(fd, "rb", closefd=False) as handle:
            return handle.read(limit)
    except OSError:  # vd EIO khi đọc `/proc/self/mem`: tệp không đọc được, không phải lỗi dùng sai
        return None
    finally:
        os.close(fd)


def read_head(path: Path, limit: int = MAX_BYTES + 1) -> str | None:
    """Phần đầu tệp để nhận diện sơ bộ (`SNIFF`), đúng bằng phần `check` sẽ đọc (`MAX_BYTES + 1` byte) nên dấu hiệu nằm sau
    vài chục KiB vẫn thấy. Giải mã UTF-8 (hay UTF-16 nếu có BOM) bỏ qua byte lỗi. Không đọc được (quyền, EIO) → None: tệp
    vẫn được giữ để `check` báo `…000` thay vì bị loại im lặng (rà #776 lượt hai 🟠)."""
    data = _read_prefix(path, limit)
    if data is None:
        return None
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16", errors="replace")
    return data.decode("utf-8", errors="replace")


def _sniffed(sniff: Callable[[str], bool], path: Path) -> bool:
    """Giữ tệp khi mang dấu hiệu đúng định dạng, hoặc khi không đọc được để nhận diện (để `check` báo `…000`)."""
    head = read_head(path)
    return head is None or sniff(head)


def _walk(folder: Path, suffixes: tuple[str, ...], only: frozenset[str] | None = None) -> list[Path]:
    found: list[Path] = []
    for here, dirs, names in os.walk(folder, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not Path(here, d).is_symlink())
        for name in sorted(names):
            path = Path(here, name)
            if (suffixes and path.suffix.lower() not in suffixes) or (only is not None and name not in only):
                continue
            try:
                regular = stat.S_ISREG(os.lstat(path).st_mode)  # lstat: liên kết và FIFO/thiết bị bị bỏ, không mở chúng
            except OSError:  # tệp biến mất giữa lúc liệt kê và lúc kiểm (đua với tiến trình khác)
                continue
            if regular:
                found.append(path)
    return found


def collect(
    paths: list[str],
    suffixes: tuple[str, ...],
    sniff: Callable[[str], bool] | None = None,
    names: frozenset[str] | None = None,
) -> list[Path]:
    """Tệp cần kiểm theo thứ tự ổn định: tệp nêu đích danh (bất kể đuôi, tên) và tệp trong thư mục có đuôi khớp. Khi quét
    thư mục, `names` (nếu có) chỉ giữ tệp đúng tên (`llms-txt` không kiểm mọi `.txt`), `sniff` (nếu có) giữ lại tệp mang
    dấu hiệu đúng định dạng — nên `sbom` không báo mọi `.json` của repo (rà #776). Liên kết tượng trưng hoặc đường dẫn
    không có → `CheckError` (không âm thầm bỏ qua đích người dùng đã nêu)."""
    out: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_symlink():
            raise CheckError(f"{raw}: liên kết tượng trưng — từ chối")
        if path.is_file():
            out.append(path)
        elif path.is_dir():
            found = _walk(path, suffixes, names)
            out.extend(p for p in found if sniff is None or _sniffed(sniff, p))
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


def sniff_for(module: ModuleType, opts: dict[str, str]) -> Callable[[str], bool] | None:
    """`SNIFF` của loại dưới dạng hàm một tham số: `sniff(text)` dùng nguyên; `sniff(text, opts)` (nhận diện phụ thuộc
    `--opt`, vd tên trường biến thể của `srm`) được gắn `opts` — để quét thư mục không bỏ im lặng tệp dùng tên tuỳ chỉnh."""
    found: Callable[..., object] | None = getattr(module, "SNIFF", None)
    if found is None:
        return None
    sniff = found
    with_opts = len(inspect.signature(sniff).parameters) >= 2

    def bound(text: str) -> bool:
        return bool(sniff(text, opts) if with_opts else sniff(text))

    return bound


def run_report(kind: str, paths: list[str], opts: dict[str, str]) -> CheckReport:
    """Chạy loại `kind` trên `paths`; kết quả sắp theo (đường dẫn, dòng, mã)."""
    module = load(kind)
    validate_opts(module, opts)
    files = collect(paths, module.SUFFIXES, sniff_for(module, opts), getattr(module, "NAMES", None))
    report: CheckReport
    if hasattr(module, "check_report"):
        report = module.check_report(files, opts)
    else:
        report = CheckReport(module.check(files, opts), {"files": len(files)})
    report.findings.sort(key=lambda f: (f.path, f.line, f.code))
    return report


def run(kind: str, paths: list[str], opts: dict[str, str]) -> list[Finding]:
    """API danh sách của ADR-0099."""
    return run_report(kind, paths, opts).findings
