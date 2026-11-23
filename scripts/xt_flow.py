"""Đọc dòng công việc của repo sản phẩm từ sổ giai đoạn, Gate, nghiệm thu và biên nhận triển khai."""

from __future__ import annotations

import argparse
import json
import datetime
import math
import re
import sys
from pathlib import Path
from typing import Any, TypeGuard

if __name__ == "__main__":
    sys.dont_write_bytecode = True
    script_dir = str(Path(__file__).resolve().parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

import xt

Doc = dict[str, Any]


def elapsed(start: Any, end: Any) -> float | None:
    a, b = xt._deploy_utc(start), xt._deploy_utc(end)
    return (b - a).total_seconds() if a is not None and b is not None and b >= a else None


def stage_times(history: list[Doc], deployments: list[Doc]) -> list[Doc]:
    """Một dòng mỗi lần trình. Sổ cũ thiếu thời điểm vẫn giữ mẫu với giá trị null."""
    result: list[Doc] = []
    opened: Any = None
    for e in history:
        kind = e["event"]
        if kind in ("init", "adopt"):
            opened = e.get("at")
        elif kind == "submit":
            dev_seconds = [
                duration
                for roll in deployments
                if roll["env"] == "dev"
                and roll["result"] == "deployed"
                and roll["subject"]["head"] == e["sha"]
                and elapsed(opened, roll["started"]) is not None
                and elapsed(roll["finished"], e.get("at")) is not None
                and (duration := elapsed(opened, roll["finished"])) is not None
            ]
            result.append(
                {
                    "cycle": e["cycle"],
                    "stage": e["stage"],
                    "sha": e["sha"],
                    "submitted": e.get("at"),
                    "cycle_start_to_submit_seconds": elapsed(opened, e.get("at")),
                    "cycle_start_to_confirmed_dev_seconds": min(dev_seconds, default=None),
                    "outcome": "pending",
                    "submit_to_decision_seconds": None,
                    "decided_by": None,
                }
            )
        else:  # read_stage đã phát lại thứ tự submit → reopen/approve và kiểm SHA.
            result[-1].update(
                outcome=kind,
                submit_to_decision_seconds=elapsed(result[-1]["submitted"], e.get("at")),
                decided_by=e.get("by"),
            )
    return result


def pr_lanes(path: Path | None) -> Doc | None:
    """Đọc export REST pull requests, phân làn theo nhãn trên bản export. Không gọi GitHub."""
    if path is None:
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("--merged-prs cần mảng JSON từ API pulls của GitHub")
    groups: dict[str, list[float]] = {"parallel": [], "sequential": []}
    seen: set[int] = set()
    for pr in data:
        if not isinstance(pr, dict) or "merged_at" not in pr:
            raise ValueError("Thiếu merged_at trong export pulls")
        if pr["merged_at"] is None:
            continue
        number, labels = pr.get("number"), pr.get("labels")
        span = elapsed(pr.get("created_at"), pr["merged_at"])
        if type(number) is not int or number <= 0 or number in seen or span is None:
            raise ValueError("PR đã merge có số hoặc thời điểm không hợp lệ/trùng")
        if not isinstance(labels, list) or not all(
            isinstance(i, dict) and isinstance(i.get("name"), str) for i in labels
        ):
            raise ValueError("Thiếu nhãn đã quan sát của PR")
        seen.add(number)
        lane = "parallel" if any(i["name"] == "xt-parallel" for i in labels) else "sequential"
        groups[lane].append(span / 3600)
    return {k: {"samples": len(v), "hours": xt._quantiles(v)} for k, v in groups.items()}


def optimization(base: Path, head: str | None) -> Doc:
    cfg: Doc = {}
    blob = None
    problem = None
    try:
        if head:
            cfg, blob = xt._trial_config(base, head)
    except xt.TrialRefused as exc:
        problem = str(exc)
    decisions = [r for r in xt.trial_live(xt.trial_rows(base)) if r["event"] == "decide"]
    measured = []
    for row in decisions:
        change = xt._trial_change(row, "primary")
        if change is not None and math.isfinite(change):
            measured.append(
                {"trial": row["id"], "base_sha": row["base_sha"], "verdict": row["verdict"], "change_pct": change}
            )
    return {
        "head": head,
        "config_blob_at_head": blob,
        "config_problem": problem,
        "metric_unit": cfg.get("metric", {}).get("unit"),
        "target": cfg.get("target"),
        "recorded_trials": len(decisions),
        "recorded_kept": sum(r["verdict"] == "kept" for r in decisions),
        "primary_changes": measured,
    }


def _completed_step(base: Path, env_states: Doc) -> tuple[str, str, str]:
    targets = [name for name in xt._deploy_env_names(base) if name in ("prod", "production")]
    if not targets:
        return (
            "cycle-completed",
            "project-owner",
            "Chu kỳ đã kết thúc. Chủ dự án có thể chọn mục tiêu mới trước khi mở chu kỳ.",
        )
    for env in targets:
        if not env_states.get(env, {}).get("current"):
            return (
                "prepare-rollout",
                "coordinator",
                f"Sổ chưa xác nhận bản hiện hành ở {env}. Chạy xt.py release-check --json cho bản sau tối ưu, "
                f"xt.py admin-plan --json và rollout-drill --env {env}. Chuyển bằng chứng cho pipeline được ủy quyền theo runbook.",
            )
    return (
        "check-operations",
        "coordinator",
        f"Đối chiếu bản sau tối ưu với receipt hiện hành ở {', '.join(targets)}. Theo runbook, chạy xt.py ops-check "
        "cho từng môi trường với dữ liệu thực địa và ngưỡng SLO đã thống nhất trước khi tăng tải hay mở chu kỳ mới.",
    )


def next_action(base: Path, stage: Doc | None, facts: Doc, opt: Doc, env_states: Doc) -> Doc:
    def action(name: str, owner: str, reason: str) -> Doc:
        return {"action": name, "owner": owner, "reason": reason, "missing": []}

    if stage is None:
        return action(
            "stage-init",
            "coordinator",
            "Dự án mới chạy xt.py stage init. Dự án đang vận hành cần chủ dự án xác định giai đoạn để adopt.",
        )
    if stage["status"] == "completed":
        return action(*_completed_step(base, env_states))
    if stage["status"] == "awaiting_approval":
        observed = facts["stage"]
        if observed["changed"] != []:
            return action(
                "check-submission",
                "coordinator",
                "Chưa xác nhận được cây hiện tại khớp bản đã nộp. Đối chiếu xt.py stage status; nếu đã đổi, mở lại và trình đúng bản.",
            )
        keys = xt._xt_keys(base)
        if keys.get(xt.STAGE_APPROVAL_KEY) == xt.STAGE_AGENT_BY and stage["stage"] <= 1 + xt._ceiling(
            "stage_approval_max", keys
        ):
            return action(
                "check-approval-policy",
                "coordinator",
                f"Bản {observed['sha']} đang chờ. Đối chiếu tiêu chí giai đoạn {stage['stage']}, rồi chạy "
                f"xt.py stage approve --sha {observed['sha']} --note <bằng chứng>. Lệnh sẽ đọc quyền ở nhánh chính và kiểm đúng ứng viên.",
            )
        return action(
            "review-submission",
            "project-owner",
            f"Đối chiếu tiêu chí với bản {observed['sha']}. Duyệt đúng SHA hoặc yêu cầu sửa. Báo cáo offline không xác minh quyền tự duyệt từ remote.",
        )
    if stage["stage"] == 3 and facts["verdict"]["verdict"] == "inactive":
        if not opt["config_blob_at_head"]:
            return action(
                "measure-baseline",
                "coordinator",
                "Chọn mục tiêu có số đo và ghi bộ đo perf/trial.json lên nhánh mặc định trước khi chạy /optimize.",
            )
        return action(
            "optimize",
            "coordinator",
            "Chạy /optimize với PLAN giai đoạn 3. Dùng xt.py perf trial status để kiểm bộ đo trên đúng commit gốc trước khi chọn phép thử.",
        )
    step = xt.next_step(facts)
    if step["action"] == "signoff-package":
        return action(
            "review-release",
            "project-owner",
            "Ảnh chụp nghiệm thu khớp ứng viên. Chạy lại xt.py release-check --json và đối chiếu các mục chờ người trước khi ký.",
        )
    result = {k: step[k] for k in ("action", "reason", "missing", "key", "work")}
    result["owner"] = "project-owner" if step["action"] == "wait-approval" else "coordinator"
    return result


def release_rows(doc: Any) -> dict[str, Doc]:
    """Kiểm schema, đủ các hàng nền và kết luận từ cùng một snapshot. Caller đối chiếu ứng viên riêng."""
    if (
        not isinstance(doc, dict)
        or doc.get("schema") not in xt.RELEASE_SCHEMAS
        or not isinstance(doc.get("rows"), list)
        or xt._deploy_utc(doc.get("at")) is None
    ):
        raise ValueError("--release cần báo cáo đầy đủ từ release-check --json")
    rows = doc["rows"]
    if not all(
        isinstance(r, dict)
        and isinstance(r.get("id"), str)
        and r.get("level") in ("BLOCKER", "SHOULD")
        and (r.get("result") in ("PASS", "FAIL", "N/A") or (r.get("result"), r.get("level")) == ("WARN", "SHOULD"))
        for r in rows
    ):
        raise ValueError("Hàng nghiệm thu không hợp lệ")
    by_id = {r["id"]: r for r in rows}
    if len(by_id) != len(rows) or not set(xt.RELEASE_ROWS).issubset(by_id):
        raise ValueError("Thiếu hoặc trùng hàng trong báo cáo nghiệm thu")
    fails = [r["id"] for r in rows if r.get("level") == "BLOCKER" and r["result"] == "FAIL"]
    waived = doc.get("waived", {})
    waivable = {
        key for key, _ in xt.RELEASE_RUN_KEYS if by_id[key]["result"] == "N/A" and by_id[key]["level"] == "BLOCKER"
    }
    if not isinstance(waived, dict) or not set(waived) <= waivable:
        raise ValueError("Danh sách miễn không hợp lệ")
    human = [r["id"] for r in rows if r.get("level") == "BLOCKER" and r["result"] == "N/A" and r["id"] not in waived]
    verdict = "NO-GO" if fails else "GO (chờ người)" if human else "GO"
    if (doc.get("fails"), doc.get("human"), doc.get("verdict")) != (fails, human, verdict) or doc.get("go") is not (
        not fails
    ):
        raise ValueError("Kết luận của báo cáo không khớp các hàng nghiệm thu")
    return by_id


def bound_release(base: Path, path: str | None) -> Doc | None:
    if path is None:
        return None
    return bind_release_document(base, json.loads(Path(path).read_text(encoding="utf-8")))


def bind_release_document(base: Path, doc: Any) -> Doc:
    """Đối chiếu đúng snapshot caller đã đọc với checkout và nguồn bằng chứng cục bộ."""
    by_id = release_rows(doc)
    artifact_row, artifacts = xt._release_artifacts(base)
    tree, head, readable = xt._release_tree(base)
    subject, why = xt._release_subject(
        base, artifacts, head, tree_readable=readable, tree_clean=tree["result"] == "PASS"
    )
    if (
        not readable
        or why
        or not head
        or doc.get("head") != head
        or doc.get("subject") != subject
        or doc.get("artifacts") != artifacts
    ):
        raise ValueError("Snapshot release không khớp HEAD, cây mã hoặc artifact hiện tại; chạy lại release-check")
    if doc.get("waived", {}) != xt._human_na_waivers(base, doc["rows"], subject):
        raise ValueError("Miễn N/A không khớp chữ ký §5 của người trên ứng viên")
    # Các nguồn này có thể thay đổi dù cùng commit (sổ vòng không theo git hoặc sổ giai đoạn được miễn vân tay).
    local_rows = [tree, xt._release_stage(base), xt._release_verify(base), *xt._release_deploy(base, subject)]
    if artifact_row is not None:
        local_rows.append(artifact_row)
    for now in local_rows:
        prior = by_id.get(now["id"], {})
        if (prior.get("result"), prior.get("level")) != (now["result"], now["level"]):
            raise ValueError(f"Hàng {now['id']} đã đổi sau khi ghi báo cáo; chạy lại release-check")
    return {key: doc[key] for key in ("head", "fails", "human", "verdict")}


ESCAPE_WINDOW_DAYS = 14  # cửa sổ quan sát lỗi lọt sau merge (SPEC-slice-ledger §2.4)


def _slice_event(line: str) -> Doc | None:
    try:
        ev = json.loads(line)
    except ValueError:
        return None
    ok = (
        isinstance(ev, dict)
        and ev.get("schema") == 1
        and ev.get("kind") in xt.SLICE_KINDS
        and all(isinstance(ev.get(k), str) for k in ("slice", "ref"))
        and isinstance(ev.get("data"), dict)
        and xt._deploy_utc(ev.get("at")) is not None
    )
    return ev if ok else None


def read_slices(base: Path) -> tuple[list[Doc], int]:
    """(sự kiện hợp lệ của mọi sổ lát, số dòng hỏng). Dòng hỏng bị bỏ, không làm hỏng số khác."""
    events: list[Doc] = []
    invalid = 0
    folder = xt.state_dir(base) / xt.SLICES_SUBDIR
    for path in sorted(folder.glob("*.jsonl")) if folder.is_dir() else []:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, ValueError):
            invalid += 1
            continue
        for line in filter(str.strip, lines):
            ev = _slice_event(line)
            events += [ev] if ev else []
            invalid += ev is None
    return events, invalid


