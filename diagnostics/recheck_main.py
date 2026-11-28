import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

from profile_shard import command, snapshot


MAIN = "614cbe3ec7eb6b691b67df25e87c0de1b6bc539c"
FIRST = "tests.test_guard_d155.GlobCommandNameTest"
source = Path(sys.argv[1]).resolve()
output = Path(sys.argv[2]).resolve()
orders = sys.argv[3:]
assert sorted(orders) == ["baseline", "current"]
assert command(["git", "rev-parse", "HEAD"], cwd=source) == MAIN
assert platform.python_version() == "3.13.18"
assert command(["nproc"]) == "4"
output.mkdir(parents=True, exist_ok=True)
measurements = []
for order in orders:
    env = dict(os.environ, XT_MIN_TESTS="100")
    env.pop("XT_SHARD_FIRST", None)
    if order == "current":
        env["XT_SHARD_FIRST"] = FIRST
    command_line = ["scripts/dev-task.sh", "test-shard", "6", "8"]
    initial = snapshot()
    start = time.monotonic()
    proc = subprocess.run(command_line, cwd=source, env=env, capture_output=True, text=True, timeout=600)
    elapsed = time.monotonic() - start
    (output / f"{order}.log").write_text(proc.stdout + proc.stderr)
    if proc.returncode:
        print(proc.stdout + proc.stderr, file=sys.stderr)
    assert proc.returncode == 0
    assert "test-shard 6/8: 116/923 id" in proc.stdout + proc.stderr
    measurements.append({"order": order, "seconds": elapsed, "start": initial, "end": snapshot()})

(output / "profile.json").write_text(
    json.dumps(
        {
            "head": MAIN,
            "python": platform.python_version(),
            "cpu": json.loads(command(["lscpu", "--json"])),
            "measurements": measurements,
        },
        indent=2,
    )
    + "\n"
)
