"""F-151. Inventory local state and protected remote configuration without changing either."""

from __future__ import annotations

import base64
import binascii

import argparse
import datetime as dt
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Callable, Protocol
from urllib.parse import quote

import xt_distribution

Doc = dict[str, Any]


class Core(Protocol):
    DEFER_ID_RE: re.Pattern[str]
    DEPLOY_ENV_NAME: re.Pattern[str]
    DeployError: type[Exception]
    _committed_xt_text: Callable[[Path, str], str | None]
    _deferred: Callable[[Doc], Doc]
    _git: Callable[..., subprocess.CompletedProcess[str]]
    _git_head: Callable[[Path], str | None]
    _go_git_env: Callable[[], dict[str, str]]
    _inside: Callable[[Path, str], Path | None]
    _release_prod_switch: Callable[..., dict[str, str]]
    _yaml_keys: Callable[[str], dict[str, str]]
    blueprint_status: Callable[[Path], Doc]
    gate_noop: Callable[[str], bool]
    github_origin_slug: Callable[[str], str]
    grant_violations: Callable[[dict[str, dict[str, str]], str, dict[str, str]], list[str]]
    human_must_ids: Callable[[], set[str]]
    loop_root: Callable[[Path], Path]
    parse_grants: Callable[[str], dict[str, dict[str, str]]]
    project_dir: Callable[[], Path]
    read_deploy_ledger: Callable[[Path], Doc]
    read_state: Callable[..., Doc | None]
    state_dir: Callable[..., Path]
    write_atomic: Callable[..., None]


OK, MISSING, UNKNOWN, SKIP, OPTIONAL = "đạt", "thiếu", "không đọc được", "không áp dụng", "tuỳ chọn"
BLOCKS = (MISSING, UNKNOWN)
LOCAL_ITEMS = ("human-musts", "deferred", "prod-switch")
REMOTE_ITEMS = (
    "repo",
    "bot-token",
    "ruleset",
    "gated-keys",
    "deploy-target",
    "deploy-secrets",
    "worker-budget",
    "worker-launcher",
    "security-updates",
    "repo-about",
    "field-workflow",
)
RULESET_FILES = {"main.json": "branch", "tags.json": "tag", "tags-create.json": "tag"}
TAG_CONDITIONS = {"ref_name": {"include": ["refs/tags/v*"], "exclude": []}}
TAG_RULES = {"tags.json": [{"type": "deletion"}, {"type": "update"}], "tags-create.json": [{"type": "creation"}]}
NAME = re.compile(r"[A-Z][A-Z0-9_]{0,99}")
KEYS = {
    "release_signoff": ("agent", "Cho agent ký khi bằng chứng đạt điều kiện của phiên bản khung."),
    "release_signoff_scale": (
        "L",
        "Đề nghị trần L. Cần bằng chứng vận hành trên ứng viên đã merge và 14 ngày đo lỗi lọt.",
    ),
    "stage_approval": ("agent", "Cho agent nghiệm thu giai đoạn trong giới hạn khung."),
    "stage_approval_max": (
        "3",
        "Đề nghị trần 3. Cần bộ nghiệm thu khoá, receipt dev và kết quả perf trên ứng viên đã merge.",
    ),
    "merge_hard_exceptions": ("auto", "Cho steward merge ngoại lệ cứng khi các cổng đạt."),
}


def field(obj: Any, key: str, default: Any = None) -> Any:
    return obj.get(key, default) if isinstance(obj, dict) else default


