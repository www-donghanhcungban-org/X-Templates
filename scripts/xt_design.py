"""Khách duyệt thiết kế (ADR-0106, D-618): sổ `docs/autopilot/DESIGN.json` và khoá task giao diện của vòng.

Dự án khai `Duyệt thiết kế: khách` ở `PROJECT.md` → task PLAN có thẻ `ui: yes` không được giao (`loop next`) hay nhận bằng
chứng (`loop record`) tới khi người duyệt đúng bản thiết kế đã trình (`stage approve --design`). Agent trình bản
(`stage design-submit`), không bao giờ tự duyệt — kể cả khi `stage_approval: agent`. Sổ chỉ `xt.py stage …` ghi (guard:
evidence); sổ hỏng → mọi lệnh đọc nó chặn. `core` là module `xt` (helper khoá, git, giờ), truyền vào để không import vòng.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Any, Callable

Doc = dict[str, Any]
LEDGER = "docs/autopilot/DESIGN.json"
SCHEMA = 1
STATUSES = ("none", "awaiting_approval", "approved")
SHA_RE = re.compile(r"[0-9a-f]{40}")
PROJECT_FILE = "PROJECT.md"
# Dòng khai theo khoá `Duyệt thiết kế` (giá trị sau `:` hoặc ô bảng `|`): tiền tố `-`/`*`/`#`/`>`/`|`, in đậm/nghiêng,
# backtick tuỳ ý, không phân biệt hoa thường; giá trị đọc bằng `_kind` (từ đầu), phần sau (`— chú thích`, `.`) bỏ qua.
DECLARE_RE = re.compile(r"^[\s>|#*_`-]*duyệt thiết kế[\s*_`]*[:|](.*)$", re.I)
# Thẻ trong nhóm ngoặc của dòng task: `ui:`/`ui =` với mọi giá trị khác `no` (`yes`, `có`, `true`…) là UI (chặt hơn).
UI_TAG_RE = re.compile(r"\bui\s*[:=](?!\s*no\b)", re.I)
CLIENT = "khách"
HUMAN_ONLY = "chỉ người — chủ dự án chạy ở terminal riêng, ngoài phiên agent; agent không tự duyệt thiết kế (ADR-0106)"
AGENT_HINT = (
    " · agent: `loop defer --task {task} --reason 'chờ khách duyệt thiết kế'` rồi làm task khác;"
    " không chạy `stage approve --design`"
)


class DesignError(Exception):
    """Lệnh thiết kế bị từ chối hoặc sổ hỏng: một dòng cho người, không ghi sổ."""


def empty() -> Doc:
    return {"schema": SCHEMA, "status": "none", "submitted": None, "history": []}


def _evidence_ok(value: Any) -> bool:
    path = PurePosixPath(str(value))
    return isinstance(value, str) and bool(value) and not path.is_absolute() and ".." not in path.parts


def _submit(ev: Doc, r: Doc) -> str:
    if r["status"] == "awaiting_approval":
        return "`submit` khi đang chờ duyệt — `reopen` trước"
    sha, evidence = ev.get("sha"), ev.get("evidence")
    if not SHA_RE.fullmatch(str(sha)) or not _evidence_ok(evidence):
        return "`submit` cần `sha` 40 hex và `evidence` là đường tương đối"
    r.update(status="awaiting_approval", submitted={"sha": sha, "evidence": evidence})
    return ""


def _reopen(ev: Doc, r: Doc) -> str:
    if r["status"] != "awaiting_approval" or not isinstance(ev.get("reason"), str) or not ev["reason"]:
        return "`reopen` chỉ khi đang chờ duyệt, cần `reason`"
    r.update(status="none", submitted=None)
    return ""


def _approve(ev: Doc, r: Doc) -> str:
    by = ev.get("by")
    if r["status"] != "awaiting_approval" or ev.get("sha") != r["submitted"]["sha"]:
        return "`approve` chỉ ngay khi đang chờ duyệt, đúng `sha` đã trình"
    if not isinstance(by, str) or not by.strip() or by.strip().casefold() == "agent":
        return "`approve` cần `by` là người (không phải agent)"
    r.update(status="approved", submitted=None)
    return ""


REPLAY: dict[str, Callable[[Doc, Doc], str]] = {"submit": _submit, "reopen": _reopen, "approve": _approve}


def _replay(ev: Any, r: Doc) -> str:
    if not isinstance(ev, dict) or not isinstance(ev.get("at"), str) or not ev["at"]:
        return "sự kiện phải là object có `at`"
    step = REPLAY.get(str(ev.get("event")))
    return step(ev, r) if step else f"`event` lạ: {ev.get('event')!r}"


def problem(led: Any) -> str:
    """Lý do sổ không hợp lệ; '' = hợp lệ. Phát lại `history` theo thứ tự phải ra đúng `status`/`submitted`."""
    if not isinstance(led, dict) or led.get("schema") != SCHEMA:
        return f"không phải object `schema: {SCHEMA}`"
    if led.get("status") not in STATUSES or not isinstance(led.get("history"), list):
        return "`status` phải " + "|".join(STATUSES) + ", `history` phải là list"
    r: Doc = {"status": "none", "submitted": None}
    for i, ev in enumerate(led["history"]):
        why = _replay(ev, r)
        if why:
            return f"history[{i}]: {why}"
    if (r["status"], r["submitted"]) != (led["status"], led.get("submitted")):
        return f"lịch sử dựng ra `{r['status']}`/{r['submitted']}, sổ ghi `{led['status']}`/{led.get('submitted')}"
    return ""


def read(base: Path) -> Doc:
    """Sổ thiết kế; vắng → `none` (xoá sổ chỉ khoá lại, không mở khoá). Hỏng → DesignError (fail-closed)."""
    p = base / LEDGER
    if not p.exists():
        return empty()
    try:
        led = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError) as exc:
        raise DesignError(f"{LEDGER} không đọc được: {exc} — người sửa hoặc khôi phục từ git") from None
    why = problem(led)
    if why:
        raise DesignError(f"{LEDGER} hỏng: {why} — người sửa hoặc khôi phục từ git (ADR-0106)")
    return dict(led)


def update(core: ModuleType, base: Path, fn: Callable[[Doc], Doc]) -> Doc:
    """Đọc–sửa–ghi trong khoá `state.lock` như sổ giai đoạn; sổ mới phải hợp lệ; thư mục cha symlink → từ chối."""
    links = [q.as_posix() for q in PurePosixPath(LEDGER).parents if q != PurePosixPath(".") and (base / q).is_symlink()]
    if links:
        raise DesignError(f"{links[-1]} là symlink — không ghi sổ thiết kế xuyên liên kết ra ngoài dự án")
    with core._state_lock(base):
        new = fn(read(base))
        why = problem(new)
        if why:  # lỗi lập trình: chặn trước khi ghi sổ sai
            raise DesignError(f"chuyển trạng thái thiết kế tạo sổ sai: {why}")
        p = base / LEDGER
        p.parent.mkdir(parents=True, exist_ok=True)
        fresh = not p.exists()
        p.touch()
        try:
            core.write_atomic(p, json.dumps(new, ensure_ascii=False, indent=2) + "\n", keep_mode=True)
        except BaseException:
            if fresh:
                p.unlink(missing_ok=True)
            raise
        return new


def _event(core: ModuleType, led: Doc, kind: str, **extra: Any) -> None:
    led["history"].append({"event": kind, **extra, "at": str(core.now_iso())})


def submit(core: ModuleType, led: Doc, sha: str, evidence: str) -> Doc:
    if led["status"] == "awaiting_approval":
        pending = led["submitted"]["sha"][:12]
        raise DesignError(f"đã trình bản {pending}, đang chờ người duyệt — sửa: `stage design-reopen --reason …` trước")
    led.update(status="awaiting_approval", submitted={"sha": sha, "evidence": evidence})
    _event(core, led, "submit", sha=sha, evidence=evidence)
    return led


def reopen(core: ModuleType, led: Doc, reason: str) -> Doc:
    if led["status"] != "awaiting_approval":
        raise DesignError("chỉ mở lại bản thiết kế đang chờ duyệt")
    led.update(status="none", submitted=None)
    _event(core, led, "reopen", reason=reason)
    return led


def approve(core: ModuleType, led: Doc, sha: str, by: str, note: str) -> Doc:
    if led["status"] != "awaiting_approval":
        raise DesignError("không có bản thiết kế chờ duyệt — agent trình bằng `stage design-submit` trước")
    want = str(led["submitted"]["sha"])
    if len(sha) < 7 or not want.startswith(sha.lower()):
        raise DesignError(f"--sha {sha!r} không phải ≥ 7 ký tự đầu của bản đã trình ({want[:12]})")
    led.update(status="approved", submitted=None)
    _event(core, led, "approve", sha=want, by=by, note=note)
    return led


def evidence_path(core: ModuleType, base: Path, raw: str) -> str:
    """Đường tương đối (POSIX) của tệp bằng chứng: trong dự án, không symlink, đã commit ở HEAD."""
    full = Path(raw) if Path(raw).is_absolute() else base / raw
    try:
        rel = full.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        raise DesignError(f"bằng chứng {raw!r} nằm ngoài dự án") from None
    if full.is_symlink() or not full.is_file():
        raise DesignError(f"bằng chứng {raw!r} không phải tệp thường trong cây")
    r = core._stage_git(base, "cat-file", "-t", f"HEAD:{rel}")
    if r.returncode != 0 or r.stdout.strip() != "blob":
        raise DesignError(f"bằng chứng {rel} chưa commit — commit mockup/ảnh rồi trình")
    return rel


def _unfenced(core: ModuleType, text: str) -> list[str]:
    """Dòng ngoài code fence ``` / ~~~ (ví dụ trong tài liệu không phải khai báo), chuẩn hoá NFC."""
    kept: list[str] = []
    fence: str | None = None
    for line in unicodedata.normalize("NFC", text).splitlines():
        m = core.FENCE_RE.match(line)
        if m and (fence is None or m.group(1) == fence):
            fence = None if fence else str(m.group(1))
        elif fence is None:
            kept.append(line)
    return kept


def _kind(value: str) -> str:
    """Giá trị sau `Duyệt thiết kế:` theo từ đầu: `khách` (cả `khách hàng`) · `không` · `<` (mẫu `<…>` chưa điền) ·
    `?` (rỗng hay từ khác — không đọc được)."""
    v = value.lstrip(" \t*_`")
    if v.startswith("<"):
        return "<"
    word = re.split(r"\W", v, maxsplit=1)[0].casefold()
    return "không" if word == "không" else CLIENT if word.startswith(CLIENT) else "?"


