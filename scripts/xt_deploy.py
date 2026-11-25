"""Verify configured deployments against the remote default branch and retain read-back artifacts."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Callable, Protocol
from urllib.parse import urlsplit

import xt_ops_setup
import xt_release_ops

Doc = dict[str, Any]


class Core(xt_release_ops.Core, Protocol):
    DEPLOY_LEDGER: str
    DEPLOY_ENV_DROP: frozenset[str]
    DEPLOY_ENV_DROP_PREFIX: tuple[str, ...]
    DEPLOY_ENV_SYSTEM: tuple[str, ...]
    GO_GIT_KEEP_ENV: tuple[str, ...]
    _go_git: Callable[..., str]
    _validate_deploy_ledger: Callable[[Any], Doc]


# Danh sách khai tường minh cho phép một số tuỳ chọn trình thông dịch đã bị lọc khỏi môi trường thừa kế.
_ENV_NEVER = frozenset({"BASH_ENV", "ENV", "SHELLOPTS", "BASHOPTS", "PS4"})
_ENV_NEVER_PREFIX = ("LD_", "DYLD_", "BASH_FUNC_", "XT_DEPLOY_")
_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_NULL_MARKERS = ("null", "Null", "NULL", "~")


def _check_env_names(core: Core, names: Sequence[str]) -> None:
    for name in names:
        forbidden_git = name.startswith("GIT_") and name not in core.GO_GIT_KEEP_ENV
        if (
            not _ENV_NAME.fullmatch(name)
            or name in _NULL_MARKERS
            or name in _ENV_NEVER
            or name.startswith(_ENV_NEVER_PREFIX)
            or forbidden_git
        ):
            raise core.DeployError(f"xt.yaml: deploy_env_pass có tên không hợp lệ hoặc không được phép qua: {name}")


def env_pass_names(core: Core, value: str) -> tuple[str, ...]:
    names = tuple(dict.fromkeys(name for name in re.split(r"[\s,]+", value) if name))
    _check_env_names(core, names)
    return names


def command_env(core: Core, environ: Mapping[str, str], names: Sequence[str] | None) -> dict[str, str]:
    """Môi trường dùng chung cho deploy, smoke, digest và rollback. Chỉ nêu tên khi thiếu biến."""
    if names is None:
        return {
            k: v
            for k, v in environ.items()
            if k not in core.DEPLOY_ENV_DROP and not k.startswith(core.DEPLOY_ENV_DROP_PREFIX)
        }
    _check_env_names(core, names)
    missing = [name for name in names if name not in environ]
    if missing:
        raise core.DeployError(f"deploy_env_pass khai {', '.join(missing)} nhưng môi trường chạy không có biến đó")
    return {k: environ[k] for k in (*core.DEPLOY_ENV_SYSTEM, *names) if k in environ}


def receipt_url(value: str) -> str | None:
    if not value:
        return None
    url = urlsplit(value)
    if url.scheme not in {"http", "https"} or not url.hostname or url.username is not None or url.query or url.fragment:
        raise ValueError("url môi trường phải là HTTP(S), không chứa thông tin đăng nhập, query hoặc fragment")
    return value


def artifact_root(state: Path, digest: str) -> Path:
    root = state / "artifacts" / digest
    if root.resolve() != root:
        raise ValueError("thư mục lưu artifact đi qua symlink")
    return root


def artifact_file(root: Path, name: str) -> Path:
    path = root / name
    if (
        not name
        or Path(name).is_absolute()
        or Path(name).as_posix() != name
        or ".." in Path(name).parts
        or path.resolve() != path
        or not path.is_relative_to(root)
        or ".git" in Path(name).parts
    ):
        raise ValueError("đường dẫn artifact phải là file tương đối trong dự án")
    return path


def verify_artifacts(root: Path, digest: str, arts: list[Doc]) -> None:
    manifest = hashlib.sha256()
    names = set()
    for item in sorted(arts, key=lambda a: a["path"]):
        name = item["path"]
        path = artifact_file(root, name)
        if name in names or not path.is_file():
            raise ValueError("thiếu hoặc trùng artifact đã lưu")
        names.add(name)
        with path.open("rb") as stream:
            observed = hashlib.file_digest(stream, "sha256").hexdigest()
        if observed != item["sha256"]:
            raise ValueError("artifact đã lưu sai SHA-256")
        manifest.update(f"{name}\0{observed}\n".encode())
    if not names or manifest.hexdigest() != digest:
        raise ValueError("bộ artifact đã lưu không khớp digest receipt")


def retain_artifacts(base: Path, state: Path, digest: str, arts: list[Doc]) -> None:
    final = artifact_root(state, digest)
    if not final.exists():
        final.parent.mkdir(mode=0o700, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=final.parent) as temp:
            dest = Path(temp) / "candidate"
            for item in arts:
                source = artifact_file(base, item["path"])
                target = artifact_file(dest, item["path"])
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                if not source.is_file():
                    raise ValueError("artifact nguồn không phải file")
                shutil.copyfile(source, target)
            verify_artifacts(dest, digest, arts)
            dest.rename(final)
    verify_artifacts(final, digest, arts)


def clean_adapter_checkout(core: Core, base: Path, destination: Path, head: str) -> Path:
    """Run promoted commands from the reviewed Git tree. Ignored files in the build checkout are not executable inputs."""
    tree = destination / "source"
    core._go_git(
        destination,
        "không tạo được checkout của adapter",
        "clone",
        "-q",
        "--no-local",
        "--no-checkout",
        "--template=",
        "--",
        str(base),
        str(tree),
    )
    core._go_git(
        tree, "không đọc được commit adapter", "-c", "core.hooksPath=/dev/null", "checkout", "-q", "--detach", head
    )
    return tree


def materialize_artifacts(saved: Path, checkout: Path, paths: tuple[str, ...]) -> None:
    for name in paths:
        dest = artifact_file(checkout, name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact_file(saved, name), dest)


def production_authority(core: Core, base: Path, env: str, head: str, ledger: Doc) -> xt_ops_setup.Origin:
    clean, actual, readable = core._release_tree(base)
    if not readable or clean["result"] != "PASS" or actual != head:
        raise ValueError("production cần checkout sạch, đúng HEAD")
    return remote_authority(core, base, env, head, ledger["envs"], (base / "xt.yaml").read_text(encoding="utf-8"))


def remote_authority(core: Core, base: Path, env: str, head: str, envs: Doc, config_text: str) -> xt_ops_setup.Origin:
    origin = xt_ops_setup.Origin(core, base)
    target = xt_ops_setup.target(origin, env)
    if not target["remote_grant"]:
        raise ValueError(f"thiếu grant deploy env={env} trên nhánh mặc định của origin")
    if not target["target_adapter"] or origin.file("xt.yaml") != config_text:
        raise ValueError("cấu hình adapter không khớp nhánh mặc định hiện hành")
    relation = origin.get(f"compare/{head}...{origin.sha}")
    if not isinstance(relation, dict) or relation.get("status") not in {"ahead", "identical"}:
        raise ValueError("HEAD chưa nằm trong nhánh chính của remote")
    upstream = origin.file(core.DEPLOY_LEDGER)
    if upstream is None or core._validate_deploy_ledger(json.loads(upstream))["envs"] != envs:
        raise ValueError("sổ triển khai chưa khớp nhánh chính của remote")
    return origin


def approve_candidate(core: Core, base: Path, env: str, subject: Doc, ledger: Doc) -> None:
    dev = ledger["envs"].get("dev", {}).get("current")
    if not dev or dev["result"] != "deployed" or not xt_release_ops.matches(subject, dev["subject"]):
        raise ValueError("dev.current chưa xác nhận đúng content và digest của ứng viên")
    report = core.release_check(base, core.RELEASE_SIGN_BLUEPRINT, core.RELEASE_SIGN_STATUS)
    if (
        report["verdict"] != "GO"
        or report["promotion"]["state"] != "approved"
        or any(report["subject"].get(k) != v for k, v in subject.items())
    ):
        raise ValueError("promotion chưa approved cho đúng HEAD, content và digest")
    origin = production_authority(core, base, env, subject["head"], ledger)
    if not xt_release_ops.protected_signoff(core, base, origin, subject):
        raise ValueError("chữ ký GO cho ứng viên không còn hiệu lực trên nhánh mặc định")
