"""Test cho kênh dự án phái sinh (ADR-0087): schema bản ghi `docs/derived/`, danh sách tệp của PR, làn `derived` của
`merge-check`/steward và CLI `xt.py derived`. Mọi đầu vào PR là dữ liệu không tin cậy — bảng ca chặn lẫn ca nhận."""

from __future__ import annotations

import base64
import datetime
import json
import os
import subprocess
import sys
import tempfile
import types
import unicodedata
import unittest
import unittest.mock
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import xt
from xt_merge_intent import RepoTarget
import xt_derived as dv
from test_merge import FakeGh, commit_base_xt, pr, run_main

DAY = datetime.date(2026, 11, 21)
HEAD_REPO = "alice/X-Templates"
NAME = "alice--X-Templates.json"
PATH = "docs/derived/" + NAME
VERSIONS = frozenset({"3.33.0", "3.34.0"})
HEAD = "a" * 40
BASE = "b" * 40
DOCS = "d" * 40
DER = "e" * 40
BLOB = "f" * 40
API = "repos/o/r"
DROP = object()


def good(**over: Any) -> dict:
    rec: dict = {
        "schema": 1,
        "repo": HEAD_REPO,
        "kind": "fork",
        "upstream": {"repo": dv.UPSTREAM, "version": "3.34.0"},
        "description": "Bản fork cho nhóm nội bộ.",
        "status": "active",
        "updated": "2026-11-21",
    }
    rec.update(over)
    return {k: v for k, v in rec.items() if v is not DROP}


def up(version: Any) -> dict:
    return {"upstream": {"repo": dv.UPSTREAM, "version": version}}


def enc(rec: Any) -> bytes:
    return json.dumps(rec).encode()


def problems(rec: Any, versions: Any = VERSIONS, head: str = HEAD_REPO) -> list:
    return dv.check_bytes(enc(rec), head, DAY, versions)[1]


REJECT = {
    "schema 2": ({"schema": 2}, "schema phải"),
    "schema chuỗi": ({"schema": "1"}, "schema phải"),
    "schema bool": ({"schema": True}, "schema phải"),
    "thiếu schema": ({"schema": DROP}, "thiếu trường: schema"),
    "repo người khác": ({"repo": "bob/X-Templates"}, "repo phải đúng head repo"),
    "repo khác hoa thường": ({"repo": "Alice/x-templates"}, "repo phải đúng head repo"),
    "repo không phải chuỗi": ({"repo": ["alice", "X-Templates"]}, "repo phải đúng head repo"),
    "kind viết hoa": ({"kind": "Fork"}, "kind phải"),
    "kind lạ": ({"kind": "mirror"}, "kind phải"),
    "upstream chuỗi": ({"upstream": "x"}, "upstream phải là object"),
    "upstream thừa trường": ({"upstream": {"repo": dv.UPSTREAM, "version": "3.34.0", "x": 1}}, "upstream phải"),
    "upstream repo khác": ({"upstream": {"repo": "evil/X-Templates", "version": "3.34.0"}}, "upstream.repo phải"),
    "version thiếu số": (up("3.34"), "X.Y.Z"),
    "version có v": (up("v3.34.0"), "X.Y.Z"),
    "version pre-release": (up("3.34.0-rc1"), "X.Y.Z"),
    "version số 0 đầu": (up("03.34.0"), "X.Y.Z"),
    "version số": (up(3), "X.Y.Z"),
    "version chưa phát hành": (up("9.9.9"), "đã phát hành"),
    "mô tả rỗng": ({"description": ""}, "description phải là chuỗi"),
    "mô tả khoảng trắng đầu": ({"description": " a"}, "description phải là chuỗi"),
    "mô tả số": ({"description": 5}, "description phải là chuỗi"),
    "mô tả dài": ({"description": "a" * 281}, "281 ký tự > 280"),
    "mô tả HTML": ({"description": "<b>x</b>"}, "HTML"),
    "mô tả link markdown": ({"description": "xem [a](b)"}, "HTML"),
    "mô tả http": ({"description": "trang HTTP chính"}, "URL"),
    "mô tả scheme": ({"description": "ftp://x"}, "URL"),
    "mô tả www": ({"description": "xem WWW.x"}, "URL"),
    "mô tả @": ({"description": "liên hệ @alice"}, "@"),
    "mô tả email": ({"description": "a@b"}, "@"),
    "mô tả backtick": ({"description": "`mã`"}, "HTML"),
    "mô tả xuống dòng": ({"description": "a\nb"}, "điều khiển"),
    "mô tả tab": ({"description": "a\tb"}, "điều khiển"),
    "mô tả NUL": ({"description": "a\x00b"}, "điều khiển"),
    "mô tả bidi": ({"description": "abc‮def"}, "điều khiển"),
    "mô tả zero-width": ({"description": "a​b"}, "điều khiển"),
    "mô tả line separator": ({"description": "a b"}, "điều khiển"),
    "mô tả surrogate lẻ": ({"description": "a\ud800b"}, "điều khiển"),
    "mô tả NFD": ({"description": unicodedata.normalize("NFD", "Dự án")}, "NFC"),
    "mô tả số điện thoại": ({"description": "gọi 0912 345 678"}, "dãy số dài"),
    "mô tả variation selector": ({"description": "a️b"}, "ký tự ẩn"),
    "mô tả variation selector bổ sung": ({"description": "a\U000e0101b"}, "ký tự ẩn"),
    "mô tả tag Unicode": ({"description": "a\U000e0041b"}, "ký tự ẩn"),
    "mô tả CGJ": ({"description": "a͏b"}, "ký tự ẩn"),
    "mô tả Hangul filler": ({"description": "aㅤb"}, "ký tự ẩn"),
    "mô tả Hangul choseong filler": ({"description": "aᅟb"}, "ký tự ẩn"),
    "mô tả Hangul halfwidth filler": ({"description": "aﾠb"}, "ký tự ẩn"),
    "mô tả Braille trống": ({"description": "a⠀b"}, "ký tự ẩn"),
    "mô tả chồng dấu": ({"description": "x́́́"}, "dấu kết hợp"),
    "mô tả @ toàn chiều rộng": ({"description": "lien＠example"}, "@"),
    "mô tả http toàn chiều rộng": ({"description": "ｈｔｔｐ x"}, "URL"),
    "mô tả số toàn chiều rộng": ({"description": "gọi ０９１２３４５６７８"}, "dãy số"),
    "mô tả số Ả Rập": ({"description": "gọi ٠٩١٢٣٤٥٦٧"}, "dãy số"),
    "mô tả số gạch chéo": ({"description": "gọi 0912/345/678"}, "dãy số"),
    "mô tả tên miền kèm đường dẫn": ({"description": "vào evil.com/free-money"}, "tên miền"),
    "mô tả tên miền lạ kèm đường dẫn": ({"description": "vào a.b.example/x"}, "tên miền"),
    "mô tả tên miền trần": ({"description": "ghé Evil.COM nhé"}, "tên miền"),
    "mô tả tên miền .vn": ({"description": "ghé shop.vn"}, "tên miền"),
    "mô tả tên miền .net": ({"description": "dùng ASP.NET"}, "tên miền"),  # asp.net là tên miền thật
    "homepage http": ({"homepage": "http://x.vn"}, "homepage chỉ nhận"),
    "homepage javascript": ({"homepage": "javascript:alert(1)"}, "homepage chỉ nhận"),
    "homepage userinfo": ({"homepage": "https://user@x.vn"}, "homepage chỉ nhận"),
    "homepage IPv4": ({"homepage": "https://127.0.0.1"}, "homepage chỉ nhận"),
    "homepage IPv6": ({"homepage": "https://[::1]/"}, "homepage chỉ nhận"),
    "homepage cổng lạ": ({"homepage": "https://x.vn:8443"}, "homepage chỉ nhận"),
    "homepage cổng 443": ({"homepage": "https://x.vn:443/"}, "homepage chỉ nhận"),
    "homepage localhost": ({"homepage": "https://localhost"}, "homepage chỉ nhận"),
    "homepage .local": ({"homepage": "https://nas.local"}, "dành riêng"),
    "homepage .internal": ({"homepage": "https://db.corp.internal/"}, "dành riêng"),
    "homepage punycode": ({"homepage": "https://xn--80ak6aa92e.com"}, "punycode"),
    "homepage query": ({"homepage": "https://x.vn/?q=1"}, "homepage chỉ nhận"),
    "homepage fragment": ({"homepage": "https://x.vn/#a"}, "homepage chỉ nhận"),
    "homepage viết hoa": ({"homepage": "HTTPS://X.VN"}, "homepage chỉ nhận"),
    "homepage khoảng trắng": ({"homepage": "https://x.vn/a b"}, "homepage chỉ nhận"),
    "homepage dấu chấm cuối": ({"homepage": "https://x.vn."}, "homepage chỉ nhận"),
    "homepage Unicode": ({"homepage": "https://ví-dụ.vn"}, "homepage chỉ nhận"),
    "homepage dài": ({"homepage": "https://x.vn/" + "a" * 190}, "≤ 200"),
    "homepage số": ({"homepage": 5}, "≤ 200"),
    "status lạ": ({"status": "deleted"}, "status phải"),
    "updated tháng 13": ({"updated": "2026-13-01"}, "không phải ngày hợp lệ"),
    "updated 30/2": ({"updated": "2026-02-30"}, "không phải ngày hợp lệ"),
    "updated ngắn": ({"updated": "26-11-21"}, "YYYY-MM-DD"),
    "updated số": ({"updated": 20261121}, "YYYY-MM-DD"),
    "updated tương lai": ({"updated": "2026-11-23"}, "tương lai"),
    "trường lạ email": ({"email": "a"}, "trường lạ: email"),
    "trường lạ tên lạ": ({"<x>": 1}, "trường lạ: <giá trị lạ>"),
}

