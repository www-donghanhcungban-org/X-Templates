"""Bộ phân giải `tool.json` (ADR-0097, pha P2): tên thật của công cụ trong dự án đích — gốc, tên tệp cấu hình, tiền tố biến
môi trường, số hợp đồng — thay cho chuỗi cứng. Chỉ stdlib. Mặc định y nguyên khung hiện tại: thiếu `tool.json` thì mọi giá
trị là mặc định; tệp có mà sai thì lỗi rõ (`ToolCfgError`), không đoán. Chưa nối vào `xt.py` (các pha sau thay từng chỗ cứng)."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ROOT = ".xtemplates"
DEFAULT_CONFIG = "xt.yaml"
DEFAULT_ENV_PREFIX = "XT_"
SUPPORTED_CONTRACT = 2  # khớp `contract` ở tests/fixtures/contract-surface.json
FILE_NAME = "tool.json"
KEYS = ("config", "env_prefix", "contract", "min_contract")

ROOT_RE = re.compile(r"\.[a-z0-9][a-z0-9._-]{0,63}")
CONFIG_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\.ya?ml")
PREFIX_RE = re.compile(r"[A-Z][A-Z0-9]{0,31}_")


class ToolCfgError(Exception):
    """`tool.json` sai (không đọc được, sai kiểu, khoá lạ, hay hợp đồng cao hơn artefact hỗ trợ)."""


@dataclass(frozen=True)
class ToolCfg:
    root: str = DEFAULT_ROOT
    config: str = DEFAULT_CONFIG
    env_prefix: str = DEFAULT_ENV_PREFIX
    contract: int = SUPPORTED_CONTRACT
    min_contract: int = 1

    def env(self, name: str, environ: Mapping[str, str]) -> str | None:
        """Giá trị biến `<tiền tố><name>` trong `environ`; không có → None."""
        return environ.get(self.env_prefix + name)


def _text(raw: object, key: str, pattern: re.Pattern[str], default: str) -> str:
    if raw is None:
        return default
    if not isinstance(raw, str) or pattern.fullmatch(raw) is None:
        raise ToolCfgError(f"{FILE_NAME}: `{key}` không hợp lệ ({raw!r})")
    return raw


def _number(raw: object, key: str, default: int) -> int:
    if raw is None:
        return default
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
        raise ToolCfgError(f"{FILE_NAME}: `{key}` phải là số nguyên ≥ 1 ({raw!r})")
    return raw


def parse(data: object, root: str = DEFAULT_ROOT) -> ToolCfg:
    """Kiểm và dựng `ToolCfg` từ nội dung JSON đã giải mã; khoá lạ bị từ chối để lỗi gõ sai không âm thầm về mặc định."""
    if not isinstance(data, dict):
        raise ToolCfgError(f"{FILE_NAME} phải là một đối tượng JSON")
    unknown = sorted(set(data) - set(KEYS))
    if unknown:
        raise ToolCfgError(f"{FILE_NAME}: khoá lạ {', '.join(unknown)}")
    cfg = ToolCfg(
        root=_text(root, "root", ROOT_RE, DEFAULT_ROOT),
        config=_text(data.get("config"), "config", CONFIG_RE, DEFAULT_CONFIG),
        env_prefix=_text(data.get("env_prefix"), "env_prefix", PREFIX_RE, DEFAULT_ENV_PREFIX),
        contract=_number(data.get("contract"), "contract", SUPPORTED_CONTRACT),
        min_contract=_number(data.get("min_contract"), "min_contract", 1),
    )
    if cfg.min_contract > SUPPORTED_CONTRACT:
        raise ToolCfgError(
            f"{FILE_NAME}: `min_contract` {cfg.min_contract} cao hơn hợp đồng artefact hỗ trợ ({SUPPORTED_CONTRACT}) — nâng artefact"
        )
    return cfg


def load(base: Path, root: str = DEFAULT_ROOT) -> ToolCfg:
    """`tool.json` ở `<base>/<root>/`: thiếu → mặc định; liên kết tượng trưng hoặc không đọc được hay không phải JSON → lỗi."""
    path = base / root / FILE_NAME
    if path.is_symlink():
        raise ToolCfgError(f"{FILE_NAME} là liên kết tượng trưng — từ chối đọc")
    if not path.exists():
        return parse({}, root)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ToolCfgError(f"{FILE_NAME} không đọc được: {exc}") from exc
    return parse(data, root)
