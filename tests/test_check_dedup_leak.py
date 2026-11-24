"""Loại `dedup-leak`: train/eval trùng mẫu, few-shot lọt vào eval, near-duplicate, ca biên và thời gian tuyến tính."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import xt_checks
from cpu_budget import assert_not_quadratic
from xt_checks import CheckError, kind_dedup_leak

BASE = {"train": "train", "eval": "eval"}


def jsonl(*records: object) -> str:
    return "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n"


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def put(self, name: str, text: str) -> Path:
        path = self.dir / name
        path.write_text(text, encoding="utf-8", newline="")
        return path

    def run_check(self, train: str, evaluation: str, **extra: str) -> list[xt_checks.Finding]:
        files = [self.put("train.jsonl", train), self.put("eval.jsonl", evaluation)]
        return kind_dedup_leak.check(files, {**BASE, **extra})

    def codes(self, found: list[xt_checks.Finding]) -> list[str]:
        return [f.code for f in found]


class InterfaceTest(Base):
    def test_module_interface(self) -> None:
        self.assertEqual(kind_dedup_leak.SUFFIXES, (".jsonl", ".csv"))
        self.assertTrue(kind_dedup_leak.HELP)
        for key in ("train", "eval", "fewshot", "field", "near"):
            self.assertIn(key, kind_dedup_leak.OPTS)
        xt_checks.validate_opts(kind_dedup_leak, dict(BASE))
        with self.assertRaises(CheckError):
            xt_checks.validate_opts(kind_dedup_leak, {"trian": "x"})


class ExactTest(Base):
    def test_clean_sets_have_no_findings(self) -> None:
        self.assertEqual(self.run_check(jsonl({"t": "a"}, {"t": "b"}), jsonl({"t": "c"})), [])

    def test_empty_files_have_no_findings(self) -> None:
        self.assertEqual(self.run_check("", ""), [])
        self.assertEqual(self.run_check("\n\n", "  \n"), [])

    def test_leak_is_normalized_and_key_order_free(self) -> None:
        train = jsonl("Xin  CHÀO\tbạn", {"a": 1, "b": 2})
        evaluation = jsonl({"x": 0}, "  xin chào bạn ", {"b": 2, "a": 1})
        found = self.run_check(train, evaluation)
        self.assertEqual([f.code for f in found], ["DDL001", "DDL001", "DDL001"])
        self.assertEqual(found[0].message, "eval dòng 2 trùng train dòng 1")
        self.assertEqual(found[1].message, "eval dòng 3 trùng train dòng 2")
        self.assertEqual((found[2].line, found[2].message), (0, "tổng 2 mẫu eval trùng train"))

    def test_nfkc_and_unicode_equivalence(self) -> None:
        composed = "Việt Nam"
        decomposed = "Vie" + chr(0x323) + chr(0x302) + "t Nam"
        full_width = "".join(chr(ord(c) + 0xFEE0) if "a" <= c <= "z" else c for c in "abc")
        found = self.run_check(jsonl(composed, "abc"), jsonl(decomposed, full_width))
        self.assertEqual(self.codes(found), ["DDL001", "DDL001", "DDL001"])

    def test_pairs_are_capped_at_twenty_then_total(self) -> None:
        rows = [f"mẫu {i}" for i in range(30)]
        found = self.run_check(jsonl(*rows), jsonl(*rows))
        self.assertEqual(len(found), 21)
        self.assertEqual(found[-1].message, "tổng 30 mẫu eval trùng train")

    def test_crlf_cr_and_lf_line_numbers(self) -> None:
        train = '"a"\r\n"b"\r\n'
        evaluation = '"x"\r\n\r\n"b"\r\n'
        found = self.run_check(train, evaluation)
        self.assertEqual(found[0].message, "eval dòng 3 trùng train dòng 2")
        found = self.run_check('"a"\n"b"', '"x"\n"b"')
        self.assertEqual(found[0].message, "eval dòng 2 trùng train dòng 2")
        lone_cr = self.run_check('"a"\r"b"', '"x"')  # CR đơn không tách dòng: dòng không phải JSON
        self.assertEqual(self.codes(lone_cr), ["DDL000"])

    def test_u2028_and_form_feed_do_not_split_lines(self) -> None:
        text = jsonl("a" + chr(0x2028) + "b\fc", "z")
        found = self.run_check(text, text)
        self.assertEqual(found[0].message, "eval dòng 1 trùng train dòng 1")
        self.assertEqual(found[1].message, "eval dòng 2 trùng train dòng 2")

    def test_duplicates_inside_eval(self) -> None:
        found = self.run_check(jsonl("q"), jsonl("a", "b", "A", "b", "a", "c"))
        self.assertEqual(self.codes(found), ["DDL004"])
        self.assertEqual(found[0].line, 3)
        self.assertEqual(found[0].message, "2 nhóm mẫu trùng trong eval (vd dòng 1 và dòng 3)")

    def test_non_string_values_are_hashed_canonically(self) -> None:
        found = self.run_check("[1,2]\n3\nnull\n", "[1, 2]\n3.0\nnull\n")
        self.assertEqual([f.line for f in found], [1, 3, 0])


class FieldTest(Base):
    def test_field_picks_value_and_ignores_other_keys(self) -> None:
        train = jsonl({"id": 1, "text": "Hello"})
        evaluation = jsonl({"id": 2, "text": "hello"}, {"id": 3, "text": "other"})
        self.assertEqual(self.codes(self.run_check(train, evaluation)), [])
        found = self.run_check(train, evaluation, field="text")
        self.assertEqual(self.codes(found), ["DDL001", "DDL001"])

    def test_missing_field_and_non_object_are_ddl002(self) -> None:
        evaluation = jsonl({"text": "x"}, {"other": 1}, ["list"], "str")
        found = self.run_check(jsonl({"text": "y"}), evaluation, field="text")
        self.assertEqual(self.codes(found), ["DDL002"] * 4)
        self.assertEqual(found[0].message, "thiếu trường 'text'")
        self.assertEqual(found[1].message, "bản ghi không phải object")
        self.assertEqual(found[3].message, "tổng 3 bản ghi thiếu trường")

    def test_non_string_field_value(self) -> None:
        found = self.run_check(jsonl({"v": [1, 2]}), jsonl({"v": [1, 2]}), field="v")
        self.assertEqual(self.codes(found), ["DDL001", "DDL001"])


class FormatErrorsTest(Base):
    def test_invalid_json_line_is_ddl000_and_stops(self) -> None:
        found = self.run_check('{"a":1}\n{oops\n', jsonl("x"))
        self.assertEqual([(f.code, f.line) for f in found], [("DDL000", 2)])

    def test_recursion_error_is_ddl000(self) -> None:
        with unittest.mock.patch.object(kind_dedup_leak.json, "loads", side_effect=RecursionError):
            found = self.run_check(jsonl("a"), jsonl("a"))
        self.assertEqual([f.code for f in found], ["DDL000", "DDL000"])

    def test_type_error_is_ddl000(self) -> None:
        train, evaluation = "[1]", jsonl("a")
        with unittest.mock.patch.object(kind_dedup_leak.json, "dumps", side_effect=TypeError):
            found = self.run_check(train, evaluation)
        self.assertEqual(self.codes(found)[0], "DDL000")

    def test_invalid_utf8_unreadable_and_oversize(self) -> None:
        bad = self.dir / "train.jsonl"
        bad.write_bytes(b'"\xff\xfe"\n')
        files = [bad, self.put("eval.jsonl", jsonl("x"))]
        found = kind_dedup_leak.check(files, dict(BASE))
        self.assertEqual([(f.code, f.line) for f in found], [("DDL000", 0)])
        with unittest.mock.patch.object(xt_checks, "MAX_BYTES", 3):
            found = self.run_check("train", "eval-long")
        self.assertEqual(self.codes(found), ["DDL000", "DDL000"])

    def test_symlink_is_ddl000(self) -> None:
        real = self.put("real.jsonl", jsonl("a"))
        link = self.dir / "train.jsonl"
        link.symlink_to(real)
        found = kind_dedup_leak.check([link, self.put("eval.jsonl", jsonl("a"))], dict(BASE))
        self.assertEqual(self.codes(found), ["DDL000"])

    def test_too_many_records(self) -> None:
        with unittest.mock.patch.object(kind_dedup_leak, "MAX_RECORDS", 2):
            found = self.run_check(jsonl("a", "b", "c"), jsonl("x"))
            self.assertEqual(found[0].code, "DDL000")
            self.assertIn("quá lớn", found[0].message)
            csv_files = [self.put("t.csv", "h\n1\n2\n3\n"), self.put("e.csv", "h\n9\n")]
            found = kind_dedup_leak.check(csv_files, {"train": "t", "eval": "e"})
            self.assertIn("quá lớn", found[0].message)
            ok = self.run_check(jsonl("a", "b"), jsonl("x"))
            self.assertEqual(ok, [])


class OptionsTest(Base):
    def files(self) -> list[Path]:
        return [self.put("train.jsonl", jsonl("a")), self.put("eval.jsonl", jsonl("b")), self.put("x.csv", "h\n")]

    def test_required_and_invalid_options(self) -> None:
        files = self.files()
        bad = [
            {},
            {"train": "train"},
            {"train": "", "eval": "eval"},
            {"train": "train", "eval": "nope"},
            {"train": "train", "eval": "train"},
            {"train": "train", "eval": "eval", "field": ""},
            {"train": "train", "eval": "eval", "fewshot": str(self.dir / "khong-co.txt")},
            {"train": "train", "eval": "eval", "near": "abc"},
            {"train": "train", "eval": "eval", "near": "1.5"},
            {"train": "train", "eval": "eval", "near": "nan"},
            {"train": "train", "eval": "eval", "near": "-0.1"},
        ]
        for opts in bad:
            with self.subTest(opts=opts), self.assertRaises(CheckError):
                kind_dedup_leak.check(files, opts)
        with self.assertRaises(CheckError):
            kind_dedup_leak.check([], dict(BASE))

    def test_duplicate_dataset_name_is_error(self) -> None:
        sub = self.dir / "sub"
        sub.mkdir()
        (sub / "train.jsonl").write_text("1\n", encoding="utf-8")
        with self.assertRaises(CheckError):
            kind_dedup_leak.check([self.dir / "train.jsonl", sub / "train.jsonl"], dict(BASE))

    def test_other_datasets_are_not_read(self) -> None:
        files = self.files()
        (self.dir / "x.csv").write_text('"unterminated\n', encoding="utf-8")
        self.assertEqual(kind_dedup_leak.check(files, dict(BASE)), [])

    def test_near_boundaries_accepted(self) -> None:
        files = self.files()
        for value in ("0", "1", "0.5"):
            kind_dedup_leak.check(files, {**BASE, "near": value})


class CsvTest(Base):
    def run_csv(self, train: str, evaluation: str, **extra: str) -> list[xt_checks.Finding]:
        files = [self.put("train.csv", train), self.put("eval.csv", evaluation)]
        return kind_dedup_leak.check(files, {**BASE, **extra})

    def test_header_is_skipped_and_rows_compared(self) -> None:
        found = self.run_csv("id,text\n1,Hello World\n2,bye\n", "id,text\n9,x\n2,  BYE\n")
        self.assertEqual(self.codes(found), ["DDL001", "DDL001"])
        self.assertEqual(found[0].message, "eval dòng 3 trùng train dòng 3")
        self.assertEqual(self.run_csv("id,text\n1,a\n", "id,text\n2,a\n"), [])

    def test_cells_are_not_merged_across_separator(self) -> None:
        self.assertEqual(self.run_csv("a,b\nx y,z\n", "a,b\nx,y z\n"), [])

    def test_field_selects_column(self) -> None:
        train = "id,text\n1,same\n"
        evaluation = "id,text\n2,SAME\n3\n"
        found = self.run_csv(train, evaluation, field="text")
        self.assertEqual(self.codes(found), ["DDL002", "DDL002", "DDL001", "DDL001"])
        self.assertEqual(found[0].message, "hàng thiếu cột 'text'")

    def test_missing_column_in_header(self) -> None:
        found = self.run_csv("id,text\n1,a\n", "id,text\n1,a\n", field="body")
        self.assertEqual([f.code for f in found], ["DDL002"] * 4)
        self.assertEqual(found[0].message, "thiếu cột 'body' ở tiêu đề")

    def test_quoted_multiline_crlf_and_blank_rows(self) -> None:
        train = 'h\r\n"a\r\nb",c\r\n\r\nz,z\r\n'
        evaluation = 'h\r\n"a\nb",c\r\n'
        found = self.run_csv(train, evaluation)
        self.assertEqual(found[0].message, "eval dòng 2 trùng train dòng 2")

    def test_empty_and_header_only(self) -> None:
        self.assertEqual(self.run_csv("", ""), [])
        self.assertEqual(self.run_csv("h\n", "h"), [])
        self.assertEqual(self.run_csv("\n\n", "h\nx\n"), [])

    def test_csv_error_is_ddl000_with_line(self) -> None:
        found = self.run_csv('h\nok\n"open\n', "h\nx\n")
        self.assertEqual([(f.code, f.line) for f in found], [("DDL000", 3)])
        self.assertIn("CSV sai định dạng", found[0].message)

    def test_oversized_field_is_ddl000_not_exception(self) -> None:
        found = self.run_csv("h\n" + "x" * 200000 + "\n", "h\nx\n")
        self.assertEqual(self.codes(found), ["DDL000"])


class FewShotTest(Base):
    def test_fewshot_hits_eval_and_train(self) -> None:
        fewshot = self.put("prompt.txt", "Ví dụ 1\r\n\r\n  EVAL   sample \nlinh tinh\ntrain item\n")
        found = self.run_check(jsonl("train item", "q"), jsonl("eval sample", "ví dụ 1"), fewshot=str(fewshot))
        hits = [f for f in found if f.code == "DDL003"]
        self.assertEqual(
            [f.message for f in hits],
            [
                "mẫu few-shot dòng 1 trùng mẫu eval",
                "mẫu few-shot dòng 3 trùng mẫu eval",
                "mẫu few-shot dòng 5 trùng mẫu train",
                "tổng 3 mẫu few-shot trùng eval/train",
            ],
        )
        self.assertEqual(hits[0].path, str(fewshot))

    def test_clean_fewshot_and_unreadable(self) -> None:
        fewshot = self.put("p.json", '{"a": 1}\n')
        self.assertEqual(self.run_check(jsonl("t"), jsonl("e"), fewshot=str(fewshot)), [])
        binary = self.dir / "b.txt"
        binary.write_bytes(b"\xff\n")
        found = self.run_check(jsonl("t"), jsonl("e"), fewshot=str(binary))
        self.assertEqual([(f.code, f.line) for f in found], [("DDL000", 0)])


class NearTest(Base):
    BASE_TEXT = " ".join(f"từ{i}" for i in range(60))

    def test_off_by_default(self) -> None:
        changed = self.BASE_TEXT.replace("từ30", "khác")
        self.assertEqual(self.run_check(jsonl(self.BASE_TEXT), jsonl(changed)), [])

    def test_near_duplicate_detected(self) -> None:
        changed = self.BASE_TEXT.replace("từ30", "khác")
        far = " ".join(f"xa{i}" for i in range(60))
        found = self.run_check(jsonl("zz", self.BASE_TEXT), jsonl(far, changed), near="0.5")
        self.assertEqual(self.codes(found), ["DDL005", "DDL005"])
        self.assertTrue(found[0].message.startswith("eval dòng 2 gần trùng train dòng 2 (Jaccard ước lượng "))
        self.assertEqual(found[1].message, "tổng 1 mẫu eval gần trùng train")

    def test_threshold_and_exact_not_double_reported(self) -> None:
        changed = self.BASE_TEXT.replace("từ30", "khác")
        self.assertEqual(self.run_check(jsonl(self.BASE_TEXT), jsonl(changed), near="1"), [])
        found = self.run_check(jsonl(self.BASE_TEXT), jsonl(self.BASE_TEXT), near="0.5")
        self.assertEqual(self.codes(found), ["DDL001", "DDL001"])

    def test_short_samples_and_duplicates_in_train(self) -> None:
        found = self.run_check(jsonl("a b", "a b", "c"), jsonl("a b c", "a b"), near="0.9")
        self.assertEqual(self.codes(found), ["DDL001", "DDL001"])

    def test_picks_best_candidate(self) -> None:
        second = self.BASE_TEXT.replace("từ30", "khác")
        third = self.BASE_TEXT.replace("từ30", "khác").replace("từ10", "nữa")
        found = self.run_check(jsonl(third, second), jsonl(self.BASE_TEXT), near="0.5")
        self.assertEqual(found[0].code, "DDL005")
        self.assertIn("train dòng 2", found[0].message)

    def test_bucket_is_capped(self) -> None:
        rows = [self.BASE_TEXT.replace("từ30", f"khác{i}") for i in range(5)]
        with unittest.mock.patch.object(kind_dedup_leak, "MAX_BUCKET", 2):
            found = self.run_check(jsonl(*rows), jsonl(self.BASE_TEXT), near="0.5")
        self.assertEqual(self.codes(found), ["DDL005", "DDL005"])

    def test_pairs_capped_with_total(self) -> None:
        rows = [" ".join(f"w{j}x{i}" for j in range(30)) for i in range(25)]
        changed = [r.replace("w5x", "q5x") for r in rows]
        found = self.run_check(jsonl(*rows), jsonl(*changed), near="0.5")
        self.assertEqual(len(found), 21)
        self.assertEqual(found[-1].message, "tổng 25 mẫu eval gần trùng train")


class LinearTimeTest(Base):
    def test_exact_check_is_linear_in_records(self) -> None:
        def work(n: int) -> None:
            train = "".join(f'"t{i}"\n' for i in range(n))
            evaluation = "".join(f'"{"e" if i % 2 else "t"}{i}"\n' for i in range(n))
            self.put("train.jsonl", train)
            self.put("eval.jsonl", evaluation)
            files = [self.dir / "train.jsonl", self.dir / "eval.jsonl"]
            found = kind_dedup_leak.check(files, dict(BASE))
            self.assertEqual(found[-1].message, f"tổng {(n + 1) // 2} mẫu eval trùng train")

        with unittest.mock.patch.object(xt_checks, "MAX_BYTES", 1 << 30):
            assert_not_quadratic(self, work, 50000)

    def test_long_line_is_linear(self) -> None:
        def work(n: int) -> None:
            long = json.dumps({"t": "ab  CD " * (n // 7)})
            self.put("train.jsonl", long + "\n")
            self.put("eval.jsonl", long + "\n")
            files = [self.dir / "train.jsonl", self.dir / "eval.jsonl"]
            found = kind_dedup_leak.check(files, {**BASE, "field": "t"})
            self.assertEqual(self.codes(found), ["DDL001", "DDL001"])

        with unittest.mock.patch.object(xt_checks, "MAX_BYTES", 1 << 30):
            assert_not_quadratic(self, work, 100000)

    def test_near_check_is_linear(self) -> None:
        def work(n: int) -> None:
            rows = [" ".join(f"w{i}_{j}" for j in range(8)) for i in range(n)]
            self.put("train.jsonl", jsonl(*rows))
            self.put("eval.jsonl", jsonl(*(r.replace("_0", "_9") for r in rows)))
            files = [self.dir / "train.jsonl", self.dir / "eval.jsonl"]
            kind_dedup_leak.check(files, {**BASE, "near": "0.9"})

        with unittest.mock.patch.object(xt_checks, "MAX_BYTES", 1 << 30):
            assert_not_quadratic(self, work, 1500)

    def test_identical_near_samples_do_not_blow_up(self) -> None:
        def work(n: int) -> None:
            rows = [" ".join(f"w{j}" for j in range(20)) + f" tail{i}" for i in range(n)]
            self.put("train.jsonl", jsonl(*rows))
            self.put("eval.jsonl", jsonl(*rows[::-1]))
            files = [self.dir / "train.jsonl", self.dir / "eval.jsonl"]
            kind_dedup_leak.check(files, {**BASE, "near": "0.9"})

        with unittest.mock.patch.object(xt_checks, "MAX_BYTES", 1 << 30):
            assert_not_quadratic(self, work, 600)


if __name__ == "__main__":
    unittest.main()