ACCEPT = {
    "tối thiểu": {},
    "homepage": {"homepage": "https://alice.example.org/du-an/v1"},
    "homepage gốc": {"homepage": "https://x.vn"},
    "archived": {"status": "archived"},
    "derived": {"kind": "derived"},
    "updated ngày mai": {"updated": "2026-11-22"},
    "updated quá khứ": {"updated": "2026-01-01"},
    "mô tả 280 ký tự": {"description": "a" * 280},
    "tiếng Việt NFC": {"description": "Dự án quản lý khách sạn — bản dùng nội bộ (2026)."},
    # Mọi dấu thanh trên mọi nguyên âm tiếng Việt: sau NFC không còn dấu kết hợp nên luật chặn dấu không chặn oan.
    "tiếng Việt đủ dấu": {
        "description": "àáảãạ ăằắẳẵặ âầấẩẫậ èéẻẽẹ êềếểễệ ìíỉĩị òóỏõọ ôồốổỗộ ơờớởỡợ ùúủũụ ưừứửữự ỳýỷỹỵ đ"
    },
    "tiếng Việt hoa đủ dấu": {
        "description": "ÀÁẢÃẠ ĂẰẮẲẴẶ ÂẦẤẨẪẬ ÈÉẺẼẸ ÊỀẾỂỄỆ ÌÍỈĨỊ ÒÓỎÕỌ ÔỒỐỔỖỘ ƠỜỚỞỠỢ ÙÚỦŨỤ ƯỪỨỬỮỰ ỲÝỶỸỴ Đ"
    },
    "tên công nghệ có dấu chấm": {"description": "Hỗ trợ Node.js, Vue.js và Python 3.15."},
    "số ngắn": {"description": "Phiên bản 2026.11, 12 mô-đun, 8 người."},
    "bản cũ": up("3.33.0"),
}


class RecordTest(unittest.TestCase):
    def test_reject_table(self) -> None:
        for name, (over, want) in REJECT.items():
            with self.subTest(name):
                got = problems(good(**over))
                self.assertTrue(any(want in p for p in got), got)

    def test_accept_table(self) -> None:
        for name, over in ACCEPT.items():
            with self.subTest(name):
                data, got = dv.check_bytes(enc(good(**over)), HEAD_REPO, DAY, VERSIONS)
                self.assertEqual(got, [])
                self.assertEqual(data, good(**over))

    def test_versions_none_checks_shape_only(self) -> None:
        self.assertEqual(problems(good(**up("9.9.9")), versions=None), [])
        self.assertIn("upstream.version phải dạng X.Y.Z", problems(good(**up("9.9")), versions=None))

    def test_head_repo_never_upstream_or_invalid(self) -> None:
        for head in (dv.UPSTREAM, "www-donghanhcungban-org/x-templates", "a--b/c", "nope"):
            with self.subTest(head):
                got = dv.check_record(good(repo=head), head, DAY, VERSIONS)
                self.assertEqual(len(got), 1)
                self.assertIn("không nhận bản ghi phái sinh", got[0])
        self.assertEqual(dv.check_record([1], HEAD_REPO, DAY), ["bản ghi phải là object JSON"])

    def test_values_from_outside_never_echoed(self) -> None:
        got = problems(good(repo="<script>x</script>", description="<img src=x>", extra="`rm`"))
        self.assertFalse(any("<script>" in p or "<img" in p for p in got), got)

    def test_parse_rules(self) -> None:
        valid = enc(good())
        cases = {
            "trống": (b"", "tệp trống"),
            "quá 2048 B": (valid + b" " * (2049 - len(valid)), "2049 B > 2048 B"),
            "BOM": (b"\xef\xbb\xbf" + valid, "BOM"),
            "không phải UTF-8": (b'{"a": "\xff"}', "UTF-8"),
            "khoá trùng": (b'{"schema": 1, "schema": 1}', "khoá trùng"),
            "NaN": (b'{"schema": NaN}', "NaN/Infinity"),
            "Infinity": (b'{"schema": Infinity}', "NaN/Infinity"),
            "-Infinity": (b'{"schema": -Infinity}', "NaN/Infinity"),
            "số thực": (b'{"schema": 1.0}', "số thực"),
            "số mũ lớn": (b'{"schema": 1e400}', "số thực"),
            "số lớn": (b'{"schema": 1234567890}', "số quá lớn"),
            "số âm lớn": (b'{"schema": -1234567890}', "số quá lớn"),
            "mảng": (b"[1]", "object JSON"),
            "chuỗi": (b'"x"', "object JSON"),
            "lồng sâu hợp lệ": (b"[" * 1024 + b"]" * 1024, "object JSON"),
            "lồng sâu hỏng": (b"[" * 2048, "JSON không hợp lệ"),
            "cú pháp": (b"{", "JSON không hợp lệ"),
        }
        for name, (raw, want) in cases.items():
            with self.subTest(name):
                data, got = dv.parse_record(raw)
                self.assertIsNone(data)
                self.assertTrue(any(want in p for p in got), got)
        self.assertEqual(dv.check_bytes(b"", HEAD_REPO, DAY, VERSIONS), (None, ["tệp trống"]))
        padded = valid + b" " * (2048 - len(valid))
        self.assertEqual(dv.check_bytes(padded, HEAD_REPO, DAY, VERSIONS)[1], [])  # đúng trần vẫn nhận


class NameTest(unittest.TestCase):
    def test_record_name_and_back(self) -> None:
        self.assertEqual(dv.record_name(HEAD_REPO), NAME)
        self.assertEqual(dv.repo_from_name(NAME), HEAD_REPO)
        self.assertEqual(dv.repo_from_name("alice--b--c.json"), "alice/b--c")  # repo được có `--`, owner thì không
        for bad in ("a--b.JSON", "ab.json", "--b.json", "a--.json", "a--b.json5", "a-b--c d.json", "a--..json"):
            with self.subTest(bad):
                self.assertIsNone(dv.repo_from_name(bad))
        for bad in (None, "", "a", "a/b/c", "a--b/c", "-a/b", "a-/b", "a/.", "a/..", "a/" + "x" * 101, "a" * 40 + "/b"):
            with self.subTest(bad):
                self.assertIsNone(dv.record_name(bad))
        self.assertEqual(dv.safe("docs/x.json"), "docs/x.json")
        self.assertEqual(dv.safe("a\nb"), "<giá trị lạ>")
        self.assertEqual(dv.safe(None), "<giá trị lạ>")