def declared(core: ModuleType, base: Path) -> tuple[bool, str]:
    """(dự án khai khách duyệt thiết kế, ghi chú). Vắng `PROJECT.md`/dòng khai → không; mẫu `<…>` chưa điền → không kèm
    ghi chú. Không đọc được, giá trị lạ hay khai mâu thuẫn → coi là khách (cách hiểu chặt hơn) kèm ghi chú."""
    p = base / PROJECT_FILE
    if not p.exists():
        return False, ""
    try:
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return True, f"không đọc được {PROJECT_FILE} ({exc}) — coi như khai `Duyệt thiết kế: {CLIENT}`"
    found = [(_kind(m[1]), m[1].strip()) for line in _unfenced(core, text) if (m := DECLARE_RE.match(line))]
    kinds, odd = {k for k, _ in found}, [raw for k, raw in found if k == "?"]
    if odd:
        return (
            True,
            f"{PROJECT_FILE}: `Duyệt thiết kế: {odd[0]}` không đọc được (cần `khách`/`không`) — coi như `{CLIENT}`",
        )
    if {CLIENT, "không"} <= kinds:
        return True, f"{PROJECT_FILE} khai `Duyệt thiết kế` mâu thuẫn — coi như `{CLIENT}`; sửa còn một dòng"
    if CLIENT in kinds:
        return True, ""
    return False, f"{PROJECT_FILE}: dòng `Duyệt thiết kế` chưa điền (`<…>`) — coi như `không`" if kinds == {"<"} else ""


