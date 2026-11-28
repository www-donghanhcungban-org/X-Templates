"""Đọc trọng số và chia shard kiểm thử (D-095)."""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Dict, Iterable, List


SHARD_DEFAULT_WEIGHT = 1.0  # file vắng/rỗng: mọi id cùng trọng số → phân hoạch trùng hệt chỉ số k mod N


def load_shard_weights(path: Path) -> Dict[str, float]:
    """`{"tests.test_x.Lop": giây}` từ `path`; file vắng → {} (mọi id lấy mặc định). JSON hỏng, không phải object,
    khoá không phải chuỗi hoặc giá trị không phải số hữu hạn ≥ 0 → ValueError (fail-closed: shard đỏ rõ)."""
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError as e:
        raise ValueError(f"không đọc được {path}: {e}") from e
    try:
        data = json.loads(raw)
    except ValueError as e:
        raise ValueError(f"{path} không phải JSON hợp lệ: {e}") from e
    if not isinstance(data, dict):
        raise ValueError(f'{path} phải là object {{"id": giây}}')
    out: Dict[str, float] = {}
    for key, val in data.items():
        ok = isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(val) and val >= 0
        if not ok:
            raise ValueError(f"{path}: trọng số của {key!r} phải là số giây hữu hạn ≥ 0 (nhận {val!r})")
        out[key] = float(val)
    return out


def shard_plan(ids: Iterable[str], weights: Dict[str, float], n: int) -> List[List[str]]:
    """Phân hoạch xác định `ids` thành `n` shard bằng tham lam LPT: sắp giảm dần theo trọng số (hoà → theo id), mỗi id
    vào shard có tổng nhẹ nhất (hoà → chỉ số nhỏ nhất). Id không có trong `weights` lấy trung vị của file (file rỗng →
    `SHARD_DEFAULT_WEIGHT`). Mọi shard tính cùng phân hoạch từ cùng đầu vào; chênh lệch tổng giữa hai shard bất kỳ
    ≤ trọng số lớn nhất (tính chất của lập lịch tham lam)."""
    default = statistics.median(weights.values()) if weights else SHARD_DEFAULT_WEIGHT
    order = sorted(set(ids), key=lambda t: (-weights.get(t, default), t))
    loads = [0.0] * n
    shards: List[List[str]] = [[] for _ in range(n)]
    for t in order:
        k = min(range(n), key=lambda j: (loads[j], j))
        loads[k] += weights.get(t, default)
        shards[k].append(t)
    # Giữ thứ tự LPT trong từng shard để xargs -P khởi chạy lớp lâu nhất trước.
    return shards