def file(path: str = PATH, status: str = "added", **over: Any) -> dict:
    return {"filename": path, "status": status, **over}


class PrFilesTest(unittest.TestCase):
    def test_accept(self) -> None:
        for name, files in {
            "added": [file()],
            "modified": [file(status="modified")],
            "dạng path + mode": [{"path": PATH, "status": "added", "mode": "100644"}],
        }.items():
            with self.subTest(name):
                self.assertEqual(dv.check_pr_files(files, HEAD_REPO), [])

    def test_reject_paths(self) -> None:
        paths = {
            "traversal ..": "docs/derived/../derived/" + NAME,
            "hai gạch chéo": "docs/derived//" + NAME,
            "./ đầu": "./docs/derived/" + NAME,
            "/./ giữa": "docs/derived/./" + NAME,
            "gạch chéo đầu": "/docs/derived/" + NAME,
            "chữ thường": "docs/derived/alice--x-templates.json",
            "Docs hoa": "Docs/derived/" + NAME,
            "Cyrillic а": "docs/derived/аlice--X-Templates.json",
            "fullwidth": "docs/derived/ａlice--X-Templates.json",
            "tệp người khác": "docs/derived/bob--X-Templates.json",
            "ngoài thư mục": "README.md",
            "đuôi hoa": "docs/derived/alice--X-Templates.JSON",
            "thư mục con": "docs/derived/x/" + NAME,
            "không phải chuỗi": None,
        }
        for name, path in paths.items():
            with self.subTest(name):
                got = dv.check_pr_files([{"filename": path, "status": "added"}], HEAD_REPO)
                self.assertTrue(any(f"khác {PATH}" in p for p in got), got)

    def test_reject_status_mode_and_count(self) -> None:
        cases = {
            "renamed": ([file(status="renamed", previous_filename="docs/derived/bob--x.json")], "đổi tên"),
            "previous trong vùng": ([file(status="modified", previous="docs/derived/bob--x.json")], "đổi tên"),
            "removed": ([file(status="removed")], "trạng thái tệp removed"),
            "copied": ([file(status="copied")], "trạng thái tệp copied"),
            "changed (mode)": ([file(status="changed")], "trạng thái tệp changed"),
            "unchanged": ([file(status="unchanged")], "trạng thái tệp unchanged"),
            "thiếu status": ([{"filename": PATH}], "trạng thái tệp <giá trị lạ>"),
            "symlink": ([file(mode="120000")], "mode 120000"),
            "thực thi": ([file(mode="100755")], "mode 100755"),
            "thư mục": ([file(mode="040000")], "mode 040000"),
            "hai tệp": ([file(), file("README.md")], "PR đổi 2 tệp"),
            "không tệp": ([], "PR đổi 0 tệp"),
            "phần tử lạ": (["x"], "PR đổi 1 tệp"),
        }
        for name, (files, want) in cases.items():
            with self.subTest(name):
                got = dv.check_pr_files(files, HEAD_REPO)
                self.assertTrue(any(want in p for p in got), got)

    def test_reject_head_repo(self) -> None:
        for head in ("", "a--b/c", "a/b/c", "-a/b", dv.UPSTREAM, "WWW-donghanhcungban-org/x-templates"):
            with self.subTest(head):
                got = dv.check_pr_files([file()], head)
                self.assertEqual(len(got), 1)
                self.assertIn("không nhận bản ghi phái sinh", got[0])


