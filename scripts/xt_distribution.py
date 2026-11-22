"""Authenticated release sources and pull-based framework upgrades."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
from typing import Any
import unicodedata
from urllib.error import HTTPError
from urllib.request import Request, urlopen

CANONICAL = "www-donghanhcungban-org/X-Templates"
TAG = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
SLUG = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9][A-Za-z0-9._-]*")
UPGRADE_BRANCH = "chore/xt-upgrade"
MANIFEST = ".xtemplates/manifest.json"
WITHDRAWN = "docs/ops/WITHDRAWN-VERSIONS.txt"
TITLE = "chore(xt): nâng khung {}"
TITLE_VERSION = re.compile(r"chore\(xt\): nâng khung (\d+\.\d+\.\d+)")
# install.py ADAPTERS (destination → host), checked equal by tests/test_upgrade_bot.py.
ADAPTER_HOSTS = {
    ".codex/hooks.json": "codex",
    ".gemini/settings.json": "gemini",
    ".cursor/hooks.json": "cursor",
    ".github/hooks/xt.json": "copilot",
    ".grok/hooks/xt.json": "grok",
    ".opencode/plugins/xt.ts": "opencode",
}
# The only environment of the authenticated push: reach GitHub and let the credential helper read the bot's token.
PUSH_ENV = frozenset(
    ("PATH", "HOME", "TMPDIR", "SSL_CERT_FILE", "SSL_CERT_DIR", "HTTPS_PROXY", "https_proxy", "NO_PROXY", "no_proxy")
    + ("GH_HOST", "GH_TOKEN", "GITHUB_TOKEN")
)
# WF-DOC-021: chữ hiển thị trên GitHub của dự án đích mô tả dự án; khung chỉ có MỘT ghi chú nguồn (`adopted_note`).
ADOPTED = re.compile(r"Áp dụng từ phiên bản v?\d+\.\d+\.\d+ của dự án X-Templates", re.I)
MENTION = re.compile(r"x-templates", re.I)
SEMVER = re.compile(r"\d+\.\d+\.\d+")


def adopted_note(version: str, repo: object = None) -> str:
    """Ghi chú nguồn duy nhất ở dự án đích (`.xtemplates/README.md`, chân trang README của `--new`); repo sai dạng → CANONICAL."""
    slug = repo if isinstance(repo, str) and SLUG.fullmatch(repo) else CANONICAL
    found = SEMVER.search(version)
    ver = found[0] if found else version.strip().removeprefix("v").removeprefix("V")
    return f"Áp dụng từ phiên bản v{ver} của dự án X-Templates (https://github.com/{slug})."


URL_TAIL = re.compile(
    r"\(?https:/{2}github\.com/[\w.-]+/[\w.-]+\)?\.?"
)  # `:/{2}`: BASE-CFG-001 cấm URL literal trong mã


def stray_mentions(text: str) -> list[int]:
    """Số dòng (từ 1) nhắc X-Templates ngoài dòng ghi chú nguồn hợp lệ (chuẩn hoá NFC). Ghi chú chuẩn dài 108 ký tự nên
    công cụ ngắt dòng có thể tách riêng đoạn URL xuống dòng sau: dòng chỉ gồm URL ngay sau dòng ghi chú không bị báo."""
    lines = unicodedata.normalize("NFC", text).splitlines()
    hits: list[int] = []
    for n, line in enumerate(lines, 1):
        if not MENTION.search(line) or ADOPTED.search(line):
            continue
        if n > 1 and ADOPTED.search(lines[n - 2]) and URL_TAIL.fullmatch(line.strip()):
            continue
        hits.append(n)
    return hits


class DistributionError(ValueError):
    def __init__(self, message: str, code: int = 3):
        super().__init__(message)
        self.code = code


def command(
    cwd: Path, *argv: str, check: bool = True, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=300, env=env)
    if check and result.returncode:
        raise DistributionError(f"{argv[0]} {argv[1]}: {result.stderr.strip() or 'lệnh thất bại'}")
    return result


def read_manifest(base: Path) -> dict[str, Any]:
    contents = json.loads((base / MANIFEST).read_text(encoding="utf-8"))
    if not isinstance(contents, dict):
        raise DistributionError("manifest cần là object")
    return contents


def repo_slug(url: str) -> str:
    slug = url.removeprefix("https://github.com/").removeprefix("git@github.com:").removesuffix(".git")
    if not url.startswith(("https://github.com/", "git@github.com:")) or not SLUG.fullmatch(slug):
        raise DistributionError("nguồn cài cần là repository trên github.com")
    return slug


def framework_repo(manifest: dict[str, Any]) -> str:
    source = manifest.get("source", {})
    repo = source.get("repo", CANONICAL) if isinstance(source, dict) else None
    if not isinstance(repo, str) or not SLUG.fullmatch(repo):
        raise DistributionError("source.repo không hợp lệ")
    return repo


def clone_source(temp: Path, repo: str) -> Path:
    if not SLUG.fullmatch(repo):
        raise DistributionError("repo cần có dạng owner/name", 2)
    git = temp / "upstream.git"
    # Bare clone fetches all tags and the default branch without checking out any upstream content.
    command(temp, "git", "clone", "--quiet", "--bare", "--", f"https://github.com/{repo}.git", str(git))
    return git


def verified_archive(git: Path, repo: str, tag: str, temp: Path, promotion: bool = False) -> tuple[str, Path]:
    if not TAG.fullmatch(tag):
        raise DistributionError("tag cần có dạng vX.Y.Z", 2)
    ref = f"refs/tags/{tag}"
    git_type = command(git, "git", "cat-file", "-t", ref, check=False)
    if git_type.stdout.strip() != "tag":
        raise DistributionError(f"{tag} thiếu annotated tag", 1)
    head = command(git, "git", "rev-parse", f"{ref}^{{commit}}").stdout.strip()
    ancestry = command(git, "git", "merge-base", "--is-ancestor", head, "HEAD", check=False)
    if ancestry.returncode:
        raise DistributionError(f"{tag} chưa xác nhận trong lịch sử nhánh chính", 1 if ancestry.returncode == 1 else 3)
    version = command(git, "git", "show", f"{head}:VERSION", check=False)
    if version.returncode or version.stdout.strip() != tag[1:]:
        raise DistributionError(f"VERSION ở {tag} không khớp tên tag", 1)
    artifact = temp / f"X-Templates-{tag}.tar.gz"
    command(git, "git", "archive", "--format=tar.gz", f"--prefix=X-Templates-{tag}/", "-o", str(artifact), head)
    verify_signature(temp, repo, artifact)
    if promotion:
        with artifact.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        receipt = temp / f"X-Templates-{tag}.promotion.json"
        receipt.write_bytes(
            (
                json.dumps(
                    {"repo": repo.casefold(), "tag": tag, "commit": head, "sha256": digest, "promotion": "approved"},
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("ascii")
        )
        verify_signature(temp, repo, receipt)
    return head, artifact


def public_bundles(temp: Path, repo: str, artifact: Path) -> Path:
    """Fetch the bundles associated with the live public repository, then let gh verify offline without a login."""
    with artifact.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    output = temp / (artifact.name + ".jsonl")
    page = 1
    with output.open("w", encoding="utf-8") as dest:
        while True:
            url = f"https://api.github.com/repos/{repo}/attestations/sha256:{digest}?per_page=100&page={page}"
            try:
                with urlopen(Request(url, headers={"Accept": "application/vnd.github+json"}), timeout=30) as response:
                    payload = json.load(response)
                    records = payload.get("attestations") if isinstance(payload, dict) else None
            except HTTPError as exc:
                if exc.code == 404:
                    raise DistributionError(f"{artifact.name}: không có attestation", 1) from exc
                raise
            if not isinstance(records, list):
                raise DistributionError("GitHub trả danh sách attestation không hợp lệ")
            for record in records:
                if not isinstance(record, dict) or not isinstance(record.get("bundle"), dict):
                    raise DistributionError("GitHub trả attestation bundle không hợp lệ")
                dest.write(json.dumps(record["bundle"]) + "\n")
            if len(records) < 100:
                break
            page += 1
    if not output.stat().st_size:
        raise DistributionError(f"{artifact.name}: không có attestation", 1)
    return output


def verify_signature(temp: Path, repo: str, artifact: Path) -> None:
    signer = f"https://github.com/{repo}/.github/workflows/release-tag.yml@refs/heads/main"
    offline = (
        []
        if os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
        else ["--bundle", str(public_bundles(temp, repo, artifact))]
    )
    verify = command(
        temp,
        "gh",
        "attestation",
        "verify",
        str(artifact),
        "--repo",
        repo,
        "--cert-identity",
        signer,
        "--source-ref",
        "refs/heads/main",
        *offline,
        check=False,
    )
    if verify.returncode:
        diagnostic = verify.stderr.strip()
        missing = re.search(
            r"no attestations? (?:were )?found|no matching attestations|failed to verify any attestations",
            diagnostic,
            re.I,
        )
        raise DistributionError(
            f"{artifact.name}: chưa xác minh attestation của workflow phát hành. {diagnostic}", 1 if missing else 3
        )


def matches_checkout(src: Path, tag: str, archive: Path) -> bool:
    """Git index flags and checkout filters can hide differences. Read the actual files that install.py will copy."""
    prefix = f"X-Templates-{tag}/"
    paths = set(command(src, "git", "ls-files", "-z").stdout.split("\0")[:-1])
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle:
            if member.isdir():
                continue
            name = member.name.removeprefix(prefix)
            paths.discard(name)
            path = src / name
            if member.issym():
                if not path.is_symlink() or os.readlink(path) != member.linkname:
                    return False
            else:
                data = bundle.extractfile(member)
                if data is None or path.is_symlink() or data.read() != path.read_bytes():
                    return False
    return not paths


def install_source(src: Path) -> dict[str, Any]:
    """A label cannot confer provenance. Untracked/modified installer input also keeps the receipt unverified."""
    source: dict[str, Any] = {"untagged": "unknown"}
    try:
        top = command(src, "git", "rev-parse", "--show-toplevel").stdout.strip()
        if Path(top).resolve() != src.resolve():
            return source
        head = command(src, "git", "rev-parse", "HEAD").stdout.strip()
        source = {"untagged": head}
        version = (src / "VERSION").read_text(encoding="utf-8").strip()
        tag = "v" + version
        if not TAG.fullmatch(tag) or tag not in command(src, "git", "tag", "--points-at", head).stdout.splitlines():
            return source
        repo = repo_slug(command(src, "git", "remote", "get-url", "origin").stdout.strip())
        source = {"repo": repo, "tag": tag, "commit": head, "verified": False}
        dirty = command(src, "git", "status", "--porcelain", "--ignored", "--untracked-files=all").stdout.splitlines()
        if any("/__pycache__/" not in line or not line.endswith(".pyc") for line in dirty):
            return source
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            signed_head, archive = verified_archive(clone_source(temp, repo), repo, tag, temp)
            source["verified"] = signed_head == head and matches_checkout(src, tag, archive)
    except OSError, ValueError, subprocess.SubprocessError:
        pass  # a normal development install remains usable offline
    return source


def withdrawn_tags(git: Path) -> set[str]:
    withdrawn = set()
    if command(git, "git", "ls-tree", "HEAD", "--", WITHDRAWN).stdout:
        for line in command(git, "git", "show", f"HEAD:{WITHDRAWN}").stdout.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                version = line.split()[0]
                if not TAG.fullmatch("v" + version):
                    raise DistributionError(f"{WITHDRAWN} có phiên bản không hợp lệ")
                withdrawn.add("v" + version)
    return withdrawn


def tags_for_wave(git: Path, installed: str, wave: str, soak: int, now: int) -> tuple[bool, list[str]]:
    current = TAG.fullmatch("v" + installed.partition(" ")[0].strip())
    if not current or wave not in {"canary", "after-canary"} or soak < 0:
        raise DistributionError("VERSION, upgrade_wave hoặc upgrade_soak_days không hợp lệ", 2)
    withdrawn = withdrawn_tags(git)
    listing = command(git, "git", "for-each-ref", "--format=%(refname:strip=2) %(taggerdate:unix)", "refs/tags").stdout
    newer = False
    eligible = []
    for line in listing.splitlines():
        tag, _, age = line.partition(" ")
        match = TAG.fullmatch(tag)
        if not match:
            continue
        number = tuple(map(int, match.groups()))
        if number > tuple(map(int, current.groups())):
            newer = True
            if tag not in withdrawn and age.isdecimal() and (wave == "canary" or now - int(age) >= soak * 86400):
                eligible.append((number, tag))
    return newer, [tag for _, tag in sorted(eligible, reverse=True)]


def install_options(manifest: dict[str, Any]) -> list[str]:
    """Reinstall with the adapters and harness choice recorded by the original install (the preset is kept by install.py).
    Never install git hooks in the bot clone: they would run the product commit gate inside the upgrade job."""
    recorded = manifest.get("adapters")
    paths = [path for path in recorded if isinstance(path, str)] if isinstance(recorded, list) else []
    hosts = {ADAPTER_HOSTS[path] for path in paths if path in ADAPTER_HOSTS}
    hosts |= {"codex"} if manifest.get("codex_files") else set()
    files = manifest.get("files")
    harness = not isinstance(files, dict) or not files or any(str(path).startswith(".claude/") for path in files)
    return [
        "--with-github",
        "--no-git-hooks",
        *(["--harness", ",".join(sorted(hosts))] if hosts else []),
        *([] if harness else ["--no-harness"]),
    ]


def remote_env() -> dict[str, str]:
    """The only environment that holds the bot's token: reach GitHub, let the credential helper authenticate."""
    return {k: v for k, v in os.environ.items() if k in PUSH_ENV} | {"GIT_TERMINAL_PROMPT": "0"}


