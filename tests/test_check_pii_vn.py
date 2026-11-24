"""Loại `pii-vn` của `static-check` (ADR-0099): fixture tốt/xấu trong thư mục tạm; số đều là số giả đúng định dạng."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from xt_checks import kind_pii_vn

CCCD = "079" + "1" + "98" + "765432"  # mã tỉnh + thế kỷ/giới tính + năm + chuỗi tự chọn
PHONE = "0" + "912" + "000111"
EMAIL = "nguoi.dung" + "@" + "congty.vn"


class PiiVnTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def scan(self, name: str, text: str | bytes, **opts: str) -> list[tuple[int, str]]:
        path = self.base / name
        if isinstance(text, bytes):
            path.write_bytes(text)
        else:
            path.write_text(text, encoding="utf-8")
        return [(f.line, f.code) for f in kind_pii_vn.check([path], opts)]

    def test_interface(self):
        self.assertTrue(kind_pii_vn.HELP)
        self.assertIn(".jsonl", kind_pii_vn.SUFFIXES)
        self.assertEqual(len(kind_pii_vn.SUFFIXES), 8)

    def test_cccd(self):
        self.assertEqual(self.scan("a.log", f"id {CCCD}\n"), [(1, "PII001")])
        for bad in ("097" + CCCD[3:], "000" + CCCD[3:], "079" + "4" + CCCD[4:], CCCD + "1", "1" + CCCD, "x-" + CCCD):
            with self.subTest(bad=bad):
                self.assertEqual(self.scan("b.log", f"id {bad}\n"), [])

    def test_phone(self):
        for good in (PHONE, "+84" + PHONE[1:], "84" + PHONE[1:]):
            with self.subTest(good=good):
                self.assertEqual(self.scan("a.txt", f"tel {good}\n"), [(1, "PII002")])
        for bad in ("1700000000000", "0212000111", PHONE + "5", "550e8400-e29b-41d4-a716-446655440000", "id-" + PHONE):
            with self.subTest(bad=bad):
                self.assertEqual(self.scan("b.txt", f"v {bad}\n"), [])

    def test_email(self):
        self.assertEqual(self.scan("a.txt", EMAIL + "\n"), [(1, "PII003")])
        for doc in ("a@example.com", "a@mail.example.org", "a@x.test", "a@x.invalid", "a@localhost", "a@EXAMPLE.net"):
            self.assertEqual(self.scan("b.txt", doc + "\n"), [], doc)
        self.assertEqual(self.scan("c.txt", EMAIL + "\n", allow_domains=" congty.vn, khac.vn,,"), [])
        self.assertEqual(self.scan("d.txt", "a@congty.vn.evil.io\n", allow_domains="congty.vn"), [(1, "PII003")])

    def test_sensitive_keys(self):
        text = "ho_ten: Nguyen Van A\n{\"Ngay-Sinh\": \"01/02/1990\", 'sdt'='0900'}\nCCCD = 12\n"
        self.assertEqual(self.scan("a.log", text), [(1, "PII004"), (2, "PII004"), (2, "PII004"), (3, "PII004")])
        masked = 'ho_ten: ***\nemail: "[REDACTED]"\ndia_chi=xxxx\nphone: null\ncmnd: ""\nsdt: None\nten: Bob\nx: 1\n'
        self.assertEqual(self.scan("b.log", masked), [])

    def test_table_columns(self):
        csv_text = "id,ho_ten,ghi_chu\n1,Tran Thi B,ok\n2,***,ok\n3\n\n"
        self.assertEqual(self.scan("a.csv", csv_text), [(2, "PII004")])
        tsv = "email\tten\nabc.def\tx\n"
        self.assertEqual(self.scan("a.tsv", tsv), [(2, "PII004")])
        self.assertEqual(self.scan("b.csv", "id,ten\n1,Tran Thi B\n"), [])
        self.assertEqual(self.scan("c.csv", ""), [])

    def test_allow_and_ignore(self):
        line = f"{CCCD} {PHONE}"
        self.assertEqual(self.scan("a.txt", line + "\n"), [(1, "PII001"), (1, "PII002")])
        self.assertEqual(self.scan("b.txt", line + "  # xt-allow: PII001\n"), [(1, "PII002")])
        self.assertEqual(self.scan("c.txt", line + " xt-allow: PII001, PII002\n"), [])
        self.assertEqual(self.scan("d.txt", line + "\n", ignore="PII002, ,PII001"), [])

    def test_message_masks_value(self):
        path = self.base / "m.txt"
        path.write_text(f"{CCCD} {EMAIL} ho_ten=Abc\n", encoding="utf-8")
        for f in kind_pii_vn.check([path], {}):
            self.assertNotIn(CCCD, f.message)
            self.assertNotIn(EMAIL, f.message)
            self.assertNotIn("Abc", f.message)
        self.assertEqual(kind_pii_vn._mask(CCCD), "07" + "*" * 8 + "32")
        self.assertEqual(kind_pii_vn._mask("abcd"), "****")
        self.assertEqual(kind_pii_vn._mask("Hương"), "*****")
        self.assertEqual(kind_pii_vn._mask("abcdefgh"), "*" * 8)
        self.assertEqual(kind_pii_vn._mask("abcdefghi"), "ab" + "*" * 5 + "hi")
        self.assertEqual(kind_pii_vn._mask(""), "")

    def test_opts(self):
        self.assertEqual(kind_pii_vn.OPTS, ("allow_domains", "ignore"))

    def test_unreadable_and_empty(self):
        self.assertEqual(self.scan("bad.txt", b"\xff\xfe\x00"), [(0, "PII000")])
        self.assertEqual(self.scan("big.log", b"a" * (2 * 1024 * 1024 + 1)), [(0, "PII000")])
        self.assertEqual(self.scan("gone.txt", b"\xff", ignore="PII000"), [])
        missing = self.base / "missing.txt"
        self.assertEqual([f.code for f in kind_pii_vn.check([missing], {})], ["PII000"])
        self.assertEqual(self.scan("empty.txt", ""), [])


if __name__ == "__main__":
    unittest.main()
