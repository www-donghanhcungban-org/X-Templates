"""Kiểm HTML/CSS/JS của starter bằng Chromium với phản hồi API kiểm soát được."""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Browser, Locator, Page, Route, expect

WIDTHS = (1280, 390, 320)
HEIGHT = 900
ASSETS = Path("src/notes-ui")
AXE_PATH = "/__e2e__/axe.min.js"
AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
EMAIL = "keyboard@example.invalid"
ACCESS = "fixture"
BODY = "Ghi chú kiểm tra bàn phím\n" + "Mã" * 140


class MatrixFailure(ValueError):
    """Cổng trình duyệt đã chạy và tìm thấy lỗi."""


class NotesFixture:
    """Chặn mọi request ngoài origin. HTML, CSS và JS lấy từ starter đã scaffold."""

    def __init__(self, origin: str, axe: Path):
        self.origin = origin
        self.assets = {
            "/": (ASSETS / "index.html", "text/html"),
            "/notes.css": (ASSETS / "app.css", "text/css"),
            "/notes.js": (ASSETS / "app.js", "text/javascript"),
            AXE_PATH: (axe, "text/javascript"),
        }
        self.notes: list[dict[str, str]] = []
        self.pending: Route | None = None
        self.hold_first_read = True
        self.fail_next_read = False
        self.unexpected: list[str] = []

    def route(self, route: Route) -> None:
        url = route.request.url
        method = route.request.method
        if not url.startswith(self.origin + "/"):
            self.unexpected.append("request ngoài origin")
            route.abort()
            return
        path = url.removeprefix(self.origin)
        if method == "GET" and path in self.assets:
            file, content_type = self.assets[path]
            route.fulfill(path=str(file), content_type=f"{content_type}; charset=utf-8")
        elif method == "GET" and path == "/favicon.ico":
            route.fulfill(status=204)
        elif method == "POST" and path == "/v1/login":
            self.login(route)
        elif path == "/v1/notes" and method in ("GET", "POST"):
            self.note_request(route)
        else:
            self.unexpected.append(f"{method} {path}")
            route.abort()

    def login(self, route: Route) -> None:
        if route.request.post_data_json == {"email": EMAIL, "password": ACCESS}:
            route.fulfill(json={"token": ACCESS})
        else:
            route.fulfill(status=401, json={})

    def note_request(self, route: Route) -> None:
        if route.request.header_value("authorization") != f"Bearer {ACCESS}":
            route.fulfill(status=401, json={})
        elif route.request.method == "GET":
            self.read_notes(route)
        elif route.request.post_data_json == {"body": BODY}:
            note = {"id": "fixture-note", "body": BODY, "created_at": "2026-11-24T00:00:00Z"}
            self.notes.append(note)
            route.fulfill(status=201, json=note)
        else:
            route.fulfill(status=400, json={})

    def read_notes(self, route: Route) -> None:
        if self.hold_first_read:
            self.hold_first_read = False
            self.pending = route
        elif self.fail_next_read:
            self.fail_next_read = False
            route.fulfill(status=503, json={})
        else:
            route.fulfill(json={"notes": self.notes})

    def resolve_first_read(self) -> None:
        if self.pending is None:
            raise MatrixFailure("không quan sát được request đang tải")
        self.pending.fulfill(json={"notes": self.notes})
        self.pending = None


def focused(locator: Locator) -> None:
    expect(locator).to_be_focused()
    visible = locator.evaluate("""el => {
        const rect = el.getBoundingClientRect(), style = getComputedStyle(el);
        return el.matches(':focus-visible') && style.outlineStyle !== 'none' &&
            parseFloat(style.outlineWidth) > 0 && rect.width > 0 && rect.height > 0 &&
            rect.left >= 0 && rect.right <= innerWidth && rect.top >= 0 && rect.bottom <= innerHeight;
    }""")
    if not visible:
        raise MatrixFailure("focus bàn phím thiếu chỉ dấu hoặc nằm ngoài viewport")


def key(page: Page, target: Locator, name: str = "Tab") -> None:
    page.keyboard.press(name)
    focused(target)


