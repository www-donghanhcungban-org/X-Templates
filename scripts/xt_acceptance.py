"""Kiểm phạm vi nghiệm thu đã review trước khi triển khai, dùng một commit Git làm mốc."""

import argparse
from collections import Counter
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import uuid
from types import ModuleType
from typing import Any, cast
import xml.etree.ElementTree as ET


SCOPE_FILE = "docs/autopilot/ACCEPTANCE.paths"


def git(root: Path, *args: str) -> bytes:
    env = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}
    env.update(
        GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0", GIT_GRAFT_FILE=os.devnull
    )
    return subprocess.check_output(
        ["git", "--no-replace-objects", "--literal-pathspecs", "-c", "core.fsmonitor=false", "-C", str(root), *args],
        env=env,
        stderr=subprocess.PIPE,
    )


def tracked_files(root: Path, baseline: str, path: str) -> dict[str, tuple[str, str]]:
    if not path or Path(path).as_posix() != path or Path(path).is_absolute() or ".." in Path(path).parts:
        raise ValueError(f"Đường dẫn phải tương đối từ gốc repo: {path!r}")
    entries = git(root, "ls-tree", "-r", "-z", "--full-tree", baseline, "--", path).split(b"\0")
    files = {}
    for entry in filter(None, entries):
        header, name = entry.split(b"\t", 1)
        mode, _, oid = header.decode("ascii").split()
        if mode not in ("100644", "100755"):
            raise ValueError(f"Mốc nghiệm thu phải chứa file thường: {os.fsdecode(name)!r}")
        files[os.fsdecode(name)] = (mode, oid)
    if not files:
        raise ValueError(f"Không có file đã review tại mốc cho {path!r}")
    return files


def matches(root: Path, name: str, mode: str, oid: str) -> bool:
    path = root / name
    if path.resolve() != path or not path.is_file():
        return False
    with path.open("rb") as stream:
        info = os.fstat(stream.fileno())
        if bool(info.st_mode & stat.S_IXUSR) != (mode == "100755"):
            return False
        digest = hashlib.new("sha256" if len(oid) == 64 else "sha1")
        digest.update(f"blob {info.st_size}\0".encode("ascii"))
        while chunk := stream.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest() == oid


def pinned_scope(root: Path, baseline: str) -> list[str]:
    lines = git(root, "cat-file", "blob", f"{baseline}:{SCOPE_FILE}").decode("utf-8").splitlines()
    paths = [line for line in lines if line and not line.startswith("#")]
    if not paths:
        raise ValueError(f"{SCOPE_FILE} thiếu đường dẫn đến bộ nghiệm thu")
    return [SCOPE_FILE, *paths]


def check(project: Path, baseline: str, paths: list[str]) -> dict[str, object]:
    root = Path(os.fsdecode(git(project, "rev-parse", "--show-toplevel")).rstrip("\n")).resolve()
    if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", baseline):
        raise ValueError("Cần SHA đầy đủ của commit nghiệm thu đã review")
    if git(root, "cat-file", "-t", baseline).strip() != b"commit":
        raise ValueError("Mốc nghiệm thu phải là commit")
    git(root, "merge-base", "--is-ancestor", baseline, "HEAD")
    source = "arguments" if paths else SCOPE_FILE
    paths = paths or pinned_scope(root, baseline)
    files = {}
    for scope in paths:
        files.update(tracked_files(root, baseline, scope))
    changed = {name for name, (mode, oid) in files.items() if not matches(root, name, mode, oid)}
    selections = (
        ["diff", "--no-ext-diff", "--no-textconv", "--name-only", "-z", baseline, "HEAD"],
        ["diff", "--no-ext-diff", "--no-textconv", "--name-only", "-z", "--cached", baseline],
        ["ls-files", "--others", "-z"],
    )
    for args in selections:
        entries = git(root, *args, "--", *paths).split(b"\0")
        changed.update(os.fsdecode(name) for name in entries if name)
    return {
        "schema": 1,
        "status": "changed" if changed else "unchanged",
        "baseline": baseline,
        "scope": paths,
        "scope_source": source,
        "reviewed_files": len(files),
        "changed": sorted(changed),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("command", choices=["check"])
    parser.add_argument("--base", required=True, help="SHA đầy đủ đã chốt trước công việc triển khai")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("paths", nargs="*", help=f"mặc định đọc {SCOPE_FILE} từ commit đã review")
    args = parser.parse_intermixed_args(argv)
    try:
        result = check(args.project, args.base, args.paths)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Không xác minh được mốc nghiệm thu: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True))
    return int(result["status"] != "unchanged")


