import argparse
import concurrent.futures
import json
import os
import platform
import subprocess
import sys
import threading
import time
from pathlib import Path


HEAD = "3ed7abeb688faab4b31aa48e56fb414a4c89a5a7"


def command(parts, **kwargs):
    return subprocess.check_output(parts, text=True, **kwargs).strip()


def snapshot():
    cpu = Path("/proc/stat").read_text().splitlines()[0].split()[1:9]
    return {
        "time": time.monotonic(),
        "load": os.getloadavg(),
        "cpu_ticks": list(map(int, cpu)),
        "pressure": Path("/proc/pressure/cpu").read_text().strip(),
    }


def test_class(test_id, root, log_dir):
    start = time.monotonic()
    with (log_dir / f"{test_id}.log").open("w") as log:
        with subprocess.Popen(
            [sys.executable, "-m", "unittest", test_id], cwd=root, stdout=log, stderr=subprocess.STDOUT
        ) as child:
            _, status, usage = os.wait4(child.pid, 0)
            child.returncode = os.waitstatus_to_exitcode(status)
    return {
        "class": test_id,
        "started": start,
        "seconds": time.monotonic() - start,
        "cpu_seconds": usage.ru_utime + usage.ru_stime,
        "rss_kib": usage.ru_maxrss,
        "exit": child.returncode,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root, output = args.source.resolve(), args.output.resolve()
    assert command(["git", "rev-parse", "HEAD"], cwd=root) == HEAD
    assert platform.python_version() == "3.13.18"
    config = (root / "xt.yaml").read_text().splitlines()
    listing = next(line.removeprefix("test_list: ") for line in config if line.startswith("test_list: "))
    ids = command(["bash", "-o", "pipefail", "-c", listing], cwd=root)
    tests = command(
        [sys.executable, "scripts/xt.py", "test-shard-plan", "6", "8", "--weights", "tests/shard-weights.json"],
        cwd=root,
        input=ids + "\n",
    ).splitlines()
    assert len(tests) == len(set(tests)) == 116
    output.mkdir(exist_ok=True, parents=True)
    logs = output / "logs"
    logs.mkdir()
    count = int(command(["nproc"]))
    metadata = {
        "head": HEAD,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "image": os.environ.get("ImageVersion"),
        "workers": count,
        "cpu_affinity": sorted(os.sched_getaffinity(0)),
        "cpu": json.loads(command(["lscpu", "--json"])),
    }
    samples = [snapshot()]
    stop = threading.Event()

    def poll():
        while not stop.wait(1):
            samples.append(snapshot())

    monitor = threading.Thread(target=poll, daemon=True)
    monitor.start()
    start = time.monotonic()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
            results = list(executor.map(lambda name: test_class(name, root, logs), tests))
    finally:
        stop.set()
        monitor.join()
    samples.append(snapshot())
    metadata["seconds"] = time.monotonic() - start
    (output / "profile.json").write_text(
        json.dumps({"metadata": metadata, "classes": results, "load_samples": samples}, indent=2) + "\n"
    )
    for result in results:
        if result["exit"]:
            print((logs / f"{result['class']}.log").read_text(), file=sys.stderr)
    return int(any(result["exit"] for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