def client_mode(core: ModuleType, base: Path, led: Doc) -> tuple[bool, str]:
    """Như `declared`, nhưng sổ đã có `history` (từng trình) thì khoá vẫn bật dù `PROJECT.md` đổi sang `không` hay bị
    xoá: agent không tắt khoá bằng cách sửa tệp khai; chỉ người xoá sổ mới tắt (ADR-0106 §Hệ quả)."""
    client, note = declared(core, base)
    if client or not led["history"]:
        return client, note
    return True, f"{LEDGER} đã có lịch sử trình — khoá giữ dù {PROJECT_FILE} không khai `{CLIENT}`; chỉ người xoá sổ"


def _stale(core: ModuleType, base: Path, led: Doc) -> str:
    """'' khi lời duyệt còn gắn với nội dung: SHA đã duyệt là tổ tiên HEAD và tệp bằng chứng không đổi từ SHA đó tới HEAD
    (`git revert` sổ về `approved` cũ, sửa mockup sau duyệt → khoá lại). Sổ `approved` hợp lệ: sự kiện cuối là `approve`,
    ngay trước là `submit` của bản đó. git lỗi/không có → khoá (fail-closed)."""
    sha, evidence = led["history"][-1]["sha"], led["history"][-2]["evidence"]
    try:
        ok = core._stage_git(base, "merge-base", "--is-ancestor", sha, "HEAD").returncode == 0
        ok = ok and core._stage_git(base, "diff", "--quiet", sha, "HEAD", "--", evidence).returncode == 0
    except (OSError, core.StageError):
        ok = False
    return (
        ""
        if ok
        else (
            f"bản đã duyệt {sha[:12]} không còn khớp HEAD (không là tổ tiên của HEAD, hoặc bản bằng chứng {evidence} đã đổi"
            " sau khi duyệt) — trình lại: `xt.py stage design-submit --evidence <tệp>` rồi chờ người duyệt"
        )
    )


