"""Cổng FIFO theo số PR cho merge-check, pr next và steward (ADR-0105)."""

from __future__ import annotations

import re
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from types import ModuleType
from typing import Any, Iterator

from xt_merge_intent import MergeIntent, RepoTarget, at_host

DEFAULT_STALL = 120
SCAN_LIMIT = 12
_ACTIONS = {"", "merge", "update", "disable-auto-merge"}
_ELIGIBLE = {"merge", "review", "wait"}
_UNKNOWN = "chưa xác minh được hàng merge (LOOP-STOP-031) — đợi rồi kiểm lại"


@dataclass(frozen=True)
class _Candidate:
    holds: bool
    behind: bool = False
    started_at: datetime | None = None


_Memo = dict[tuple[RepoTarget, str, int, str], _Candidate]
_scope: ContextVar[_Memo | None] = ContextVar("merge_queue_scope", default=None)


@contextmanager
def queue_scope() -> Iterator[None]:
    """Chỉ giữ kết quả đọc chi tiết trong một lượt.

    Listing luôn đọc sống để sau khi merge, PR kế tiếp thấy PR đầu đã rời hàng.
    """
    marker = _scope.set({})
    try:
        yield
    finally:
        _scope.reset(marker)


def stall_minutes(raw: str) -> int | None:
    """Giá trị lỗi cũng dùng được để doctor phân biệt với mặc định."""
    if raw.isascii() and raw.isdecimal():
        try:
            return int(raw)
        except ValueError:
            pass  # Chuỗi số vượt giới hạn chuyển đổi của Python.
    return None


def _policy(host: ModuleType, branch: str) -> tuple[bool, int]:
    try:
        base = host.project_dir()
        keys = host._committed_xt_keys(base, host._pr_policy_ref(base, branch))
    except (OSError, ValueError):
        return True, DEFAULT_STALL
    ttl = stall_minutes(keys.get("merge_queue_stall_minutes", ""))
    return keys.get("merge_queue") != "off", DEFAULT_STALL if ttl is None else ttl