class Api:
    """Giả `core` của xt.py: `_gh_one` theo đường dẫn REST, `_git` trả CHANGELOG của nhánh đích."""

    def __init__(self, raw: bytes, changelog: str = "## [3.34.0] - 2026-11-19\n## [3.33.0] - 2026-11-08\n") -> None:
        self.calls: list[str] = []
        self.changelog = changelog
        self.git_rc = 0
        b64 = base64.b64encode(raw).decode()
        self.routes: dict[str, Any] = {
            f"{API}/branches/main": {"commit": {"sha": BASE}},  # đỉnh nhánh đích đọc lúc kiểm
            f"{API}/compare/{BASE}...{HEAD}": {"files": [file(sha=BLOB)]},
            f"{API}/git/trees/{HEAD}": {"truncated": False, "tree": [{"path": "docs", "type": "tree", "sha": DOCS}]},
            f"{API}/git/trees/{DOCS}": {"truncated": False, "tree": [{"path": "derived", "type": "tree", "sha": DER}]},
            f"{API}/git/trees/{DER}": {
                "truncated": False,
                "tree": [{"path": NAME, "type": "blob", "mode": "100644", "sha": BLOB, "size": len(raw)}],
            },
            f"{API}/git/blobs/{BLOB}": {"encoding": "base64", "content": "\n".join([b64[:20], b64[20:]])},
        }
        self.core = types.SimpleNamespace(
            _gh_one=self.one, PrInputError=xt.PrInputError, _git=self.git, project_dir=lambda: ROOT
        )

    def one(self, path: str) -> dict:
        self.calls.append(path)
        got = self.routes.get(path)
        if isinstance(got, Exception):
            raise got
        return got if isinstance(got, dict) else {}

    def git(self, cwd: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(["git", *args], self.git_rc, self.changelog, "")

    def entry(self, **over: Any) -> None:
        self.routes[f"{API}/git/trees/{DER}"]["tree"][0].update(over)


def pull(**over: Any) -> dict:
    p: dict = {
        "head": {"sha": HEAD, "repo": {"full_name": HEAD_REPO, "owner": {"login": "alice", "type": "User"}}},
        "base": {"sha": "c" * 40, "ref": "main", "repo": {"full_name": dv.UPSTREAM}},  # base.sha cũ: không dùng
        "user": {"login": "alice"},
        "changed_files": 1,
    }
    p.update(over)
    return p


class EvaluateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.enterContext(unittest.mock.patch.object(dv, "today", return_value=DAY))

    def run_eval(self, api: Api, p: dict | None = None) -> dict:
        return dv.evaluate(api.core, API, pull() if p is None else p)

    def test_ok_pins_head_and_reads_by_tree(self) -> None:
        api = Api(enc(good()))
        got = self.run_eval(api)
        self.assertEqual(got, {"ok": True, "file": PATH, "repo": HEAD_REPO, "head": HEAD, "reasons": []})
        self.assertEqual(len(api.calls), 6)  # đỉnh nhánh + compare + 3 cây + blob; không API contents (theo symlink)
        self.assertIn(f"{API}/compare/{BASE}...{HEAD}", api.calls)  # so với đỉnh nhánh đích, không với base.sha cũ

    def assert_reason(self, api: Api, want: str, p: dict | None = None) -> dict:
        got = self.run_eval(api, p)
        self.assertFalse(got["ok"])
        self.assertTrue(any(want in r for r in got["reasons"]), got["reasons"])
        return got

    def test_identity(self) -> None:
        api = Api(enc(good()))
        self.assert_reason(api, "không có head repo", pull(head={"sha": HEAD, "repo": None}))
        self.assert_reason(api, "không có head repo", pull(head="x"))
        same = pull(head={"sha": HEAD, "repo": {"full_name": "WWW-donghanhcungban-org/x-templates"}})
        self.assert_reason(api, "chính repo đích", same)
        # Fork của khung chạy steward riêng (repo đích khác): không có làn derived.
        other = pull(base={"ref": "main", "repo": {"full_name": "bob/X-Templates"}})
        self.assert_reason(api, "repo đích không phải www-donghanhcungban-org/X-Templates", other)
        self.assert_reason(api, "repo đích không phải", pull(base={"ref": "main"}))
        self.assertEqual(api.calls, [])  # danh tính sai: không gọi API thêm

    def test_author_must_own_personal_fork(self) -> None:
        api = Api(enc(good()))
        self.assert_reason(api, "không phải chủ fork cá nhân", pull(user={"login": "mallory"}))
        self.assertTrue(self.run_eval(api, pull(user={"login": "ALICE"}))["ok"])  # login không phân biệt hoa thường
        org = {"sha": HEAD, "repo": {"full_name": HEAD_REPO, "owner": {"login": "alice", "type": "Organization"}}}
        self.assertTrue(self.run_eval(api, pull(head=org, user={"login": "bob"}))["ok"])  # thành viên tổ chức
        for p in (
            pull(user=None),
            pull(user={"login": 5}),
            pull(head={"sha": HEAD, "repo": {"full_name": HEAD_REPO}}),
            pull(head={"sha": HEAD, "repo": {"full_name": HEAD_REPO, "owner": {"login": "alice", "type": "Bot"}}}),
        ):
            with self.subTest(p):
                self.assert_reason(api, "không xác minh được chủ head repo hoặc tác giả PR", p)

    def test_file_list_pinned_to_snapshot(self) -> None:
        api = Api(enc(good()))
        base = {"ref": "", "repo": {"full_name": dv.UPSTREAM}}
        self.assert_reason(api, "API GitHub (ValueError)", pull(base=base))  # thiếu nhánh đích
        api.routes[f"{API}/branches/main"] = {"commit": {"sha": "main"}}
        self.assert_reason(api, "API GitHub (ValueError)")  # đỉnh nhánh không phải SHA
        api.routes[f"{API}/branches/main"] = {"commit": None}
        self.assert_reason(api, "API GitHub (ValueError)")
        api.routes[f"{API}/branches/main"] = xt.PrInputError("403")
        self.assert_reason(api, "API GitHub (PrInputError)")
        api = Api(enc(good()))
        self.assert_reason(api, "API GitHub (ValueError)", pull(head={**pull()["head"], "sha": "abc"}))
        api.routes[f"{API}/compare/{BASE}...{HEAD}"] = xt.PrInputError("gh lỗi")
        self.assert_reason(api, "API GitHub (PrInputError)")
        api.routes[f"{API}/compare/{BASE}...{HEAD}"] = {"files": "x"}
        self.assert_reason(api, "API GitHub (ValueError)")
        api = Api(enc(good()))
        self.assert_reason(api, "changed_files", pull(changed_files=2))
        self.assert_reason(api, "changed_files", pull(changed_files="1"))
        # Ca đồng thời: push chen giữa — danh sách `pulls/N/files` mới chỉ còn tệp JSON nhưng head trong ảnh chụp (SHA sẽ
        # bị ghim khi merge) còn đổi tệp khác: compare của đúng cặp SHA quyết định.
        api.routes[f"{API}/compare/{BASE}...{HEAD}"] = {"files": [file(sha=BLOB), file(".github/workflows/ci.yml")]}
        self.assert_reason(api, "PR đổi 2 tệp", pull(changed_files=2))

    def test_tree_problems(self) -> None:
        cases = {
            "cây bị cắt": lambda a: a.routes[f"{API}/git/trees/{HEAD}"].update(truncated=True),
            "thiếu docs": lambda a: a.routes[f"{API}/git/trees/{HEAD}"].update(tree=[]),
            "docs là blob": lambda a: a.routes[f"{API}/git/trees/{HEAD}"]["tree"][0].update(type="blob"),
            "sha cây lạ": lambda a: a.routes[f"{API}/git/trees/{DOCS}"]["tree"][0].update(sha="../x"),
            "tên trùng": lambda a: a.routes[f"{API}/git/trees/{DER}"]["tree"].append({"path": NAME}),
            "blob không base64": lambda a: a.routes[f"{API}/git/blobs/{BLOB}"].update(encoding="none"),
            "base64 hỏng": lambda a: a.routes[f"{API}/git/blobs/{BLOB}"].update(content="!!!"),
            "kích thước lệch": lambda a: a.entry(size=3),
            "blob lỗi gh": lambda a: a.routes.update({f"{API}/git/blobs/{BLOB}": xt.PrInputError("x")}),
        }
        for name, mutate in cases.items():
            with self.subTest(name):
                api = Api(enc(good()))
                mutate(api)
                self.assert_reason(api, "không đọc được tệp ở head")

    def test_entry_problems(self) -> None:
        cases = {
            "symlink": ({"mode": "120000"}, "mode Git 120000"),
            "thực thi": ({"mode": "100755"}, "mode Git 100755"),
            "thư mục": ({"mode": "040000", "type": "tree"}, "mode Git 040000"),
            "submodule": ({"mode": "160000", "type": "commit"}, "mode Git 160000"),
            "trống": ({"size": 0}, "tệp trống hoặc > 2048 B"),
            "quá lớn": ({"size": 3000}, "tệp trống hoặc > 2048 B"),
            "size chuỗi": ({"size": "10"}, "tệp trống hoặc > 2048 B"),
            "blob khác compare": ({"sha": "c" * 40}, "không khớp"),
            "sha lạ": ({"sha": "zz"}, "không khớp"),
        }
        for name, (over, want) in cases.items():
            with self.subTest(name):
                api = Api(enc(good()))
                api.entry(**over)
                self.assert_reason(api, want)

    def test_released_versions_from_base_branch(self) -> None:
        api = Api(enc(good()))
        api.git_rc = 128
        self.assert_reason(api, "CHANGELOG.md")
        api = Api(enc(good()), changelog="## [Unreleased]\n")
        self.assert_reason(api, "CHANGELOG.md")
        api = Api(enc(good(**up("3.35.0"))))
        self.assert_reason(api, "không phải bản khung đã phát hành")
        self.assertEqual(dv.released_versions(Api(b"x").core, "origin/main"), VERSIONS)

    def test_content_problems(self) -> None:
        self.assert_reason(Api(enc(good(description="xem https://x.vn"))), "URL")
        self.assert_reason(Api(enc(good(repo="bob/X-Templates"))), "repo phải đúng head repo")
        got = self.assert_reason(
            Api(enc(good())),
            "không nhận",
            pull(head={"sha": HEAD, "repo": {"full_name": "a--b/c", "owner": {"login": "alice", "type": "User"}}}),
        )
        self.assertEqual((got["file"], got["repo"]), ("", ""))

    def test_lane_only_for_derived_paths(self) -> None:
        api = Api(enc(good()))
        self.assertIsNone(dv.lane(api.core, API, pull(), [file("src/a.py"), "x", {"filename": 5}]))
        self.assertEqual(api.calls, [])
        self.assertTrue(dv.lane(api.core, API, pull(), [file()])["ok"])
        moved = [file("README.md", status="renamed", previous_filename=PATH)]  # dời bản ghi ra khỏi vùng vẫn bị xét
        api.routes[f"{API}/compare/{BASE}...{HEAD}"] = {"files": moved}
        got = dv.lane(api.core, API, pull(), moved)
        assert got is not None
        self.assertEqual(
            got["reasons"],
            [
                f"tệp README.md khác {PATH}",
                "PR đổi tên/di chuyển tệp",
                "trạng thái tệp renamed — chỉ nhận added/modified",
            ],
        )


DERIVED_OK = {"ok": True, "file": PATH, "repo": HEAD_REPO, "head": "abc1234def", "reasons": []}


def dpr(**over: Any) -> dict:
    return pr(**{"files": [{"path": PATH, "additions": 11, "deletions": 0}], "derived": DERIVED_OK, **over})


# Trường danh tính như `_pr_rest` dựng: PR từ fork của người ngoài (không quyền ghi repo đích).
FORK = {"repo": dv.UPSTREAM, "headRepo": HEAD_REPO, "author": "alice", "authorAssociation": "NONE"}
SAME = {"repo": dv.UPSTREAM, "headRepo": dv.UPSTREAM, "author": "chu", "authorAssociation": "OWNER"}
FORK_WHY = f"PR từ fork {HEAD_REPO} — người merge"


class ForkIdentityTest(unittest.TestCase):
    """PR từ fork / tác giả không quyền ghi ngoài làn derived hợp lệ: `merge-check`/`pr next`/guard không ra merge ở mọi
    mức tự chủ và mọi làn (trước đây chỉ steward kiểm — `steward_untrusted`)."""

    FILES = {
        "tài liệu": [{"path": "README.md", "additions": 3, "deletions": 1}],
        "hook guard": [{"path": ".claude/hooks/guard.py", "additions": 5, "deletions": 1}],
        "workflow CI": [{"path": ".github/workflows/ci.yml", "additions": 2, "deletions": 2}],
    }

    def test_fork_never_merges_at_any_level(self) -> None:
        for name, files in self.FILES.items():
            for level in (1, 2, 3):
                with self.subTest(name, level=level):
                    same = xt.merge_decision(pr(files=files, **SAME), level)
                    fork = xt.merge_decision(pr(files=files, **FORK), level)
                    self.assertEqual(fork["verdict"], "human")
                    self.assertEqual(fork["reasons"][0], FORK_WHY)
                    self.assertEqual(fork["lane"], same["lane"])  # làn tính như cũ, chỉ verdict giữ người
                    self.assertNotIn("next_rest", fork)
                    self.assertEqual(fork["next"], "để người merge; báo cáo lý do")
                    old = xt.merge_decision(pr(files=files), level)
                    self.assertEqual({**same, "repo": ""}, old)  # cùng repo: như trước khi xét danh tính
        l3 = xt.merge_decision(pr(files=self.FILES["workflow CI"], **SAME), 3)
        self.assertEqual(l3["verdict"], "merge")  # cùng repo ở L3 vẫn tự merge làn chuẩn

    def test_author_without_write_access(self) -> None:
        same_repo = {"repo": dv.UPSTREAM, "headRepo": dv.UPSTREAM}
        cases = {
            "CONTRIBUTOR": ({"author": "bob", "authorAssociation": "CONTRIBUTOR"}, "human"),
            "MEMBER không quyền ghi": ({"author": "bob", "authorAssociation": "MEMBER"}, "human"),
            "MEMBER có quyền ghi": (
                {"author": "bob", "authorAssociation": "MEMBER", "authorCanWrite": "true"},
                "merge",
            ),
            "COLLABORATOR": ({"author": "bob", "authorAssociation": "COLLABORATOR"}, "merge"),
            "dependabot": ({"author": "dependabot[bot]", "authorAssociation": "NONE"}, "merge"),
            "chỉ headRepo, thiếu association": ({}, "human"),  # có danh tính mà không rõ quyền: chặt
        }
        for name, (who, want) in cases.items():
            with self.subTest(name):
                d = xt.merge_decision(pr(**same_repo, **who), 3)
                self.assertEqual(d["verdict"], want, d["reasons"])
                self.assertEqual(d["reasons"][0] == xt.steward_untrusted({**same_repo, **who}), want == "human")
        # Ảnh chụp `--pr-json` dạng MERGE_FIELDS (không trường danh tính): luật cũ.
        self.assertEqual(xt.merge_identity_reason(pr()), "")
        self.assertEqual(xt.merge_decision(pr(), 3)["verdict"], "merge")

    def test_derived_lane_and_precedence(self) -> None:
        ok = xt.derived_steward_only(xt.merge_check_result(dpr(**FORK), 3, [], False, "harden"))
        self.assertEqual((ok["verdict"], ok["lane"], ok["auto_merge_ok"]), ("wait", "derived", False))
        self.assertNotIn(FORK_WHY, ok["reasons"])
        bad = dpr(**FORK, derived={**DERIVED_OK, "ok": False, "reasons": ["description rỗng"]})
        d = xt.derived_steward_only(xt.merge_check_result(bad, 3, [], False, "harden"))
        self.assertEqual((d["verdict"], d["lane"], d["reasons"][0]), ("human", "nhanh", FORK_WHY))
        self.assertIn("làn derived: không — description rỗng", d["reasons"])
        # Ngoại lệ cứng đứng trước (guard chặn theo `hard`); miễn ngoại lệ cứng thì danh tính vẫn giữ người.
        auth = pr(files=[{"path": "src/auth/login.py", "additions": 1, "deletions": 0}], **FORK)
        hard = xt.merge_decision(auth, 3)
        self.assertTrue(hard["hard"] and hard["reasons"][0].startswith("ngoại lệ cứng"), hard)
        waived = xt.merge_decision(auth, 3, hard_auto=True)
        self.assertEqual((waived["verdict"], waived["hard"], waived["reasons"][0]), ("human", [], FORK_WHY))
        # Trạng thái chặn (đóng, CI đỏ) vẫn báo đúng như PR thường.
        self.assertEqual(xt.merge_decision(pr(state="CLOSED", **FORK), 3)["verdict"], "closed")
        red = [{"__typename": "CheckRun", "name": "test", "status": "COMPLETED", "conclusion": "FAILURE"}]
        self.assertEqual(xt.merge_decision(pr(statusCheckRollup=red, **FORK), 3)["verdict"], "fix")

    def test_cli_and_guard_read_human(self) -> None:
        base = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(unittest.mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(base)}))
        commit_base_xt(base, "merge_autonomy: L3\nmerge_review: optional\n")
        p = pr(files=self.FILES["tài liệu"], **FORK)
        rc, out, _ = run_main("merge-check", "--pr-json", "-", "--json", stdin=json.dumps(p))
        d = json.loads(out)
        self.assertEqual((rc, d["verdict"], d["eligible"]), (1, "human", False))
        rc, out, _ = run_main("pr", "next", "--pr-json", "-", stdin=json.dumps(p))
        self.assertEqual((rc, out.splitlines()[0]), (0, f"DEFER-HUMAN · PR #7 · head abc1234 — {FORK_WHY}"))
        rc, out, _ = run_main("merge-check", "--pr-json", "-", "--json", stdin=json.dumps({**p, **SAME}))
        self.assertEqual((rc, json.loads(out)["verdict"]), (0, "merge"))
        sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
        import guard

        with unittest.mock.patch.object(guard, "merge_check", return_value=d):
            verdict, why = guard.gh_pr_merge_rule(["7", "--match-head-commit", "abc1234def"], str(base))
        self.assertEqual(verdict, "ask")  # không còn allow như khi merge-check trả merge
        self.assertIn(f"merge-check: human: {FORK_WHY}", why)