def lock_reason(core: ModuleType, base: Path) -> str:
    """Lý do task giao diện bị khoá; '' = không khoá (không khai khách, hoặc bản đã duyệt còn khớp HEAD). Sổ hỏng → khoá."""
    try:
        led = read(base)
    except DesignError as exc:
        return str(exc)
    client, note = client_mode(core, base, led)
    if not client:
        return ""
    head = f"task giao diện (`ui: yes`) chờ khách duyệt thiết kế{f' ({note})' if note else ''} — "
    if led["status"] == "approved":
        stale = _stale(core, base, led)
        return head + stale if stale else ""
    if led["status"] == "awaiting_approval":
        sha = led["submitted"]["sha"][:12]
        return head + f"chờ người duyệt bản {sha}: `xt.py stage approve --design --sha {sha} --note …` (ADR-0106)"
    return head + "trình mockup: `xt.py stage design-submit --evidence <tệp>` rồi chờ người `stage approve --design`"


def is_ui(core: ModuleType, task: Doc) -> bool:
    """Thẻ `ui:` khác `no` trong nhóm ngoặc của dòng task (trước `Gate:`, bỏ span backtick) như `topo:`/`files:`."""
    rest = str(task.get("rest") or "")
    gate = core.GATE_RE.search(rest)
    head = core.PLAN_CODE_SPAN_RE.sub(" ", rest[: gate.start()] if gate else rest)
    groups, unclosed = core._paren_groups(head)
    return any(UI_TAG_RE.search(g) for g in [*groups, unclosed or ""])