def _date(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        at = datetime.fromisoformat(value)
    except ValueError:
        return None
    return at if at.tzinfo is not None else None


def _expired(now: datetime, at: datetime | None, ttl: int) -> bool:
    return at is not None and (now - at).total_seconds() / 60 > ttl


def _field(obj: Any, name: str) -> Any:
    return obj.get(name) if isinstance(obj, dict) else None


def _listing_candidate(pull: dict[str, Any], target: RepoTarget, branch: str, before: int | None = None) -> bool:
    number = pull.get("number")
    if (
        type(number) is not int
        or number <= 0
        or (before is not None and number >= before)
        or pull.get("draft")
        or pull.get("state", "open") != "open"
    ):
        return False
    base, head = pull.get("base"), pull.get("head")
    ref = _field(base, "ref")
    if ref and ref != branch:
        return False
    if isinstance(head, dict) and "repo" in head and head["repo"] is None:
        return False  # Fork đã xoá.
    repos = (_field(_field(side, "repo"), "full_name") for side in (base, head))
    return all(not repo or str(repo).lower() == target.repo for repo in repos)


def _current_candidate(host: ModuleType, pr: dict[str, Any], target: RepoTarget, branch: str) -> _Candidate:
    if pr.get("state") in ("CLOSED", "MERGED") or pr.get("isDraft"):
        return _Candidate(False)
    ref, repo, head_repo = (str(pr.get(key) or "") for key in ("baseRefName", "repo", "headRepo"))
    if pr.get("state") != "OPEN" or not (ref and repo and head_repo):
        raise host.PrInputError("thiếu trạng thái, nhánh hoặc repo của PR trong hàng")
    if ref != branch or repo.lower() != target.repo or head_repo.lower() != target.repo:
        return _Candidate(False)
    behind = pr.get("mergeStateStatus") == "BEHIND"
    normalized = {**pr, "mergeStateStatus": "CLEAN"} if behind else pr
    d, _ = host._merge_eval(normalized)
    if d["verdict"] not in _ELIGIBLE or d.get("hard") or d.get("stacked"):
        return _Candidate(False)
    if d.get("lane") != "derived" and host.steward_untrusted(pr):
        return _Candidate(False)
    return _Candidate(True, behind and host._merge_eval(pr)[0]["verdict"] == "update", _oldest_check(pr))


def _oldest_check(pr: dict[str, Any]) -> datetime | None:
    values = (_date(_field(check, "startedAt")) for check in pr.get("statusCheckRollup") or [])
    return min((at for at in values if at is not None), default=None)


def _candidate(host: ModuleType, pull: dict[str, Any], target: RepoTarget, branch: str, fresh: bool) -> _Candidate:
    number = pull["number"]
    sha = _field(pull.get("head"), "sha")
    memo = _scope.get()
    key = (target, branch, number, sha)
    if memo is not None and isinstance(sha, str) and not fresh and key in memo:
        return memo[key]
    pr = host._pr_rest(str(number), local_check=False, target=target)
    if isinstance(sha, str) and pr.get("headRefOid") != sha:
        raise host.PrInputError("head của PR trong hàng vừa đổi")
    result = _current_candidate(host, pr, target, branch)
    if memo is not None and isinstance(sha, str):
        memo[key] = result
    return result


def _holds(
    host: ModuleType, pull: dict[str, Any], target: RepoTarget, branch: str, now: datetime, ttl: int, fresh: bool
) -> bool:
    updated_at = _date(pull.get("updated_at"))
    try:
        candidate = _candidate(host, pull, target, branch, fresh)
    except (host.PrInputError, OSError, ValueError):
        return not _expired(now, updated_at, ttl)
    return candidate.holds and (candidate.behind or not _expired(now, candidate.started_at or updated_at, ttl))


def _queue_reason(host: ModuleType, intent: MergeIntent, branch: str, ttl: int, fresh: bool) -> str:
    target = intent.target
    try:
        pulls = host._pr_open(target)
    except (host.PrInputError, OSError, ValueError):
        return _UNKNOWN
    candidates = sorted(
        (pull for pull in pulls if _listing_candidate(pull, target, branch, intent.pr)), key=lambda pull: pull["number"]
    )
    now = datetime.now(timezone.utc)
    for pull in candidates[:SCAN_LIMIT]:
        if _holds(host, pull, target, branch, now, ttl, fresh):
            return f"chờ tới lượt: #{pull['number']} đứng đầu hàng (LOOP-STOP-031) — kẹt thì chuyển nháp"
    return _UNKNOWN if len(candidates) > SCAN_LIMIT else ""


def _wait(host: ModuleType, d: dict[str, Any], reason: str) -> dict[str, Any]:
    result = {**d, "verdict": "wait", "reasons": [reason], "eligible": False, "next": host.MERGE_WAIT_NEXT}
    result.pop("next_rest", None)
    return result


def check_live_base(host: ModuleType, pr: dict[str, Any], d: dict[str, Any]) -> dict[str, Any]:
    """`base.sha` và `mergeable_state` có thể cùng cũ. Chỉ hỏi nhánh đích khi PR đã qua các cổng khác."""
    repo = pr.get("strictBaseRepo")
    if d["verdict"] != "merge" or not repo:
        return d
    base = str(pr.get("baseRefName") or "")
    with at_host(host.PR_READ_HOST, str(pr.get("live_host") or "")):
        behind = host._live_base_distance(repo, base, str(d["head"]))
    if behind == 0:
        return d
    verdict, reason, cmd = (
        (
            "wait",
            "chưa xác minh được head chứa nhánh đích hiện tại theo ruleset — đợi rồi kiểm lại",
            host.MERGE_WAIT_NEXT,
        )
        if behind is None
        else ("update", host.PR_BEHIND_REASON, host._pr_update_next(d["pr"], d["head"], base))
    )
    result = {
        **d,
        "verdict": verdict,
        "reasons": [reason, *host._waived_notes(d["hard_waived"])],
        "next": cmd,
        "eligible": False,
    }
    result.pop("next_rest", None)
    return result


def gate(
    host: ModuleType, pr: dict[str, Any], d: dict[str, Any], action: str, *, fresh: bool = False
) -> dict[str, Any]:
    """Chặn merge/cập nhật nhánh khi PR nhỏ hơn còn trong hàng."""
    if d["verdict"] not in {"merge", "update"} or action not in _ACTIONS:
        return d
    if pr.get("live_intent"):
        target = RepoTarget(str(pr.get("live_host") or ""), str(pr.get("repo") or "").lower())
        intent = MergeIntent.from_action({**d, "merge_intent": pr["live_intent"]}, target)
        branch = pr.get("baseRefName")
        if intent is None or not isinstance(branch, str) or not branch:
            return _wait(host, d, _UNKNOWN)
        enabled, ttl = _policy(host, branch)
        if enabled and (reason := _queue_reason(host, intent, branch, ttl, fresh)):
            return _wait(host, d, reason)
    return check_live_base(host, pr, d) if action in {"", "merge"} else d


def before_action(host: ModuleType, out: dict[str, Any], target: RepoTarget, expected_base: str) -> str:
    """Đọc lại head, nhánh đích, review, CI và hàng ngay trước merge/cập nhật của steward."""
    try:
        pr = host._pr_rest(str(out["pr"]), local_check=False, target=target)
        if pr.get("state") != "OPEN":
            return "PR đã đóng/merge"
        intent = MergeIntent.from_action({**out, "merge_intent": pr.get("live_intent")}, target)
        if intent is None or pr.get("baseRefName") != expected_base:
            return "head đổi hoặc nhánh đích không còn khớp — chạy lại pr next"
        d, _ = host._merge_eval(pr)
        current = gate(host, pr, d, "", fresh=True)
    except (host.PrInputError, OSError, ValueError) as exc:
        return f"không đọc lại được PR trước khi làm: {exc}"
    if current.get("lane") != "derived" and (why := host.steward_untrusted(pr)):
        return str(why)
    action = out["action"]
    if current["verdict"] != action or current.get("hard") or current.get("stacked"):
        return "cổng vừa đổi — " + "; ".join(current["reasons"])
    if action == "update" and pr.get("autoMergeRequest"):
        return "auto-merge đang bật — cần tắt trước khi cập nhật nhánh"
    return ""


def followup_update(host: ModuleType, out: dict[str, Any], target: RepoTarget, base: str) -> dict[str, Any]:
    why = before_action(host, {**out, "action": "update"}, target, base)
    if why:
        host._add_note(out, f"bỏ qua cập nhật nhánh — {why}")
        return out
    error = host._steward_run([host._update_branch_cmd(target, str(out["pr"]), str(out["head"]))])
    out["then"] = f"update ✗ {error}" if error else "update ✓"
    if error:
        out["error"] = error
    return out


def event_successors(host: ModuleType, out: dict[str, Any], target: RepoTarget) -> list[str]:
    """Chỉ nối PR đầu hàng cùng nhánh sau khi GitHub xác nhận PR sự kiện đã merge."""
    try:
        merged = host._pr_rest(str(out["pr"]), local_check=False, target=target)
        branch = merged.get("baseRefName")
        if merged.get("state") != "MERGED" or not branch:
            return []
        enabled, ttl = _policy(host, branch)
        pulls = host._pr_open(target) if enabled else []
    except (host.PrInputError, OSError, ValueError):
        return []
    candidates = sorted((p for p in pulls if _listing_candidate(p, target, branch)), key=lambda p: p["number"])
    now = datetime.now(timezone.utc)
    for pull in candidates[:SCAN_LIMIT]:
        if _holds(host, pull, target, branch, now, ttl, True):
            return [str(pull["number"])]
    return []


def queue_summary(results: list[dict[str, Any]]) -> list[str]:
    """Tóm tắt các PR steward đã quan sát trong lượt, theo nhánh đích."""
    by_branch: dict[str, list[tuple[dict[str, Any], bool]]] = {}
    for result in results:
        branch = result.pop("_queue_branch", "")
        absent = result.pop("_queue_checks_absent", False)
        if branch:
            by_branch.setdefault(branch, []).append((result, absent))
    lines = []
    for branch, observed in by_branch.items():
        left = [f"#{r['pr']}" for r, _ in observed if r["action"] in {"done", "closed"} or _merged(r)]
        queued = [(r, absent) for r, absent in observed if r["action"] in _QUEUE_REPORT_ACTIONS and not _merged(r)]
        if queued:
            head, absent = queued[0]
            blocker = re.search(r"chờ tới lượt: (#\d+) đứng đầu hàng \(LOOP-STOP-031\)", head["why"])
            later = queued if blocker else queued[1:]
            after = ", ".join(f"#{r['pr']}" for r, _ in later) or "—"
            first = blocker[1] if blocker else f"#{head['pr']}"
            start = f"{first} ({head['why']})"
            if absent:
                lines.append(f"⚠ {branch}: nhánh đích không có check bắt buộc (LOOP-STOP-033)")
        else:
            start = after = "—"
        lines.append(f"{branch} · hàng: đầu {start} · rời hàng: {', '.join(left) or '—'} · sau: {after}")
    return lines


_QUEUE_REPORT_ACTIONS = {"merge", "update", "wait", "review", "disable-auto-merge", "republish-review"}


def _merged(result: dict[str, Any]) -> bool:
    return result["action"] == "merge" and bool(result.get("applied"))
