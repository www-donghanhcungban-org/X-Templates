"""Loại `llms-txt` (XC-DOCAI-010, llms.txt v2): `llms.txt` / `llms-full.txt` đúng dạng. Báo: `LLM000` không đọc được/không
UTF-8/rỗng, `LLM001` dòng đầu không phải H1 (hoặc có H1 thứ hai), `LLM002` thiếu blockquote tóm tắt ngay sau H1, `LLM003` mục H2
không có link, `LLM004` dòng link sai dạng `- [tên](đích): ghi chú`, `LLM005` `## Optional` không đứng cuối hay H2 trùng tên,
`LLM006` link trùng đích, `LLM007` H2 rỗng hay H3 trở xuống, `LLM008` (cần `--opt root=<thư mục>`) link tương đối trỏ tệp không
có/thoát khỏi root/đi qua liên kết tượng trưng/dài quá `MAX_DEST` ký tự, `LLM009` (`--opt md=1`, cần root) link `.html` thiếu
bản `.md`/`.html.md`. Quét thư mục chỉ nhận tệp tên `NAMES`; tệp nêu đích danh luôn được kiểm. Quét từng dòng, regex neo đầu
dòng và chiếm hữu, dò root từng thành phần bằng `dir_fd` nên thời gian tuyến tính theo kích thước tệp."""

from __future__ import annotations

import os
import posixpath
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlsplit

from . import CheckError, Finding, read_text

HELP = "llms.txt v2: H1, blockquote tóm tắt, H2 chứa link `- [tên](đích): ghi chú`, Optional cuối, link trùng/chết"
SUFFIXES = (".txt",)
NAMES = frozenset({"llms.txt", "llms-full.txt"})
OPTS = ("ignore", "root", "md")
MAX_DEST = 4096
DIR_FLAGS = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_DIRECTORY", 0)
SHOW = 80
BOM = chr(0xFEFF)
ELLIPSIS = chr(0x2026)
WEB_SCHEMES = ("http", "https")

HEAD_RE = re.compile(r"(#{1,6})[ \t]++(\S[^\n]*+)")
ITEM_RE = re.compile(r"[-*+][ \t]")
LINK_RE = re.compile(r"-[ \t]++\[([^\]]*+)\]\(([^)]*+)\)([^\n]*+)")


def _show(text: str) -> str:
    return text if len(text) <= SHOW else text[: SHOW - 1] + ELLIPSIS


def _valid_dest(dest: str) -> bool:
    """Đích là http/https tuyệt đối (có tên máy chủ) hay đường dẫn tương đối bắt đầu `/` hoặc `./` (không phải `//máy-chủ`);
    `\\` bị từ chối (trình duyệt coi như `/`, máy chủ thì không)."""
    if not dest or "\\" in dest or any(ch.isspace() for ch in dest):
        return False
    try:
        parts = urlsplit(dest)
    except ValueError:
        return False
    if parts.scheme:
        return parts.scheme in WEB_SCHEMES and bool(parts.hostname)
    return not parts.netloc and (dest.startswith("/") or dest.startswith("./"))


def _is_relative(dest: str) -> bool:
    return not urlsplit(dest).scheme


def _note_ok(rest: str) -> bool:
    """Phần sau `)`: rỗng, hoặc `:` kèm ghi chú không rỗng."""
    tail = rest.strip()
    if not tail:
        return True
    return tail.startswith(":") and bool(tail[1:].strip())


def _rel_path(dest: str) -> str | None:
    """Đường dẫn trong root của link tương đối ("" = không phải tệp: thư mục/chỉ anchor); None khi thoát khỏi root."""
    path = unquote(urlsplit(dest).path)
    if path.endswith("/") or not path.strip("/."):
        return ""
    norm = posixpath.normpath(path.lstrip("/"))
    if norm == ".." or norm.startswith("../"):
        return None
    return norm


