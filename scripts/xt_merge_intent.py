"""Định danh đích và pin phía máy chủ cho một lần merge PR (ADR-0102)."""

from __future__ import annotations

import os
import re
import shlex
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Callable, Iterator, NamedTuple

HOST_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
HOST = rf"{HOST_LABEL}(?:\.{HOST_LABEL})*"
SLUG = r"[A-Za-z0-9_-][A-Za-z0-9_.-]*/[A-Za-z0-9_-][A-Za-z0-9_.-]*"
PR_URL = re.compile(rf"https://(?P<host>{HOST})/(?P<repo>{SLUG})/pull/(?P<pr>[1-9][0-9]*)/?\Z", re.ASCII)
NAMED_PR = re.compile(rf"(?P<repo>{SLUG})#(?P<pr>[1-9][0-9]*)", re.ASCII)
ENV_REPO = re.compile(rf"(?:(?P<host>{HOST})/)?(?P<repo>{SLUG})", re.ASCII)
CHECKOUT_REPO = "repos/{owner}/{repo}"


@contextmanager
def at_host(setting: ContextVar[str], host: str) -> Iterator[None]:
    previous = setting.set(host)
    try:
        yield
    finally:
        setting.reset(previous)


class MergeIntent(NamedTuple):
    host: str
    repo: str
    pr: int
    expected_head: str

    @classmethod
    def from_pull(cls, pull: dict[str, Any]) -> MergeIntent | None:
        raw_url = pull.get("html_url")
        url = PR_URL.fullmatch(raw_url) if isinstance(raw_url, str) else None
        base, head = pull.get("base"), pull.get("head")
        repo = base.get("repo") if isinstance(base, dict) else None
        sha = head.get("sha") if isinstance(head, dict) else None
        number = pull.get("number")
        if not url or type(number) is not int or str(number) != url["pr"] or not isinstance(repo, dict):
            return None
        if (
            url["repo"].lower() != str(repo.get("full_name", "")).lower()
            or not isinstance(sha, str)
            or not re.fullmatch("[0-9a-f]{40}", sha)
        ):
            return None
        return cls(url["host"].lower(), url["repo"].lower(), number, str(sha))

    @classmethod
    def from_action(cls, out: dict[str, Any], repo_path: str) -> MergeIntent | None:
        data = out.get("merge_intent")
        if not isinstance(data, dict) or set(data) != set(cls._fields):
            return None
        intent = cls(**data)
        if not isinstance(intent.repo, str) or not re.fullmatch(SLUG, intent.repo):
            return None
        if not isinstance(intent.host, str) or not re.fullmatch(HOST, intent.host):
            return None
        if type(intent.pr) is not int or intent.pr <= 0 or intent.pr != out.get("pr"):
            return None
        if (
            not isinstance(intent.expected_head, str)
            or not re.fullmatch("[0-9a-f]{40}", intent.expected_head)
            or intent.expected_head != out.get("head")
        ):
            return None
        return intent if repo_path.lower() in (CHECKOUT_REPO, "repos/" + intent.repo.lower()) else None

    @property
    def path(self) -> str:
        return f"repos/{self.repo}/pulls/{self.pr}"

    def command(self, subject: str = "", body: str = "") -> list[str]:
        args = [
            "gh",
            "api",
            "-X",
            "PUT",
            "--hostname",
            self.host,
            self.path + "/merge",
            "-f",
            "merge_method=squash",
            "-f",
            "sha=" + self.expected_head,
        ]
        if subject:
            args.extend(["-f", "commit_title=" + subject])
        if body:
            args.extend(["-f", "commit_message=" + body])
        return args

    def step(self) -> str:
        return shlex.join(self.command())


def bind(pr: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    intent = MergeIntent.from_action({**out, "merge_intent": pr["live_intent"]}, "repos/" + str(pr.get("repo", "")))
    if not intent:
        return {**out, "action": "wait", "do": "", "why": "chưa xác minh đủ host, repo, PR và SHA"}
    return {**out, "merge_intent": intent._asdict(), "do": intent.step()}


def current(out: dict[str, Any], repo: str, read: Callable[..., list[Any]]) -> str:
    intent = MergeIntent.from_action(out, repo)
    if not intent:
        return "ý định merge không khớp đích"
    values = read(intent.path, host=intent.host)
    if len(values) != 1 or not isinstance(values[0], dict):
        return "không xác minh được PR tại đích đã ghim"
    pull = values[0]
    if pull.get("merged") or pull.get("state") != "open":
        return "PR đã đóng/merge"
    if MergeIntent.from_pull(pull) != intent:
        return "head đổi hoặc đích PR không còn khớp — chạy lại pr next"
    return ""


def stale_action(
    out: dict[str, Any], repo: str, read_values: Callable[..., list[Any]], read_one: Callable[[str], dict[str, Any]]
) -> str:
    """AUTO-05 đọc lại PR ngay trước tác vụ. Chuỗi rỗng khi hành động vẫn cần ở đúng head đã xét."""
    if out["action"] == "merge":
        return current(out, repo, read_values)
    pull = read_one(f"{repo}/pulls/{out['pr']}")
    raw = pull.get("head")
    sha = str(raw.get("sha") or "") if isinstance(raw, dict) else ""
    if pull.get("merged") or pull.get("state") != "open":
        return "PR đã đóng/merge"
    if sha != out["head"]:
        return f"head đổi {str(out['head'])[:7]} → {sha[:7] or '?'} — lượt sau xét head mới"
    if out["action"] == "disable-auto-merge" and not pull.get("auto_merge"):
        return "auto-merge đã tắt"
    return ""


PrDetails = Callable[[str, str, bool, dict[str, Any], dict[str, Any] | None], dict[str, Any]]


def read_pr(
    selector: str | None,
    local_check: bool,
    setting: ContextVar[str],
    target: Callable[[str | None], tuple[str, str]],
    fetch: Callable[[str], dict[str, Any]],
    details: PrDetails,
    error: type[Exception],
) -> dict[str, Any]:
    url = PR_URL.fullmatch(selector or "")
    if "://" in (selector or "") and not url:
        raise error("URL PR không hợp lệ")
    named = url or NAMED_PR.fullmatch(selector or "")
    raw_repo = os.environ.get("GH_REPO", "") if not named else ""
    env_repo = ENV_REPO.fullmatch(raw_repo)
    if raw_repo and env_repo is None:
        raise error("GH_REPO phải dạng [host/]owner/repo")
    host = url["host"] if url else (env_repo and env_repo["host"]) or os.environ.get("GH_HOST", "")
    if host and not re.fullmatch(HOST, host):
        raise error("GH_HOST không hợp lệ")
    with at_host(setting, host.lower()):
        repo, number = (f"repos/{named['repo']}", named["pr"]) if named else target(selector)
        if repo == CHECKOUT_REPO and env_repo:
            repo = f"repos/{env_repo['repo']}"
        pull = fetch(f"{repo}/pulls/{number}")
        intent = verified(pull, repo, number, setting.get(), error)
        if intent is None:
            return details(repo, number, local_check, pull, None)
        with at_host(setting, intent.host):
            return details(f"repos/{intent.repo}", number, local_check, pull, intent._asdict())


def verified(pull: dict[str, Any], repo: str, number: str, host: str, error: type[Exception]) -> MergeIntent | None:
    intent = MergeIntent.from_pull(pull)
    if intent and (
        str(intent.pr) != number
        or repo.lower() not in (CHECKOUT_REPO, "repos/" + intent.repo)
        or host not in ("", intent.host)
    ):
        raise error("Đích PR trả về khác host, repo hoặc số PR đã yêu cầu")
    return intent