LEDGER = "docs/autopilot/ACCEPTANCE.json"
MAX_FILES = 2000
MAX_BYTES = 5 * 1024 * 1024
SCENARIO = re.compile(r"\bS-\d{3,}\b")
HEADING = re.compile(r"^###\s+(S-\d{3,})\b", re.M)
HASH = re.compile("[0-9a-f]{64}")


def project_file(base: Path, name: str) -> Path:
    path = base / name
    if not name or Path(name).is_absolute() or ".." in Path(name).parts or path.resolve() != path:
        raise ValueError(f"Đường dẫn phải nằm trong dự án, không qua symlink: {name!r}")
    return path


def snapshot(base: Path, paths: list[str]) -> dict[str, tuple[str, set[str]]]:
    files: dict[str, tuple[str, set[str]]] = {}
    for name in paths:
        path = project_file(base, name)
        entries = path.walk(on_error=raise_walk_error) if path.is_dir() else [(path.parent, [], [path.name])]
        for directory, _, names in entries:
            for child in names:
                item = directory / child
                if item.is_symlink():
                    print(f"Bỏ qua symlink {item.relative_to(base)}", file=sys.stderr)
                    continue
                rel = item.relative_to(base).as_posix()
                if rel in files:
                    continue
                if not item.is_file() or item.stat().st_size > MAX_BYTES or len(files) >= MAX_FILES:
                    raise ValueError(f"{rel}: cần file thường ≤ 5 MiB, tối đa 2 000 file")
                raw = item.read_bytes()
                files[rel] = (
                    hashlib.sha256(raw).hexdigest(),
                    set(SCENARIO.findall(raw.decode("utf-8", errors="replace"))),
                )
    return files


def raise_walk_error(exc: OSError) -> None:
    raise exc


def _ledger(base: Path, core: ModuleType) -> dict[str, Any]:
    path = base / LEDGER
    if path.exists() or path.is_symlink():
        path = project_file(base, LEDGER)  # sổ có thật thì đường dẫn phải là đường thật, không qua symlink
    if not path.exists():
        if (
            any((p / ".git").exists() for p in (base, *base.parents))
            and core._git(base, "log", "-1", "--format=%H", "HEAD", "--", LEDGER).stdout.strip()
        ):
            raise ValueError(f"Thiếu sổ đã có trong Git: {LEDGER}")
        return {"schema": 1, "locks": [], "events": []}
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or set(doc) != {"schema", "locks", "events"} or doc["schema"] != 1:
        raise ValueError(f"Sổ {LEDGER} sai schema")
    if not isinstance(doc["locks"], list) or not isinstance(doc["events"], list):
        raise ValueError(f"Sổ {LEDGER} thiếu khoá/lịch sử")
    if (
        not doc["locks"]
        and core._git(base, "log", "-1", "-G", r'"A-[0-9]+"', "--format=%H", "HEAD", "--", LEDGER).stdout.strip()
    ):
        raise ValueError(f"Sổ {LEDGER} mất các khoá đã có trong Git")
    _validate_records(doc, core)
    return doc