class MergeLaneTest(unittest.TestCase):
    def test_derived_lane_merges_without_review(self) -> None:
        d = xt.merge_decision(dpr(), 2)
        self.assertEqual((d["verdict"], d["lane"]), ("merge", "derived"))
        self.assertEqual(d["reasons"][0], "làn derived, CI xanh, không xung đột")
        self.assertIn(f"làn derived: {PATH} hợp lệ (schema v1) từ {HEAD_REPO}", d["reasons"][1])
        self.assertEqual(xt.merge_decision(dpr(), 1)["verdict"], "human")  # L1 vẫn để người merge
        res = xt.merge_check_result(dpr(), 3, [], False, "harden")  # merge_review: required, chưa có review nào
        self.assertEqual((res["verdict"], res["review"], res["eligible"]), ("merge", "na", True))
        seen = xt.merge_check_result(dpr(labels=[{"name": xt.STANDARD_LABEL}]), 3, [], False, "harden")
        self.assertEqual((seen["verdict"], seen["eligible"]), ("review", False))  # từng vào làn chuẩn: vẫn đòi review
        nxt = xt.pr_next(xt.merge_decision(dpr(), 2), False, {})
        self.assertEqual(nxt["action"], "merge")
        self.assertIn("làn derived", nxt["why"])
        # Tiêu đề PR fork không lên nhánh chính nên không chặn làn derived; ở làn khác vẫn chặn như cũ.
        self.assertEqual(xt.merge_decision(dpr(title="Sửa @bob http://x"), 2)["verdict"], "merge")
        self.assertEqual(xt.merge_decision(dpr(title="Sửa", derived="x"), 2)["verdict"], "fix")

    def test_fixed_commit_subject_and_body(self) -> None:
        hostile = dpr(title="docs: xem https://evil.example @bob", number=12)
        subject, body = xt.derived_commit(hostile)
        self.assertEqual(subject, "docs(derived): cập nhật alice--X-Templates (#12)")
        self.assertEqual(body, f"Bản ghi {PATH} của {HEAD_REPO}, merge qua làn derived (ADR-0087).")
        self.assertEqual(xt.pr_title_problems(subject.removesuffix(" (#12)")), [])
        long_name = {**DERIVED_OK, "file": f"docs/derived/{'a' * 39}--{'b' * 100}.json"}
        subject, _ = xt.derived_commit(dpr(derived=long_name))
        self.assertEqual(subject, "docs(derived): cập nhật bản ghi dự án phái sinh (#7)")
        out = {
            "pr": 12,
            "head": HEAD,
            "action": "merge",
            "merge_intent": {"host": "github.com", "repo": "o/r", "pr": 12, "expected_head": HEAD},
        }
        cmd = xt._steward_command(out, RepoTarget("github.com", "o/r"), *xt.derived_commit(hostile))[0]
        self.assertIn("commit_title=docs(derived): cập nhật alice--X-Templates (#12)", cmd)
        self.assertIn(f"commit_message={body}", cmd)
        self.assertFalse(any("evil" in a or "@" in a for a in cmd), cmd)
        self.assertNotIn(
            "commit_message", " ".join(xt._steward_command(out, RepoTarget("github.com", "o/r"), "fix: a (#12)")[0])
        )

    def test_agent_merge_check_waits_for_steward(self) -> None:
        d = xt.derived_steward_only({**xt.merge_decision(dpr(), 3), "eligible": True})
        self.assertEqual((d["verdict"], d["eligible"], d["next"]), ("wait", False, xt.DERIVED_WAIT))
        self.assertNotIn("next_rest", d)
        self.assertEqual(d["reasons"][-1], xt.DERIVED_STEWARD)
        self.assertIs(d["auto_merge_ok"], False)  # chỉ steward merge: không phát tín hiệu auto-merge
        fast = xt.merge_decision(pr(), 3)
        self.assertIs(xt.derived_steward_only(fast), fast)
        red = xt.merge_decision(dpr(mergeable="CONFLICTING"), 3)
        out = xt.derived_steward_only({**red, "auto_merge_ok": True})
        self.assertEqual({**out, "auto_merge_ok": True}, {**red, "auto_merge_ok": True})
        self.assertEqual((out["verdict"], out["auto_merge_ok"]), ("fix", False))

    def test_falls_back_to_existing_rules(self) -> None:
        mismatch = dpr(derived={**DERIVED_OK, "head": "khác"})
        cases = {
            "head lệch": (mismatch, "nhanh", "head lệch"),
            "nhãn risk:": (dpr(labels=[{"name": "risk:data"}]), "chuẩn", "nhãn risk:"),
            "danh sách bị cắt": (dpr(filesTruncated=True), "chuẩn", "head lệch"),
            "ngoại lệ cứng": (
                pr(
                    files=[{"path": "docs/derived/alice--auth.json", "additions": 1, "deletions": 0}],
                    derived=DERIVED_OK,
                ),
                "chuẩn",
                "ngoại lệ cứng",
            ),
            "không hợp lệ": (dpr(derived={**DERIVED_OK, "ok": False, "reasons": ["PR đổi 2 tệp"]}), "nhanh", "2 tệp"),
            "reasons lạ": (dpr(derived={**DERIVED_OK, "ok": "true", "reasons": "x"}), "nhanh", "head lệch"),
            "thêm tệp khác": (
                dpr(files=[{"path": PATH, "additions": 1, "deletions": 0}, {"path": "README.md"}]),
                "nhanh",
                "PR đổi tệp khác",
            ),
            "tệp khác bản ghi": (dpr(files=[{"path": "docs/derived/bob--x.json"}]), "nhanh", "head lệch"),
            "đổi tên": (dpr(files=[{"path": PATH, "previous": "docs/derived/bob--x.json"}]), "nhanh", "head lệch"),
            "phần tử lạ": (dpr(files=[{"path": PATH}, "x"]), "nhanh", "head lệch"),
        }
        for name, (p, lane, want) in cases.items():
            with self.subTest(name):
                d = xt.merge_decision(p, 3, hard_auto=True)
                self.assertEqual(d["lane"], lane)
                notes = [r for r in d["reasons"] if r.startswith("làn derived: không — ")]
                self.assertEqual(len(notes), 1, d["reasons"])
                self.assertIn(want, notes[0])
                # PR fork không qua kiểm: chờ người như PR fork thường (docs/derived/README.md), không phải merge.
                forked = xt.merge_decision({**p, **FORK}, 3, hard_auto=True)
                self.assertEqual((forked["verdict"], forked["lane"]), ("human", lane))
                # ngoại lệ cứng không miễn được (danh sách bị cắt) đứng trước lý do danh tính
                lead = "ngoại lệ cứng" if forked["hard"] else FORK_WHY
                self.assertTrue(forked["reasons"][0].startswith(lead), forked["reasons"])
        plain = xt.merge_decision(pr(derived="x"), 2)
        self.assertFalse(any("làn derived" in r for r in plain["reasons"]))

    def test_blocked_keeps_derived_note(self) -> None:
        red = [{"__typename": "CheckRun", "name": "test", "status": "COMPLETED", "conclusion": "FAILURE"}]
        d = xt.merge_decision(dpr(statusCheckRollup=red), 3)
        self.assertEqual((d["verdict"], d["lane"]), ("fix", "derived"))
        self.assertIn("làn derived: docs/derived/", d["reasons"][-1])

    def test_merge_check_cli_with_review_required(self) -> None:
        base = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(unittest.mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(base)}))
        commit_base_xt(base, "merge_autonomy: L3\n")  # merge_review: required
        rc, out, _ = run_main("merge-check", "--pr-json", "-", stdin=json.dumps(dpr()))
        self.assertEqual(rc, 1, out)  # guard đọc verdict này: phiên agent không merge làn derived (thân = commit fork)
        self.assertTrue(out.startswith("WAIT · PR #7 · làn derived"), out)
        self.assertIn("làn derived: docs/derived/alice--X-Templates.json hợp lệ", out)
        self.assertIn(xt.DERIVED_STEWARD, out)
        self.assertNotIn("match-head-commit", out)
        rc, out, _ = run_main("pr", "next", "--pr-json", "-", stdin=json.dumps(dpr()))
        self.assertEqual((rc, out.splitlines()[0]), (0, f"WAIT · PR #7 · head abc1234 — {xt.DERIVED_STEWARD}"))
        self.assertEqual(out.splitlines()[1], f"→ {xt.DERIVED_WAIT}")
        rc, out, _ = run_main("pr", "next", "--pr-json", "-", stdin=json.dumps(pr()))
        self.assertTrue(out.startswith("MERGE · PR #7"), out)  # làn khác không đổi


