"""Bộ phân giải `tool.json` (ADR-0097, pha P2): tên thật của công cụ trong dự án đích — gốc, tên tệp cấu hình, tiền tố biến
môi trường, số hợp đồng — thay cho chuỗi cứng. Chỉ stdlib. Mặc định y nguyên khung hiện tại: thiếu `tool.json` thì mọi giá
trị là mặc định; tệp có mà sai thì lỗi rõ (`ToolCfgError`), không đoán. Chưa nối vào `xt.py` (các pha sau thay từng chỗ cứng).

Đọc `tool.json` là đọc tệp do dự án đích commit, nên chặt: không theo liên kết (tệp lẫn thư mục gốc), chỉ tệp thường, trần
kích thước, khoá trùng/`null`/khoá lạ bị từ chối, JSON lồng sâu thành lỗi rõ chứ không làm sập tiến trình."""

from __future__ import annotations

import json
import os
import re
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ROOT = ".xtemplates"
DEFAULT_CONFIG = "xt.yaml"
DEFAULT_ENV_PREFIX = "XT_"
SUPPORTED_CONTRACT = 2  # khớp `contract` ở tests/fixtures/contract-surface.json
FILE_NAME = "tool.json"
MAX_BYTES = 1 << 20
KEYS = ("config", "env_prefix", "contract", "min_contract")
# Thư mục dấu chấm mà công cụ khác sở hữu: gốc của khung không được trùng (`--tool-name git` đặt công cụ vào `.git/`).
RESERVED_ROOTS = frozenset(
    {".git", ".github", ".claude", ".codex", ".agents", ".gemini", ".cursor", ".vscode", ".autopilot", ".idea"}
)

ROOT_RE = re.compile(r"\.[a-z0-9][a-z0-9._-]{0,63}")
CONFIG_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\.ya?ml")
PREFIX_RE = re.compile(r"[A-Z](?:[A-Z0-9_]{0,30}[A-Z0-9])?_")
_MISSING = object()


class ToolCfgError(Exception):
    """`tool.json` sai (không đọc được, sai kiểu, khoá lạ/trùng, hay hợp đồng cao hơn artefact hỗ trợ)."""


@dataclass(frozen=True)
class ToolCfg:
    root: str = DEFAULT_ROOT
    config: str = DEFAULT_CONFIG
    env_prefix: str = DEFAULT_ENV_PREFIX
    contract: int = SUPPORTED_CONTRACT
    min_contract: int = 1

    def env(self, name: str, environ: Mapping[str, str]) -> str | None:
        """Giá trị biến `<tiền tố><name>`; chưa đặt thì rơi về `XT_<name>` (đổi tên công cụ không làm biến cũ như
        `XT_GUARD_POLICY=strict` bị bỏ qua âm thầm). Không có ở cả hai → None."""
        value = environ.get(self.env_prefix + name)
        if value is None and self.env_prefix != DEFAULT_ENV_PREFIX:
            value = environ.get(DEFAULT_ENV_PREFIX + name)
        return value


def _text(raw: object, key: str, pattern: re.Pattern[str], default: str) -> str:
    if raw is _MISSING:
        return default
    if not isinstance(raw, str) or pattern.fullmatch(raw) is None:
        raise ToolCfgError(f"{FILE_NAME}: `{key}` không hợp lệ ({raw!r})")
    return raw


def _number(raw: object, key: str, default: int) -> int:
    if raw is _MISSING:
        return default
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
        raise ToolCfgError(f"{FILE_NAME}: `{key}` phải là số nguyên ≥ 1 ({raw!r})")
    return raw


def _check_root(root: str) -> str:
    if ROOT_RE.fullmatch(root) is None or root in RESERVED_ROOTS:
        raise ToolCfgError(f"{FILE_NAME}: `root` không hợp lệ hay trùng thư mục của công cụ khác ({root!r})")
    return root


def parse(data: object, root: str = DEFAULT_ROOT) -> ToolCfg:
    """Kiểm và dựng `ToolCfg` từ nội dung JSON đã giải mã; khoá lạ hoặc `null` bị từ chối để lỗi gõ sai không âm thầm về
    mặc định. `contract` (mặc định = hợp đồng artefact hỗ trợ) không được thấp hơn `min_contract`."""
    if not isinstance(data, dict):
        raise ToolCfgError(f"{FILE_NAME} phải là một đối tượng JSON")
    unknown = sorted(set(data) - set(KEYS))
    if unknown:
        raise ToolCfgError(f"{FILE_NAME}: khoá lạ {', '.join(repr(k) for k in unknown)}")
    cfg = ToolCfg(
        root=_check_root(root),
        config=_text(data.get("config", _MISSING), "config", CONFIG_RE, DEFAULT_CONFIG),
        env_prefix=_text(data.get("env_prefix", _MISSING), "env_prefix", PREFIX_RE, DEFAULT_ENV_PREFIX),
        contract=_number(data.get("contract", _MISSING), "contract", SUPPORTED_CONTRACT),
        min_contract=_number(data.get("min_contract", _MISSING), "min_contract", 1),
    )
    if cfg.min_contract > SUPPORTED_CONTRACT:
        raise ToolCfgError(
            f"{FILE_NAME}: `min_contract` {cfg.min_contract} cao hơn hợp đồng artefact hỗ trợ ({SUPPORTED_CONTRACT}) — nâng artefact"
        )
    if cfg.contract < cfg.min_contract:
        raise ToolCfgError(f"{FILE_NAME}: `contract` {cfg.contract} thấp hơn `min_contract` {cfg.min_contract}")
    return cfg


def _no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    out: dict[str, object] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"khoá trùng {key!r}")
        out[key] = value
    return out


def _read_bytes(path: Path) -> bytes | None:
    """Nội dung tệp thường (không theo liên kết, không mở FIFO/thiết bị, có trần); không có tệp → None."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    except OSError as exc:  # gồm ELOOP khi là liên kết tượng trưng, EACCES
        raise ToolCfgError(f"{FILE_NAME} không mở được: {exc.strerror or exc}") from exc
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
        os.close(fd)
        raise ToolCfgError(f"{FILE_NAME} không phải tệp thường hay quá {MAX_BYTES} byte")
    with os.fdopen(fd, "rb") as fh:
        return fh.read(MAX_BYTES + 1)


def load(base: Path, root: str = DEFAULT_ROOT) -> ToolCfg:
    """`tool.json` ở `<base>/<root>/`: thiếu → mặc định; `root` sai, liên kết tượng trưng (tệp hay thư mục gốc), không phải
    tệp thường, quá lớn, không đọc được hay không phải JSON hợp lệ → `ToolCfgError`."""
    _check_root(root)
    folder = base / root
    if folder.is_symlink():
        raise ToolCfgError(f"thư mục {root} là liên kết tượng trưng — từ chối đọc {FILE_NAME}")
    raw = _read_bytes(folder / FILE_NAME)
    if raw is None:
        return parse({}, root)
    if len(raw) > MAX_BYTES:  # tệp lớn lên giữa lúc kiểm và lúc đọc
        raise ToolCfgError(f"{FILE_NAME} quá {MAX_BYTES} byte")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates)
    except (ValueError, RecursionError) as exc:  # ValueError gồm JSONDecodeError, UTF-8 hỏng và khoá trùng
        raise ToolCfgError(f"{FILE_NAME} không phải JSON hợp lệ: {type(exc).__name__}") from exc
    return parse(data, root)