def _validate_manifest(row: dict[str, Any]) -> None:
    if "testcases" not in row:
        return
    manifest = row["testcases"]
    if not isinstance(manifest, dict) or set(manifest) != set(row["files"]):
        raise ValueError(f"Sổ {LEDGER} có manifest sai")
    for name, cases in manifest.items():
        if (
            not isinstance(cases, list)
            or len(cases) != row["counts"][name]
            or any(
                not isinstance(c, list) or len(c) != 2 or not all(isinstance(x, str) for x in c) or not c[1].strip()
                for c in cases
            )
            or len({tuple(c) for c in cases}) != len(cases)
        ):
            raise ValueError(f"Sổ {LEDGER} có danh tính testcase sai")


def _validate_records(doc: dict[str, Any], core: ModuleType) -> None:
    ids: set[str] = set()
    specs: set[str] = set()
    owned: set[str] = set()
    for row in doc["locks"]:
        if not isinstance(row, dict) or set(row) - {"testcases"} != {
            "id",
            "spec",
            "scenarios",
            "paths",
            "files",
            "cmd_sha256",
            "cases",
            "counts",
            "author",
            "session",
            "locked_at",
            "head",
            "existing",
            "decisions_at_lock",
        }:
            raise ValueError(f"Sổ {LEDGER} có khoá sai schema")
        if not (
            isinstance(row["files"], dict)
            and row["files"]
            and isinstance(row["counts"], dict)
            and set(row["counts"]) == set(row["files"])
            and all(isinstance(n, int) and n >= 1 for n in row["counts"].values())
            and sum(row["counts"].values()) == row["cases"]
            and all(isinstance(v, str) and HASH.fullmatch(v) for v in row["files"].values())
            and isinstance(row["cmd_sha256"], str)
            and HASH.fullmatch(row["cmd_sha256"])
            and isinstance(row["id"], str)
            and re.fullmatch(r"A-\d{3,}", row["id"])
            and isinstance(row["spec"], str)
            and isinstance(row["author"], str)
            and row["author"].strip()
            and isinstance(row["paths"], list)
            and row["paths"]
            and all(isinstance(x, str) for x in row["paths"])
            and isinstance(row["scenarios"], list)
            and row["scenarios"]
            and all(isinstance(x, str) and SCENARIO.fullmatch(x) for x in row["scenarios"])
            and isinstance(row["decisions_at_lock"], list)
            and all(isinstance(x, str) for x in row["decisions_at_lock"])
            and isinstance(row["locked_at"], str)
            and core._parse_iso(row["locked_at"])
            and isinstance(row["session"], str)
            and isinstance(row["head"], str)
        ):
            raise ValueError(f"Sổ {LEDGER} có dữ liệu khoá không hợp lệ")
        _validate_manifest(row)
        if row["id"] in ids or row["spec"] in specs or owned.intersection(row["files"]):
            raise ValueError(f"Sổ {LEDGER} trùng khoá, SPEC hoặc quyền sở hữu file")
        ids.add(row["id"])
        specs.add(row["spec"])
        owned.update(row["files"])
    if not all(
        isinstance(e, dict)
        and isinstance(e.get("lock"), str)
        and e["lock"] in ids
        and e.get("event") in ("lock", "amend")
        for e in doc["events"]
    ):
        raise ValueError(f"Sổ {LEDGER} có sự kiện sai")
    if {e["lock"] for e in doc["events"] if e["event"] == "lock"} != ids:
        raise ValueError(f"Sổ {LEDGER} thiếu sự kiện khoá")


def required_specs(core: ModuleType, base: Path) -> set[str]:
    state = core.read_state(base) or {}
    if state and not state.get("active"):
        return set()
    plan = project_file(base, state.get("plan") or "docs/autopilot/PLAN.md")
    if not plan.exists() and not state:
        return set()
    required = set()
    visible = core._markdown_shown(plan.read_text(encoding="utf-8"))
    for link in re.findall(r"\]\(([^\s)]+\.md)(?:#[^)]*)?\)", visible):
        if not Path(link).name.startswith("SPEC-"):
            continue
        target = (plan.parent / link).resolve()
        target.relative_to(base)
        if re.search(
            r"^\|\s*(?:Trạng thái|Status)\s*\|[^\n]*\bApproved\b",
            core._markdown_shown(target.read_text(encoding="utf-8")),
            re.I | re.M,
        ):
            required.add(target.relative_to(base).as_posix())
    return required