def _amount(value: Any) -> TypeGuard[float]:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def _cost_usd(data: Doc) -> float | None:
    """`usd` khai thẳng, hoặc token quy đổi bằng giá có nguồn và ngày; thiếu một phần → None (không đoán giá)."""
    if _amount(data.get("usd")):
        return float(data["usd"])
    price, tokens = data.get("price"), data.get("tokens")
    if not (isinstance(price, dict) and isinstance(tokens, dict) and price.get("source") and price.get("as_of")):
        return None
    total = 0.0
    for k in ("in", "out"):
        n, p = tokens.get(k), price.get(f"usd_per_mtok_{k}")
        if not (_amount(n) and _amount(p)):
            return None
        total += float(n) * float(p)
    return total / 1_000_000


def cost_per_slice(events: list[Doc]) -> tuple[Doc | None, str]:
    """{lát: USD}; mỗi `cost_id` (ref) tính một lần. Không có sự kiện → `no_source`; một khoản không quy đổi → `unpriced`."""
    costs: dict[str, Doc] = {}
    for ev in events:
        if ev["kind"] == "cost":
            costs.setdefault(ev["ref"], ev)
    if not costs:
        return None, "no_source"
    total: dict[str, float] = {}
    for ev in costs.values():
        usd = _cost_usd(ev["data"])
        if usd is None:
            return None, "unpriced"
        total[ev["slice"]] = total.get(ev["slice"], 0.0) + usd
    return {k: round(v, 6) for k, v in sorted(total.items())}, ""


