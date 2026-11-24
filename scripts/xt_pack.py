#!/usr/bin/env python3
"""Dựng artefact `.pyz` tất định của khung (ADR-0097, pha P1).

Artefact là một zipapp stdlib chứa `xt.py`, các module `xt_*.py` và gói `xt_app`; đích chỉ giữ tệp này thay cho mã
nguồn chép vào `.xtemplates/scripts/`. Tất định: mục sắp theo tên, `mtime` và quyền cố định, `ZIP_STORED` (đo P0: nạp từ
zip không đổi độ trễ đáng kể, deflate chậm hơn và phụ thuộc phiên bản zlib), dòng shebang cố định. Hai lần dựng cùng
nguồn cho cùng `sha256`. Không gồm `app/` (giao diện tĩnh của `xt.py app` đọc tệp cạnh mã, chưa chạy từ zip).

    python3 scripts/xt_pack.py build --out DIST/xt.pyz
    python3 scripts/xt_pack.py verify DIST/xt.pyz [--sha256 HEX]
"""

from __future__ import annotations

import argparse
import hashlib
import io
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


def entries(scripts: Path) -> List[Tuple[str, bytes]]:
    """(tên trong zip, nội dung) theo thứ tự tên; thiếu `xt.py` là lỗi, module tuỳ chọn vắng thì bỏ qua."""
    names = [n for n in ARTIFACT_SCRIPTS if (scripts / n).is_file()]
    if "xt.py" not in names:
        raise FileNotFoundError(f"thiếu xt.py ở {scripts}")
    for pkg in PACKAGES:
        names += [p.relative_to(scripts).as_posix() for p in (scripts / pkg).rglob("*.py")]
    out = [(n, (scripts / n).read_bytes()) for n in sorted(set(names))]
    out.append(("__main__.py", MAIN))
    return sorted(out)


def build_bytes(scripts: Path) -> bytes:
    buf = io.BytesIO()
    buf.write(SHEBANG)
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for name, data in entries(scripts):
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = FILE_MODE
            info.create_system = 3
            z.writestr(info, data)
    return buf.getvalue()


def build(scripts: Path, out: Path) -> str:
    """Ghi artefact ra `out` (chmod 755) và trả `sha256` của nó."""
    data = build_bytes(scripts)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    out.chmod(0o755)
    return hashlib.sha256(data).hexdigest()


def verify(artifact: Path, scripts: Path, sha256: str = "") -> List[str]:
    """Lỗi nếu tệp không phải bản dựng tất định của `scripts` (hoặc lệch `sha256` khai báo); rỗng là khớp."""
    data = artifact.read_bytes()
    errors: List[str] = []
    if sha256 and hashlib.sha256(data).hexdigest() != sha256:
        errors.append("sha256 không khớp giá trị ghim")
    if data != build_bytes(scripts):
        errors.append("nội dung không khớp bản dựng tất định từ nguồn")
    return errors


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scripts", type=Path, default=Path(__file__).resolve().parent, help="thư mục chứa xt.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="dựng artefact")
    b.add_argument("--out", type=Path, required=True)
    v = sub.add_parser("verify", help="kiểm artefact khớp nguồn")
    v.add_argument("artifact", type=Path)
    v.add_argument("--sha256", default="")
    args = ap.parse_args(argv)
    if args.cmd == "build":
        print(build(args.scripts, args.out))
        return 0
    errors = verify(args.artifact, args.scripts, args.sha256)
    for e in errors:
        print(f"✗ {e}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
