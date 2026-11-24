#!/usr/bin/env python3
"""Dựng artefact `.pyz` tất định của khung (ADR-0097, pha P1).

Artefact là một zipapp stdlib chứa `xt.py`, các module `xt_*.py`, gói `xt_app` và `VERSION` của khung; ở pha P5 đích sẽ
giữ tệp này thay cho mã nguồn chép vào `.xtemplates/scripts/`. Tất định: mục sắp theo tên, `mtime` và quyền cố định,
`ZIP_STORED` (đo P0: nạp từ zip không đổi độ trễ đáng kể, deflate chậm hơn và phụ thuộc phiên bản zlib), dòng shebang
cố định. Hai lần dựng cùng nguồn cho cùng `sha256`. Không gồm `app/` (giao diện tĩnh của `xt.py app` đọc tệp cạnh mã, chưa
chạy từ zip), `dev-task.sh`, guard và hook (pha P5).

    python3 scripts/xt_pack.py build --out DIST/xt.pyz [--strict]
    python3 scripts/xt_pack.py verify DIST/xt.pyz [--sha256 HEX]

Mã thoát: 0 đạt · 1 lệch bản dựng hoặc lệch ghim · 2 dùng sai (tệp thiếu, ghim sai dạng, nguồn thiếu/symlink).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import re
import sys
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple

ARTIFACT_SCRIPTS = (
    "xt.py",
    "xt_adapter.py",
    "xt_flow.py",
    "xt_acceptance.py",
    "xt_ops_setup.py",
    "xt_release_ops.py",
    "xt_deploy.py",
    "xt_distribution.py",
    "xt_scale.py",
    "xt_field.py",
)
PACKAGES = ("xt_app",)
SHEBANG = b"#!/usr/bin/env python3\n"
MAIN = b"import sys\nimport xt\n\nsys.exit(xt.main())\n"
FIXED_TIME = (1980, 1, 1, 0, 0, 0)
FILE_MODE = 0o100644 << 16
SHA256_RE = re.compile(r"[0-9a-f]{64}")


class PackError(Exception):
    """Nguồn hoặc đối số không dùng được (mã thoát 2)."""


def _read(p: Path) -> bytes:
    if p.is_symlink():
        raise PackError(f"không đóng gói liên kết tượng trưng: {p}")
    return p.read_bytes()


def entries(scripts: Path, strict: bool = False) -> List[Tuple[str, bytes]]:
    """(tên trong zip, nội dung) theo thứ tự tên. Thiếu `xt.py` là lỗi; module tuỳ chọn vắng thì bỏ qua, trừ khi
    `strict` (bản phát hành đòi đủ). `VERSION` của khung (cạnh `scripts/`) vào artefact khi có."""
    names = [n for n in ARTIFACT_SCRIPTS if (scripts / n).is_file() or (scripts / n).is_symlink()]
    if "xt.py" not in names:
        raise PackError(f"thiếu xt.py ở {scripts}")
    absent = [n for n in ARTIFACT_SCRIPTS if n not in names]
    if strict and absent:
        raise PackError(f"thiếu module: {', '.join(absent)}")
    for pkg in PACKAGES:
        names += [p.relative_to(scripts).as_posix() for p in (scripts / pkg).rglob("*.py")]
    out = [(n, _read(scripts / n)) for n in sorted(set(names))]
    if (scripts.parent / "VERSION").is_file():
        out.append(("VERSION", _read(scripts.parent / "VERSION")))
    out.append(("__main__.py", MAIN))
    return sorted(out)


def build_bytes(scripts: Path, strict: bool = False) -> bytes:
    buf = io.BytesIO()
    buf.write(SHEBANG)
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for name, data in entries(scripts, strict):
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = FILE_MODE
            info.create_system = 3
            z.writestr(info, data)
    return buf.getvalue()


def build(scripts: Path, out: Path, strict: bool = False) -> str:
    """Ghi artefact ra `out` nguyên tử (tệp tạm cạnh đích rồi đổi tên; không ghi qua liên kết tượng trưng), chmod 755,
    trả `sha256` của nó."""
    if out.is_symlink():
        raise PackError(f"đích là liên kết tượng trưng: {out}")
    data = build_bytes(scripts, strict)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(f".{out.name}.{os.getpid()}.tmp")
    tmp.write_bytes(data)
    tmp.chmod(0o755)
    os.replace(tmp, out)
    return hashlib.sha256(data).hexdigest()


def verify(artifact: Path, scripts: Path, sha256: Optional[str] = None) -> List[str]:
    """Lỗi nếu tệp không phải bản dựng tất định của `scripts` (hoặc lệch `sha256` ghim); rỗng là khớp. `sha256` đã
    khai (kể cả chuỗi rỗng) mà không đúng dạng 64 hex là lỗi dùng sai, không bị bỏ qua."""
    if sha256 is not None and not SHA256_RE.fullmatch(sha256.lower()):
        raise PackError("ghim sha256 phải là 64 ký tự hex")
    data = artifact.read_bytes()
    errors: List[str] = []
    if sha256 is not None and hashlib.sha256(data).hexdigest() != sha256.lower():
        errors.append("sha256 không khớp giá trị ghim")
    if data != build_bytes(scripts):
        errors.append("nội dung không khớp bản dựng tất định từ nguồn")
    return errors


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Dựng artefact .pyz tất định của khung (ADR-0097)")
    ap.add_argument("--scripts", type=Path, default=Path(__file__).resolve().parent, help="thư mục chứa xt.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="dựng artefact")
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--strict", action="store_true", help="đòi đủ mọi module (bản phát hành)")
    v = sub.add_parser("verify", help="kiểm artefact khớp nguồn")
    v.add_argument("artifact", type=Path)
    v.add_argument("--sha256", default=None)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "build":
            print(build(args.scripts, args.out, args.strict))
            return 0
        errors = verify(args.artifact, args.scripts, args.sha256)
    except (PackError, OSError) as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    for err in errors:
        print(f"✗ {err}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