class DerivedGh(FakeGh):
    SHA = HEAD
    TARGET = f"repos/{dv.UPSTREAM.lower()}"

    def route(self, command: list[str]) -> tuple[str, bool]:
        path, later = super().route(command)
        return path.replace(self.TARGET + "/", self.REPO + "/", 1), later


class RestLaneTest(unittest.TestCase):
    """`_pr_rest` → `merge-check`/steward: PR fork chỉ đổi tệp của mình vào làn derived; chạm tệp khác hay API lỗi thì không."""

    def setUp(self) -> None:
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(unittest.mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.base)}))
        commit_base_xt(self.base, "merge_autonomy: L3\n")
        self.enterContext(unittest.mock.patch.object(dv, "today", return_value=DAY))
        self.enterContext(unittest.mock.patch.object(dv, "released_versions", return_value=VERSIONS))

    def gh(self, files: list | None = None, reviews: list | None = None) -> DerivedGh:
        api = Api(enc(good()))
        listed = files if files is not None else [file(sha=BLOB, additions=11, deletions=0)]
        raw = {k.replace(API, DerivedGh.REPO): json.dumps(v) for k, v in api.routes.items()}
        raw[f"{DerivedGh.REPO}/pulls/7/files?per_page=100"] = json.dumps(listed)
        raw[f"{DerivedGh.REPO}/compare/{BASE}...{HEAD}"] = json.dumps({"files": listed})
        base = {"sha": BASE, "ref": "main", "repo": {"full_name": dv.UPSTREAM, "default_branch": "main"}}
        head = {"sha": HEAD, "repo": {"full_name": HEAD_REPO, "owner": {"login": "alice", "type": "User"}}}
        # Tiêu đề và thân PR do fork viết (link, @, trailer giả) — không được lên lệnh merge.
        hostile = {"title": "Xem https://evil.example @bob", "body": "Co-authored-by: x <x@y>"}
        p = {
            "head": head,
            "base": base,
            "html_url": f"https://github.com/{dv.UPSTREAM}/pull/7",
            "changed_files": len(listed),
            **hostile,
        }
        user = {"user": {"login": "alice"}, "author_association": "NONE"}
        return DerivedGh(pull={**p, **user}, raw=raw, reviews=reviews, real_git=True)

    def test_deleted_fork_counts_as_untrusted_source(self) -> None:
        """Fork đã xoá: `head.repo` null — không được coi là PR nội bộ (COLLABORATOR quyền đọc vẫn ra merge trước đây)."""
        gh = self.gh()
        gh.pull["head"]["repo"] = None
        with gh.patch():
            p = xt._pr_rest("7")
        self.assertEqual(p["headRepo"], "(đã xoá)")
        self.assertTrue(xt.merge_identity_reason({**p, "authorAssociation": "COLLABORATOR"}))

    def test_fork_pr_own_file_merges_by_steward(self) -> None:
        gh = self.gh()
        with gh.patch(), unittest.mock.patch.object(xt, "_steward_apply", side_effect=lambda out, d, r, c, *a: c):
            p = xt._pr_rest("7")
            rc, out, _ = run_main("merge-check", "--pr", "7", "--json")
            cmds = xt._steward_one("7", RepoTarget("github.com", dv.UPSTREAM.lower()), self.base, True)
        self.assertEqual(p["derived"], {"ok": True, "file": PATH, "repo": HEAD_REPO, "head": HEAD, "reasons": []})
        d = json.loads(out)
        self.assertEqual((rc, d["verdict"], d["lane"]), (1, "wait", "derived"))  # agent/guard: chỉ steward merge
        self.assertEqual(len(cmds), 1)  # steward tự merge PR fork chỉ ở làn derived, ghim head
        cmd = cmds[0]
        self.assertEqual(
            cmd[:7], ["gh", "api", "-X", "PUT", "--hostname", "github.com", f"{DerivedGh.TARGET}/pulls/7/merge"]
        )
        self.assertIn(f"sha={HEAD}", cmd)
        self.assertIn("commit_title=docs(derived): cập nhật alice--X-Templates (#7)", cmd)
        self.assertIn(f"commit_message=Bản ghi {PATH} của {HEAD_REPO}, merge qua làn derived (ADR-0087).", cmd)
        self.assertFalse(any("evil" in a or "@" in a or "Co-authored" in a for a in cmd), cmd)
        self.assertIn(f"{DerivedGh.TARGET}/compare/{BASE}...{HEAD}", gh.paths())

    def test_changes_requested_leaves_lane_even_when_review_optional(self) -> None:
        commit_base_xt(self.base, "merge_autonomy: L3\nmerge_review: optional\n")
        asked = [{"user": {"login": "carol"}, "state": "CHANGES_REQUESTED"}]
        with self.gh(reviews=asked).patch():
            p = xt._pr_rest("7")
            step = xt._steward_one("7", RepoTarget("github.com", dv.UPSTREAM.lower()), self.base, False)
        self.assertFalse(p["derived"]["ok"])
        self.assertIn("có review yêu cầu sửa (CHANGES_REQUESTED)", p["derived"]["reasons"])
        self.assertEqual(step["action"], "defer-human")
        approved = [*asked, {"user": {"login": "carol"}, "state": "APPROVED"}]
        with self.gh(reviews=approved).patch():
            self.assertTrue(xt._pr_rest("7")["derived"]["ok"])

    def test_fork_pr_touching_other_file_waits_for_human(self) -> None:
        listed = [file(sha=BLOB, additions=11, deletions=0), file("README.md", additions=1, deletions=0)]
        with self.gh(listed).patch():
            p = xt._pr_rest("7")
            step = xt._steward_one("7", RepoTarget("github.com", dv.UPSTREAM.lower()), self.base, False)
        self.assertFalse(p["derived"]["ok"])
        self.assertEqual(step["action"], "defer-human")
        self.assertIn("PR từ fork alice/X-Templates", step["why"])
        with self.gh(listed).patch():
            rc, out, _ = run_main("merge-check", "--pr", "7", "--json")
        # Guard đọc đúng kết quả này: tiêu đề fork sai dạng chặn trước (`fix`); sửa tiêu đề thì vẫn giữ người.
        self.assertEqual((rc, json.loads(out)["verdict"]), (1, "fix"))
        titled = xt.merge_decision({**p, "title": "docs: thêm bản ghi"}, 3)
        self.assertEqual((titled["verdict"], titled["reasons"][0]), ("human", FORK_WHY))

    def test_api_failure_never_enters_lane(self) -> None:
        with (
            self.gh().patch(),
            unittest.mock.patch.object(dv, "pinned_files", side_effect=xt.PrInputError("403")),
        ):
            p = xt._pr_rest("7")
            step = xt._steward_one("7", RepoTarget("github.com", dv.UPSTREAM.lower()), self.base, False)
        self.assertFalse(p["derived"]["ok"])
        d = xt.merge_decision({**p, "title": "docs: thêm bản ghi"}, 3)
        self.assertEqual((d["lane"], d["verdict"], d["reasons"][0]), ("nhanh", "human", FORK_WHY))
        self.assertEqual(step["action"], "defer-human")

    def test_other_prs_untouched_and_module_optional(self) -> None:
        with FakeGh().patch():
            self.assertNotIn("derived", xt._pr_rest("7"))
        bare = [p for p in sys.path if p != str(xt.SCRIPT_DIR)]
        with unittest.mock.patch.dict(sys.modules), unittest.mock.patch.object(sys, "path", bare):
            del sys.modules["xt_derived"]
            fresh = xt._derived()  # nạp theo đường tệp, không thêm thư mục scripts vào sys.path
            self.assertIsNot(fresh, dv)
            self.assertIs(xt._derived(), fresh)
            self.assertEqual((fresh.UPSTREAM, fresh.__file__), (dv.UPSTREAM, str(xt.DERIVED_MODULE)))
            self.assertNotIn(str(xt.SCRIPT_DIR), sys.path)
        with unittest.mock.patch.object(xt, "DERIVED_MODULE", self.base / "khong-co.py"):
            with self.gh().patch():
                self.assertNotIn("derived", xt._pr_rest("7"))
            sub = next(a for a in xt.build_parser()._actions if a.__class__.__name__ == "_SubParsersAction")
            self.assertNotIn("derived", sub.choices)


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(unittest.mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.base)}))
        self.enterContext(unittest.mock.patch.object(dv, "today", return_value=DAY))
        (self.base / "CHANGELOG.md").write_text("## [Unreleased]\n## [3.34.0] - 2026-11-19\n", encoding="utf-8")
        self.dir = self.base / "docs" / "derived"
        self.dir.mkdir(parents=True)
        (self.dir / "README.md").write_text("# x\n", encoding="utf-8")

    def put(self, name: str = NAME, rec: Any = None) -> Path:
        path = self.dir / name
        path.write_bytes(enc(good() if rec is None else rec))
        return path

    def test_check_files(self) -> None:
        ok = self.put()
        rc, out, _ = run_main("derived", "check", str(ok))
        self.assertEqual((rc, out.strip()), (0, f"✓ {ok}"))
        bad = self.put("bob--x.json", good(repo="bob/x", description="a@b"))
        rc, out, _ = run_main("derived", "check", str(ok), str(bad))
        self.assertEqual(rc, 1)
        self.assertIn("  - description không được có HTML", out)
        rc, out, _ = run_main("derived", "check", "--json", str(ok))
        row = json.loads(out)["files"][0]
        self.assertEqual((rc, row["ok"], row["repo"], row["record"]["kind"]), (0, True, HEAD_REPO, "fork"))

    def test_check_files_local_rules(self) -> None:
        named = self.put("sai-ten.json")
        link = self.dir / "carol--x.json"
        link.symlink_to(self.put("carol--y.json", good(repo="carol/y")))
        execu = self.put("dave--x.json", good(repo="dave/x"))
        execu.chmod(0o755)
        for path, want in ((named, "tên tệp"), (link, "symlink"), (execu, "thực thi")):
            with self.subTest(want):
                rc, out, _ = run_main("derived", "check", str(path))
                self.assertEqual(rc, 1)
                self.assertIn(want, out)
        rc, out, _ = run_main("derived", "check", str(self.dir / "khong-co--x.json"))
        self.assertEqual(rc, 2)
        self.assertIn("không đọc được", out)
        odd = self.put("e--x\x1b.json", good(repo="e/x"))
        rc, out, _ = run_main("derived", "check", str(odd))
        self.assertNotIn("\x1b", out)  # tên tệp có ký tự điều khiển in dạng thoát

    def test_check_without_changelog_checks_shape(self) -> None:
        (self.base / "CHANGELOG.md").unlink()
        rc, out, _ = run_main("derived", "check", str(self.put(rec=good(**up("9.9.9")))))
        self.assertEqual(rc, 0)
        self.assertIn("⚠ không đọc được bản đã phát hành", out)
        (self.base / "CHANGELOG.md").mkdir()
        self.assertIsNone(dv._local_versions(xt))

    def test_check_usage(self) -> None:
        for args in ((), ("--pr", "7", "x.json")):
            with self.subTest(args):
                rc, _, err = run_main("derived", "check", *args)
                self.assertEqual(rc, 2)
                self.assertIn("đúng một trong --pr N hoặc TỆP", err)

    def test_check_pr(self) -> None:
        got = {"ok": False, "file": PATH, "repo": HEAD_REPO, "head": HEAD, "reasons": ["PR đổi 2 tệp"]}
        with (
            unittest.mock.patch.object(xt, "_pr_target", return_value=(API, "7")),
            unittest.mock.patch.object(xt, "_gh_one", return_value=pull()) as one,
            unittest.mock.patch.object(dv, "evaluate", return_value=got),
        ):
            rc, out, _ = run_main("derived", "check", "--pr", "7")
            self.assertEqual((rc, out), (1, "✗ PR #7 · làn derived: không\n  - PR đổi 2 tệp\n"))
            one.assert_called_once_with(f"{API}/pulls/7")
            got.update(ok=True, reasons=[])
            rc, out, _ = run_main("derived", "check", "--pr", "7", "--json")
            self.assertEqual((rc, json.loads(out)["ok"]), (0, True))
            rc, out, _ = run_main("derived", "check", "--pr", "7")
            self.assertEqual((rc, out), (0, "✓ PR #7 · làn derived: đủ điều kiện\n"))
        with unittest.mock.patch.object(xt, "_pr_target", side_effect=xt.PrInputError("không có PR")):
            rc, _, err = run_main("derived", "check", "--pr", "x")
        self.assertEqual(rc, 2)
        self.assertIn("không có PR", err)

    def test_check_pr_url_targets_upstream(self) -> None:
        """README hướng dẫn dạng URL: trong clone của fork, số PR trần có thể trỏ repo fork (`{owner}/{repo}`)."""
        got = {"ok": True, "file": PATH, "repo": HEAD_REPO, "head": HEAD, "reasons": []}
        url = f"https://github.com/{dv.UPSTREAM}/pull/12"
        with (
            unittest.mock.patch.object(xt, "_gh_one", return_value=pull()) as one,
            unittest.mock.patch.object(dv, "evaluate", return_value=got) as ev,
        ):
            rc, out, _ = run_main("derived", "check", "--pr", url)
        self.assertEqual((rc, out), (0, "✓ PR #12 · làn derived: đủ điều kiện\n"))
        one.assert_called_once_with(f"repos/{dv.UPSTREAM}/pulls/12")
        self.assertEqual(ev.call_args.args[1], f"repos/{dv.UPSTREAM}")

    def test_list(self) -> None:
        self.put()
        rc, out, _ = run_main("derived", "list")
        self.assertEqual(rc, 0)
        self.assertIn(f"{HEAD_REPO} · fork · 3.34.0 · active · 2026-11-21 — Bản fork cho nhóm nội bộ.", out)
        self.assertIn("1 bản ghi hợp lệ, 0 trái luật", out)
        self.put("bob--x.json", good(repo="bob/x", homepage="http://x.vn"))
        rc, out, _ = run_main("derived", "list")
        self.assertEqual(rc, 1)
        self.assertIn("1 bản ghi hợp lệ, 1 trái luật", out)
        self.assertIn("homepage chỉ nhận", out)
        rc, out, _ = run_main("derived", "list", "--json")
        d = json.loads(out)
        self.assertEqual((rc, [r["repo"] for r in d["records"]], len(d["invalid"])), (1, [HEAD_REPO], 1))
        (self.dir / "bob--x.json").unlink()
        rc, out, _ = run_main("derived", "list", "--json")
        self.assertEqual((rc, len(json.loads(out)["records"])), (0, 1))
        (self.dir / "c--x.json").mkdir()  # không đọc được → exit 2 ở cả hai dạng
        self.assertEqual(run_main("derived", "list")[0], 2)
        self.assertEqual(run_main("derived", "list", "--json")[0], 2)

    def test_list_without_folder(self) -> None:
        for p in self.dir.iterdir():
            p.unlink()
        self.dir.rmdir()
        rc, _, err = run_main("derived", "list")
        self.assertEqual(rc, 2)
        self.assertIn("không có thư mục docs/derived/", err)


