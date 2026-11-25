"""Định danh đích và pin phía máy chủ cho một lần merge PR (ADR-0102)."""

from __future__ import annotations

import os
import re
import shlex
import urllib.parse
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Callable, Iterator, NamedTuple

HOST_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
HOST = rf"{HOST_LABEL}(?:\.{HOST_LABEL})*"
SLUG = r"[A-Za-z0-9_-][A-Za-z0-9_.-]*/(?!\.{1,2}(?![A-Za-z0-9_.-]))[A-Za-z0-9_.-]+"
PR_URL_BASE = rf"https://(?P<host>{HOST})/(?P<repo>{SLUG})/pull/(?P<pr>[1-9][0-9]*)"
PR_URL = re.compile(rf"{PR_URL_BASE}/?\Z", re.ASCII)
PR_USER_URL = re.compile(
    rf"{PR_URL_BASE}(?:/(?:files|changes|commits|checks)(?:/[a-f0-9]+)?)?/?(?:[?#][^\s]*)?\Z", re.ASCII
)
NAMED_PR = re.compile(rf"(?P<repo>{SLUG})#(?P<pr>[1-9][0-9]*)", re.ASCII)
ENV_REPO = re.compile(rf"(?:(?P<host>{HOST})/)?(?P<repo>{SLUG})", re.ASCII)
ORIGIN_URL = re.compile(
    rf"(?:(?P<scheme>https|ssh)://(?P<userinfo>git@)?(?P<host>{HOST})/|git@(?P<scp_host>{HOST}):)(?P<repo>{SLUG})/?",
    re.ASCII,
)


@contextmanager
def at_host(setting: ContextVar[str], host: str) -> Iterator[None]:
    previous = setting.set(host)
    try:
        yield
    finally:
        setting.reset(previous)


class RepoTarget(NamedTuple):
    host: str
    repo: str

    @classmethod
    def from_origin(cls, raw: str, error: type[Exception]) -> RepoTarget:
        # `git config -z --get-all` phải có đúng một origin. Không dùng URL do `insteadOf` biến đổi.
        values = raw.split("\0")
        match = ORIGIN_URL.fullmatch(values[0]) if len(values) == 2 and values[1] == "" else None
        repo = match["repo"].removesuffix(".git") if match else ""
        # Dạng URL dùng `git@` đúng khi scheme là SSH; dạng SCP đã ghim `git@` riêng.
        if not match or (match["scheme"] == "ssh") != bool(match["userinfo"]) or not re.fullmatch(SLUG, repo):
            raise error("không xác minh được host/repo của origin trong checkout đang cung cấp chính sách PR")
        target = cls((match["host"] or match["scp_host"]).lower(), repo.lower())
        if host := os.environ.get("GH_HOST", ""):
            target.require(host, target.repo, "GH_HOST", error)
        if value := os.environ.get("GH_REPO", ""):
            target.require_repo(value, "GH_REPO", error)
        return target

    @property
    def path(self) -> str:
        return f"repos/{self.repo}"

    @property
    def qualified(self) -> str:
        return f"{self.host}/{self.repo}"

    def pull_url(self, number: object) -> str:
        return f"https://{self.qualified}/pull/{number}"

    def require(self, host: str | None, repo: str, source: str, error: type[Exception]) -> None:
        if (host and host.lower() != self.host) or repo.lower() != self.repo:
            raise error(f"{source} khác host/repo của origin đang cung cấp chính sách PR ({self.qualified})")

    def require_repo(self, value: str, source: str, error: type[Exception]) -> None:
        match = ENV_REPO.fullmatch(value)
        if not match:
            raise error(f"{source} phải dạng [host/]owner/repo")
        self.require(match["host"], match["repo"], source, error)

    def action(self, method: str, resource: str, *fields: str) -> list[str]:
        args = ["gh", "api", "-X", method, "--hostname", self.host, self.path + "/" + resource]
        for value in fields:
            args.extend(["-f", value])
        return args


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
    def from_action(cls, out: dict[str, Any], target: RepoTarget) -> MergeIntent | None:
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
        return intent if intent.target == target else None

    @property
    def target(self) -> RepoTarget:
        return RepoTarget(self.host, self.repo)

    @property
    def path(self) -> str:
        return f"repos/{self.repo}/pulls/{self.pr}"

    def command(self, subject: str = "", body: str = "") -> list[str]:
        args = self.target.action("PUT", f"pulls/{self.pr}/merge", "merge_method=squash", "sha=" + self.expected_head)
        if subject:
            args.extend(["-f", "commit_title=" + subject])
        if body:
            args.extend(["-f", "commit_message=" + body])
        return args

    def step(self) -> str:
        return shlex.join(self.command())


