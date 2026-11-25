"""Kiểm luồng ghi chú trên bản dev của dự án sinh từ gói web-api-ts.

Chạy từ gốc dự án sau `xt.py deploy run --env dev`. File bằng chứng chỉ ghi sau khi trình duyệt
thấy dữ liệu đã lưu trong hai phiên tách biệt và bản đang phục vụ khớp artifact đã kiểm.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

from playwright.sync_api import Browser, BrowserContext, Error, Page, Route, expect, sync_playwright


PREVIEW_ORIGIN = "http://127.0.0.1:4317"


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def confirmed_candidate() -> tuple[dict, str]:
    ledger = json.loads(Path("docs/ops/DEPLOYS.json").read_text(encoding="utf-8"))
    state = ledger["envs"]["dev"]
    current = state["current"]
    require(not state["unknown"] and current["result"] == "deployed", "Chưa có bản dev được xác nhận")
    require(current["url"] == PREVIEW_ORIGIN, "Receipt phải trỏ đúng origin của adapter preview")
    digest = hashlib.sha256(Path("dist/app.tgz").read_bytes()).hexdigest()
    artifacts = {a["path"]: a["sha256"] for a in current["artifacts"]}
    require(artifacts.get("dist/app.tgz") == digest, "Artifact cục bộ khác receipt")
    return current, digest


def preview_request(route: Route) -> None:
    # Kiểm từng request và không cho một phản hồi redirect chuyển request đã duyệt sang origin khác.
    if not route.request.url.startswith(PREVIEW_ORIGIN + "/"):
        route.abort()
        return
    response = route.fetch(max_redirects=0)
    try:
        if 300 <= response.status < 400:
            route.abort()
        else:
            route.fulfill(response=response)
    finally:
        response.dispose()


def preview_context(browser: Browser) -> BrowserContext:
    context = browser.new_context(service_workers="block")
    context.route("**/*", preview_request)
    # Gói notes dùng HTTP. Phiên có tài khoản thử không cần mở WebSocket.
    context.route_web_socket("**/*", lambda socket: socket.close())
    return context


def login(page: Page, account: dict[str, str]) -> None:
    page.goto(PREVIEW_ORIGIN + "/")
    require(page.url == PREVIEW_ORIGIN + "/", "Trang đăng nhập phải thuộc origin preview")
    page.locator("#email").fill(account["email"])
    page.locator("#password").fill(account["password"])
    with page.expect_response(lambda r: r.url == PREVIEW_ORIGIN + "/v1/login" and r.request.method == "POST") as result:
        page.locator("#login-form").get_by_role("button", name="Đăng nhập").click()
    require(result.value.status == 200, "Không đăng nhập được vào API")
    expect(page.locator("#note-form")).to_be_visible()


def served_digest(context: BrowserContext, expected_digest: str) -> str:
    health_url = PREVIEW_ORIGIN + "/healthz"
    health = context.request.get(health_url, max_redirects=0)
    require(health.url == health_url and health.status == 200, "HTTP /healthz không thành công")
    observed = health.json()["digest"]
    require(observed == expected_digest, "Digest HTTP khác ứng viên")
    return observed


def browser_flow(expected_digest: str, account: dict[str, str]) -> str:
    body = "Kiểm thử ghi chú " + uuid4().hex
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.environ.get("XT_E2E_CHROMIUM"))
        with preview_context(browser) as first:
            observed = served_digest(first, expected_digest)
            page = first.new_page()
            login(page, account)
            page.locator("#note-body").fill(body)
            with page.expect_response(
                lambda r: r.url == PREVIEW_ORIGIN + "/v1/notes" and r.request.method == "POST"
            ) as saved:
                page.locator("#note-form").get_by_role("button", name="Lưu ghi chú").click()
            require(saved.value.status == 201, "API chưa tạo ghi chú")
            note = saved.value.json()
            require(note["body"] == body and bool(note["id"]), "API trả ghi chú khác nội dung đã nhập")
            expect(page.locator("#notes-list")).to_contain_text(body)
        with preview_context(browser) as second:
            page = second.new_page()
            with page.expect_response(
                lambda r: r.url == PREVIEW_ORIGIN + "/v1/notes" and r.request.method == "GET"
            ) as loaded:
                login(page, account)
            require(loaded.value.status == 200, "Không lấy lại được ghi chú từ API")
            matches = [item for item in loaded.value.json()["notes"] if item["id"] == note["id"]]
            require(len(matches) == 1 and matches[0]["body"] == body, "Ghi chú không tồn tại ở phiên mới")
            expect(page.locator("#notes-list")).to_contain_text(body)
        browser.close()
    return observed


def preview_receipt(output: Path) -> None:
    start = time.monotonic()
    current, artifact = confirmed_candidate()
    result = subprocess.run(
        ["node", "scripts/dev-preview.mjs", "credentials"], capture_output=True, text=True, check=True, timeout=10
    )
    account = json.loads(result.stdout)["owner"]
    observed = browser_flow(current["subject"]["digest"], account)
    require(current["served_digest"] == observed, "Digest HTTP không khớp receipt")
    run_url = os.environ.get("GITHUB_RUN_ID")
    if run_url:
        run_url = f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{run_url}"
    proof = {
        "schema": 1,
        "result": "passed",
        "subject": current["subject"],
        "served_digest": observed,
        "artifact_sha256": artifact,
        "checks": ["login", "create-note", "reload-note"],
        "elapsed_seconds": round(time.monotonic() - start, 3),
        "run_url": run_url,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent, delete_on_close=False) as draft:
        json.dump(proof, draft, ensure_ascii=False, indent=2)
        draft.write("\n")
        draft.close()
        os.link(draft.name, output)
    print(f"Đã xác nhận luồng ghi chú ở bản {observed}.")


def ui_matrix(axe: Path, output: Path) -> int:
    from pack_ui_matrix import MatrixFailure, matrix

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=os.environ.get("XT_E2E_CHROMIUM") or None)
            try:
                matrix(browser, PREVIEW_ORIGIN, axe, output)
            finally:
                browser.close()
    except (MatrixFailure, AssertionError) as exc:
        print(f"pack-ui: {exc}", file=sys.stderr)
        return 1
    except (Error, OSError) as exc:
        print(f"pack-ui: chưa đo đủ ma trận trình duyệt: {exc}", file=sys.stderr)
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path, help="ghi biên nhận bản dev đã triển khai")
    mode.add_argument("--ui-matrix", type=Path, help="thư mục bằng chứng ma trận UI trên starter")
    parser.add_argument("--axe", type=Path, help="đường dẫn axe đã ghim, dùng cùng --ui-matrix")
    args = parser.parse_args()
    if args.ui_matrix is not None:
        if args.axe is None or not args.axe.is_file():
            parser.error("--ui-matrix cần --axe trỏ đến tệp axe đã ghim.")
        return ui_matrix(args.axe.resolve(), args.ui_matrix)
    if args.axe is not None:
        parser.error("--axe dùng cùng --ui-matrix.")
    if args.output.exists() or args.output.is_symlink():
        parser.error("Đích bằng chứng đã tồn tại. Hãy chọn tên mới hoặc chạy bash tests_e2e/preview.sh.")
    preview_receipt(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