def _plain_file(root: Path, rel: str) -> bool:
    """Tệp thường tại `root/rel`, không thành phần nào là liên kết tượng trưng. Đi từng thành phần bằng `os.open(…,
    dir_fd=…)` không theo liên kết, dừng ở thành phần thiếu: tuyến tính theo số thành phần (rà 🔴1: nối chuỗi cả đường
    dẫn cho mỗi thành phần là bậc hai)."""
    *dirs, leaf = rel.split("/")
    try:
        fd = os.open(root, DIR_FLAGS)
    except OSError:
        return False
    try:
        for part in dirs:
            child = os.open(part, DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = child
        return stat.S_ISREG(os.stat(leaf, dir_fd=fd, follow_symlinks=False).st_mode)
    except (OSError, ValueError):  # ValueError: NUL trong tên
        return False
    finally:
        os.close(fd)


def _root_opt(opts: dict[str, str]) -> Path | None:
    raw = opts.get("root")
    if raw is None:
        return None
    path = Path(raw)
    if not raw or path.is_symlink() or not path.is_dir():
        raise CheckError(f"--opt root: không thấy thư mục thường {raw!r}")
    return path


def _md_opt(opts: dict[str, str], root: Path | None) -> bool:
    raw = opts.get("md", "0")
    if raw not in ("0", "1"):
        raise CheckError(f"--opt md nhận 0 hoặc 1, không phải {raw!r}")
    if raw == "1" and root is None:
        raise CheckError("--opt md=1 cần --opt root=<thư mục>")
    return raw == "1"


@dataclass
class _Section:
    name: str
    line: int
    links: int = 0
    content: int = 0


@dataclass
class _Scan:
    path: str
    root: Path | None
    md: bool
    found: list[Finding] = field(default_factory=list)
    section: _Section | None = None
    h2: list[tuple[str, int]] = field(default_factory=list)
    names: set[str] = field(default_factory=set)
    seen: dict[str, int] = field(default_factory=dict)
    fenced: bool = False

    def add(self, line: int, code: str, message: str) -> None:
        self.found.append(Finding(self.path, line, code, message))

    def run(self, lines: list[str]) -> list[Finding]:
        self._head(lines)
        for index in range(1, len(lines)):
            self._line(index + 1, lines[index].rstrip("\r"))
        self._close()
        self._optional_last()
        return self.found

    def _head(self, lines: list[str]) -> None:
        match = HEAD_RE.match(lines[0].rstrip("\r"))
        if match is None or len(match.group(1)) != 1:
            self.add(1, "LLM001", "dòng đầu phải là H1 dạng `# Tên`")
        for index in range(1, len(lines)):
            text = lines[index].rstrip("\r").strip()
            if not text:
                continue
            if not (text.startswith(">") and text[1:].strip()):
                self.add(index + 1, "LLM002", "thiếu blockquote tóm tắt `> …` ngay sau H1")
            return
        self.add(1, "LLM002", "thiếu blockquote tóm tắt `> …` ngay sau H1")

    def _line(self, number: int, text: str) -> None:
        if text.lstrip().startswith("```"):
            self.fenced = not self.fenced
            return
        if self.fenced:
            return
        head = HEAD_RE.match(text)
        if head is not None:
            self._heading(number, len(head.group(1)), head.group(2).strip())
            return
        section = self.section
        if section is None or not text.strip():
            return
        section.content += 1
        if ITEM_RE.match(text):
            self._item(number, text, section)

    def _heading(self, number: int, level: int, title: str) -> None:
        if level >= 3:
            self.add(number, "LLM007", f"H{level} không dùng trong llms.txt v2 (chỉ H1/H2): {_show(title)}")
            return
        self._close()
        if level == 1:
            self.add(number, "LLM001", f"chỉ được một H1, thấy thêm: {_show(title)}")
            return
        self.section = _Section(title, number)
        key = title.casefold()
        if key in self.names:
            self.add(number, "LLM005", f"H2 trùng tên: {_show(title)}")
        self.names.add(key)
        self.h2.append((title, number))

    def _close(self) -> None:
        section, self.section = self.section, None
        if section is None:
            return
        if section.content == 0:
            self.add(section.line, "LLM007", f"mục H2 rỗng: {_show(section.name)}")
        elif section.links == 0:
            self.add(section.line, "LLM003", f"mục H2 không có link: {_show(section.name)}")

    def _optional_last(self) -> None:
        for index, (name, number) in enumerate(self.h2):
            if name.casefold() == "optional" and index != len(self.h2) - 1:
                self.add(number, "LLM005", "`## Optional` phải là mục H2 cuối cùng")

    def _item(self, number: int, text: str, section: _Section) -> None:
        match = LINK_RE.match(text)
        if match is None or not match.group(1).strip():
            self.add(number, "LLM004", "dòng link phải có dạng `- [tên](đích): ghi chú`")
            return
        section.links += 1
        dest = match.group(2)
        if not _note_ok(match.group(3)):
            self.add(number, "LLM004", "sau `)` chỉ được rỗng hoặc `: ghi chú` không rỗng")
        if not _valid_dest(dest):
            self.add(number, "LLM004", f"đích phải là http/https tuyệt đối hay bắt đầu `/` hoặc `./`: {_show(dest)}")
            return
        first = self.seen.setdefault(dest, number)
        if first != number:
            self.add(number, "LLM006", f"link trùng đích với dòng {first}: {_show(dest)}")
        if self.root is not None and _is_relative(dest):
            self._probe(number, dest, self.root)

    def _probe(self, number: int, dest: str, root: Path) -> None:
        if len(dest) > MAX_DEST:
            self.add(number, "LLM008", f"đích quá dài (> {MAX_DEST} ký tự): {_show(dest)}")
            return
        rel = _rel_path(dest)
        if rel is None:
            self.add(number, "LLM008", f"link thoát khỏi root: {_show(dest)}")
        elif rel and not _plain_file(root, rel):
            self.add(number, "LLM008", f"link trỏ tệp không có trong root: {_show(dest)}")
        elif rel and self.md and rel.lower().endswith(".html"):
            if not (_plain_file(root, rel[:-5] + ".md") or _plain_file(root, rel + ".md")):
                self.add(number, "LLM009", f"link .html thiếu bản .md/.html.md kề: {_show(dest)}")


def _check_file(path: Path, root: Path | None, md: bool) -> list[Finding]:
    name = str(path)
    text = read_text(path)
    if text is None:
        return [Finding(name, 0, "LLM000", "không đọc được dưới dạng UTF-8 (hoặc quá lớn, không phải tệp thường)")]
    text = text.removeprefix(BOM)
    if not text.strip():
        return [Finding(name, 0, "LLM000", "tệp rỗng")]
    return _Scan(name, root, md).run(text.split("\n"))


def check(files: list[Path], opts: dict[str, str]) -> list[Finding]:
    ignore = {code for code in opts.get("ignore", "").split(",") if code}
    root = _root_opt(opts)
    md = _md_opt(opts, root)
    found: list[Finding] = []
    for path in files:  # lọc theo `NAMES` chỉ áp khi quét thư mục (`collect`); tệp nêu đích danh luôn được kiểm
        found.extend(_check_file(path, root, md))
    found = [f for f in found if f.code not in ignore]
    return sorted(found, key=lambda f: (f.path, f.line, f.code))