class Origin:
    """Use only the checkout's GitHub origin. Pin config, plan and ancestry to one remote commit."""

    def __init__(self, core: Core, base: Path, *, load_config: bool = True) -> None:
        self.core, self.base = core, base
        self.cache: Doc = {}
        git_env = core._go_git_env()
        remote = core._git(base, "config", "--local", "--no-includes", "--get", "remote.origin.url", env=git_env)
        origin = remote.stdout.strip() if remote.returncode == 0 else ""
        self.has_origin = bool(origin)
        self.repo = core.github_origin_slug(origin)
        prefix = core._git(base, "rev-parse", "--show-prefix", env=git_env)
        self.prefix = prefix.stdout.strip() if prefix.returncode == 0 else ""
        default = field(self.get(""), "default_branch")
        commit = self.get(f"commits/{quote(default, safe='')}") if isinstance(default, str) else None
        sha = field(commit, "sha")
        self.tree_sha = field(field(field(commit, "commit"), "tree"), "sha")
        self.sha = sha if isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{40}", sha) else None
        self.branch = default
        raw = self.file("xt.yaml") if load_config else None
        if load_config and not self.has_origin:
            raw = core._committed_xt_text(base, "refs/heads/main") or core._committed_xt_text(base, "refs/heads/master")
        self.cfg = core._yaml_keys(raw) if raw is not None else None

    def get(self, path: str) -> Any:
        if not self.repo:
            return None
        if path in self.cache:
            return self.cache[path]
        endpoint = f"repos/{self.repo}" + (f"/{path}" if path else "")
        try:
            result = subprocess.run(
                ["gh", "api", "--hostname", "github.com", "--method", "GET", endpoint],
                cwd=self.base,
                capture_output=True,
                timeout=15,
                check=False,
                env={**os.environ, "GH_PROMPT_DISABLED": "1"},
            )
            doc = json.loads(result.stdout) if result.returncode == 0 else None
        except (OSError, ValueError, subprocess.TimeoutExpired):
            doc = None
        self.cache[path] = doc
        return doc

    def file(self, path: str, *, repo_root: bool = False) -> str | None:
        if not self.sha:
            return None
        path = path if repo_root else self.prefix + path
        doc = self.get(f"contents/{quote(path, safe='/')}?ref={self.sha}")
        if field(doc, "encoding") != "base64" or not isinstance(doc.get("content"), str):
            return None
        try:
            return base64.b64decode("".join(doc["content"].split()), validate=True).decode("utf-8")
        except (UnicodeError, binascii.Error, ValueError):
            return None

    def pages(self, path: str, key: str | None = None) -> list[Doc] | None:
        values = []
        for number in range(1, 51):
            data = self.get(f"{path}?per_page=100&page={number}")
            page = field(data, key) if key else data
            if not isinstance(page, list) or any(not isinstance(item, dict) for item in page):
                return None
            values.extend(page)
            if len(page) < 100:
                return values
        return None


def target(origin: Origin, env: str) -> dict[str, bool]:
    cfg = origin.cfg or {}
    names = cfg.get("deploy_envs", "").split()
    declared = env in names and all(
        not origin.core.gate_noop(cfg.get(f"{key}_{env}", "")) for key in ("deploy", "smoke", "digest", "rollback")
    )
    raw = origin.file("docs/autopilot/PLAN.md")
    grants = origin.core.parse_grants(raw or "")
    grant = raw is not None and not origin.core.grant_violations(grants, "deploy", {"env": env})
    return {"target_adapter": bool(declared and origin.sha), "remote_grant": grant}


def state(check: bool) -> str:
    return OK if check else MISSING


def row(name: str, status: str, why: str, action: str, verify: str, **extra: Any) -> Doc:
    return {"id": name, "status": status, "reason": why, "action": action, "verify": verify, **extra}


def release_actor(actors: Any) -> bool:
    """Một App riêng được tạo tag; không đoán App ID hoặc mở rộng tới role của repo."""
    if not isinstance(actors, list) or len(actors) != 1 or not isinstance(actors[0], dict):
        return False
    actor = actors[0]
    return (
        type(actor.get("actor_id")) is int
        and actor["actor_id"] > 0
        and actor.get("actor_type") == "Integration"
        and actor.get("bypass_mode") == "always"
    )


def tag_rules_configured(filename: str, expected: Doc) -> bool:
    """Bypass áp cả ruleset: quyền tạo không được nằm cùng quyền sửa/xoá."""
    rules = expected.get("rules")
    if not isinstance(rules, list) or sorted(rules, key=json.dumps) != TAG_RULES[filename]:
        return False
    actors = expected.get("bypass_actors")
    return (
        expected.get("target") == "tag"
        and expected.get("enforcement") == "active"
        and expected.get("conditions") == TAG_CONDITIONS
        and (release_actor(actors) if filename == "tags-create.json" else actors == [])
    )


