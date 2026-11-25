"""Dựng starter tạm, kiểm tương phản và chạy ma trận UI thật cùng hai ca sai."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from xt import contrast_check, read_contrast_pairs

AXE = ROOT / "tests_e2e/vendor/axe/axe.min.js"
PREVIEW = "tests_e2e/pack_preview.py"
CSS = "src/notes-ui/app.css"
PAIRS = "src/notes-ui/contrast-pairs.txt"
HTML = "src/notes-ui/index.html"
EMAIL_LABEL = '<label for="email">Email</label>'
OVERFLOW = "\n@media (max-width: 320px) { .masthead { min-width: 640px; } }\n"


class PackUiFailure(ValueError):
    """Cổng thử có bằng chứng sai hoặc đối chứng bất ngờ đi qua."""


def pinned_axe() -> Path:
    source = AXE.with_name("SOURCE").read_text(encoding="utf-8")
    pins = [line.split()[2] for line in source.splitlines() if line.startswith("axe.min.js sha256: ")]
    if pins != [hashlib.sha256(AXE.read_bytes()).hexdigest()]:
        raise PackUiFailure("Digest axe.min.js không khớp SOURCE.")
    return AXE


def scaffold(project: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/install.py"),
            str(project),
            "--new",
            "--pack",
            "web-api-ts",
            "--idea",
            "Sổ ghi chú dùng để kiểm giao diện starter",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise PackUiFailure(f"Không dựng được starter, exit {result.returncode}.\n{result.stderr}")


def measure_contrast(project: Path) -> list[dict[str, object]]:
    pairs_text = (project / PAIRS).read_text(encoding="utf-8")
    declarations = [line for line in pairs_text.splitlines() if line.partition("#")[0].strip()]
    pairs = read_contrast_pairs(pairs_text)
    wanted = {(fg, bg, floor) for fg, bg, floor in pairs}
    if not wanted or len(wanted) != len(declarations):
        raise PackUiFailure("contrast-pairs.txt thiếu cặp, sai cú pháp hoặc có cặp trùng.")
    rows, missing = contrast_check((project / CSS).read_text(encoding="utf-8"), pairs_text)
    checked = {(row["fg"], row["bg"], row["min"]) for row in rows if row["status"] == "ok"}
    if missing or not wanted.issubset(checked) or any(row["status"] != "ok" for row in rows):
        failures = [row for row in rows if row["status"] != "ok"]
        raise PackUiFailure(
            f"Tương phản không đạt. Cặp chưa đạt hoặc chưa đo: {wanted - checked}. Kết quả lỗi: {failures}"
        )
    return rows


def browser_case(project: Path, axe: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, PREVIEW, "--ui-matrix", str(output), "--axe", str(axe)],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=180,
    )


def require_matrix(output: Path) -> None:
    expected = {
        f"{width}-{state}.png"
        for width in (1280, 390, 320)
        for state in ("login", "loading", "empty", "error", "success")
    }
    report = json.loads((output / "matrix.json").read_text(encoding="utf-8"))
    if report.get("schema") != 1 or report.get("result") != "passed":
        raise PackUiFailure("Biên bản Chromium thiếu kết quả đạt.")
    states = report.get("states")
    if not isinstance(states, list) or len(states) != len(expected):
        raise PackUiFailure("Biên bản Chromium thiếu các viewport hoặc trạng thái yêu cầu.")
    for state in states:
        file = f"{state['width']}-{state['state']}.png"
        if file not in expected or state["image"] != file or state["axe_passes"] <= 0:
            raise PackUiFailure(f"Biên bản Chromium có hàng sai hoặc chưa đo axe: {file}")
        expected.remove(file)
        with (output / file).open("rb") as image:
            if image.read(8) != b"\x89PNG\r\n\x1a\n":
                raise PackUiFailure(f"Ảnh Chromium sai định dạng PNG: {file}")


def require_control(result: subprocess.CompletedProcess[str], check: str, axe_rule: str = "") -> None:
    prefix = f"pack-ui: {check}: "
    details = [line.removeprefix(prefix) for line in result.stderr.splitlines() if line.startswith(prefix)]
    found = bool(details) and (not axe_rule or axe_rule in details[0].split(", "))
    if result.returncode != 1 or not found:
        raise PackUiFailure(f"Ca sai cần đỏ ở {check}, exit {result.returncode}.\n{result.stderr}")


def controls(project: Path, axe: Path, output: Path) -> dict[str, dict[str, object]]:
    css = project / CSS
    original = css.read_bytes()
    try:
        css.write_bytes(original + OVERFLOW.encode())
        overflow = browser_case(project, axe, output / "overflow")
        require_control(overflow, "320px/login/overflow")
    finally:
        css.write_bytes(original)

    html = project / HTML
    original = html.read_bytes()
    label = EMAIL_LABEL.encode()
    if original.count(label) != 1:
        raise PackUiFailure("Ca axe cần nhãn Email duy nhất để tạo đối chứng.")
    try:
        html.write_bytes(original.replace(label, b""))
        accessibility = browser_case(project, axe, output / "axe")
        require_control(accessibility, "1280px/login/axe", "label")
    finally:
        html.write_bytes(original)

    return {
        "overflow": {"exit_code": overflow.returncode, "finding": overflow.stderr.strip()},
        "axe": {"exit_code": accessibility.returncode, "finding": accessibility.stderr.strip()},
    }


def run(output: Path, axe: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="xt-pack-starter-") as temp:
        project = Path(temp) / "app"
        scaffold(project)
        contrast = measure_contrast(project)
        result = browser_case(project, axe, output / "good")
        if result.returncode != 0:
            raise PackUiFailure(f"Ca starter cần đạt, exit {result.returncode}.\n{result.stderr}")
        require_matrix(output / "good")
        negative_results = controls(project, axe, output)
    (output / "checks.json").write_text(
        json.dumps({"schema": 1, "contrast": contrast, "controls": negative_results}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="thư mục mới để lưu ảnh và kết quả")
    args = parser.parse_args()
    if importlib.util.find_spec("playwright") is None:
        print("pack-ui: chưa đo Chromium. Cài Playwright đã ghim từ requirements-e2e.txt.", file=sys.stderr)
        return 2
    try:
        axe = pinned_axe()
        if args.output is None:
            output = Path(tempfile.mkdtemp(prefix="xt-pack-ui-"))
        else:
            output = args.output.resolve()
            output.mkdir(parents=True, exist_ok=False)
        run(output, axe)
    except PackUiFailure as exc:
        print(f"pack-ui: {exc}", file=sys.stderr)
        return 1
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"pack-ui: chưa đo đủ ma trận: {exc}", file=sys.stderr)
        return 2
    print(f"Bằng chứng ma trận UI và hai ca đối chứng: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