def _scenarios(core: ModuleType, base: Path, spec: str) -> set[str]:
    ids = set(HEADING.findall(core._markdown_shown(project_file(base, spec).read_text(encoding="utf-8"))))
    if not ids:
        raise ValueError(f"{spec} thiếu tiêu đề scenario ### S-NNN")
    return ids


def _inputs(core: ModuleType, base: Path) -> tuple[list[str], str, str]:
    keys = core._xt_keys(base)
    return keys.get("acceptance_paths", "").split(), keys.get("acceptance", ""), keys.get("acceptance_report", "")


def _verify_row(
    core: ModuleType,
    base: Path,
    row: dict[str, Any],
    cmd: str,
    actual: dict[str, tuple[str, set[str]]],
    out: dict[str, Any],
) -> None:
    problems = out["problems"]
    rid = row["id"]
    out["locks"].append(rid)
    out["authors"][rid] = {"author": row["author"], "session": row["session"]}
    out["expected_cases"].update(row["counts"])
    if "testcases" not in row:
        out["legacy_locks"].append(rid)
    else:
        out["identity_binding"].update(row["testcases"])
    if core.cmd_sha256(cmd) != row["cmd_sha256"]:
        problems.append(f"{rid}: lệnh acceptance khác lúc khoá")
    for name, digest in row["files"].items():
        if name not in actual or actual[name][0] != digest:
            problems.append(f"{rid}: file lệch hoặc mất {name}")
    missing = _scenarios(core, base, row["spec"]).symmetric_difference(row["scenarios"])
    if missing:
        problems.append(f"{rid}: scenario thay đổi {', '.join(sorted(missing))}")


def verify(core: ModuleType, base: Path) -> dict[str, Any]:
    problems: list[str] = []
    out: dict[str, Any] = {
        "enabled": True,
        "ok": False,
        "problems": problems,
        "locks": [],
        "authors": {},
        "expected_cases": {},
        "legacy_locks": [],
        "identity_binding": {},
        "amendments": 0,
    }
    try:
        doc = _ledger(base, core)
        configured, cmd, _ = _inputs(core, base)
        locks = doc["locks"]
        out["enabled"] = bool(configured or locks)
        if out["enabled"]:
            if not locks:
                problems.append("chưa có bộ nghiệm thu khoá")
            all_paths = sorted(set(configured).union(*(row["paths"] for row in locks)))
            actual = snapshot(base, all_paths)
            for row in locks:
                _verify_row(core, base, row, cmd, actual, out)
            for name in sorted(set(actual) - set(out["expected_cases"])):
                problems.append(f"File chưa thuộc khoá: {name}")
            for spec in sorted(required_specs(core, base) - {row["spec"] for row in locks}):
                problems.append(f"SPEC đã Approved trong PLAN chưa có khoá: {spec}")
            out["amendments"] = sum(e["event"] == "amend" for e in doc["events"])
    except (OSError, ValueError, RuntimeError) as exc:
        problems.append(str(exc))
    out["ok"] = not problems
    return out


def _case_outcome(case: ET.Element) -> str:
    outcomes = [child.tag for child in case if child.tag in ("failure", "error", "skipped")]
    if (
        any(
            child.tag not in ("failure", "error", "skipped", "system-out", "system-err") or len(child) for child in case
        )
        or len(outcomes) > 1
    ):
        raise ValueError("JUnit testcase có kết quả hoặc cấu trúc mâu thuẫn")
    outcome = outcomes[0] if outcomes else "passed"
    aliases = {
        "passed": "passed",
        "pass": "passed",
        "failure": "failure",
        "failed": "failure",
        "error": "error",
        "skipped": "skipped",
    }
    for attr in ("status", "result"):
        value = case.get(attr)
        if value is not None and aliases.get(value.lower()) != outcome:
            raise ValueError("JUnit status/result không khớp kết quả")
    return outcome