def rules_configured(filename: str, expected: Doc) -> bool:
    """Một bộ kiểm dùng cho cấu hình đã commit và file chủ repo chuẩn bị ghi lên GitHub."""
    name = expected.get("name")
    return (
        filename in RULESET_FILES
        and isinstance(name, str)
        and bool(name.strip())
        and expected.get("target") == RULESET_FILES[filename]
        and expected.get("enforcement") == "active"
        and isinstance(expected.get("conditions"), dict)
        and isinstance(expected.get("rules"), list)
        and isinstance(expected.get("bypass_actors"), list)
        and (filename not in TAG_RULES or tag_rules_configured(filename, expected))
    )


def check_ruleset_file(path: str) -> int:
    """Chỉ đọc ba tệp mẫu được phép; lỗi đọc, JSON hay policy đều dừng trước POST/PUT."""
    if path not in {f".github/rulesets/{filename}" for filename in RULESET_FILES}:
        print("Ruleset phải là main.json, tags.json hoặc tags-create.json trong .github/rulesets/.", file=sys.stderr)
        return 2
    try:
        expected = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print(f"Ruleset không đọc được hoặc JSON sai: {path}", file=sys.stderr)
        return 2
    if not isinstance(expected, dict) or not rules_configured(Path(path).name, expected):
        print(f"Ruleset chưa đủ cấu hình hợp lệ: {path}", file=sys.stderr)
        return 2
    return 0


def rules_file_status(origin: Origin, listing: list[Doc], filename: str, target_type: str) -> str:
    raw = origin.file(f".github/rulesets/{filename}", repo_root=True)
    if raw is None:
        return MISSING if origin.sha else UNKNOWN
    try:
        expected = json.loads(raw)
    except ValueError:
        return UNKNOWN
    if not isinstance(expected, dict):
        return UNKNOWN
    if not rules_configured(filename, expected):
        return MISSING
    found = [i for i in listing if i.get("target") == target_type and i.get("name") == expected.get("name")]
    if len(found) != 1:
        return MISSING
    return match_rules(origin, found[0].get("id"), expected)


def rules_status(origin: Origin) -> str:
    if not origin.has_origin:
        return MISSING
    listing = origin.pages("rulesets")
    if listing is None:
        return UNKNOWN
    for filename, target_type in RULESET_FILES.items():
        status = rules_file_status(origin, listing, filename, target_type)
        if status != OK:
            return status
    active = origin.get(f"rules/branches/{quote(origin.branch, safe='')}")
    return OK if isinstance(active, list) and active else UNKNOWN


def match_rules(origin: Origin, identifier: Any, expected: Any) -> str:
    if type(identifier) is not int or not isinstance(expected, dict):
        return UNKNOWN
    actual = origin.get(f"rulesets/{identifier}")
    keys = ("name", "target", "conditions", "rules", "bypass_actors", "enforcement")
    if not isinstance(actual, dict) or any(k not in expected or k not in actual for k in keys):
        return UNKNOWN
    if expected["enforcement"] != "active":
        return MISSING
    if expected["target"] == "tag" and not any(tag_rules_configured(name, actual) for name in TAG_RULES):
        return MISSING
    if expected["target"] == "tag" and isinstance(expected["rules"], list):
        expected = {**expected, "rules": sorted(expected["rules"], key=json.dumps)}
        actual = {**actual, "rules": sorted(actual["rules"], key=json.dumps)}
    return state(all(actual[k] == expected[k] for k in keys))


def names_status(origin: Origin, wanted: set[str], secrets: list[Doc] | None) -> str:
    if not wanted:
        return SKIP
    if not origin.has_origin:
        return MISSING
    if secrets is None:
        return UNKNOWN
    return state(wanted <= {i.get("name") for i in secrets if isinstance(i.get("name"), str)})


def deploy_secret_status(origin: Origin, cfg: dict[str, str]) -> str:
    names = cfg.get("deploy_secrets", "").split()
    if not all(NAME.fullmatch(n) for n in names):
        return UNKNOWN
    if not names:
        return SKIP
    return names_status(origin, set(names), origin.pages("actions/secrets", "secrets"))


