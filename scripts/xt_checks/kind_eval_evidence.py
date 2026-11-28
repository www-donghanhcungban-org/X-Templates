"""Kiểm policy eval và bytes của từng artefact đã khai."""

from contextlib import contextmanager
from hashlib import sha256
import os
from pathlib import Path
import stat
from typing import Iterator, cast

from . import CheckError, CheckReport, Finding
from .kind_eval_report import Invalid, evaluate, read_payload, revision_ok, timestamp

HELP = "Đối chiếu chính sách eval và SHA-256 của artefact"
SUFFIXES = (".json",)
OPTS = ("policy", "revision", "at", "artifacts")
MAX_BLOB = 16 * 1024 * 1024
MAX_TOTAL = 128 * 1024 * 1024
MAX_DIGESTS = 4096
CHUNK = 64 * 1024


@contextmanager
def _directory(path: Path) -> Iterator[int]:
    if not path.is_absolute() or ".." in path.parts:
        raise CheckError("Kho artefact cần đường dẫn tuyệt đối, không có thành phần ..")
    if os.open not in os.supports_dir_fd or not all(
        hasattr(os, flag) for flag in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK")
    ):
        raise CheckError("Máy không hỗ trợ mở artefact tương đối theo descriptor và không theo liên kết")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(path.anchor, flags)
    try:
        for part in path.parts[1:]:
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


def _names(report: dict[str, object]) -> set[str]:
    identity = cast(dict[str, str], report["identity"])
    digests = {cast(str, report["content_sha256"])}
    digests.update(value for key, value in identity.items() if key.endswith("_sha256"))
    for case in cast(list[dict[str, object]], report["cases"]):
        digests.add(cast(str, case["evidence_sha256"]))
        if "infra_confirmation" in case:
            digests.add(cast(dict[str, str], case["infra_confirmation"])["evidence_sha256"])
    return digests


def _blob(fd: int, name: str, maximum: int) -> tuple[int, str]:
    file_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    seen = 0
    digest = sha256()
    try:
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            raise OSError("Artefact không phải tệp thường")
        while chunk := os.read(file_fd, min(CHUNK, maximum - seen + 1)):
            seen += len(chunk)
            if seen > maximum:
                return seen, "EVA002"
            digest.update(chunk)
        return seen, "" if digest.hexdigest() == name else "EVA001"
    except OSError:
        return seen, "EVA000"
    finally:
        os.close(file_fd)


def _check_artifacts(path: Path, names: set[str], checked: dict[str, int]) -> list[Finding]:
    checked["artifacts_expected"] = len(names)
    if len(names) > MAX_DIGESTS:
        return [Finding(str(path), 1, "EVA002", "Số digest vượt giới hạn")]
    findings = []
    with _directory(path) as fd:
        for name in sorted(names):
            remaining = MAX_TOTAL - checked["artifact_bytes_read"]
            try:
                seen, code = _blob(fd, name, min(MAX_BLOB, remaining))
            except OSError:
                seen, code = 0, "EVA000"
            checked["artifact_bytes_read"] += seen
            if code:
                findings.append(Finding(str(path / name), 1, code, "Không xác minh được bytes của artefact"))
                if checked["artifact_bytes_read"] > MAX_TOTAL:
                    break
            else:
                checked["artifacts_verified"] += 1
    return findings


def check_report(files: list[Path], opts: dict[str, str]) -> CheckReport:
    if len(files) != 1 or set(opts) != set(OPTS) or not all(opts.values()):
        raise CheckError("eval-evidence cần đúng một report và policy, revision, at, artifacts")
    if not revision_ok(opts["revision"]):
        raise CheckError("revision phải là SHA Git đầy đủ")
    try:
        timestamp(opts["at"])
    except Invalid as error:
        raise CheckError("at phải là thời điểm RFC 3339") from error
    report_path = files[0]
    checked = dict.fromkeys(("artifacts_expected", "artifacts_verified", "artifact_bytes_read"), 0)
    try:
        report = read_payload(report_path)
        policy = read_payload(Path(opts["policy"]))
    except (OSError, ValueError) as error:
        return CheckReport([Finding(str(report_path), 1, "EVR000", str(error))], checked)
    problems, metadata, validated = evaluate(report, policy, opts["revision"], opts["at"])
    checked.update(metadata)
    checked["report_policy_gates"] = checked["quality_gates"]
    checked["quality_gates"] = 0
    if validated is None or problems:
        return CheckReport([Finding(str(report_path), 1, code, message) for code, message in problems], checked)
    folder = Path(opts["artifacts"])
    try:
        findings = _check_artifacts(folder, _names(validated), checked)
    except (OSError, ValueError):
        findings = [Finding(str(folder), 1, "EVA000", "Không mở được kho artefact")]
    checked["quality_gates"] = int(not findings)
    return CheckReport(findings, checked)


def check(files: list[Path], opts: dict[str, str]) -> list[Finding]:
    return check_report(files, opts).findings
