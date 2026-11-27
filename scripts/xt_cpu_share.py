"""Khay CPU dùng chung theo máy cho việc nặng (T-5082; D-629 khay, D-630 cổng tải; ADR-0112). Chỉ stdlib.

`jobs [--fallback X]` in số tiến trình một việc nặng được dùng. `run [--head] -- <lệnh>` chờ khay nhận, đăng ký, đặt
`XT_JOBS` theo phần được cấp, giới hạn nhân bằng affinity (khi hệ có và việc đã nhận ngân sách), hạ ưu tiên (`nice`) việc
không phải PR đầu hàng, chạy lệnh, xoá đăng ký, trả đúng mã thoát của lệnh (lệnh chết vì tín hiệu thì chết theo cùng tín
hiệu). `probe` in dấu khi khay dùng được (dev-task.sh hỏi trước khi bọc).

Công thức, với n = số nhân hiệu dụng (affinity, cắt theo quota cgroup v2): reserve = ceil(n/8) (0 khi n = 1), slots =
max(1, n // 4), usable = n − reserve. Mỗi việc chỉ lấy phần còn trống sau khi trừ mọi lease đang chạy.
Cổng tải: áp lực = MAX(CPU bận thật từ /proc/stat qua 0,5 s, loadavg 1 phút / n, PSI `some avg10` / 100), 1,0 = bão hoà;
đóng khi vượt ngưỡng cao (85 %), mở lại khi xuống dưới ngưỡng thấp (cao − 15 điểm); luôn nhận khi khay trống. Việc của
PR đầu hàng bỏ qua cổng tải và có tối đa một suất bổ sung trong ngân sách CPU. Bị từ chối thì chờ lùi dần, không hạn thời gian.

Fail-open về luồng: `XT_CPU_SHARE=off` (mặc định ở CI, `XT_CPU_SHARE=on` bật lại), nền tảng không có `fcntl` thì chạy lệnh như cũ. Khay hỏng dừng trước khi chạy lệnh;
khi lệnh đã chạy, khay giữ mã thoát của lệnh."""

from __future__ import annotations

import importlib
import json
import math
import os
import re
import signal
import stat
import subprocess
import sys
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from types import FrameType
from typing import Any

PROC = Path("/proc")
CGROUP = Path("/sys/fs/cgroup")
PSI = PROC / "pressure" / "cpu"
STAT = PROC / "stat"
SAMPLE = 0.5  # giây giữa hai lần đọc /proc/stat (khoảng lấy mẫu mức dùng CPU)
MARK = "xt-cpu-share-ok"
HIGH = 0.85  # D-630: ngưỡng cao mặc định, tỉ lệ so với mức bão hoà
GAP = 0.15  # ngưỡng thấp = cao − GAP (trễ, không dao động)
NICE = 5  # việc không phải PR đầu hàng chạy thấp hơn phiên tương tác và việc đầu hàng
FIRST_WAIT = 1.0
MAX_WAIT = 30.0
JOB = "job-"
WAIT = "wait-"
CLOSED = "gate-closed"
LOCK = "tray.lock"
JOBS_RE = re.compile(r"[1-9][0-9]{0,5}")  # như `test_jobs()` của dev-task.sh
INT_RE = re.compile(r"[0-9]{1,6}")
PID_RE = re.compile(r"[0-9]{1,10}")  # pid_max của Linux tới 4 194 304 (7 chữ số)
PCT_RE = re.compile(r"[0-9]{1,4}(?:\.[0-9]{1,3})?")
AVG10_RE = re.compile(r"^some\b.*?\bavg10=([0-9]{1,3}(?:\.[0-9]+)?)(?:\s|$)", re.M)
FORWARD = frozenset({"SIGINT", "SIGTERM", "SIGHUP"})
DEPTH = 64  # trần độ sâu khi lần ngược tiến trình cha


def log(msg: str) -> None:
    print(f"[xt-cpu] {msg}", file=sys.stderr, flush=True)


