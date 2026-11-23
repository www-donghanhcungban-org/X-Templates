"""Đo chỉ đọc một tệp Python lớn (mặc định `.claude/hooks/guard.py`): chi phí compile, họ hàm theo tiền tố, cạnh gọi
giữa các họ và hằng dùng chung nhiều họ. Số đo cho việc quyết cụm tách và cụm nạp lười (ADR-0090, ADR-0091, T-3984).

Chỉ đọc: không ghi tệp, không chạy mã của tệp được đo. Cạnh gọi là xấp xỉ theo tên: tên cục bộ trùng tên định nghĩa
cấp tệp bị tính nhầm. Exit 0 khi đo được, 2 khi đối số hoặc tệp đầu vào không đọc được."""

from __future__ import annotations

import argparse
import ast
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

DEFAULT_PATH = ".claude/hooks/guard.py"
DEFAULT_REPEAT = 5
DEFAULT_TOP = 15

Definition = ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef


def family(name: str) -> str:
    """Họ của một tên: bỏ gạch dưới đầu rồi lấy đến gạch dưới kế; tên chỉ gồm gạch dưới giữ nguyên."""
    stripped = name.lstrip("_")
    return stripped.partition("_")[0] or name


def top_level_definitions(tree: ast.Module) -> list[Definition]:
    return [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]


def span(node: Definition) -> int:
    return (node.end_lineno or node.lineno) - node.lineno + 1


def referenced(node: ast.AST, known: frozenset[str]) -> set[str]:
    """Tên trong `known` được đọc (Load) ở bên trong `node`."""
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in known}


def declared_constants(tree: ast.Module) -> frozenset[str]:
    """Tên IN HOA gán trực tiếp ở cấp tệp (`NAME = …` hoặc `NAME: kiểu = …`); gán bộ (`a, B = …`) không tính."""
    names: set[str] = set()
    for node in tree.body:
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        names.update(t.id for t in targets if isinstance(t, ast.Name) and t.id.isupper())
    return frozenset(names)


def family_table(defs: list[Definition], fam_of: dict[str, str], total: int) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    lines: Counter[str] = Counter()
    for d in defs:
        counts[fam_of[d.name]] += 1
        lines[fam_of[d.name]] += span(d)
    rows = [
        {"family": f, "defs": counts[f], "lines": n, "share_pct": round(100 * n / max(total, 1), 1)}
        for f, n in lines.items()
    ]
    return sorted(rows, key=lambda r: (-r["lines"], r["family"]))


def cross_family_edges(defs: list[Definition], fam_of: dict[str, str]) -> list[dict[str, Any]]:
    known = frozenset(fam_of)
    edges: Counter[tuple[str, str]] = Counter()
    for d in defs:
        for name in referenced(d, known) - {d.name}:
            if fam_of[name] != fam_of[d.name]:
                edges[(fam_of[d.name], fam_of[name])] += 1
    rows = [{"from": a, "to": b, "edges": n} for (a, b), n in edges.items()]
    return sorted(rows, key=lambda r: (-r["edges"], r["from"], r["to"]))


def shared_constants(defs: list[Definition], fam_of: dict[str, str], constants: frozenset[str]) -> list[dict[str, Any]]:
    users: dict[str, set[str]] = defaultdict(set)
    for d in defs:
        for name in referenced(d, constants):
            users[name].add(fam_of[d.name])
    rows = [{"name": c, "families": sorted(f)} for c, f in users.items() if len(f) > 1]
    return sorted(rows, key=lambda r: (-len(r["families"]), r["name"]))


def compile_runs(source: str, name: str, repeat: int, clock: Callable[[], float]) -> list[float]:
    runs: list[float] = []
    for _ in range(repeat):
        start = clock()
        compile(source, name, "exec", dont_inherit=True)
        runs.append(clock() - start)
    return runs


def compile_summary(runs: list[float]) -> dict[str, Any]:
    ms = [r * 1000 for r in runs]
    return {"runs": len(ms), "median": statistics.median(ms), "min": min(ms), "max": max(ms)}


def profile(path: Path, repeat: int, clock: Callable[[], float], top: int = DEFAULT_TOP) -> dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    runs = compile_runs(source, str(path), repeat, clock)
    tree = ast.parse(source, str(path))
    defs = top_level_definitions(tree)
    fam_of = {d.name: family(d.name) for d in defs}
    lines = source.count("\n")
    return {
        "path": str(path),
        "bytes": len(source.encode("utf-8")),
        "lines": lines,
        "defs": len(defs),
        "compile_ms": compile_summary(runs),
        "families": family_table(defs, fam_of, sum(span(d) for d in defs))[:top],
        "edges": cross_family_edges(defs, fam_of)[:top],
        "shared_constants": shared_constants(defs, fam_of, declared_constants(tree))[:top],
    }


def render(result: dict[str, Any], path: Path) -> str:
    c = result["compile_ms"]
    out = [
        f"{path.name}: {result['lines']} dòng, {result['bytes']} B, {result['defs']} định nghĩa cấp tệp",
        f"compile ({c['runs']} lần): trung vị {c['median']:.1f} ms, nhỏ nhất {c['min']:.1f} ms, lớn nhất {c['max']:.1f} ms",
        "Họ hàm (theo số dòng):",
        *(
            f"  {f['family']:<12} {f['defs']:>4} định nghĩa {f['lines']:>6} dòng {f['share_pct']:>5.1f} %"
            for f in result["families"]
        ),
        "Cạnh gọi giữa các họ (nhiều nhất):",
        *([f"  {e['from']} -> {e['to']}  {e['edges']}" for e in result["edges"]] or ["  (không có)"]),
        "Hằng dùng chung nhiều họ:",
        *([f"  {s['name']}: {', '.join(s['families'])}" for s in result["shared_constants"]] or ["  (không có)"]),
    ]
    return "\n".join(out)


def positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"không phải số nguyên: {text!r}") from None
    if value < 1:
        raise argparse.ArgumentTypeError(f"phải ≥ 1: {value}")
    return value


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Đo chỉ đọc một tệp Python lớn (mặc định: guard của khung).")
    p.add_argument("--path", default=DEFAULT_PATH, help=f"tệp cần đo (mặc định {DEFAULT_PATH})")
    p.add_argument("--repeat", type=positive_int, default=DEFAULT_REPEAT, help="số lần đo thời gian compile")
    p.add_argument("--top", type=positive_int, default=DEFAULT_TOP, help="số hàng tối đa mỗi bảng")
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = Path(args.path)
    try:
        result = profile(path, args.repeat, time.perf_counter, args.top)
    except (OSError, SyntaxError, ValueError) as exc:
        print(f"không đọc được {path}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else render(result, path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