class JUnitReader:
    def __init__(self, files: set[str]) -> None:
        self.files = files
        self.identities: dict[str, set[tuple[str, str]]] = {f: set() for f in files}
        self.failed: set[str] = set()
        self.skipped = False
        self.modules: dict[str, set[str]] = {}
        for name in files:
            mod = str(Path(name).with_suffix("")).replace("/", ".")
            self.modules.setdefault(mod, set()).add(name)
        self.module_max = max(map(len, self.modules), default=0)

    def file_for(self, case: ET.Element) -> str:
        name = case.get("file")
        classname = case.get("classname", "")
        if name is not None:
            candidate = Path(name).as_posix()
            matches = {candidate} & self.files
        else:
            matches = set()
            prefix = classname[: self.module_max + 1]
            for boundary in re.finditer(r"\.|\Z", prefix):
                matches.update(self.modules.get(prefix[: boundary.start()], ()))
        if len(matches) != 1:
            raise ValueError(f"JUnit không quy được testcase về đúng một file đã khoá: {name or classname}")
        return matches.pop()

    def case_result(self, case: ET.Element) -> Counter[str]:
        outcome = _case_outcome(case)
        classname, name = case.get("classname", ""), case.get("name", "")
        if not name.strip():
            raise ValueError("JUnit testcase thiếu tên")
        matched = self.file_for(case)
        identity = (classname, name)
        if identity in self.identities[matched]:
            raise ValueError("JUnit trùng danh tính testcase")
        self.identities[matched].add(identity)
        if outcome != "passed":
            self.failed.add(matched)
        self.skipped |= outcome == "skipped"
        total: Counter[str] = Counter(tests=1)
        if outcome != "passed":
            total[{"failure": "failures", "error": "errors", "skipped": "skipped"}[outcome]] += 1
        return total

    def visit(self, node: ET.Element, depth: int = 0) -> Counter[str]:
        if node.tag == "testcase":
            return self.case_result(node)
        depth += int(node.tag == "testsuite")
        if depth > 100:
            raise ValueError("JUnit lồng quá sâu")
        allowed = {"testsuite", "properties", "system-out", "system-err"}
        if node.tag == "testsuite":
            allowed.add("testcase")
        total: Counter[str] = Counter()
        for child in node:
            if child.tag not in allowed:
                raise ValueError(f"JUnit có phần tử sai vị trí: {child.tag}")
            if child.tag in ("testsuite", "testcase"):
                total.update(self.visit(child, depth))
            else:
                _metadata(child)
        _counters(node, total)
        return total


def _metadata(node: ET.Element) -> None:
    if node.tag == "properties":
        if any(p.tag != "property" or len(p) for p in node):
            raise ValueError("JUnit properties không hợp lệ")
    elif len(node):
        raise ValueError("JUnit metadata không hợp lệ")


def _counters(node: ET.Element, total: Counter[str]) -> None:
    for key in ("tests", "failures", "errors", "skipped"):
        value = node.get(key)
        if value is not None and (not re.fullmatch(r"[0-9]+", value) or int(value) != total[key]):
            raise ValueError(f"JUnit counter {key} không khớp")


def _read_report(raw: bytes, files: set[str]) -> JUnitReader:
    if len(raw) > MAX_BYTES:
        raise ValueError("JUnit vượt 5 MiB")
    root = None
    for event, node in ET.iterparse(BytesIO(raw), events=("start-ns", "start")):
        if event == "start-ns":
            raise ValueError("JUnit không hỗ trợ namespace")
        if root is None:
            root = node
    root = cast(ET.Element, root)
    if root.tag not in ("testsuite", "testsuites"):
        raise ValueError("acceptance_report phải là JUnit XML")
    reader = JUnitReader(files)
    reader.visit(root)
    return reader