def about_status(origin: Origin) -> tuple[str, list[str]]:
    """WF-DOC-021: mô tả repo (About, homepage, topics) mô tả dự án — trống, chưa đọc được hoặc nhắc khung ngoài ghi chú
    nguồn là việc tuỳ chọn của chủ repo (installer ngoại tuyến không đặt được metadata GitHub). Repo khung: không áp."""
    if not origin.has_origin or (origin.base / "framework" / "00-method" / "README.md").is_file():
        return SKIP, []
    doc = origin.get("")
    if not isinstance(doc, dict):  # AUD-CODE-066: chưa đọc được thì nói đúng là chưa đọc, không nói "đang trống"
        return OPTIONAL, [
            "chưa đọc được About/homepage/topics (API không trả về): chạy "
            "`gh repo view --json description,homepageUrl,repositoryTopics` rồi mới đặt bằng `gh repo edit` nếu cần, "
            "đừng ghi đè mô tả đang có"
        ]
    topics, description = doc.get("topics"), doc.get("description")
    words = [description, doc.get("homepage"), *(topics if isinstance(topics, list) else [])]
    # AUD-XFEAT-053: xét từng trường riêng — nối bằng xuống dòng làm homepage bị coi như dòng ghi chú bị ngắt.
    texts = [w for w in words if isinstance(w, str)]
    if (
        isinstance(description, str)
        and description.strip()
        and not any(xt_distribution.stray_mentions(t) for t in texts)
    ):
        return OK, []
    return OPTIONAL, ['gh repo edit --description "<mô tả dự án>" — About/homepage/topics đang trống hoặc mô tả khung']


def field_workflow_status(origin: Origin) -> str:
    """AUD-CI-037, AUD-CI-040: khi repo có `.github/workflows/xt-field.yml`, kiểm environment `xt-field-read`
    (không đòi quyền tạo PR của Actions: PR mở bằng `XT_STEWARD_TOKEN`). Repo không cài `xt-field.yml`: `SKIP`."""
    wf = ".github/workflows/xt-field.yml"
    if not origin.has_origin:
        return MISSING if (origin.base / wf).is_file() else SKIP
    if origin.sha is None:
        return UNKNOWN if (origin.base / wf).is_file() else SKIP
    if origin.file(wf, repo_root=True) is None:
        return SKIP
    envs = origin.pages("environments", "environments")
    if envs is None:
        return UNKNOWN
    # PR số field mở bằng XT_STEWARD_TOKEN (hàng bot-token), không bằng GITHUB_TOKEN: không đòi quyền tạo PR của Actions.
    return state(any(str(e.get("name", "")).lower() == "xt-field-read" for e in envs))


def budget_valid(cfg: dict[str, str]) -> bool:
    try:
        amount = float(cfg.get("worker_budget_usd", ""))
        turns = int(cfg.get("worker_max_turns", ""))
        return math.isfinite(amount) and amount > 0 and turns > 0
    except ValueError:
        return False


def human_item(core: Core, base: Path) -> Doc:
    human, ids = UNKNOWN, []
    bp = base / "BLUEPRINT.md"
    if bp.is_file():
        result = core.blueprint_status(bp)
        try:
            ids = sorted(core.human_must_ids().intersection(result["open_must"]))
        except (OSError, ValueError):
            pass  # Giữ UNKNOWN nếu không đọc được danh mục của đúng bản khung.
        else:
            if not result["bad_lines"] and not result["bad_waivers"]:
                human = MISSING if ids else OK
    return row(
        "human-musts",
        human,
        "Cần bằng chứng của người chịu trách nhiệm.",
        "Hoàn tất các MUST lớp B đang áp dụng trong BLUEPRINT.md.",
        "blueprint-status",
        ids=ids,
    )