def _held(core: ModuleType, base: Path, ready: list[Doc]) -> tuple[list[Doc], dict[str, str]]:
    ui = [t for t in ready if is_ui(core, t)]
    why = lock_reason(core, base) if ui else ""
    if not why:
        return ready, {}
    return [t for t in ready if t not in ui], {str(t["id"]): why for t in ui}


def hold(core: ModuleType, base: Path, ready: list[Doc]) -> tuple[list[Doc], dict[str, str]]:
    """(task sẵn sàng còn giao được, {task giao diện bị giữ: lý do + việc agent làm}) cho `loop next`."""
    kept, held = _held(core, base, ready)
    return kept, {k: why + AGENT_HINT.format(task=k) for k, why in held.items()}


def defer_held(core: ModuleType, base: Path, st: Doc) -> Doc:
    """Bản sao `st` cho verdict (không ghi đĩa): task giao diện còn mở đang bị giữ tính như `loop defer` — verdict không
    dẫn agent vào task khoá; chỉ còn chúng thì ra `done-pending-human` kèm lý do khoá."""
    deferred = core._deferred(st)
    tasks = [t for t in core._plan_tasks(base, st) if t["state"] == " " and t["id"] not in deferred]
    held = _held(core, base, tasks)[1]
    if not held:
        return st
    return {**st, "deferred": {**deferred, **{k: {"reason": why, "at": core.now_iso()} for k, why in held.items()}}}


def record_problem(core: ModuleType, base: Path, st: Doc, task: str) -> str:
    """Lý do `loop record` từ chối `task`; '' = nhận."""
    found = [t for t in core._plan_tasks(base, st) if t["id"] == task and is_ui(core, t)]
    why = lock_reason(core, base) if found else ""
    return why + AGENT_HINT.format(task=task) if why else ""


def _check(core: ModuleType, base: Path, as_json: bool) -> int:
    try:
        led = read(base)
    except DesignError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    client, note = client_mode(core, base, led)
    reason = lock_reason(core, base)
    if as_json:
        out = {"ledger": LEDGER, "client": client, "note": note, "design": led, "ok": not reason, "reason": reason}
        print(json.dumps(out, ensure_ascii=False))
    else:
        tail = f" · {note}" if note else ""
        print(f"Duyệt thiết kế: {CLIENT if client else 'không'} · {LEDGER}: {led['status']}{tail}")
        print(f"  ✗ {reason}" if reason else "  ✓ task giao diện không bị khoá")
    return 1 if reason else 0


def _transition(core: ModuleType, args: argparse.Namespace, base: Path) -> Callable[[Doc], Doc]:
    """Hàm chuyển trạng thái; kiểm người/agent, HEAD sạch và bằng chứng TRƯỚC khi lấy khoá."""
    if args.stage_cmd == "design-submit":
        sha = str(core._stage_clean_head(base))
        rel = evidence_path(core, base, args.evidence)
        return lambda led: submit(core, led, sha, rel)
    if args.stage_cmd == "design-reopen":
        return lambda led: reopen(core, led, args.reason)
    if core.agent_session():
        raise DesignError(f"`stage approve --design` {HUMAN_ONLY}")
    by = str(core._stage_by(base))
    return lambda led: approve(core, led, args.sha, by, args.note)


def cmd(core: ModuleType, args: argparse.Namespace, base: Path) -> int:
    """`stage design-submit|design-reopen|design-check` và `stage approve --design` (ADR-0106)."""
    if args.stage_cmd == "design-check":
        return _check(core, base, args.json)
    try:
        led = update(core, base, _transition(core, args, base))
    except (DesignError, core.StageError) as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    sub = led["submitted"]
    print(f"{LEDGER}: {led['status']}" + (f" · bản {sub['sha'][:12]}: {sub['evidence']}" if sub else ""))
    print(f"  → commit + push `{LEDGER}` (trình/duyệt chỉ có hiệu lực khi sổ lên git)")
    return 0