def inspect_state(page: Page, width: int, state: str, output: Path) -> dict[str, object]:
    metrics = page.evaluate("""() => {
        const root = document.documentElement;
        return {viewport: innerWidth, visible: root.clientWidth, document: Math.max(root.scrollWidth, document.body.scrollWidth)};
    }""")
    if metrics["viewport"] != width or metrics["document"] > metrics["visible"]:
        raise MatrixFailure(f"{width}px/{state}/overflow: {metrics}")
    results = page.evaluate(
        """async tags => {
            const result = await axe.run(document, {runOnly: {type: 'tag', values: tags}});
            return {passes: result.passes.length, violations: result.violations.map(v => v.id)};
        }""",
        AXE_TAGS,
    )
    if results["passes"] == 0:
        raise MatrixFailure(f"{width}px/{state}/axe-unmeasured: axe không báo luật nào đạt")
    if results["violations"]:
        raise MatrixFailure(f"{width}px/{state}/axe: {', '.join(sorted(results['violations']))}")
    target = output / f"{width}-{state}.png"
    page.screenshot(path=target, full_page=True)
    return {"width": width, "height": HEIGHT, "state": state, "axe_passes": results["passes"], "image": target.name}


def journey(page: Page, fixture: NotesFixture, width: int, output: Path) -> list[dict[str, object]]:
    page.goto(fixture.origin + "/", wait_until="load")
    page.add_script_tag(url=fixture.origin + AXE_PATH)
    evidence = [inspect_state(page, width, "login", output)]

    email = page.get_by_role("textbox", name="Email")
    access = page.get_by_label("Mật khẩu")
    sign_in = page.get_by_role("button", name="Đăng nhập")
    editor = page.get_by_role("textbox", name="Nội dung")
    save = page.get_by_role("button", name="Lưu ghi chú")
    refresh = page.get_by_role("button", name="Tải lại")
    leave = page.get_by_role("button", name="Đăng xuất")
    status = page.get_by_role("status")
    list_view = page.locator("#notes-list")

    key(page, email)
    page.keyboard.type(EMAIL)
    key(page, access)
    page.keyboard.type(ACCESS)
    key(page, sign_in)
    page.keyboard.press("Enter")
    expect(status).to_have_text("Đang tải ghi chú…")
    focused(editor)
    evidence.append(inspect_state(page, width, "loading", output))
    fixture.resolve_first_read()
    expect(page.get_by_text("Nhóm chưa có ghi chú nào.")).to_be_visible()
    expect(status).to_be_empty()
    evidence.append(inspect_state(page, width, "empty", output))

    key(page, save)
    key(page, refresh)
    fixture.fail_next_read = True
    page.keyboard.press("Enter")
    expect(status).to_have_text("Dịch vụ đang bận. Vui lòng thử lại sau.")
    expect(refresh).to_be_enabled()
    focused(refresh)
    evidence.append(inspect_state(page, width, "error", output))
    page.keyboard.press("Enter")
    expect(status).to_have_text("Đã tải lại danh sách.")
    expect(refresh).to_be_enabled()
    focused(refresh)

    key(page, save, "Shift+Tab")
    key(page, editor, "Shift+Tab")
    page.keyboard.insert_text(BODY)
    key(page, save)
    page.keyboard.press("Enter")
    expect(status).to_have_text("Đã lưu ghi chú.")
    expect(list_view.get_by_role("listitem")).to_have_count(1)
    expect(list_view).to_contain_text(BODY)
    focused(editor)
    evidence.append(inspect_state(page, width, "success", output))

    key(page, save)
    key(page, refresh)
    page.keyboard.press("Enter")
    expect(status).to_have_text("Đã tải lại danh sách.")
    expect(list_view.get_by_role("listitem")).to_have_count(1)
    expect(list_view).to_contain_text(BODY)
    expect(refresh).to_be_enabled()
    key(page, save, "Shift+Tab")
    key(page, editor, "Shift+Tab")
    key(page, leave, "Shift+Tab")
    page.keyboard.press("Enter")
    focused(email)
    return evidence


def matrix(browser: Browser, origin: str, axe: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    all_states = []
    for width in WIDTHS:
        with browser.new_context(viewport={"width": width, "height": HEIGHT}, service_workers="block") as context:
            fixture = NotesFixture(origin, axe)
            context.route("**/*", fixture.route)
            context.route_web_socket("**/*", lambda socket: socket.close())
            page = context.new_page()
            page_errors: list[str] = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            all_states.extend(journey(page, fixture, width, output))
            if page_errors or fixture.unexpected:
                raise MatrixFailure(
                    f"{width}px: lỗi trang hoặc request ngoài fixture: {page_errors + fixture.unexpected}"
                )
    (output / "matrix.json").write_text(
        json.dumps({"schema": 1, "result": "passed", "states": all_states}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