def deferred_item(core: Core, base: Path) -> Doc:
    deferred, waits = SKIP, []
    doc = core.read_state(base)
    if doc is not None:
        waits = sorted(key for key in core._deferred(doc) if core.DEFER_ID_RE.fullmatch(key))
        deferred = MISSING if waits else OK
    elif (core.state_dir(base) / "state.json").exists():
        deferred = UNKNOWN
    return row(
        "deferred",
        deferred,
        "Các quyết định được vòng chuyển cho chủ dự án.",
        "Xử lý mục tương ứng trong PLAN.",
        "loop status --json",
        ids=waits,
    )


def switch_item(core: Core, base: Path) -> Doc:
    switch = core._release_prod_switch(base)
    decision = {"PASS": OK, "FAIL": UNKNOWN, "N/A": MISSING if switch["level"] == "BLOCKER" else SKIP}
    return row(
        "prod-switch",
        decision[switch["result"]],
        "Phương án vận hành thật cần người chọn.",
        "Quyết từng đề xuất đang chờ trong DECISIONS.md.",
        "release-check, hàng prod_switch",
    )


def local_items(core: Core, base: Path, only: str | None = None) -> list[Doc]:
    makers = {"human-musts": human_item, "deferred": deferred_item, "prod-switch": switch_item}
    return [make(core, base) for name, make in makers.items() if only is None or only == name]


def deploy_target_item(origin: Origin) -> Doc:
    cfg = origin.cfg or {}
    envs = [
        env for env in cfg.get("deploy_envs", "").split() if env != "dev" and origin.core.DEPLOY_ENV_NAME.fullmatch(env)
    ]
    targets = {env: target(origin, env) for env in envs}
    authorized = bool(targets) and all(all(checks.values()) for checks in targets.values())
    return row(
        "deploy-target",
        UNKNOWN if origin.has_origin and origin.cfg is None else state(authorized),
        "Đích, rollback và phạm vi ủy quyền thuộc chủ dự án.",
        "Khai bốn lệnh cho đích và cấp grant deploy đúng môi trường trong PLAN đã duyệt.",
        "commands ở main và grant-check deploy env=<env>",
        environments=targets,
    )


def gated_item(origin: Origin) -> Doc:
    cfg = origin.cfg or {}
    missing_keys = [f"+ {k}: {v} — {why}" for k, (v, why) in KEYS.items() if cfg.get(k) != v]
    return row(
        "gated-keys",
        UNKNOWN if origin.has_origin and origin.cfg is None else OPTIONAL if missing_keys else OK,
        "Chủ dự án chọn giới hạn tự chủ.",
        "Giữ quyền duyệt hiện tại hoặc merge riêng từng thay đổi cần thiết.",
        "xt.yaml đã commit trên nhánh chính",
        changes=missing_keys,
    )


def security_updates_item(origin: Origin) -> Doc:
    updates = field(origin.get("automated-security-fixes"), "enabled")
    return row(
        "security-updates",
        state(updates) if type(updates) is bool else UNKNOWN,
        "Cài đặt bảo mật cần quản trị repo.",
        "Bật Dependabot security updates trong Settings.",
        "GET automated-security-fixes",
    )


def about_item(origin: Origin) -> Doc:
    about, about_changes = about_status(origin)
    return row(
        "repo-about",
        about,
        "Mô tả repo trên GitHub do chủ repo đặt.",
        "Đặt About, homepage và topics mô tả dự án.",
        "GET repos/<owner>/<repo> (description, homepage, topics)",
        changes=about_changes,
    )