def report_identities(raw: bytes, files: set[str]) -> tuple[dict[str, set[tuple[str, str]]], set[str]]:
    reader = _read_report(raw, files)
    return reader.identities, reader.failed


def report_counts(raw: bytes, files: set[str]) -> tuple[Counter[str], set[str]]:
    identities, failed = report_identities(raw, files)
    return Counter({f: len(cases) for f, cases in identities.items()}), failed


def read_report_bytes(path: Path) -> bytes:
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("JUnit vượt 5 MiB")
    return raw


def report_sha256(path: Path) -> str:
    return hashlib.sha256(read_report_bytes(path)).hexdigest()


def release_rows(
    core: ModuleType, base: Path, run: tuple[dict[str, str], dict[str, Any] | None]
) -> list[dict[str, str]]:
    out = verify(core, base)
    if not out["enabled"]:
        return []
    problems = out["problems"]
    if out["legacy_locks"]:
        problems.append(
            "Khoá cũ thiếu danh tính: " + ", ".join(out["legacy_locks"]) + "; cần amend với quyết định và reviewer"
        )
    row, report = run
    if row["result"] != "PASS" or not report or report["status"] != "PASS":
        problems.append("hàng acceptance và report JUnit phải PASS")
    elif not problems:
        try:
            raw = read_report_bytes(project_file(base, report["path"]))
            if hashlib.sha256(raw).hexdigest() != report["sha256"]:
                raise ValueError("report đã thay đổi sau khi chạy")
            floors = out["expected_cases"]
            identities, failed = report_identities(raw, set(floors))
            for f, n in floors.items():
                if identities[f] != {tuple(c) for c in out["identity_binding"][f]} or f in failed:
                    problems.append(f"{f}: đã chạy {len(identities[f])}/{n} ca, cần đúng danh tính và mọi ca xanh")
        except (OSError, ValueError, ET.ParseError) as exc:
            problems.append(str(exc))
    evidence = (
        "; ".join(problems) if problems else f"{', '.join(out['locks'])}: khớp danh tính ca đã khoá trên từng file"
    )
    return [core._release_row("acceptance_lock", "FAIL" if problems else "PASS", evidence)]


def review_paths(core: ModuleType, base: Path, ref: str | None, changed: list[str]) -> list[str]:
    """Xét phạm vi ở cả cây làm việc và nhánh đích, kể cả khi cấu hình mới bỏ khoá."""
    paths = {LEDGER}
    try:
        keys = [_inputs(core, base)[0], core._committed_xt_keys(base, ref).get("acceptance_paths", "").split()]
        paths.update(p for items in keys for p in items)
        disk = project_file(base, LEDGER)
        committed = core._git(base, "show", f"{ref}:./{LEDGER}", env=core._go_git_env()) if ref is not None else None
        sources = ([disk.read_text(encoding="utf-8")] if disk.exists() else []) + (
            [committed.stdout] if committed is not None and committed.returncode == 0 else []
        )
        for source in sources:
            for record in json.loads(source)["locks"]:
                paths.update(record["paths"])
                paths.update(record["files"])
                paths.add(record["spec"])
    except (ValueError, OSError, KeyError, TypeError):
        return changed
    patterns = core.prefixed_globs(sorted(paths), core.project_prefix())
    return [f for f in changed if any(f == p or f.startswith(p.rstrip("/") + "/") for p in patterns)]


def _decisions(core: ModuleType, base: Path) -> dict[str, tuple[str, str]]:
    decisions = {}
    for text in core.decision_texts(base, base / core.DECISIONS_LOG).values():
        sections = re.split(r"^###\s+(D-\d{3,})\b([^\n]*)\n", core._markdown_shown(text), flags=re.M)
        for rid, heading, body in zip(sections[1::3], sections[2::3], sections[3::3], strict=True):
            dates = re.findall(r"\d{4}-\d{2}-\d{2}T[^\s·]+", heading)
            decisions[rid] = (dates[0] if dates else "", heading + "\n" + body)
    return decisions


