"""P0: đo nạp guard.py từ tệp rời so với từ zip (stored / deflate). Chạy: python3 2026-11-24-zip-load-bench.py <guard.py> <N> <thư mục tạm>."""

import statistics
import subprocess
import sys
import time
import zipfile
from pathlib import Path

guard = Path(sys.argv[1])
n = int(sys.argv[2])
tmp = Path(sys.argv[3])
for name, comp in (("stored", zipfile.ZIP_STORED), ("deflate", zipfile.ZIP_DEFLATED)):
    with zipfile.ZipFile(tmp / f"g-{name}.pyz", "w", comp) as z:
        z.write(guard, "guard.py")

LOOSE = "import sys\np=sys.argv[1]\ncode=compile(open(p,'rb').read(),p,'exec',dont_inherit=True)\nm=type(sys)('guard')\nexec(code,m.__dict__)\n"
ZIP = (
    "import sys, zipfile\n"
    "p=sys.argv[1]\n"
    "code=compile(zipfile.ZipFile(p).read('guard.py'),p+'/guard.py','exec',dont_inherit=True)\n"
    "m=type(sys)('guard')\nexec(code,m.__dict__)\n"
)


def run(script: str, target: Path) -> list[float]:
    out = []
    for _ in range(n):
        t = time.perf_counter()
        subprocess.run([sys.executable, "-I", "-B", "-c", script, str(target)], check=True, capture_output=True)
        out.append((time.perf_counter() - t) * 1000)
    return out


rows = {
    "rời": run(LOOSE, guard),
    "zip stored": run(ZIP, tmp / "g-stored.pyz"),
    "zip deflate": run(ZIP, tmp / "g-deflate.pyz"),
}
for k, v in rows.items():
    v.sort()
    print(f"{k:12s} median {statistics.median(v):7.1f} ms  p95 {v[int(len(v) * 0.95) - 1]:7.1f} ms  min {v[0]:7.1f} ms")
print("kích thước:", {p.name: p.stat().st_size for p in tmp.glob("g-*.pyz")}, "guard.py", guard.stat().st_size)
print("python", sys.version.split()[0])