def remote_items(origin: Origin, only: str | None = None) -> list[Doc]:
    cfg = origin.cfg or {}
    protected = UNKNOWN if origin.has_origin and origin.cfg is None else None
    makers: dict[str, Callable[[], Doc]] = {
        "repo": lambda: row(
            "repo",
            state(origin.has_origin),
            "Chủ dự án chọn tổ chức và quyền truy cập.",
            "Tạo repo rồi đặt Git remote origin.",
            "git remote get-url origin",
        ),
        "bot-token": lambda: row(
            "bot-token",
            names_status(origin, {"XT_STEWARD_TOKEN"}, origin.pages("actions/secrets", "secrets")),
            "Quyền CI do chủ repo cấp.",
            "Đặt secret XT_STEWARD_TOKEN theo RUNBOOK-PR-STEWARD.",
            "GET actions/secrets (chỉ tên)",
        ),
        "ruleset": lambda: row(
            "ruleset",
            rules_status(origin),
            "Bảo vệ nhánh và tag cần quản trị repo.",
            "So main.json, tags.json và tags-create.json đã commit; chỉ ruleset tạo tag có một App phát hành được bypass.",
            "GET rulesets và rules/branches của nhánh mặc định",
        ),
        "gated-keys": lambda: gated_item(origin),
        "deploy-target": lambda: deploy_target_item(origin),
        "deploy-secrets": lambda: row(
            "deploy-secrets",
            protected or deploy_secret_status(origin, cfg),
            "Chủ tài khoản cấp quyền đích.",
            "Tạo các tên khai trong deploy_secrets từ hệ quản lý bí mật của dự án.",
            "GET actions/secrets (chỉ tên)",
        ),
        "worker-budget": lambda: row(
            "worker-budget",
            protected or state(budget_valid(cfg)),
            "Ngân sách thuộc người trả phí.",
            "Đặt worker_budget_usd và worker_max_turns dương trên main.",
            "xt.yaml trên nhánh chính",
        ),
        "worker-launcher": lambda: row(
            "worker-launcher",
            OK if origin.file(".github/workflows/worker.yml", repo_root=True) else UNKNOWN,
            "Nơi chạy worker do chủ dự án vận hành.",
            "Kiểm workflow worker.yml hoặc xác nhận lịch chạy ngoài repo.",
            "GET workflow trên nhánh chính; lịch ngoài repo cần kiểm tay",
        ),
        "security-updates": lambda: security_updates_item(origin),
        "repo-about": lambda: about_item(origin),
        "field-workflow": lambda: row(
            "field-workflow",
            field_workflow_status(origin),
            "xt-field.yml cần môi trường xt-field-read (giữ khoá đọc số field).",
            "Tạo environment xt-field-read trong Settings → Environments.",
            "GET environments",
        ),
    }
    return [make() for name, make in makers.items() if only is None or only == name]


def dev_snapshot(core: Core, base: Path) -> Doc:
    try:
        dev = core.read_deploy_ledger(base)["envs"].get("dev", {})
        dev_digest = field(dev.get("current"), "served_digest") if dev.get("unknown") is False else None
        dev_state = "deployed" if dev_digest else "absent"
    except core.DeployError:
        dev_state, dev_digest = "unreadable", None
    return {"state": dev_state, "digest": dev_digest}


def inventory(core: Core, base: Path, only: str | None = None) -> Doc:
    origin = Origin(core, base, load_config=only != "ruleset") if only not in LOCAL_ITEMS else None
    return {
        "schema": 1,
        "dev": dev_snapshot(core, base) if only is None else {"state": "not_checked", "digest": None},
        "items": (remote_items(origin, only) if origin else []) + local_items(core, base, only),
        "only": only,
        "head": core._git_head(base),
        "at": dt.datetime.now(dt.timezone.utc).date().isoformat(),
        "main_sha": origin.sha if origin else None,
    }


def markdown(doc: Doc) -> str:
    states = {"unreadable": "không đọc được", "not_checked": "không kiểm ở --only"}
    dev = doc["dev"]["digest"] or states.get(doc["dev"]["state"], "chưa có")
    lines = [f"# Thiết lập một lần — bản dev: {dev}", ""]
    todo = [i for i in doc["items"] if i["status"] in BLOCKS or i["id"] == doc.get("only")]
    if todo:
        lines.extend(["| Mục | Trạng thái | Vì sao | Việc cần làm | Máy kiểm |", "|---|---|---|---|---|"])
        lines.extend(f"| {i['id']} | {i['status']} | {i['reason']} | {i['action']} | {i['verify']} |" for i in todo)
    else:
        lines.append("Không còn việc thiết lập bắt buộc.")
    optional = [change for item in doc["items"] if item["status"] == OPTIONAL for change in item["changes"]]
    if optional:
        lines.extend(["", "## Tuỳ chọn — chủ dự án quyết", ""])
        lines.extend(f"- {change}" for change in optional)
    lines.extend(["", f"UTC {doc['at']} · HEAD {doc['head'] or '—'} · dev {dev}"])
    return "\n".join(lines) + "\n"