def conflicted_rate(events: list[Doc]) -> tuple[float | None, str]:
    """Tỷ lệ PR từng thấy `mergeable: CONFLICTING` trên số PR có sự kiện `pr`."""
    prs: dict[str, bool] = {}
    for ev in events:
        if ev["kind"] == "pr":
            prs[ev["ref"]] = prs.get(ev["ref"], False) or ev["data"].get("mergeable") == "CONFLICTING"
    if not prs:
        return None, "no_events"
    return round(sum(prs.values()) / len(prs), 4), ""


def escaped(events: list[Doc], now: Any) -> tuple[Doc | None, str]:
    """Sự cố trỏ PR đã merge, trong cửa sổ 14 ngày, chỉ tính PR đã đóng cửa sổ; còn PR mở cửa sổ → kèm `window_open`."""
    merged: dict[str, Any] = {}
    for ev in events:
        if ev["kind"] == "merged":
            merged.setdefault(ev["ref"], xt._deploy_utc(ev["at"]))
    if not merged:
        return None, "no_events"
    window = datetime.timedelta(days=ESCAPE_WINDOW_DAYS)
    closed = {pr for pr, at in merged.items() if at + window <= now}
    if not closed:
        return None, "window_open"
    severity: dict[str, int] = {}
    for ev in events:
        pr, at = ev["data"].get("introduced_by"), xt._deploy_utc(ev["at"])
        if (
            ev["kind"] == "incident"
            and isinstance(pr, str)
            and pr in closed
            and merged[pr] <= at <= merged[pr] + window
        ):
            key = str(ev["data"].get("severity") or "unknown")
            severity[key] = severity.get(key, 0) + 1
    doc = {"closed_prs": len(closed), "open_prs": len(merged) - len(closed), "by_severity": severity}
    return doc, "window_open" if len(closed) < len(merged) else ""