class GuardDenied(ValueError):
    pass


def _baseline(
    core: ModuleType, base: Path, cmd: str, report: str, available: set[str], selected: set[str], red: bool
) -> dict[str, list[list[str]]]:
    if core.gate_noop(cmd) or not report:
        raise ValueError("Cần khai acceptance và acceptance_report trong xt.yaml")
    path = project_file(base, report)
    before = path.stat() if path.exists() else None
    code, _ = core.run_gate_shell(cmd, base, core._record_timeout() or 1800)
    if code == 126:
        raise GuardDenied("Guard cấm lệnh acceptance")
    if not path.is_file() or (
        before and before.st_mtime_ns == path.stat().st_mtime_ns and before.st_ino == path.stat().st_ino
    ):
        raise ValueError("Thiếu report JUnit mới do lần chạy này sinh")
    reader = _read_report(read_report_bytes(path), available)
    identities, failed = reader.identities, reader.failed
    if reader.skipped:
        raise ValueError("Không thể khoá testcase bị skip")
    if any(not identities[f] for f in selected):
        raise ValueError(
            "Thiếu ca đã chạy cho file nghiệm thu: " + ", ".join(sorted(f for f in selected if not identities[f]))
        )
    if red and (not code or not failed.intersection(selected)):
        raise ValueError("Bộ nghiệm thu phải đỏ trên ca của SPEC trước khi viết mã")
    if not red and (bool(code) != bool(failed)):
        raise ValueError("Exit của lệnh nghiệm thu không khớp các ca lỗi trong JUnit")
    return {f: [list(c) for c in sorted(identities[f])] for f in sorted(selected)}


def _actor(
    args: argparse.Namespace,
    previous: dict[str, Any] | None,
    decisions: dict[str, tuple[str, str]],
    core: ModuleType,
    doc: dict[str, Any],
) -> tuple[str, str | None]:
    amend = args.action == "amend"
    actor = (args.reviewer if amend else args.author).strip()
    if not actor or actor.lower() == "self":
        raise ValueError("Tác giả/reviewer phải là một agent độc lập")
    decision = args.decision if amend else args.existing
    if decision is not None and decision not in decisions:
        raise ValueError(f"Quyết định chưa ghi trong sổ: {decision}")
    if amend:
        if not previous:
            raise ValueError(f"Khoá chưa tồn tại: {args.lock}")
        when, body = decisions[args.decision]
        stamp = core._parse_iso(when)
        if (
            not stamp
            or not core._parse_iso(previous["locked_at"]) <= stamp <= core._parse_iso(core.now_iso())
            or decision in previous["decisions_at_lock"]
            or not re.search(rf"\b{re.escape(args.lock)}\b", body)
        ):
            raise ValueError(f"{decision} phải ghi sau khi khoá và nhắc {args.lock}")
        if (
            actor == previous["author"]
            or not args.why.strip()
            or any(e.get("decision") == decision for e in doc["events"] if e["lock"] == args.lock)
        ):
            raise ValueError("Cần reviewer độc lập, lý do và quyết định mới cho lần sửa")
    return actor, decision