def owner_script(doc: Doc) -> str:
    lines = [
        "#!/bin/sh",
        "set -eu",
        "# Chủ repo chọn đúng kho trước khi tự chạy.",
        ': "${GH_REPO:?set GH_REPO to OWNER/REPO}"',
        'gh repo view "$GH_REPO" --json nameWithOwner',
        'printf "Nhập lại OWNER/REPO để tiếp tục: "',
        "read -r confirmed",
        '[ "$confirmed" = "$GH_REPO" ] || exit 1',
    ]
    items = {item["id"]: item["status"] for item in doc["items"]}
    if items.get("bot-token") == MISSING:
        lines.append('gh secret set XT_STEWARD_TOKEN --repo "$GH_REPO"')
    if items.get("ruleset") == MISSING:
        lines.extend(
            [
                "# Chọn XT_NEW_RULESET_FILE sau khi xem ruleset live. Nếu đã tồn tại, đặt XT_EXISTING_RULESET_ID để PUT.",
                "# Điền App ID phát hành thật vào tags-create.json rồi commit trước khi áp; tags.json không bypass.",
                "# Di trú: tạo ruleset tags-create trước; rồi PUT tags.json vào ID ruleset tag cũ để bỏ creation.",
                "# Không POST lại tên đã có: hai ruleset cũ/mới cùng tên không phải là cập nhật.",
                'if test -n "${XT_NEW_RULESET_FILE:-}"; then',
                "    XT_SETUP_SCRIPTS=.xtemplates/scripts",
                "    if test -f framework/00-method/README.md; then XT_SETUP_SCRIPTS=scripts; fi",
                '    test -f "$XT_SETUP_SCRIPTS/xt_ops_setup.py" || exit 2',
                '    python3 -I - "$XT_SETUP_SCRIPTS" "$XT_NEW_RULESET_FILE" <<\'PY\'',
                "import sys",
                "sys.path.insert(0, sys.argv[1])",
                "from xt_ops_setup import check_ruleset_file",
                "raise SystemExit(check_ruleset_file(sys.argv[2]))",
                "PY",
                "    export GH_REPO",
                '    case "${XT_EXISTING_RULESET_ID:-}" in',
                '      "")',
                '        gh api --method POST "repos/{owner}/{repo}/rulesets" --input "$XT_NEW_RULESET_FILE" ;;',
                "      0*|*[!0-9]*) exit 2 ;;",
                "      *)",
                '        gh api --method PUT "repos/{owner}/{repo}/rulesets/$XT_EXISTING_RULESET_ID" --input "$XT_NEW_RULESET_FILE" ;;',
                "    esac",
                "fi",
            ]
        )
    if items.get("security-updates") == MISSING:
        lines.append('gh api --method PUT "repos/$GH_REPO/automated-security-fixes"')
    lines.append("# Các mục còn lại dùng hướng dẫn trong admin-plan. Chạy lại admin-plan để kiểm.")
    return "\n".join(lines)


def command(core: Core, args: argparse.Namespace) -> int:
    if args.only is not None and args.only not in REMOTE_ITEMS + LOCAL_ITEMS:
        print(f"admin-plan: mục không hợp lệ: {args.only}", file=sys.stderr)
        return 2
    base = core.loop_root(core.project_dir())
    out = None
    if args.out:
        out = core._inside(base, args.out)
        if not out or out.suffix.lower() != ".md" or any(part.startswith(".") for part in out.relative_to(base).parts):
            return 2
        if out.exists() and not out.read_text(encoding="utf-8").startswith("# Thiết lập một lần — bản dev:"):
            return 2
    doc = inventory(core, base, args.only)
    if out:
        core.write_atomic(out, markdown(doc), keep_mode=True)
    print(json.dumps(doc, ensure_ascii=False) if args.json else owner_script(doc) if args.script else markdown(doc))
    return int(doc["dev"]["state"] == "unreadable" or any(i["status"] in BLOCKS for i in doc["items"]))