def lead_time_hours(events: list[Doc]) -> tuple[Doc | None, str]:
    """{lát: giờ} từ `requirement` đầu tiên tới `deployed` production đầu tiên — theo đồng hồ, không cộng việc song song."""
    first: dict[tuple[str, str], Any] = {}
    for ev in events:
        kind = f"deployed:{ev['ref']}" if ev["kind"] == "deployed" and ev["ref"] != "production" else ev["kind"]
        at, key = xt._deploy_utc(ev["at"]), (ev["slice"], kind)
        first[key] = at if key not in first or at < first[key] else first[key]
    hours = {
        s: round((at - first[(s, "requirement")]).total_seconds() / 3600, 3)
        for (s, kind), at in sorted(first.items())
        if kind == "deployed" and (s, "requirement") in first
    }
    return (hours, "") if hours else (None, "no_events")


def slice_metrics(base: Path, as_of: str) -> tuple[Doc, Doc]:
    """(số đo đọc từ sổ lát, mã lý do cho số `null` và số dòng hỏng) — SPEC-slice-ledger."""
    events, invalid = read_slices(base)
    now = xt._deploy_utc(as_of)
    found = {
        "cost_usd_per_slice": cost_per_slice(events),
        "ever_conflicted_pr_rate": conflicted_rate(events),
        "escaped_after_merge": escaped(events, now),
        "lead_time_hours": lead_time_hours(events),
    }
    reasons = {k: why for k, (_, why) in found.items() if why}
    return {k: v for k, (v, _) in found.items()}, {"invalid_lines": invalid, "null_or_partial": reasons}