@dataclass(frozen=True)
class Shape:
    """Hình dạng máy cho khay: số nhân hiệu dụng, phần dành, số việc tối đa, phần dùng được, mã các nhân."""

    n: int
    reserve: int
    slots: int
    usable: int
    cpus: tuple[int, ...]


@dataclass(frozen=True)
class Seen:
    """Những gì khay thấy lúc một việc xin vào."""

    active: int
    slots: int
    head: bool
    head_waiting: bool
    pressure: float | None
    closed: bool


@dataclass(frozen=True)
class Job:
    cpus: tuple[int, ...]
    jobs: int
    nested: bool = False


def off(env: Mapping[str, str]) -> bool:
    """Khay và cổng tắt: `XT_CPU_SHARE=off`; hoặc đang ở CI (`CI` đặt, khác `false`/`0` — runner dành riêng cho một việc)
    mà không có `XT_CPU_SHARE=on`."""
    mode = env.get("XT_CPU_SHARE", "").strip().lower()
    if mode in ("off", "on"):
        return mode == "off"
    return env.get("CI", "").strip().lower() not in ("", "false", "0")


def env_int(env: Mapping[str, str], key: str, low: int) -> int | None:
    raw = env.get(key, "").strip()
    return int(raw) if INT_RE.fullmatch(raw) and int(raw) >= low else None


def env_ratio(env: Mapping[str, str], key: str) -> float | None:
    raw = env.get(key, "").strip()
    return float(raw) / 100 if PCT_RE.fullmatch(raw) else None


def user_jobs(env: Mapping[str, str]) -> int | None:
    raw = env.get("XT_JOBS", "")
    return int(raw) if JOBS_RE.fullmatch(raw) else None


def cpu_ids() -> list[int]:
    """Mã các nhân tiến trình được chạy: affinity khi hệ có (WSL/container có thể đã giới hạn), không thì cpu_count."""
    get = getattr(os, "sched_getaffinity", None)
    ids = sorted(get(0)) if get is not None else []
    return ids or list(range(os.cpu_count() or 1))


def cgroup_paths(proc: Path, root: Path) -> tuple[Path, ...]:
    """Nhóm cgroup v2 hiện hành và các nhóm cha nhìn thấy từ mount."""
    try:
        lines = (proc / "self" / "cgroup").read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()
    rel = next((Path(line[3:].lstrip("/")) for line in lines if line.startswith("0::")), None)
    if rel is None or ".." in rel.parts:
        return ()
    group = root / rel
    return (group, *(p for p in group.parents if p == root or root in p.parents))


def cpu_limit(group: Path) -> Fraction | None:
    try:
        limit, period = map(int, (group / "cpu.max").read_text(encoding="ascii").split())
    except (OSError, ValueError):
        return None
    return Fraction(limit, period) if limit > 0 and period > 0 else None


def quota(proc: Path = PROC, cgroup: Path = CGROUP) -> Fraction | None:
    limits = [value for group in cgroup_paths(proc, cgroup) if (value := cpu_limit(group)) is not None]
    return min(limits, default=None)