def _from_read(pr: dict[str, Any], out: dict[str, Any]) -> MergeIntent | None:
    target = RepoTarget(str(pr.get("live_host", "")), str(pr.get("repo", "")).lower())
    return MergeIntent.from_action({**out, "merge_intent": pr["live_intent"]}, target)


def bind(pr: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    intent = _from_read(pr, out)
    if not intent:
        return {**out, "action": "wait", "do": "", "why": "chưa xác minh đủ host, repo, PR và SHA"}
    return {**out, "merge_intent": intent._asdict(), "do": intent.step()}


def current(out: dict[str, Any], target: RepoTarget, read: Callable[..., list[Any]]) -> str:
    intent = MergeIntent.from_action(out, target)
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


def stale_action(out: dict[str, Any], target: RepoTarget, read: Callable[..., list[Any]]) -> str:
    """AUTO-05 đọc lại PR ngay trước tác vụ. Chuỗi rỗng khi hành động vẫn cần ở đúng head đã xét."""
    if out["action"] == "merge":
        return current(out, target, read)
    values = read(f"{target.path}/pulls/{out['pr']}", host=target.host)
    pull = values[0] if len(values) == 1 and isinstance(values[0], dict) else {}
    intent = MergeIntent.from_pull(pull)
    if pull.get("merged") or pull.get("state") != "open":
        return "PR đã đóng/merge"
    if intent != MergeIntent(target.host, target.repo, out["pr"], out["head"]):
        sha = intent.expected_head[:7] if intent else "?"
        return f"head đổi {str(out['head'])[:7]} → {sha} hoặc đích PR đổi — lượt sau xét head mới"
    if out["action"] == "disable-auto-merge" and not pull.get("auto_merge"):
        return "auto-merge đã tắt"
    return ""


PrDetails = Callable[[str, str, bool, dict[str, Any], dict[str, Any] | None], dict[str, Any]]


def pr_number(
    selector: str | None,
    target: RepoTarget,
    branch: Callable[[], str],
    items: Callable[[str], list[dict[str, Any]]],
    error: type[Exception],
) -> str:
    value = selector or ""
    url = PR_USER_URL.fullmatch(value)
    if "://" in value and not url:
        raise error("URL PR không hợp lệ")
    if named := url or NAMED_PR.fullmatch(value):
        target.require(url["host"] if url else None, named["repo"], "PR", error)
        return str(named["pr"])
    if re.fullmatch(r"#?[0-9]+", value):
        if digits := value.lstrip("#").lstrip("0"):
            return digits
        raise error("số PR phải lớn hơn 0")
    if not (head := value or branch()):
        raise error("không có nhánh hiện tại — chọn số bằng --pr")
    owner = target.repo.split("/", 1)[0]
    found = items(f"{target.path}/pulls?head={owner}:{urllib.parse.quote(head, safe='/')}&state=open&per_page=100")
    if not found:
        raise error(f"không có PR mở cho nhánh {head}")
    if len(found) != 1:
        raise error(f"nhiều PR mở cho nhánh {head} — chọn số bằng --pr")
    number = found[0].get("number")
    if type(number) is not int or number <= 0:
        raise error("số PR của nhánh không hợp lệ")
    return str(number)


def read_pr(
    selector: str | None,
    local_check: bool,
    setting: ContextVar[str],
    target: RepoTarget,
    branch: Callable[[], str],
    items: Callable[[str], list[dict[str, Any]]],
    fetch: Callable[[str], list[Any]],
    details: PrDetails,
    error: type[Exception],
    on_selector: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    repo = target.path
    with at_host(setting, target.host):
        number = pr_number(selector, target, branch, items, error)
        route = target.pull_url(number)
        if on_selector is not None:
            on_selector(route)  # giữ đích đọc ngay cả khi phản hồi đầu tiên lỗi
        values = fetch(f"{repo}/pulls/{number}")
        if len(values) != 1 or not isinstance(values[0], dict):
            raise error(f"không xác minh được phản hồi duy nhất cho PR #{number}")
        pull = values[0]
        intent = verified(pull, repo, number, target.host, error)
        result = details(repo, number, local_check, pull, intent._asdict() if intent else None)
        return {**result, "live_host": target.host, "live_selector": route}


def verified(pull: dict[str, Any], repo: str, number: str, host: str, error: type[Exception]) -> MergeIntent | None:
    raw_number = pull.get("number")
    if "number" in pull and (type(raw_number) is not int or str(raw_number) != number):
        raise error(f"Đích PR trả về khác host, repo hoặc số PR đã yêu cầu (số trả về không phải #{number})")
    raw_url, base = pull.get("html_url"), pull.get("base")
    url = PR_USER_URL.fullmatch(raw_url) if isinstance(raw_url, str) else None
    base_repo = base.get("repo") if isinstance(base, dict) else None
    full_name = base_repo.get("full_name") if isinstance(base_repo, dict) else None
    repo = repo.lower()
    if (
        url
        and (url["pr"] != number or url["host"].lower() != host or "repos/" + url["repo"].lower() != repo)
        or (full_name and "repos/" + str(full_name).lower() != repo)
    ):
        raise error("Đích PR trả về khác host, repo hoặc số PR đã yêu cầu")
    return MergeIntent.from_pull(pull)


def watch_selector(decision: dict[str, Any], fallback: str = "") -> str:
    return str(decision.get("live_selector") or fallback or decision.get("pr") or "")


def review_target(target: RepoTarget, selector: str, key: str, error: type[Exception]) -> RepoTarget:
    if "://" not in selector:
        return target  # _pr_key đã chuẩn hoá số PR và dạng #N
    url = PR_USER_URL.fullmatch(selector)
    if not url or url["pr"] != key:
        raise error("URL review không khớp số PR")
    target.require(url["host"], url["repo"], "URL review", error)
    return target


def live_action(pr: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    if "live_intent" not in pr:
        return action
    if action["action"] == "merge":
        return bind(pr, action)
    if not (intent := _from_read(pr, action)):
        if action["action"] in {"update", "disable-auto-merge"}:
            return {**action, "do": "", "why": f"{action['why']} — chưa xác minh đủ đích và head của PR"}
        return action
    target, number = intent.target, intent.pr
    if action["action"] == "update":
        cmd = target.action("PUT", f"pulls/{number}/update-branch", f"expected_head_sha={intent.expected_head}")
    elif action["action"] == "disable-auto-merge":
        cmd = ["gh", "pr", "merge", target.pull_url(number), "--disable-auto"]
    else:
        return {**action, "do": action["do"].replace(f"--pr {number}", f"--pr {target.pull_url(number)}")}
    return {**action, "do": shlex.join(cmd)}


def preview_only(action: dict[str, Any]) -> dict[str, Any]:
    if not action["do"] or action["do"].startswith("báo người: "):
        return action
    return {**action, "do": "", "why": f"{action['why']} — ảnh chụp, chạy lại pr next với dữ liệu live"}


def merge_check_result(pr: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    verdict = decision["verdict"]
    if verdict not in {"merge", "update"}:
        return decision
    result = {key: value for key, value in decision.items() if key != "next_rest"}
    if "live_intent" not in pr:  # ảnh chụp của merge-check chỉ báo verdict
        return {**result, "next": ""}
    action = live_action(pr, {"action": verdict, "pr": decision["pr"], "head": decision["head"], "why": "", "do": ""})
    if action["action"] == verdict and action["do"]:
        return {**result, "next": action["do"]}
    return {
        **result,
        "verdict": "wait",
        "eligible": False,
        "reasons": [*decision["reasons"], action["why"]],
        "next": "",
    }


WriteCommands = Callable[[list[list[str]]], str]


def steward_command(
    out: dict[str, Any], target: RepoTarget, can_update: bool, subject: str, body: str
) -> list[list[str]]:
    number, action = str(out["pr"]), out["action"]
    if action == "merge":
        intent = MergeIntent.from_action(out, target)
        return [intent.command(subject, body)] if intent else []
    if action == "disable-auto-merge":
        return [["gh", "pr", "merge", number, "--repo", target.qualified, "--disable-auto"]]
    if action == "update" and can_update:
        return [target.action("PUT", f"pulls/{number}/update-branch", f"expected_head_sha={out['head']}")]
    return []


def steward_can_update() -> bool:
    # GITHUB_TOKEN không kích lại workflow pull_request sau khi cập nhật nhánh (review #153–154).
    flag = os.environ.get("XT_STEWARD_UPDATE", "").strip().lower()
    if flag:
        return flag in ("on", "true", "1", "yes")
    return os.environ.get("GITHUB_ACTIONS", "").strip().lower() != "true"


def workflow_run(target: RepoTarget, name: str, base: str, *fields: str) -> str:
    return shlex.join(["gh", "workflow", "run", name, "--repo", target.qualified, "--ref", base, *fields])


def ci_workflow() -> tuple[str, str]:
    name = os.environ.get("XT_CI_WORKFLOW", "").strip() or "ci.yml"
    error = (
        ""
        if re.fullmatch(r"[\w.-]+\.ya?ml", name, re.ASCII)
        else (f"XT_CI_WORKFLOW={name!r} không phải tên file workflow (*.yml)")
    )
    return name, error


def dispatch_ci(out: dict[str, Any], target: RepoTarget, base: str, run: WriteCommands) -> None:
    """Khởi chạy CI của đích vì merge qua GITHUB_TOKEN không kích workflow push (T-2402)."""
    name, err = ci_workflow()
    if not err:
        err = run([target.action("POST", f"actions/workflows/{name}/dispatches", f"ref={base}")])
    out["then"] = "dispatch CI " + (f"✗ {err}" if err else "✓")
    if err:
        text = (
            f"CI không chạy trên `{base}` sau merge ({err}) — job steward cần `actions: write`"
            " (chạy lại install.py --with-github) hoặc đặt XT_STEWARD_TOKEN; chạy tay: "
            + workflow_run(target, name, base)
        )
        out["warn"] = "; ".join(x for x in (out.get("warn"), text) if x)


def dispatch_tag(
    out: dict[str, Any],
    target: RepoTarget,
    base: str,
    name: str,
    read: Callable[..., list[Any]],
    run: WriteCommands,
    read_error: type[Exception],
) -> None:
    """Đọc merge commit từ đúng PR đã ghim trước khi dispatch release-tag (AUD-HAR-124)."""
    intent = MergeIntent.from_action(out, target)
    sha, err = "", ""
    if intent:
        try:
            values = read(intent.path, host=target.host)
            pull = values[0] if len(values) == 1 and isinstance(values[0], dict) else {}
            if pull.get("merged") and MergeIntent.from_pull(pull) == intent:
                sha = str(pull.get("merge_commit_sha") or "")
        except read_error as exc:
            err = str(exc)
    ok = re.fullmatch(r"[0-9a-f]{40}", sha) is not None
    if ok:
        err = run([target.action("POST", f"actions/workflows/{name}/dispatches", f"ref={base}", f"inputs[sha]={sha}")])
    else:
        err = err or "không xác minh được merge_commit_sha tại PR đã ghim"
    out["then"] = "; ".join(x for x in (out.get("then"), "dispatch tag " + (f"✗ {err}" if err else "✓")) if x)
    if err:
        how = workflow_run(target, name, base, "-f", f"sha={sha}") if ok else "sha commit merge"
        text = f"tag phát hành chưa gắn ({err}) — chạy tay workflow_dispatch {name} ({how})"
        out["warn"] = "; ".join(x for x in (out.get("warn"), text) if x)