class RepoRecordsTest(unittest.TestCase):
    """Bản ghi đã commit và ví dụ của hướng dẫn qua đúng kiểm của làn derived; TARGETS.md trỏ tới bản ghi X-Office."""

    def test_committed_records_valid(self) -> None:
        versions = frozenset(dv.RELEASE_RE.findall((ROOT / "CHANGELOG.md").read_text(encoding="utf-8")))
        records = sorted((ROOT / "docs" / "derived").glob("*.json"))
        self.assertIn(ROOT / "docs/derived/www-donghanhcungban-org--X-Office.json", records)
        for path in records:
            with self.subTest(path.name):
                head = dv.repo_from_name(path.name)
                assert head is not None
                data, got = dv.check_bytes(path.read_bytes(), head, dv.today(), versions)
                self.assertEqual(got, [])
                self.assertFalse(path.stat().st_mode & 0o111)
        targets = (ROOT / "docs" / "ops" / "TARGETS.md").read_text(encoding="utf-8")
        self.assertIn("(../derived/www-donghanhcungban-org--X-Office.json)", targets)

    def test_readme_example_valid(self) -> None:
        text = (ROOT / "docs" / "derived" / "README.md").read_text(encoding="utf-8")
        example = text.split("```json\n", 1)[1].split("```", 1)[0].encode()
        versions = frozenset(dv.RELEASE_RE.findall((ROOT / "CHANGELOG.md").read_text(encoding="utf-8")))
        self.assertEqual(dv.check_bytes(example, HEAD_REPO, DAY, versions)[1], [])


if __name__ == "__main__":
    unittest.main()