def memory_kib(proc: Path = PROC, cgroup: Path = CGROUP) -> int | None:
    """RAM còn khả dụng theo hệ điều hành và các hạn mức cgroup v2 đọc được."""
    headrooms = []
    try:
        available = re.search(r"^MemAvailable:[ \t]+([0-9]+) kB$", (proc / "meminfo").read_text(), re.M)
        if available:
            headrooms.append(int(available[1]))
    except OSError:
        pass
    for group in cgroup_paths(proc, cgroup):
        try:
            maximum = int((group / "memory.max").read_text(encoding="ascii"))
            current = int((group / "memory.current").read_text(encoding="ascii"))
        except (OSError, ValueError):
            continue
        if maximum >= 0 and current >= 0:
            headrooms.append(max(0, maximum - current) // 1024)
    return min(headrooms, default=None)


def shape(env: Mapping[str, str], ids: Sequence[int] | None = None, cores: Fraction | int | None = None) -> Shape:
    cpus = tuple(cpu_ids() if ids is None else ids)
    n = max(1, min(len(cpus), math.floor(cores)) if cores else len(cpus))
    reserve = env_int(env, "XT_CPU_RESERVE", 0)
    reserve = min(n - 1, (0 if n == 1 else math.ceil(n / 8)) if reserve is None else reserve)
    slots = env_int(env, "XT_CPU_SLOTS", 1) or max(1, n // 4)
    return Shape(n, reserve, slots, n - reserve, cpus)


def share(usable: int, active: int) -> int:
    """Phần nhân của một việc khi `active` việc đang chạy (kể cả việc này)."""
    return max(min(2, usable), min(math.ceil(2 * usable / 3), usable // max(1, active)))


def thresholds(env: Mapping[str, str]) -> tuple[float, float]:
    high = env_ratio(env, "XT_CPU_HIGH")
    high = HIGH if high is None else high
    low = env_ratio(env, "XT_CPU_LOW")
    return high, min(high, max(0.0, high - GAP) if low is None else low)


def psi(path: Path = PSI) -> float | None:
    """PSI `some avg10` (phần trăm thời gian có ít nhất một tác vụ chờ nhân trong 10 s) quy về [0, 1]; hỏng → None."""
    try:
        found = AVG10_RE.search(path.read_text(encoding="ascii"))
    except (OSError, UnicodeDecodeError):
        return None
    value = float(found[1]) / 100 if found else None
    return value if value is not None and value <= 1 else None


def loadavg(n: int) -> float | None:
    try:
        return os.getloadavg()[0] / n
    except (OSError, AttributeError):
        return None


def stat_sample(path: Path) -> tuple[int, int] | None:
    """(tổng, rảnh) từ dòng `cpu` tổng của /proc/stat — rảnh = idle + iowait; hỏng/thiếu → None."""
    try:
        fields = path.read_text(encoding="ascii").splitlines()[0].split()
        values = [int(v) for v in fields[1:9]]
    except (OSError, UnicodeDecodeError, IndexError, ValueError):
        return None
    if fields[0] != "cpu" or len(values) < 5 or min(values) < 0:
        return None
    return sum(values), values[3] + values[4]


def cpu_busy(path: Path = STAT, sleep: Callable[[float], None] = time.sleep) -> float | None:
    """Phần CPU bận thật giữa hai lần đọc /proc/stat cách nhau SAMPLE giây (khoảng lấy mẫu, không phải hạn của việc)."""
    first = stat_sample(path)
    if first is None:
        return None
    sleep(SAMPLE)
    second = stat_sample(path)
    if second is None:
        return None
    total, idle = second[0] - first[0], second[1] - first[1]
    return min(1.0, max(0.0, (total - idle) / total)) if total > 0 else None


def pressure(
    n: int, psi_path: Path = PSI, stat_path: Path = STAT, sleep: Callable[[float], None] = time.sleep
) -> float | None:
    """Áp lực = MAX(CPU bận thật, loadavg 1 phút / n, PSI some avg10 / 100), mỗi tín hiệu thiếu/hỏng thì bỏ; thiếu cả ba
    → None (bỏ qua cổng)."""
    found = [v for v in (cpu_busy(stat_path, sleep), loadavg(n), psi(psi_path)) if v is not None]
    return max(found) if found else None


def gate_closed(p: float | None, closed: bool, high: float, low: float) -> bool:
    """Trễ hai ngưỡng: đóng khi vượt `high`, mở khi dưới `low`; không đo được → giữ trạng thái."""
    if p is None:
        return closed
    return p > high or (closed and p >= low)


def decide(seen: Seen, high: float, low: float) -> tuple[bool, bool, str]:
    """(nhận?, trạng thái cổng sau lần đo, lý do từ chối)."""
    closed = gate_closed(seen.pressure, seen.closed, high, low)
    if seen.head_waiting and not seen.head:
        return False, closed, "nhường việc của PR đầu hàng đang chờ"
    slots = seen.slots + int(seen.head)
    if seen.active >= slots:
        return False, closed, f"khay đầy ({seen.active}/{slots} việc)"
    if seen.head or seen.active == 0 or seen.pressure is None or not closed:
        return True, closed, ""
    return False, closed, f"áp lực CPU {seen.pressure:.0%} (nhận lại khi dưới {low:.0%})"


def pick(cpus: Sequence[int], reserve: int, taken: Sequence[Sequence[int]], k: int) -> tuple[int, ...]:
    """Chọn nhân chưa được cấp, ngoài phần dành."""
    leased = {cpu for group in taken for cpu in group}
    return tuple(cpu for cpu in cpus[reserve:] if cpu not in leased)[:k]


def worker_budget(sh: Shape, live: Sequence[dict[str, Any]], requested: int | None) -> tuple[int, ...]:
    """Phần còn trống tính theo số worker đã cấp và các CPU khả dụng của lượt này."""
    usable = min([sh.usable, *(e.get("usable", sh.usable) for e in live)])
    remaining = usable - sum(e["jobs"] for e in live)
    cap = share(sh.usable, len(live) + 1)
    count = max(0, min(remaining, cap, requested or cap))
    return pick(sh.cpus, sh.reserve, [e["cpus"] for e in live], count)


def memory_workers(
    headroom_kib: int | None, reserve_mib: int, cost_mib: int, live: Sequence[dict[str, Any]]
) -> int | None:
    """Trừ toàn bộ giữ chỗ khi chưa đo được mức sử dụng theo từng cây tiến trình."""
    if headroom_kib is None:
        return None
    reserved = sum(int(e.get("memory_mib", 0) or e["jobs"] * cost_mib) for e in live)
    return max(0, (headroom_kib // 1024 - reserve_mib - reserved) // cost_mib)


def tray_dir(env: Mapping[str, str]) -> Path:
    base = env.get("XDG_CACHE_HOME", "")
    root = Path(base) if os.path.isabs(base) else Path(os.path.expanduser("~")) / ".cache"
    return root / "xt-cpu"


@contextmanager
def locked(d: Path) -> Iterator[None]:
    """Khoá độc quyền của khay (`flock`: tiến trình chết thì hệ tự nhả)."""
    fcntl = importlib.import_module("fcntl")
    d.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = d.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise ValueError(f"quyền thư mục khay CPU không hợp lệ: {d}")
    fd = os.open(d / LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def proc_stat(pid: int, proc: Path = PROC) -> list[str]:
    """Các trường sau `comm` của /proc/<pid>/stat: [0] trạng thái, [1] ppid, [19] thời điểm khởi động; không đọc được → []."""
    try:
        raw = (proc / str(pid) / "stat").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return raw.rpartition(")")[2].split()


def started(pid: int, proc: Path = PROC) -> str | None:
    fields = proc_stat(pid, proc)
    return fields[19] if len(fields) > 19 else None


def alive(pid: int, start: object, proc: Path = PROC) -> bool:
    """PID còn sống và đúng tiến trình đã đăng ký (cùng thời điểm khởi động khi /proc có); zombie tính là chết."""
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, OverflowError):
        return False  # PID vượt giới hạn int của hệ điều hành không thể là tiến trình đang sống
    except PermissionError:
        pass
    fields = proc_stat(pid, proc)
    if fields[:1] == ["Z"]:
        return False
    now = fields[19] if len(fields) > 19 else None
    return start is None or now is None or now == start


def ancestors(pid: int, proc: Path = PROC) -> set[int]:
    out: set[int] = set()
    for _ in range(DEPTH):
        fields = proc_stat(pid, proc)
        if len(fields) < 2 or not PID_RE.fullmatch(fields[1]) or int(fields[1]) <= 1:
            break
        pid = int(fields[1])
        out.add(pid)
    return out


def read_entry(f: Path) -> dict[str, Any] | None:
    try:
        e = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(e, dict) or type(e.get("pid")) is not int or e["pid"] <= 0:
        return None
    cpus = e.get("cpus")
    e["cpus"] = [c for c in cpus if type(c) is int] if isinstance(cpus, list) else []
    return e


def load(d: Path, prefix: str, proc: Path = PROC) -> list[dict[str, Any]]:
    """Chỉ dọn lease đã xác minh hết hạn. Báo lỗi nếu không đọc được ngân sách của lease."""
    live = []
    for f in sorted(d.glob(prefix + "*.json")):
        e = read_entry(f)
        if e is None or not alive(e["pid"], e.get("start"), proc):
            if e is None and prefix == JOB:
                raise ValueError(f"lease CPU hỏng: {f.name}")
            f.unlink(missing_ok=True)
            continue
        if prefix == JOB and (type(e.get("jobs")) is not int or e["jobs"] < 1):
            raise ValueError(f"lease CPU thiếu ngân sách: {f.name}")
        if "usable" in e and (type(e["usable"]) is not int or e["usable"] < 1):
            raise ValueError(f"lease CPU có ngân sách miền không hợp lệ: {f.name}")
        if "memory_mib" in e and (type(e["memory_mib"]) is not int or e["memory_mib"] < 0):
            raise ValueError(f"lease RAM không hợp lệ: {f.name}")
        live.append(e)
    return live


def put(d: Path, name: str, data: Mapping[str, object]) -> None:
    tmp = d / f".{name}.tmp"
    tmp.write_text(json.dumps(data), encoding="utf-8")
    os.replace(tmp, d / name)


def gated(active: int, slots: int, head: bool, head_waiting: bool) -> bool:
    """Kết quả có phụ thuộc cổng tải không — chỉ khi đó mới đo (đo CPU bận tốn SAMPLE giây)."""
    return 0 < active < slots and not head and not head_waiting


def attempt(
    d: Path,
    sh: Shape,
    head: bool,
    limits: tuple[float, float],
    proc: Path,
    measure: Callable[[int], float | None],
    requested: int | None = None,
    memory: tuple[int, int] | None = None,
) -> Job | str:
    """Một lần xin vào khay (dưới khoá): Job khi nhận, lý do khi phải chờ."""
    me = os.getpid()
    with locked(d):
        jobs = load(d, JOB, proc)
        parents = ancestors(me, proc)
        for active in jobs:
            if active["pid"] in parents:
                return Job((), min(active["jobs"], requested or active["jobs"]), nested=True)
        waits = [e for e in load(d, WAIT, proc) if e["pid"] != me]
        head_waiting = any(e.get("head") is True for e in waits)
        p = measure(sh.n) if gated(len(jobs), sh.slots, head, head_waiting) else None
        seen = Seen(len(jobs), sh.slots, head, head_waiting, p, (d / CLOSED).exists())
        ok, closed, why = decide(seen, *limits)
        if closed:
            (d / CLOSED).touch()
        else:
            (d / CLOSED).unlink(missing_ok=True)
        entry: dict[str, object] = {"pid": me, "start": started(me, proc), "head": head}
        cpus = worker_budget(sh, jobs, requested) if ok else ()
        if not cpus:
            why = why or "hết ngân sách CPU"
        cost, reserve = memory or (0, 0)
        if cpus and memory:
            cap = memory_workers(memory_kib(proc), reserve, cost, jobs)
            if cap is None:
                raise ValueError("không đo được RAM khả dụng")
            cpus = cpus[:cap]
            if not cpus:
                why = "thiếu RAM khả dụng"
        if not cpus:
            put(d, f"{WAIT}{me}.json", entry)
            return why
        k = len(cpus)
        put(d, f"{JOB}{me}.json", {**entry, "cpus": list(cpus), "jobs": k, "usable": sh.usable, "memory_mib": cost * k})
        (d / f"{WAIT}{me}.json").unlink(missing_ok=True)
        log(
            f"việc nặng: {k} tiến trình trên {len(cpus)}/{sh.n} nhân (dành {sh.reserve}; {len(jobs) + 1}/{sh.slots} việc)"
        )
        return Job(cpus, k)


def admit(
    env: Mapping[str, str],
    sh: Shape,
    head: bool,
    d: Path,
    proc: Path = PROC,
    measure: Callable[[int], float | None] = pressure,
    sleep: Callable[[float], None] = time.sleep,
) -> Job:
    """Chờ tới khi khay nhận: thử lại lùi dần (1 s, nhân đôi, trần 30 s), không hạn thời gian (BASE-GATE-005)."""
    limits, wait, last = thresholds(env), FIRST_WAIT, ""
    requested = user_jobs(env)
    cost = env_int(env, "XT_RESOURCE_RAM_PER_WORKER", 1)
    reserve = env_int(env, "XT_RESOURCE_RAM_RESERVE", 0)
    memory = (cost, 512 if reserve is None else reserve) if cost else None
    timeout = env_int(env, "XT_RESOURCE_WAIT_TIMEOUT", 1)
    deadline = time.monotonic() + timeout if timeout else None
    while True:
        got = attempt(d, sh, head, limits, proc, measure, requested, memory)
        if isinstance(got, Job):
            return got
        if got != last:
            log(f"chờ khay: {got}")
            last = got
        if deadline is not None:
            left = deadline - time.monotonic()
            if left <= 0:
                (d / f"{WAIT}{os.getpid()}.json").unlink(missing_ok=True)
                raise ValueError(f"hết thời gian chờ tài nguyên: {got}")
            wait = min(wait, left)
        sleep(wait)
        wait = min(wait * 2, MAX_WAIT)


def plain(cmd: Sequence[str], env: Mapping[str, str]) -> int:
    """Chạy lệnh như không có khay (môi trường nguyên vẹn): cùng mã thoát và tín hiệu như chạy thẳng."""
    return exit_code(spawn(cmd, env))


def limit(job: Job, head: bool) -> None:
    """Hạ ưu tiên việc không đầu hàng; ghim vào các CPU được cấp khi hệ có affinity. Lỗi → bỏ qua (fail-open)."""
    try:
        os.nice(0 if head else NICE)  # nice(0) không đổi gì: việc đầu hàng giữ ưu tiên của người gọi
    except OSError:
        pass
    setaff = getattr(os, "sched_setaffinity", None)
    if setaff is not None and job.cpus:
        try:
            setaff(0, job.cpus)
        except OSError:
            pass


def child_env(env: Mapping[str, str], job: Job) -> dict[str, str]:
    return dict(env, XT_CPU_SHARE_ID=str(os.getpid()), XT_JOBS=str(job.jobs))


def spawn(cmd: Sequence[str], env: Mapping[str, str]) -> int:
    """Chạy lệnh con (không shell; stdin/stdout/stderr kế thừa, không qua bộ đệm), chuyển SIGINT/SIGTERM/SIGHUP gửi tới
    tiến trình này cho nó — kể cả tín hiệu tới trước khi lệnh con kịp khởi động —, trả returncode (âm = chết vì tín
    hiệu); lệnh không có → 127, không thực thi được → 126."""
    children: list[subprocess.Popen[bytes]] = []
    pending: list[int] = []

    def forward(sig: int, _frame: FrameType | None) -> None:
        for child in children:
            child.send_signal(sig)
        if not children:
            pending.append(sig)

    old = {s: signal.signal(s, forward) for s in signal.Signals if s.name in FORWARD}
    try:
        sys.stdout.flush()
        try:
            children.append(subprocess.Popen(list(cmd), env=dict(env)))
        except OSError as e:
            log(f"không chạy được {cmd[0]!r}: {e}")
            return 127 if isinstance(e, FileNotFoundError) else 126
        for sig in pending:
            children[0].send_signal(sig)
        return children[0].wait()
    finally:
        for s, handler in old.items():
            signal.signal(s, handler)


def exit_code(rc: int, kill: Callable[[int, int], None] = os.kill) -> int:
    """Mã thoát của lệnh; lệnh chết vì tín hiệu → tự gửi cùng tín hiệu (người gọi thấy như chạy thẳng), không được → 128+n."""
    if rc >= 0:
        return rc
    try:
        signal.signal(-rc, signal.SIG_DFL)
    except (OSError, ValueError):
        pass
    kill(os.getpid(), -rc)
    return 128 - rc


def run(cmd: Sequence[str], env: Mapping[str, str], head: bool) -> int:
    if not probe(env) or env.get("XT_CPU_SHARE_ID"):
        return plain(cmd, env)
    tray = tray_dir(env)
    try:
        sh = shape(env, cores=quota())
        job = admit(env, sh, head, tray)
    except (OSError, ValueError) as e:
        log(f"khay CPU không dùng được ({type(e).__name__}: {e}); đặt XT_CPU_SHARE=off để chạy không qua khay")
        return 2
    if job.nested:
        return plain(cmd, child_env(env, job))
    limit(job, head)
    try:
        rc = spawn(cmd, child_env(env, job))
    finally:
        (tray / f"{JOB}{os.getpid()}.json").unlink(missing_ok=True)
    return exit_code(rc)


def jobs(env: Mapping[str, str], fallback: str) -> str:
    """Trả ngân sách đã cấp, hoặc ước lượng số worker khi chưa có lease."""
    if not probe(env):
        return fallback
    try:
        sh = shape(env, cores=quota())
        user = user_jobs(env)
        if env.get("XT_CPU_SHARE_ID"):
            return str(min(user or sh.n, sh.n))
        tray = tray_dir(env)
        with locked(tray):
            live = load(tray, JOB, PROC)
        parents = ancestors(os.getpid())
        for entry in live:
            if entry["pid"] in parents:
                return str(min(sh.n, entry["jobs"], user or sh.n))
        return str(max(1, len(worker_budget(sh, live, user))))
    except (OSError, ValueError):
        return "1"


def resource_info(env: Mapping[str, str]) -> dict[str, object]:
    limit = quota()
    sh = shape(env, cores=limit)
    mem = memory_kib()
    return {
        "available_cpus": len(sh.cpus),
        "cpu_quota": str(limit) if limit is not None else None,
        "worker_capacity": sh.usable,
        "cpu_reserve": sh.reserve,
        "slots": sh.slots,
        "memory_available_mib": mem // 1024 if mem is not None else None,
        "memory_per_worker_mib": env_int(env, "XT_RESOURCE_RAM_PER_WORKER", 1),
        "registry": str(tray_dir(env)),
        "managed": probe(env),
    }


def probe(env: Mapping[str, str]) -> bool:
    if off(env):
        return False
    try:
        importlib.import_module("fcntl")
    except ImportError:
        return False
    return True


USAGE = "dùng: xt_cpu_share.py jobs [--fallback X] | run [--head] -- <lệnh> [đối số…] | info | probe"


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    env = os.environ
    verb, rest = (args[0], args[1:]) if args else ("", [])
    if verb == "info" and not rest:
        print(json.dumps(resource_info(env)))
        return 0
    if verb == "probe" and not rest:
        if probe(env):
            print(MARK)
        return 0
    if verb == "jobs" and (not rest or (len(rest) == 2 and rest[0] == "--fallback")):
        print(jobs(env, rest[1] if rest else str(len(cpu_ids()))))
        return 0
    if verb == "run" and "--" in rest:
        opts, cmd = rest[: rest.index("--")], rest[rest.index("--") + 1 :]
        if cmd and set(opts) <= {"--head"}:
            return run(cmd, env, "--head" in opts or env.get("XT_CPU_HEAD") == "1")
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