def push_branch(project: Path, url: str, hooks: Path, local_env: dict[str, str]) -> None:
    """Publish from a fresh bare repository that never ran installer or product code, with hooks off. The working clone
    itself never sees the bot credentials."""
    clean = project.parent / "publish.git"
    ref = f"refs/heads/{UPGRADE_BRANCH}"
    command(project.parent, "git", "init", "--quiet", "--bare", f"--template={hooks}", str(clean), env=local_env)
    command(
        project, "git", "-c", f"core.hooksPath={hooks}", "push", "--quiet", str(clean), f"HEAD:{ref}", env=local_env
    )
    command(clean, "git", "-c", f"core.hooksPath={hooks}", "push", "--quiet", url, f"{ref}:{ref}", env=remote_env())


def publish_upgrade(base: Path, repo: str, tag: str, head: str, archive: Path, temp: Path) -> None:
    """Build a reviewable PR in an isolated clone. Existing upgrade branches advance by fast-forward."""
    origin = repo_slug(command(base, "git", "remote", "get-url", "origin").stdout.strip())
    url = f"https://github.com/{origin}.git"
    project = temp / "project"
    command(temp, "git", "clone", "--quiet", "--", url, str(project), env=remote_env())
    # Nothing runs in the working clone with the bot's token, not even read-only git commands.
    local_env = {k: v for k, v in os.environ.items() if k not in {"GH_TOKEN", "GITHUB_TOKEN", "XT_STEWARD_TOKEN"}}
    branch = command(project, "git", "branch", "--show-current", env=local_env).stdout.strip()
    if branch == UPGRADE_BRANCH:
        raise DistributionError("nhánh nâng khung phải khác nhánh mặc định")
    ref = f"refs/remotes/origin/{UPGRADE_BRANCH}"
    old = command(project, "git", "rev-parse", "--verify", ref, check=False, env=local_env)
    manifest = read_manifest(project)
    packs = manifest.get("packs", {})
    if not isinstance(packs, dict):
        raise DistributionError("manifest.packs không hợp lệ", 2)
    label = (project / ".xtemplates/VERSION").read_text(encoding="utf-8").split()[:1]
    if (
        framework_repo(manifest) != repo
        or label != (base / ".xtemplates/VERSION").read_text(encoding="utf-8").split()[:1]
    ):
        raise DistributionError("nhánh chính của dự án đã đổi nguồn hoặc phiên bản, kiểm lại trước khi nâng")
    hooks = temp / "no-hooks"  # empty: overrides .git/hooks and any core.hooksPath of the clone or global config
    hooks.mkdir()
    git = ("git", "-c", f"core.hooksPath={hooks}")
    if not old.returncode:
        # Base the new review tree on the protected default branch; retain the old bot branch as a parent.
        command(project, *git, "merge", "--no-commit", "--no-ff", "-s", "ours", old.stdout.strip(), env=local_env)
    # Run only installer bytes from the verified archive. Never execute the default branch or a PR checkout upstream.
    with tarfile.open(archive, "r:gz") as bundle:
        bundle.extractall(temp / "release", filter="data")
    release = temp / "release" / f"X-Templates-{tag}"
    for pack in list(packs) or [None]:
        options = (["--pack", pack] if pack is not None else []) + install_options(manifest)
        command(project, sys.executable, str(release / "scripts/install.py"), ".", *options, env=local_env)
    installed = read_manifest(project)
    installed["source"] = {"repo": repo, "tag": tag, "commit": head, "verified": True}
    (project / MANIFEST).write_text(
        json.dumps(installed, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    command(project, *git, "add", "--all", env=local_env)
    if (project / "BLUEPRINT.md").is_file():
        # Parse only. `— Kiểm:` commands are product code: the PR's own CI runs them, never this job.
        command(project, sys.executable, ".xtemplates/scripts/xt.py", "blueprint-status", "BLUEPRINT.md", env=local_env)
    tree = command(project, "git", "write-tree", env=local_env).stdout.strip()
    title = TITLE.format(tag[1:])
    if (
        old.returncode
        or tree != command(project, "git", "rev-parse", f"{old.stdout.strip()}^{{tree}}", env=local_env).stdout.strip()
    ):
        command(project, *git, "commit", "--no-verify", "-m", title, env=local_env)
        push_branch(project, url, hooks, local_env)
    open_or_update_pr(origin, branch, title, f"Nâng khung lên {repo}@{head} ({tag}).", release, tag, temp)


def open_or_update_pr(origin: str, branch: str, title: str, intro: str, release: Path, tag: str, temp: Path) -> None:
    body = temp / "pr-body.md"
    changes = (release / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(rf"^## \[{re.escape(tag[1:])}\][^\n]*\n(.*?)(?=^## |\Z)", changes, re.M | re.S)
    body.write_text(f"{intro}\n\n" + (match[1].strip() if match else tag), encoding="utf-8")
    query = f"repos/{origin}/pulls?state=open&base={branch}&head={origin.split('/')[0]}:{UPGRADE_BRANCH}"
    prs = json.loads(command(temp, "gh", "api", query).stdout)
    if prs:
        command(
            temp,
            "gh",
            "pr",
            "edit",
            str(prs[0]["number"]),
            "--repo",
            origin,
            "--title",
            title,
            "--body-file",
            str(body),
        )
    else:
        command(
            temp,
            *("gh", "pr", "create", "--repo", origin, "--base", branch, "--head", UPGRADE_BRANCH),
            *("--title", title, "--body-file", str(body)),
        )


def withdrawn_pr(base: Path, withdrawn: set[str]) -> tuple[str, int, str] | None:
    """Open upgrade PR whose title names a withdrawn version. Best effort: a token that cannot list PRs only warns, so
    projects still on an older workflow keep receiving upgrades (the PR's CI and merge lane stay the gate)."""
    if not withdrawn:
        return None
    origin = repo_slug(command(base, "git", "remote", "get-url", "origin").stdout.strip())
    query = f"repos/{origin}/pulls?state=open&head={origin.split('/')[0]}:{UPGRADE_BRANCH}"
    listing = command(base, "gh", "api", query, check=False)
    if listing.returncode:
        print(f"Không đọc được PR nâng khung đang mở: {listing.stderr.strip()}", file=sys.stderr)
        return None
    for pr in json.loads(listing.stdout):
        match = TITLE_VERSION.fullmatch(str(pr.get("title"))) if isinstance(pr, dict) else None
        if match and "v" + match[1] in withdrawn:
            return origin, int(pr["number"]), "v" + match[1]
    return None


def close_withdrawn(action: str, base: Path, git: Path, temp: Path) -> int | None:
    """Close (reversibly, the branch stays) an open upgrade PR whose version was withdrawn after it was opened."""
    stale = withdrawn_pr(base, withdrawn_tags(git))
    if stale is None:
        return None
    origin, number, tag = stale
    if action == "check":
        print(f"PR #{number} nâng khung {tag} trỏ bản đã thu hồi; open-pr đóng PR này.")
        return 10
    note = f"Bản {tag} đã bị thu hồi ở nguồn ({WITHDRAWN}). Đóng PR; lần chạy sau mở PR mới khi có bản hợp lệ."
    command(temp, "gh", "pr", "close", str(number), "--repo", origin, "--comment", note)
    print(f"Đã đóng PR #{number}: {tag} bị thu hồi")
    return 0


def upgrade(core: Any, action: str, base: Path, temp: Path) -> int:
    manifest = read_manifest(base)
    repo = framework_repo(manifest)
    git = clone_source(temp, repo)
    keys = core._xt_keys(base)
    wave = keys.get("upgrade_wave", "after-canary")
    soak = int(keys.get("upgrade_soak_days", "3"))
    label = (base / ".xtemplates/VERSION").read_text(encoding="utf-8")
    newer, tags = tags_for_wave(git, label, wave, soak, int(dt.datetime.now(dt.UTC).timestamp()))
    for tag in tags:
        try:
            head, archive = verified_archive(git, repo, tag, temp, promotion=True)
        except DistributionError as exc:
            if exc.code != 1:
                raise
            print(exc, file=sys.stderr)
            continue
        if action == "check":
            print(tag)
            return 10
        # A newer valid tag replaces the tree of an open PR, including one built from a now withdrawn version.
        publish_upgrade(base, repo, tag, head, archive, temp)
        print(f"PR nâng khung {tag} đã sẵn sàng")
        return 0
    closed = close_withdrawn(action, base, git, temp)
    if closed is not None:
        return closed
    print(
        "Có bản mới nhưng chưa đủ tuổi hoặc thiếu bản chưa thu hồi có attestation hợp lệ."
        if newer
        else "Không có bản mới."
    )
    return 11 if newer else 0


def run(core: Any, args: argparse.Namespace) -> int:
    base = Path.cwd()
    try:
        with tempfile.TemporaryDirectory(prefix="xt-release-") as directory:
            temp = Path(directory)
            if args.cmd == "release-verify":
                repo = args.repo
                git = clone_source(temp, repo)
                head, _ = verified_archive(git, repo, args.tag, temp)
                print(f"{repo} {args.tag} {head}: attestation hợp lệ")
                return 0
            return upgrade(core, args.upgrade_action, base, temp)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(exc, file=sys.stderr)
        return exc.code if isinstance(exc, DistributionError) else 3