def report(base: Path, args: argparse.Namespace) -> Doc:
    if not base.is_dir():
        raise ValueError(f"Thư mục dự án không tồn tại: {base}")
    stage = xt.read_stage(base)
    state = xt.read_state(base)
    if state is None and (xt.state_dir(base) / "state.json").exists():
        raise ValueError("state.json không đọc được; khôi phục sổ vòng trước khi chọn bước kế")
    prs = xt._read_prs(args.prs)
    release = {"release": bound_release(base, args.release)}
    objective = xt.NEXT_STEP_OBJECTIVES[int(bool(stage and stage["stage"] == 2))]
    facts = xt.next_step_facts(base, state or {}, xt.AUDIT_STATUS_DEFAULT, prs, objective, release, offline=True)
    current = {k: stage[k] for k in ("cycle", "stage", "status")} if stage else None
    observed = facts["stage"]
    if current != ({k: observed.get(k) for k in ("cycle", "stage", "status")} if observed else None):
        raise ValueError("Sổ giai đoạn đã thay đổi trong lúc đọc; chạy lại")
    opt = optimization(base, facts["head"])
    log = xt.read_deploy_ledger(base)
    loops = xt.loop_stats(base, all_loops=True)
    samples = loops["runs"]
    episode = (state or {}).get("episode")
    cost = episode.get("cost_usd") if isinstance(episode, dict) else None
    if isinstance(cost, bool) or not isinstance(cost, (float, int)) or not 0 <= cost <= sys.float_info.max:
        cost = None
    as_of = xt.now_iso()
    ledger, ledger_cov = slice_metrics(base, as_of)
    waiting = {
        key: elapsed(item.get("at"), as_of) if isinstance(item, dict) else None
        for key, item in xt._deferred(state or {}).items()
    }
    resolved = xt._interventions(state or {}, "resolved")
    stats = xt._deploy_metrics(log)
    for m in stats.values():
        if not m["runs"]:
            m["rollback_rate"] = None
    return {
        "schema": 1,
        "observed_at": as_of,
        "stage": current,
        "next": next_action(base, stage, facts, opt, log["envs"]),
        "metrics": {
            "stage_submissions": stage_times(stage["history"], log["events"]) if stage else [],
            "gate_runs": samples,
            "tasks_observed": loops["task_count"],
            "failed_gate_runs": loops["failed_runs"] if samples else None,
            "time_to_first_green_hours": loops["time_to_green_hours"],
            "first_pass_rate": loops["first_pass_rate"],
            "resolved_interventions": len(resolved) if state is not None else None,
            "resolved_human_waits": [
                {"task": item.get("id"), "seconds": elapsed(item.get("deferred_at"), item.get("at"))}
                for item in resolved
            ],
            "pending_human_seconds_by_task": waiting if state is not None else None,
            "reported_ci_episode_cost_usd": cost,
            "deploy_by_env": stats,
            "pr_open_to_merge": pr_lanes(args.merged_prs),
            **ledger,
            "optimization": opt,
        },
        "coverage": {
            "loop": f".autopilot/runs.jsonl: {samples} lượt Gate hợp lệ còn giữ trên checkout",
            "deploy": f"{xt.DEPLOY_LEDGER}: {len(log['events'])} receipt còn giữ",
            "approval": "Khoảng từ submit tới quyết định tính theo timestamp có UTC của từng lần trình.",
            "cost": "episode.cost_usd chỉ phản ánh phần chi phí sửa CI được khai; chi phí theo lát đọc từ sổ lát.",
            "integration": "Lead time của PR lấy từ --merged-prs; xung đột, lỗi lọt và lead time lát đọc từ sổ lát.",
            "slices": ledger_cov,
            "human": "Thời gian chờ theo từng việc defer → resolve. Việc cũ thiếu timestamp có giá trị null; các việc có thể chờ đồng thời.",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--prs", help="JSON pr next --json của các PR trong đợt")
    parser.add_argument("--release", help="Báo cáo release-check --json đã chạy")
    parser.add_argument("--merged-prs", type=Path, help="Mảng REST pulls có number, created_at, merged_at và labels")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true")
    output.add_argument("--github-summary", action="store_true", help="Markdown tóm tắt ra stdout cho GitHub Actions")
    args = parser.parse_args(argv)
    try:
        out = report(args.project.resolve(), args)
    except (ValueError, OSError, RecursionError, xt.StageError, xt.DeployError, xt.TrialRefused) as exc:
        message = (
            "Không thể tổng hợp tiến độ; chạy lại với --json để xem lỗi."
            if args.github_summary
            else f"Không thể đọc luồng: {exc}"
        )
        print(message, file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(out, ensure_ascii=False, allow_nan=False))
    elif args.github_summary:
        print(github_summary(out))
    else:
        print(f"{out['next']['action']} ({out['next']['owner']}) — {out['next']['reason']}")
        print(f"Gate: {out['metrics']['gate_runs']} lượt ghi nhận. Xem số đo và phạm vi dữ liệu bằng --json.")
    return 0


def github_summary(out: Doc) -> str:
    """Chỉ các token ASCII, giai đoạn và bộ đếm. Không nhúng lý do, tên repo, nội dung PLAN hay PR vào Markdown."""
    stage = out["stage"]["stage"] if out["stage"] else None
    action, owner = (str(out["next"][key]) for key in ("action", "owner"))
    metrics = out["metrics"]

    def count(value: Any) -> str:
        return str(value) if type(value) is int and value >= 0 else "chưa đo"

    def token(value: str) -> str:
        return value if re.fullmatch(r"[a-z][a-z-]{0,39}", value) else "unknown"

    return (
        "### Tiến độ sản phẩm\n\n| Giai đoạn | Bước kế | Phụ trách | Lượt Gate ghi nhận | Gate đỏ |\n"
        "|---|---|---|---|---|\n"
        f"| {count(stage)} | `{token(action)}` | `{token(owner)}` | {count(metrics['gate_runs'])} | {count(metrics['failed_gate_runs'])} |"
    )


if __name__ == "__main__":
    sys.exit(main())
