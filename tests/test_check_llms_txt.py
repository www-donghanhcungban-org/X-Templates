"""Loại `llms-txt` (XC-DOCAI-010): mã LLM000-LLM009, `--opt root/md` và thời gian tuyến tính."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
import unittest.mock
from collections.abc import Callable
from contextlib import chdir
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import xt_checks
from cpu_budget import assert_not_quadratic
from xt_checks import kind_llms_txt

SITE = "https" + ":" + "//" + "example.org"
LSEP = chr(0x2028)  # bằng mã: nguồn không chứa ký tự ẩn thật
# Tăng độ sâu 4 lần: tổng độ dài các tiền tố của bản đột biến tăng gần 16 lần.
MUTANT_RATIO = 6
GOOD = f"# Dự án\n\n> Tóm tắt.\n\n## Docs\n\n- [Bắt đầu]({SITE}/start): hướng dẫn\n- [API](/api.md)\n\n## Optional\n\n- [Thêm](./more.md): phụ\n"


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def put(self, text: str, name: str = "llms.txt") -> Path:
        path = self.base / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        return path

    def run_text(self, text: str, **opts: str) -> list[xt_checks.Finding]:
        return kind_llms_txt.check([self.put(text)], opts)

    def codes(self, text: str, **opts: str) -> list[str]:
        return [f.code for f in self.run_text(text, **opts)]


class InterfaceTest(Base):
    def test_interface(self) -> None:
        self.assertEqual(kind_llms_txt.SUFFIXES, (".txt",))
        self.assertIsInstance(kind_llms_txt.HELP, str)
        xt_checks.validate_opts(kind_llms_txt, {"root": "x", "md": "1", "ignore": "LLM006"})
        with self.assertRaisesRegex(xt_checks.CheckError, "--opt lạ"):
            xt_checks.validate_opts(kind_llms_txt, {"roots": "x"})

    def test_good_file_is_clean(self) -> None:
        self.assertEqual(self.codes(GOOD), [])
        self.assertEqual(self.codes(GOOD.replace("\n", "\r\n")), [])
        self.assertEqual(self.codes(chr(0xFEFF) + GOOD), [])
        self.assertIn("LLM002", self.codes(GOOD.replace("\n", "\r")))  # CR đơn không tách dòng

    def test_no_files(self) -> None:
        self.assertEqual(kind_llms_txt.check([], {}), [])

    def test_ignore(self) -> None:
        text = GOOD + "- [Lại](/api.md)\n"
        self.assertEqual(self.codes(text), ["LLM006"])
        self.assertEqual(self.codes(text, ignore="LLM006"), [])

    def test_named_files_are_always_checked(self) -> None:
        other = self.put("rác", "notes.txt")
        good = self.put(GOOD)
        found = kind_llms_txt.check([other, good], {})  # nêu đích danh: kiểm cả tệp tên khác
        self.assertEqual(
            [(Path(f.path).name, f.code) for f in found], [("notes.txt", "LLM001"), ("notes.txt", "LLM002")]
        )
        full = self.put("rác", "llms-full.txt")
        self.assertEqual([f.code for f in kind_llms_txt.check([good, full], {})], ["LLM001", "LLM002"])

    def test_directory_scan_only_takes_llms_names(self) -> None:
        self.assertEqual(kind_llms_txt.NAMES, frozenset({"llms.txt", "llms-full.txt"}))
        self.put("rác", "notes.txt")
        self.put("rác", "sub/requirements.txt")
        self.assertEqual(xt_checks.run("llms-txt", [str(self.base)], {}), [])  # không có llms.txt: không kiểm .txt khác
        self.put("rác", "sub/llms-full.txt")
        found = xt_checks.run("llms-txt", [str(self.base)], {})
        self.assertEqual({Path(f.path).name for f in found}, {"llms-full.txt"})


class FileErrorTest(Base):
    def test_unreadable_empty_and_non_utf8(self) -> None:
        for text in ("", " \n\t\n"):
            found = self.run_text(text)
            self.assertEqual([(f.code, f.line) for f in found], [("LLM000", 0)])
        bad = self.base / "llms.txt"
        bad.write_bytes(b"# x\n\xff\xfe\n")
        self.assertEqual([f.code for f in kind_llms_txt.check([bad], {})], ["LLM000"])
        self.assertEqual([f.code for f in kind_llms_txt.check([self.base / "none.txt"], {})], ["LLM000"])


class StructureTest(Base):
    def test_llm001_heading(self) -> None:
        self.assertEqual(self.codes("Dự án\n> t\n"), ["LLM001"])
        self.assertEqual(self.codes("## Dự án\n> t\n"), ["LLM001"])
        self.assertEqual(self.codes("#Dự án\n> t\n"), ["LLM001"])
        self.assertEqual(self.codes("\n# Dự án\n> t\n"), ["LLM001", "LLM001", "LLM002"])
        found = self.run_text("# A\n> t\n\n## B\n\n- [x](/x)\n\n# C\n")
        self.assertEqual([(f.code, f.line) for f in found], [("LLM001", 8)])

    def test_llm002_summary(self) -> None:
        self.assertEqual(self.codes("# A\n"), ["LLM002"])
        self.assertEqual(self.codes("# A\n\n\n"), ["LLM002"])
        self.assertEqual(self.codes("# A\nvăn xuôi\n"), ["LLM002"])
        self.assertEqual(self.codes("# A\n>\n"), ["LLM002"])
        self.assertEqual(self.codes("# A\n\n\n> ok\n"), [])
        found = self.run_text("# A\n\nvăn\n> muộn\n")
        self.assertEqual([(f.code, f.line) for f in found], [("LLM002", 3)])

    def test_llm003_and_llm007_sections(self) -> None:
        head = "# A\n> t\n"
        found = self.run_text(head + "## B\n\nchỉ văn xuôi\n")
        self.assertEqual([(f.code, f.line) for f in found], [("LLM003", 3)])
        found = self.run_text(head + "## B\n\n## C\n\n- [x](/x)\n")
        self.assertEqual([(f.code, f.line) for f in found], [("LLM007", 3)])
        found = self.run_text(head + "## B\n")
        self.assertEqual([(f.code, f.line) for f in found], [("LLM007", 3)])
        found = self.run_text(head + "## B\n- [x](/x)\n### Con\n- [y](/y)\n")
        self.assertEqual([(f.code, f.line) for f in found], [("LLM007", 5)])
        found = self.run_text(head + "## B\n### Con\n")
        self.assertEqual([f.code for f in found], ["LLM007", "LLM007"])

    def test_llm005_optional_and_duplicates(self) -> None:
        item = "- [x](/x)\n"
        head = "# A\n> t\n"
        found = self.run_text(head + f"## Optional\n{item}## B\n- [y](/y)\n")
        self.assertEqual([(f.code, f.line) for f in found], [("LLM005", 3)])
        found = self.run_text(head + f"## B\n{item}## b\n- [y](/y)\n")
        self.assertEqual([(f.code, f.line) for f in found], [("LLM005", 5)])
        self.assertEqual(self.codes(head + f"## B\n{item}## Optional\n- [y](/y)\n"), [])

    def test_fenced_code_is_ignored(self) -> None:
        text = "# A\n> t\n## B\n- [x](/x)\n```\n# code\n## H2\n- hỏng\n```\n"
        self.assertEqual(self.codes(text), [])


class LinkTest(Base):
    def codes_for(self, line: str) -> list[str]:
        return self.codes(f"# A\n> t\n## B\n{line}\n- [ok](/ok)\n")

    def test_valid_forms(self) -> None:
        for line in (
            f"- [a]({SITE}/x)",
            f"- [a]({SITE}/x): ghi chú",
            "- [a](/x) : ghi chú",
            "- [a](./x#frag): n",
            "- [a](http" + "://h.example/x)",
            "- [a](/x)   ",
        ):
            with self.subTest(line=line):
                self.assertEqual(self.codes_for(line), [])

    def test_invalid_forms(self) -> None:
        for line in (
            "- chỉ chữ",
            "* [a](/x)",
            "- [](/x)",
            "- [ ](/x)",
            "- [a](/x",
            "- [a] (/x)",
            "- [a](/x):",
            "- [a](/x):   ",
            "- [a](/x) ghi chú không dấu hai chấm",
            "- [a]()",
            "- [a](x.md)",
            "- [a](../x.md)",
            "- [a](//host/x)",
            "- [a](mailto:me@example.org)",
            "- [a](ftp" + "://h.example/x)",
            "- [a](/x y)",
            "- [a](https" + ":" + "//)",
            "- [a](http" + "://[::1)",
            "- [a](x:y)",
            "- [a](/docs\\a.md)",
            "- [a](." + "\\" + "x.md)",
            "- [a](https" + ":" + "//@/x)",
            "- [a](https" + ":" + "//:80/x)",
            "- [a](https" + ":" + "//user@/x)",
        ):
            with self.subTest(line=line):
                self.assertEqual(self.codes_for(line), ["LLM004"], line)

    def test_note_with_bad_destination_reports_both(self) -> None:
        self.assertEqual(self.codes_for("- [a](x.md):"), ["LLM004", "LLM004"])

    def test_invalid_link_still_counts_for_llm003(self) -> None:
        self.assertEqual(self.codes("# A\n> t\n## B\n- [a](x.md)\n"), ["LLM004"])
        self.assertEqual(self.codes("# A\n> t\n## B\n- chữ\n"), ["LLM003", "LLM004"])

    def test_llm006_duplicates(self) -> None:
        found = self.run_text("# A\n> t\n## B\n- [a](/x)\n## C\n- [b](/x)\n- [c](/y)\n- [d](/x)\n")
        self.assertEqual([(f.code, f.line) for f in found], [("LLM006", 6), ("LLM006", 8)])
        self.assertIn("dòng 4", found[0].message)

    def test_long_destination_is_truncated_in_message(self) -> None:
        found = self.run_text("# A\n> t\n## B\n- [a](x" + "y" * 500 + ")\n")
        self.assertLess(len(found[0].message), 200)
        self.assertIn(kind_llms_txt.ELLIPSIS, found[0].message)


class RootTest(Base):
    def setUp(self) -> None:
        super().setUp()
        self.site = self.base / "site"
        (self.site / "docs").mkdir(parents=True)
        (self.site / "docs" / "a.md").write_text("x", encoding="utf-8")
        (self.site / "docs" / "b.html").write_text("x", encoding="utf-8")
        (self.site / "docs" / "b.html.md").write_text("x", encoding="utf-8")
        (self.site / "docs" / "c.html").write_text("x", encoding="utf-8")
        (self.site / "docs" / "d.html").write_text("x", encoding="utf-8")
        (self.site / "docs" / "d.md").write_text("x", encoding="utf-8")
        (self.site / "docs" / "Tài liệu.md").write_text("x", encoding="utf-8")
        (self.base / "secret.md").write_text("x", encoding="utf-8")

    def run_links(self, *dests: str, **opts: str) -> list[tuple[str, int]]:
        lines = "".join(f"- [l{i}]({d})\n" for i, d in enumerate(dests))
        found = self.run_text(f"# A\n> t\n## B\n{lines}", root=str(self.site), **opts)
        return [(f.code, f.line) for f in found]

    def test_existing_and_missing(self) -> None:
        self.assertEqual(
            self.run_links("/docs/a.md", "./docs/a.md", "/docs/a.md#x", "/docs/T%C3%A0i%20li%E1%BB%87u.md"),
            [],
        )
        self.assertEqual(self.run_links("/docs/none.md"), [("LLM008", 4)])
        self.assertEqual(self.run_links("/docs/" + "Tài liệu.md"), [("LLM004", 4)])  # khoảng trắng thô: phải mã hoá %20

    def test_web_and_directory_links_are_not_probed(self) -> None:
        self.assertEqual(self.run_links(f"{SITE}/none.md", "/", "/docs/", "./", "/#frag", "/."), [])

    def test_escape_from_root(self) -> None:
        self.assertEqual(self.run_links("/../secret.md"), [("LLM008", 4)])
        self.assertEqual(self.run_links("./docs/../../secret.md"), [("LLM008", 4)])
        self.assertEqual(self.run_links("/docs/%2e%2e/%2e%2e/secret.md"), [("LLM008", 4)])
        self.assertEqual(self.run_links("/docs/../docs/a.md"), [])
        self.assertEqual(self.run_links("/.."), [])  # thư mục/không phải tệp: không dò

    def test_symlink_is_not_followed(self) -> None:
        os.symlink(self.base / "secret.md", self.site / "docs" / "link.md")
        os.symlink(self.base, self.site / "out")
        self.assertEqual(self.run_links("/docs/link.md"), [("LLM008", 4)])
        self.assertEqual(self.run_links("/out/secret.md"), [("LLM008", 4)])

    def test_nul_byte_in_destination(self) -> None:
        self.assertEqual(self.run_links("/docs/a%00.md"), [("LLM008", 4)])
        self.assertEqual(self.run_links("/docs%00/a.md"), [("LLM008", 4)])

    def test_walk_stops_at_files_directories_and_missing_parts(self) -> None:
        self.assertEqual(
            self.run_links("/docs/a.md/x.md", "/docs", "/none/a.md"), [("LLM008", 4), ("LLM008", 5), ("LLM008", 6)]
        )
        os.mkfifo(self.site / "docs" / "pipe.md")
        self.assertEqual(self.run_links("/docs/pipe.md"), [("LLM008", 4)])
        self.assertFalse(kind_llms_txt._plain_file(self.base / "none", "docs/a.md"))  # root biến mất giữa chừng
        self.assertTrue(kind_llms_txt._plain_file(self.site, "docs/a.md"))

    def test_destination_length_cap(self) -> None:
        cap = kind_llms_txt.MAX_DEST
        ok = "/docs/a.md#" + "x" * (cap - len("/docs/a.md#"))
        self.assertEqual(self.run_links(ok), [])
        found = self.run_text(f"# A\n> t\n## B\n- [l]({ok}x)\n", root=str(self.site))
        self.assertEqual([(f.code, f.line) for f in found], [("LLM008", 4)])
        self.assertIn("quá dài", found[0].message)
        self.assertEqual(self.codes(f"# A\n> t\n## B\n- [l]({ok}x)\n"), [])  # không có root: không dò

    def test_md_option(self) -> None:
        links = ("/docs/b.html", "/docs/c.html", "/docs/d.html", "/docs/a.md", "/docs/none.html")
        self.assertEqual(self.run_links(*links), [("LLM008", 8)])
        self.assertEqual(self.run_links(*links, md="1"), [("LLM009", 5), ("LLM008", 8)])
        self.assertEqual(self.run_links("/docs/B.HTML", md="1"), [("LLM008", 4)])

    def test_bad_options(self) -> None:
        with self.assertRaisesRegex(xt_checks.CheckError, "root"):
            kind_llms_txt.check([], {"root": str(self.base / "none")})
        with self.assertRaisesRegex(xt_checks.CheckError, "root"):
            kind_llms_txt.check([], {"root": ""})
        with self.assertRaisesRegex(xt_checks.CheckError, "root"):
            kind_llms_txt.check([], {"root": str(self.site / "docs" / "a.md")})
        os.symlink(self.site, self.base / "linkroot")
        with self.assertRaisesRegex(xt_checks.CheckError, "root"):
            kind_llms_txt.check([], {"root": str(self.base / "linkroot")})
        with self.assertRaisesRegex(xt_checks.CheckError, "md"):
            kind_llms_txt.check([], {"md": "yes", "root": str(self.site)})
        with self.assertRaisesRegex(xt_checks.CheckError, "cần --opt root"):
            kind_llms_txt.check([], {"md": "1"})
        self.assertEqual(kind_llms_txt.check([], {"md": "0"}), [])


class LinearTimeTest(Base):
    @staticmethod
    def links(n: int) -> str:
        return "# A\n> t\n## B\n" + "".join(f"- [l{i}](/p/{i}.md): n\n" for i in range(n))

    def test_many_links_are_linear(self) -> None:
        text = self.links(200000)
        self.assertEqual(len(kind_llms_txt._Scan("t", None, False).run(text.split("\n"))), 0)
        assert_not_quadratic(
            self, lambda n: kind_llms_txt._Scan("t", None, False).run(self.links(n).split("\n")), 50000
        )

    def test_long_lines_are_linear(self) -> None:
        shapes: dict[str, Callable[[int], str]] = {
            "longdest": lambda n: "- [a](" + SITE + "/" + "a:/@" * (n // 4) + ")",
            "brackets": lambda n: "- " + "[(" * (n // 2),
            "open": lambda n: "- [" + "a" * n,
            "unclosed_dest": lambda n: "- [a](" + "(" * n,
            "closers": lambda n: "- [a](/x)" + "]()" * (n // 3),
            "spaces": lambda n: "-" + " " * n + "x",
            "hashes": lambda n: "#" * n,
            "heading_spaces": lambda n: "## " + " " * n + "x",
        }
        for name, build in shapes.items():
            with self.subTest(shape=name):

                def work(n: int, b: Callable[[int], str] = build) -> None:
                    text = "# A\n> t\n## B\n" + b(n) + "\n"
                    kind_llms_txt._Scan("t", None, False).run(text.split("\n"))

                work(400000)
                assert_not_quadratic(self, work, 100000)

    def test_many_duplicate_links_are_linear(self) -> None:
        def work(n: int) -> None:
            lines = "".join("- [a](/same)\n" for _ in range(n))
            kind_llms_txt._Scan("t", None, False).run(("# A\n> t\n## B\n" + lines).split("\n"))

        work(100000)
        assert_not_quadratic(self, work, 25000)

    def test_many_h2_sections_are_linear(self) -> None:
        def work(n: int) -> None:
            body = "".join(f"## S{i}\n- [a](/x{i})\n" for i in range(n))
            kind_llms_txt._Scan("t", None, False).run(("# A\n> t\n" + body).split("\n"))

        work(100000)
        assert_not_quadratic(self, work, 25000)

    def test_check_end_to_end_with_long_line(self) -> None:
        path = self.put("# A\n> t\n## B\n- [a](" + "[(" * 200000 + ")\n")
        self.assertEqual([f.code for f in kind_llms_txt.check([path], {})], ["LLM004"])


def deep_link(n: int) -> str:
    return "# A\n> t\n## B\n- [l](/" + "a/" * n + "x.md)\n"


def old_plain_file(root: Path, rel: str) -> bool:
    """Bản cũ (rà 🔴1): nối chuỗi và `islink` cho từng thành phần — bậc hai theo số thành phần."""
    current = str(root)
    for part in rel.split("/"):
        current = os.path.join(current, part)
        if os.path.islink(current):
            return False
    return os.path.isfile(current)


class RootLinearTimeTest(Base):
    """Đích tương đối hàng trăm nghìn thành phần khi có `--opt root=` (rà 🔴1: tệp 2 MB mất 2 phút 22 giây)."""

    def setUp(self) -> None:
        super().setUp()
        self.site = self.base / "site"
        (self.site / "a" / "a").mkdir(parents=True)

    def run_deep(self, n: int) -> list[str]:
        return [f.code for f in kind_llms_txt.check([self.put(deep_link(n))], {"root": str(self.site)})]

    def test_many_components_with_root_are_linear(self) -> None:
        self.assertEqual(self.run_deep(400000), ["LLM008"])
        assert_not_quadratic(self, self.run_deep, 100000)

    def test_walk_without_cap_is_linear(self) -> None:
        with unittest.mock.patch.object(kind_llms_txt, "MAX_DEST", 10**9):
            self.assertEqual(self.run_deep(400000), ["LLM008"])
            assert_not_quadratic(self, self.run_deep, 100000)

    def walk_path_bytes(self, walk: Callable[[Path, str], bool], n: int) -> int:
        sizes: list[int] = []

        def measured(root: Path, rel: str) -> bool:
            with (
                unittest.mock.patch.object(os, "open", wraps=os.open) as opened,
                unittest.mock.patch.object(os, "stat", wraps=os.stat) as stated,
                unittest.mock.patch.object(os, "lstat", wraps=os.lstat) as lstated,
            ):
                result = walk(root, rel)
            self.assertFalse(result)
            for probe in (opened, stated, lstated):
                sizes.extend(len(os.fsencode(call.args[0])) for call in probe.call_args_list)
            return result

        # Root tương đối giữ số byte mỗi tiền tố độc lập với độ dài đường dẫn của runner.
        with chdir(self.base), unittest.mock.patch.object(kind_llms_txt, "_plain_file", measured):
            self.assertEqual(self.codes(deep_link(n), root="site"), ["LLM008"])
        self.assertTrue(sizes, "chưa quan sát được lời gọi hệ tệp nào trong walker")
        total = sum(sizes)
        self.assertGreater(total, 0)
        return total

    def test_quadratic_walk_mutant_is_detected(self) -> None:
        for walk, linear in ((kind_llms_txt._plain_file, True), (old_plain_file, False)):
            with self.subTest(walk=walk.__name__):
                small = self.walk_path_bytes(walk, 128)
                big = self.walk_path_bytes(walk, 512)
                self.assertEqual(big < MUTANT_RATIO * small, linear, f"{small} → {big} byte đường dẫn")


class RobustnessTest(Base):
    def test_urlsplit_failure_is_reported_not_raised(self) -> None:
        with unittest.mock.patch.object(kind_llms_txt, "urlsplit", side_effect=ValueError("x")):
            self.assertFalse(kind_llms_txt._valid_dest("/x"))

    def test_odd_text_never_raises(self) -> None:
        for text in ("\x00\x00", "#", "# ", "-", "- [", ">", "\r\r\r", "```", LSEP + "# A\n> t\n", "\x0c# A\n"):
            with self.subTest(text=text):
                self.assertIsInstance(self.run_text(text + "\n"), list)

    def test_unicode_line_separators_do_not_split_lines(self) -> None:
        found = self.run_text("# A\n> t\n## B\n- [a](/x)" + LSEP + "- [b](/y)\n")
        self.assertEqual([(f.code, f.line) for f in found], [("LLM004", 4)])

    def test_results_are_sorted(self) -> None:
        a = self.put("x", "llms.txt")
        sub = self.base / "sub"
        sub.mkdir()
        b = sub / "llms.txt"
        b.write_text("y", encoding="utf-8")
        found = kind_llms_txt.check([b, a], {})
        self.assertEqual([f.path for f in found], sorted(f.path for f in found))


if __name__ == "__main__":
    unittest.main()