def update(core: ModuleType, base: Path, args: argparse.Namespace) -> str:
    base = base.resolve()
    root = Path(os.fsdecode(git(base, "rev-parse", "--show-toplevel")).strip())
    if (root / ".git").is_file():
        raise OSError("Chỉ phiên điều phối tại worktree chính được ghi sổ nghiệm thu")
    doc = _ledger(base, core)
    initial = json.dumps(doc, sort_keys=True)
    locks = doc["locks"]
    amend = args.action == "amend"
    previous = next((r for r in locks if (r["id"] == args.lock if amend else r["spec"] == args.spec)), None)
    decisions = _decisions(core, base)
    actor, decision = _actor(args, previous, decisions, core, doc)
    spec = previous["spec"] if previous else args.spec
    paths, cmd, report = _inputs(core, base)
    paths = sorted(set(paths) | set(previous["paths"] if previous else []))
    scenarios = _scenarios(core, base, spec)
    actual = snapshot(base, paths)
    owners = {f for r in locks if r is not previous for f in r["files"]}
    files = {
        f: digest for f, (digest, ids) in sorted(actual.items()) if f not in owners and ids.intersection(scenarios)
    }
    missing = scenarios.difference(*(actual[f][1] for f in files))
    if missing:
        raise ValueError("Thiếu nghiệm thu cho " + ", ".join(sorted(missing)) + " (mỗi file chỉ thuộc một khoá)")
    if previous and not amend:
        if (
            "testcases" in previous
            and previous["files"] == files
            and previous["cmd_sha256"] == core.cmd_sha256(cmd)
            and previous["scenarios"] == sorted(scenarios)
        ):
            return str(previous["id"])
        raise ValueError(f"{previous['id']} đã có, dùng amend")
    manifest = _baseline(core, base, cmd, report, set(actual) | owners, set(files), not amend and not decision)
    counts = {f: len(cases) for f, cases in manifest.items()}
    if (
        snapshot(base, paths) != actual
        or _scenarios(core, base, spec) != scenarios
        or _inputs(core, base)[1:] != (cmd, report)
    ):
        raise ValueError("Đầu vào nghiệm thu thay đổi trong lúc chạy")
    rid = previous["id"] if previous else f"A-{max((int(r['id'][2:]) for r in locks), default=0) + 1:03d}"
    now = core.now_iso()
    head = core._git_head(base)
    if not head:
        raise ValueError("Cần commit Git để khoá nghiệm thu")
    row = {
        "id": rid,
        "spec": spec,
        "scenarios": sorted(scenarios),
        "paths": paths,
        "files": files,
        "cmd_sha256": core.cmd_sha256(cmd),
        "cases": sum(counts.values()),
        "counts": counts,
        "testcases": manifest,
        "author": previous["author"] if previous else actor,
        "session": core.session_id() or os.environ.get("CODEX_THREAD_ID") or f"cli-{uuid.uuid4()}",
        "locked_at": now,
        "head": head,
        "existing": previous["existing"] if previous else decision,
        "decisions_at_lock": sorted(decisions),
    }
    with core._state_lock(base):
        if json.dumps(_ledger(base, core), sort_keys=True) != initial:
            raise ValueError("Sổ nghiệm thu vừa đổi, hãy chạy lại")
        if previous:
            locks[locks.index(previous)] = row
        else:
            locks.append(row)
        doc["events"].append(
            {
                "event": "amend" if amend else "lock",
                "lock": rid,
                "at": now,
                "by": actor,
                "decision": decision,
                "reviewer": actor if amend else None,
                "why": args.why if amend else None,
                "previous": previous,
            }
        )
        path = project_file(base, LEDGER)
        path.parent.mkdir(parents=True, exist_ok=True)
        core.write_atomic(path, json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    return str(rid)


def command(core: ModuleType, args: argparse.Namespace) -> int:
    base = core.project_dir().resolve()
    if args.action == "check":
        out = verify(core, base)
        if args.json:
            executors = sorted({r["executor"] for r in core.read_runs(base) if isinstance(r.get("executor"), str)})
            out["declared_executors"] = executors
            out["author_executor_overlap"] = [
                rid for rid, info in out["authors"].items() if info["author"] in executors
            ]
        messages = list(out["problems"])
        if out["legacy_locks"]:
            messages.append("Khóa thiếu danh tính: " + ", ".join(out["legacy_locks"]) + " — cần acceptance amend")
        print(json.dumps(out, ensure_ascii=False) if args.json else ("\n".join(messages) or "Nghiệm thu khớp"))
        return int(not out["ok"])
    try:
        print(update(core, base, args))
        return 0
    except GuardDenied as exc:
        print(exc, file=sys.stderr)
        return 126
    except (ValueError, ET.ParseError) as exc:
        print(exc, file=sys.stderr)
        return 1
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
