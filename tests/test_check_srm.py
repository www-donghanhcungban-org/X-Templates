"""Loại `srm`: p-value chi-bình-phương, SRM001–SRM006, ca biên và thời gian tuyến tính."""

from __future__ import annotations

import csv
import json
import math
import random
import sys
import tempfile
import unittest
import unittest.mock
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import xt_checks
from cpu_budget import assert_not_quadratic
from xt_checks import CheckError, kind_srm

BOM = chr(0xFEFF)
# Tăng số đơn vị 4 lần: số phép băm tăng 4 lần, số phép so sánh của bản đột biến tăng gần 16 lần.
MUTANT_RATIO = 6


def csv_text(rows: list[tuple[str, str]], header: str = "unit_id,variant") -> str:
    return header + "\n" + "".join(f"{u},{v}\n" for u, v in rows)


def balanced(n: int, names: tuple[str, ...] = ("a", "b")) -> list[tuple[str, str]]:
    return [(f"u{i}", names[i % len(names)]) for i in range(n)]


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def put(self, name: str, text: str) -> Path:
        path = self.dir / name
        path.write_text(text, encoding="utf-8", newline="")
        return path

    def run_check(self, name: str, text: str, **opts: str) -> list[xt_checks.Finding]:
        return kind_srm.check([self.put(name, text)], dict(opts))

    def codes(self, found: list[xt_checks.Finding]) -> list[str]:
        return [f.code for f in found]


class PvalueTest(unittest.TestCase):
    def test_known_critical_values(self) -> None:
        self.assertAlmostEqual(kind_srm.chi2_pvalue(3.841, 1), 0.05, delta=1e-4)
        self.assertAlmostEqual(kind_srm.chi2_pvalue(10.828, 1), 0.001, delta=1e-5)
        self.assertAlmostEqual(kind_srm.chi2_pvalue(5.991, 2), 0.05, delta=1e-4)
        self.assertAlmostEqual(kind_srm.chi2_pvalue(7.815, 3), 0.05, delta=1e-4)
        self.assertAlmostEqual(kind_srm.chi2_pvalue(18.307, 10), 0.05, delta=1e-4)

    def test_df2_closed_form(self) -> None:
        for x in (0.1, 1.0, 4.0, 9.0, 30.0):
            self.assertAlmostEqual(kind_srm.chi2_pvalue(x, 2), math.exp(-x / 2), places=12)

    def test_df1_matches_erfc(self) -> None:
        for x in (0.05, 0.5, 2.0, 8.0, 40.0):
            self.assertAlmostEqual(kind_srm.chi2_pvalue(x, 1), math.erfc(math.sqrt(x / 2)), places=12)

    def test_zero_and_degenerate(self) -> None:
        self.assertEqual(kind_srm.chi2_pvalue(0.0, 1), 1.0)
        self.assertEqual(kind_srm.chi2_pvalue(-1.0, 3), 1.0)
        self.assertEqual(kind_srm.chi2_pvalue(float("nan"), 3), 1.0)
        self.assertEqual(kind_srm.chi2_pvalue(5.0, 0), 1.0)
        self.assertEqual(kind_srm.chi2_pvalue(math.inf, 3), 0.0)
        self.assertEqual(kind_srm.chi2_pvalue(1e6, 1), 0.0)

    def test_subnormal_chi2_does_not_raise(self) -> None:
        self.assertEqual(kind_srm.chi2_pvalue(5e-324, 1), 1.0)  # chi2/2 làm tròn về 0: log(0) không được văng
        self.assertEqual(kind_srm.chi2_pvalue(5e-324, 4), 1.0)

    def test_large_df(self) -> None:
        # trung vị chi2 với df lớn xấp xỉ df - 2/3; p quanh 0.5
        self.assertAlmostEqual(kind_srm.chi2_pvalue(1000 - 2 / 3, 1000), 0.5, delta=0.01)
        self.assertAlmostEqual(kind_srm.chi2_pvalue(1074.679, 1000), 0.05, delta=1e-3)
        self.assertAlmostEqual(kind_srm.chi2_pvalue(100000.0, 100000), 0.5, delta=0.01)

    def test_monotone_decreasing_in_chi2_and_symmetric_range(self) -> None:
        for df in (1, 2, 5, 40):
            values = [kind_srm.chi2_pvalue(x / 2, df) for x in range(0, 400)]
            self.assertEqual(values, sorted(values, reverse=True))
            self.assertTrue(all(0.0 <= v <= 1.0 for v in values))

    def test_iteration_cap_still_returns_probability(self) -> None:
        with unittest.mock.patch.object(kind_srm, "MAX_ITER", 2):
            self.assertTrue(0.0 <= kind_srm.chi2_pvalue(3.0, 4) <= 1.0)
            self.assertTrue(0.0 <= kind_srm.chi2_pvalue(30.0, 4) <= 1.0)

    def test_tiny_guards_in_fraction(self) -> None:
        with unittest.mock.patch.object(kind_srm, "TINY", 1e300):
            self.assertTrue(0.0 <= kind_srm.chi2_pvalue(30.0, 4) <= 1.0)


class InterfaceTest(Base):
    def test_module_interface(self) -> None:
        self.assertEqual(kind_srm.SUFFIXES, (".csv", ".json", ".jsonl"))
        self.assertTrue(kind_srm.HELP)
        self.assertIs(kind_srm.SNIFF, kind_srm.sniff)
        self.assertTrue(kind_srm.sniff('[{"variant": "a"}]', {}))
        self.assertTrue(kind_srm.sniff("unit_id,variant", {}))
        self.assertFalse(kind_srm.sniff("unit_id,x", {}))
        self.assertFalse(kind_srm.sniff('{"bomFormat": 1}', {}))
        xt_checks.validate_opts(kind_srm, {"variant": "v", "alpha": "0.01"})
        with self.assertRaises(CheckError):
            xt_checks.validate_opts(kind_srm, {"alfa": "1"})

    def test_registry_scan_with_sniff(self) -> None:
        self.put("ok.csv", csv_text(balanced(40)))
        self.put("other.json", '{"bomFormat": "CycloneDX"}')
        files = xt_checks.collect([str(self.dir)], kind_srm.SUFFIXES, xt_checks.sniff_for(kind_srm, {}))
        self.assertEqual([p.name for p in files], ["ok.csv"])


class SniffTest(Base):
    """Quét thư mục: SNIFF dùng tên trường từ `--opt variant=` và cấu trúc bản ghi, không chữ cố định (rà 🔴3)."""

    def scan(self, **opts: str) -> list[tuple[str, str]]:
        return [(Path(f.path).name, f.code) for f in xt_checks.run("srm", [str(self.dir)], dict(opts))]

    def test_custom_variant_field_is_scanned(self) -> None:
        rows = "uid,arm\n" + "".join(f"u{i},{'a' if i < 600 else 'b'}\n" for i in range(1000))
        self.put("exp.csv", rows)
        self.assertEqual(self.scan(variant="arm", unit="uid"), [("exp.csv", "SRM001")])
        self.assertEqual(self.scan(), [])  # không có trường `variant`: không phải tệp gán biến thể

    def test_ui_json_with_variant_key_is_not_scanned(self) -> None:
        self.put("button.json", '{"variant": "primary", "size": "lg"}')
        self.put("theme.json", '{\n  "variant": "dark"\n}\n')
        self.put("list.json", '[{"name": "x"}, "variant"]')
        self.put("ok.json", json.dumps({"records": [{"variant": "ab"[i % 2]} for i in range(40)]}))
        self.assertEqual(self.scan(), [])
        self.assertEqual(len(xt_checks.collect([str(self.dir)], kind_srm.SUFFIXES, None)), 4)

    def test_sniff_shapes(self) -> None:
        opts = {"variant": "arm"}
        record = '{"arm": "a"}'
        for text, expected in (
            ("", False),
            (" \n\n", False),
            ("uid,arm\n", True),
            (BOM + "arm,uid\r\n", True),
            ("\n\nuid,arm\n", True),
            ("uid,armed\n", False),
            ("[" + record + "]", True),
            ('{"records": [' + record + "]}", True),
            ('{"records": [{"x": 1}]}', False),
            ('{"arm": "primary"}', False),
            ("[1, 2]", False),
            ('{"x": 1}\n' + record + "\n", True),
            ('{"x": 1}\n{"y": 2}\n', False),
            ('{"x": 1}\n{"arm": oops\n', True),  # hỏng mà mang tên trường: giữ để `check` báo SRM000
            ('{"x": 1}\n{oops\n', False),
            ('{"x": 1}\n\n3\n', False),
            ("arm," + "x" * 200000 + "\n", True),  # vượt field_size_limit của csv: vẫn nhận theo chuỗi
        ):
            with self.subTest(text=text[:40]):
                self.assertIs(kind_srm.sniff(text, opts), expected)

    def test_sniff_deep_json_does_not_raise(self) -> None:
        with unittest.mock.patch.object(json, "loads", side_effect=RecursionError):
            self.assertTrue(kind_srm.sniff('[{"variant": 1}]', {}))
            self.assertFalse(kind_srm.sniff("[[[", {}))

    def test_sniff_rejects_empty_field_option(self) -> None:
        with self.assertRaises(CheckError):
            kind_srm.sniff("variant\n", {"variant": ""})


class SrmTest(Base):
    def test_balanced_is_clean(self) -> None:
        self.assertEqual(self.run_check("a.csv", csv_text(balanced(1000))), [])

    def test_mismatch_reports_counts_and_p(self) -> None:
        rows = [(f"u{i}", "a" if i < 600 else "b") for i in range(1000)]
        found = self.run_check("a.csv", csv_text(rows))
        self.assertEqual(self.codes(found), ["SRM001"])
        self.assertIn("'a'=600", found[0].message)
        self.assertIn("'b'=400", found[0].message)
        self.assertIn("p=", found[0].message)
        self.assertEqual(found[0].line, 0)

    def test_alpha_option(self) -> None:
        rows = [(f"u{i}", "a" if i < 520 else "b") for i in range(1000)]  # chi2 = 1.6, p ~ 0.2
        self.assertEqual(self.run_check("a.csv", csv_text(rows)), [])
        self.assertEqual(self.codes(self.run_check("a.csv", csv_text(rows), alpha="0.5")), ["SRM001"])

    def test_default_alpha_boundary(self) -> None:
        rows = [(f"u{i}", "a" if i < 550 else "b") for i in range(1000)]  # chi2=10, p~0.0016 > 0.001
        self.assertEqual(self.run_check("a.csv", csv_text(rows)), [])
        rows = [(f"u{i}", "a" if i < 553 else "b") for i in range(1000)]  # chi2=11.2, p~0.0008
        self.assertEqual(self.codes(self.run_check("a.csv", csv_text(rows))), ["SRM001"])

    def test_ratio_option(self) -> None:
        rows = [(f"u{i}", "a" if i < 750 else "b") for i in range(1000)]
        self.assertEqual(self.run_check("a.csv", csv_text(rows), ratio="3:1"), [])
        self.assertEqual(self.codes(self.run_check("a.csv", csv_text(rows), ratio="1:1")), ["SRM001"])

    def test_three_variants(self) -> None:
        names = ("a", "b", "c")
        self.assertEqual(self.run_check("a.csv", csv_text(balanced(900, names))), [])
        rows = [(f"u{i}", "a" if i < 500 else "b" if i < 700 else "c") for i in range(900)]
        self.assertEqual(self.codes(self.run_check("a.csv", csv_text(rows))), ["SRM001"])
        self.assertEqual(self.run_check("a.csv", csv_text(rows), ratio="5:2:2"), [])

    def test_ratio_more_parts_than_variants_is_insufficient(self) -> None:
        found = self.run_check("a.csv", csv_text(balanced(100)), ratio="1:1:1")
        self.assertEqual(self.codes(found), ["SRM006"])

    def test_ratio_fewer_parts_than_variants_is_srm000(self) -> None:
        found = self.run_check("a.csv", csv_text(balanced(90, ("a", "b", "c"))), ratio="1:1")
        self.assertEqual(self.codes(found), ["SRM000"])

    def test_small_expected_under_ratio_is_insufficient(self) -> None:
        rows = [(f"u{i}", "a") for i in range(8)] + [(f"w{i}", "b") for i in range(2)]
        found = self.run_check("a.csv", csv_text(rows), ratio="99:1")  # kỳ vọng b = 0,1 < 5
        self.assertEqual(self.codes(found), ["SRM006"])
        self.assertIn("kỳ vọng", found[0].message)
        rows = [(f"u{i}", "a") for i in range(495)] + [(f"w{i}", "b") for i in range(5)]
        self.assertEqual(self.run_check("b.csv", csv_text(rows), ratio="99:1"), [])  # kỳ vọng b = 5: chạy kiểm

    def test_variant_names_are_escaped_in_message(self) -> None:
        names = (chr(0xD800), chr(0x1B) + "[31m", "a\nb", "x" + chr(0x2028) + "y")
        records = [{"variant": names[0]} for _ in range(400)]
        records += [{"variant": name} for name in names[1:] for _ in range(100)]
        found = self.run_check("a.json", json.dumps(records))
        self.assertEqual(self.codes(found), ["SRM001"])
        message = found[0].message
        message.encode("utf-8")  # không văng UnicodeEncodeError
        for raw in (chr(0xD800), chr(0x1B), "\n", chr(0x2028)):
            self.assertNotIn(raw, message)
        self.assertIn("\\ud800", message)

    def test_many_variants_are_capped_in_message(self) -> None:
        records = [{"variant": "v0"} for _ in range(5000)]
        records += [{"variant": f"v{i}"} for i in range(1, 8000) for _ in range(5)]
        found = self.run_check("a.json", json.dumps(records))
        self.assertEqual(self.codes(found), ["SRM001"])
        self.assertIn("và 7995 biến thể nữa", found[0].message)
        self.assertLess(len(found[0].message), 300)

    def test_variant_option_and_custom_unit(self) -> None:
        text = "uid,arm\n" + "".join(f"u{i},{'a' if i % 2 else 'b'}\n" for i in range(100))
        self.assertEqual(self.run_check("a.csv", text, variant="arm", unit="uid"), [])
        self.assertEqual(self.codes(self.run_check("a.csv", text)), ["SRM000"])


class InsufficientTest(Base):
    def test_too_few_samples(self) -> None:
        found = self.run_check("a.csv", csv_text([("u1", "a"), ("u2", "b"), ("u3", "a")]))
        self.assertEqual(self.codes(found), ["SRM006"])
        self.assertIn("3", found[0].message)

    def test_exactly_threshold_runs_test(self) -> None:
        rows = [(f"u{i}", "a") for i in range(9)]
        rows.append(("x", "b"))
        found = self.run_check("a.csv", csv_text(rows), alpha="0.05")  # 10 = 5×2: chạy chi2 (6,4; p~0,011)
        self.assertEqual(self.codes(found), ["SRM001"])
        found = self.run_check("a.csv", csv_text(rows[1:]), alpha="0.05")  # 9 < 10: chưa đủ
        self.assertEqual(self.codes(found), ["SRM006"])

    def test_single_variant(self) -> None:
        found = self.run_check("a.csv", csv_text([(f"u{i}", "a") for i in range(50)]))
        self.assertEqual(self.codes(found), ["SRM006"])


class UnitTest(Base):
    def test_duplicates_with_examples_capped(self) -> None:
        rows = balanced(100)
        rows += [(f"u{i}", rows[i][1]) for i in range(8)]  # trùng cùng biến thể
        found = self.run_check("a.csv", csv_text(rows))
        self.assertEqual(self.codes(found), ["SRM002"])
        self.assertIn("8 đơn vị", found[0].message)
        self.assertEqual(found[0].message.count("dòng"), 5)
        self.assertEqual(found[0].line, 2)

    def test_leak_across_variants(self) -> None:
        rows = balanced(100)
        rows.append(("u0", "b"))  # u0 ở a và b
        found = self.run_check("a.csv", csv_text(rows))
        self.assertEqual(self.codes(found), ["SRM002", "SRM003"])
        self.assertIn("1 đơn vị nằm ở", found[1].message)

    def test_long_unit_is_truncated(self) -> None:
        rows = [("x" * 100, "a"), ("x" * 100, "a"), *balanced(40)]
        found = self.run_check("a.csv", csv_text(rows))
        self.assertNotIn("x" * 50, found[0].message)

    def test_unit_ignored_when_absent_by_default(self) -> None:
        text = "variant\n" + "a\nb\n" * 50
        self.assertEqual(self.run_check("a.csv", text), [])

    def test_unit_explicit_but_absent(self) -> None:
        text = "variant\n" + "a\nb\n" * 50
        self.assertEqual(self.codes(self.run_check("a.csv", text, unit="uid")), ["SRM000"])

    def test_variant_missing_unit_still_matches_unit_of_other_rows(self) -> None:
        text = "unit_id,variant\nu1,a\nu1,\nu1,b\n" + "".join(f"x{i},{'a' if i % 2 else 'b'}\n" for i in range(50))
        found = self.run_check("a.csv", text)
        self.assertEqual(self.codes(found), ["SRM004", "SRM002", "SRM003"])

    def test_missing_variant_first_then_variants_seen(self) -> None:
        text = "unit_id,variant\nu1,\nu1,a\nu1,a\n" + "".join(f"x{i},{'a' if i % 2 else 'b'}\n" for i in range(50))
        self.assertEqual(self.codes(self.run_check("a.csv", text)), ["SRM004", "SRM002"])


class MissingTest(Base):
    def test_missing_fields_counted_with_examples(self) -> None:
        text = "unit_id,variant\n,a\nx2,\nx3\n" + csv_text(balanced(60)).split("\n", 1)[1]
        found = self.run_check("a.csv", text)
        self.assertEqual(self.codes(found), ["SRM004"])
        self.assertEqual(found[0].line, 2)
        self.assertIn("3 bản ghi", found[0].message)
        self.assertIn("2, 3, 4", found[0].message)

    def test_json_wrong_types(self) -> None:
        records = [{"unit_id": [1], "variant": "a"}, {"unit_id": "u", "variant": {"x": 1}}, 5, None]
        records += [{"unit_id": f"u{i}", "variant": "ab"[i % 2]} for i in range(40)]
        found = self.run_check("a.json", json.dumps(records))
        self.assertEqual(self.codes(found), ["SRM004"])
        self.assertIn("4 bản ghi", found[0].message)

    def test_numbers_and_bools_are_scalars(self) -> None:
        first = [{"unit_id": i, "variant": i % 2 == 0} for i in range(60)]
        self.assertEqual(self.run_check("a.json", json.dumps(first)), [])
        second = [{"unit_id": float(i), "variant": i % 2} for i in range(60)]
        self.assertEqual(self.run_check("a.json", json.dumps(second)), [])


class ExposureTest(Base):
    def rows(self, exposed_a: int, exposed_b: int) -> str:
        lines = ["unit_id,variant,exposed"]
        for i in range(500):
            lines.append(f"a{i},a,{'true' if i < exposed_a else 'false'}")
            lines.append(f"b{i},b,{'1' if i < exposed_b else '0'}")
        return "\n".join(lines) + "\n"

    def test_balanced_exposure_clean(self) -> None:
        self.assertEqual(self.run_check("a.csv", self.rows(400, 400), exposed="exposed"), [])

    def test_exposure_skew(self) -> None:
        found = self.run_check("a.csv", self.rows(450, 300), exposed="exposed")
        self.assertEqual(self.codes(found), ["SRM005"])
        self.assertIn("'a'=450", found[0].message)
        self.assertIn("'b'=300", found[0].message)

    def table(self, per_arm: int, exposed: tuple[int, ...]) -> str:
        lines = ["variant,exposed"]
        for arm, hits in zip("abc", exposed):
            lines += [f"{arm},{'1' if i < hits else '0'}" for i in range(per_arm)]
        return "\n".join(lines) + "\n"

    def test_homogeneity_catches_small_gap_on_high_exposure(self) -> None:
        # Bảng 2×2: exposed 9900/9800, không exposed 100/200 trên 10000/nhánh → chi2 ≈ 33,84 (bậc 1)
        found = self.run_check("a.csv", self.table(10000, (9900, 9800)), exposed="exposed")
        self.assertEqual(self.codes(found), ["SRM005"])
        self.assertIn("chi2=33.84", found[0].message)
        self.assertIn("bậc 1", found[0].message)

    def test_homogeneity_unbiased_simulation_is_clean(self) -> None:
        rng = random.Random(20261124)
        for rate in (0.5, 0.98):
            lines = ["variant,exposed"]
            for arm in "abc":
                lines += [f"{arm},{int(rng.random() < rate)}" for _ in range(5000)]
            with self.subTest(rate=rate):
                self.assertEqual(self.run_check("s.csv", "\n".join(lines) + "\n", exposed="exposed"), [])

    def test_all_or_none_exposed_is_skipped(self) -> None:
        rows = ["variant,exposed", *(["a,1"] * 600), *(["b,1"] * 400)]
        self.assertEqual(self.codes(self.run_check("a.csv", "\n".join(rows) + "\n", exposed="exposed")), ["SRM001"])
        self.assertEqual(self.run_check("b.csv", self.table(500, (500, 500)), exposed="exposed"), [])
        self.assertEqual(self.run_check("c.csv", self.table(500, (0, 0)), exposed="exposed"), [])

    def test_small_expected_cell_is_insufficient(self) -> None:
        found = self.run_check("a.csv", self.table(500, (498, 497)), exposed="exposed")  # kỳ vọng không exposed 2,5
        self.assertEqual(self.codes(found), ["SRM006"])
        self.assertIn("exposed", found[0].message)

    def test_exposure_not_checked_without_option(self) -> None:
        self.assertEqual(self.run_check("a.csv", self.rows(450, 300)), [])

    def test_exposure_insufficient(self) -> None:
        found = self.run_check("a.csv", self.rows(2, 1), exposed="exposed")
        self.assertEqual(self.codes(found), ["SRM006"])
        self.assertIn("exposed", found[0].message)

    def test_exposure_invalid_values(self) -> None:
        text = self.rows(400, 400) + "z1,a,maybe\nz2,b,\n"
        found = self.run_check("a.csv", text, exposed="exposed")
        self.assertEqual(self.codes(found), ["SRM004"])
        self.assertIn("2 bản ghi", found[0].message)

    def test_exposed_field_absent(self) -> None:
        found = self.run_check("a.csv", csv_text(balanced(100)), exposed="exposed")
        self.assertEqual(self.codes(found), ["SRM000"])

    def test_exposed_json_bool_and_case(self) -> None:
        records = []
        for i in range(500):
            records.append({"unit_id": f"a{i}", "variant": "a", "exposed": True})
            records.append({"unit_id": f"b{i}", "variant": "b", "exposed": "TRUE" if i < 200 else False})
        found = self.run_check("a.json", json.dumps(records), exposed="exposed")
        self.assertEqual(self.codes(found), ["SRM005"])


class FormatTest(Base):
    def test_json_array_object_records_and_jsonl(self) -> None:
        records = [{"unit_id": f"u{i}", "variant": "ab"[i % 2]} for i in range(100)]
        self.assertEqual(self.run_check("a.json", json.dumps(records)), [])
        self.assertEqual(self.run_check("b.json", json.dumps({"records": records})), [])
        self.assertEqual(self.run_check("c.jsonl", "\n".join(json.dumps(r) for r in records) + "\n"), [])
        self.assertEqual(self.run_check("d.jsonl", "\r\n\r\n".join(json.dumps(r) for r in records)), [])

    def test_jsonl_skew_and_blank_lines(self) -> None:
        records = [{"unit_id": f"u{i}", "variant": "a" if i < 80 else "b"} for i in range(100)]
        text = "\n\n".join(json.dumps(r) for r in records)
        self.assertEqual(self.codes(self.run_check("a.jsonl", text)), ["SRM001"])

    def test_crlf_and_cr_csv(self) -> None:
        text = csv_text(balanced(100)).replace("\n", "\r\n")
        self.assertEqual(self.run_check("a.csv", text), [])
        self.assertEqual(self.codes(self.run_check("b.csv", text.replace("\r\n", "\r"))), ["SRM000"])

    def test_blank_csv_rows_and_no_trailing_newline(self) -> None:
        text = "unit_id,variant\n\n" + "".join(f"u{i},{'ab'[i % 2]}\n\n" for i in range(50)).rstrip("\n")
        self.assertEqual(self.run_check("a.csv", text), [])

    def test_unicode_variants_and_units(self) -> None:
        rows = [(f"người{i}", "đối-chứng" if i % 2 else "thử-nghiệm") for i in range(100)]
        self.assertEqual(self.run_check("a.csv", csv_text(rows)), [])

    def test_utf8_bom_is_stripped(self) -> None:
        rows = balanced(100)
        rows.append(("u0", "a"))  # trùng đơn vị: chỉ thấy khi cột đầu `unit_id` không dính BOM
        self.assertEqual(self.codes(self.run_check("a.csv", BOM + csv_text(rows))), ["SRM002"])
        self.assertEqual(self.run_check("b.csv", BOM + csv_text(balanced(100)), unit="unit_id"), [])
        records = [{"unit_id": f"u{i}", "variant": "ab"[i % 2]} for i in range(100)]
        self.assertEqual(self.run_check("c.json", BOM + json.dumps(records)), [])
        self.assertEqual(self.run_check("d.jsonl", BOM + "\n".join(json.dumps(r) for r in records)), [])

    def test_quoted_csv_with_commas(self) -> None:
        text = "unit_id,variant\n" + "".join(f'"u,{i}","{"ab"[i % 2]}"\n' for i in range(50))
        self.assertEqual(self.run_check("a.csv", text), [])


class Srm000Test(Base):
    def test_empty_and_whitespace_files(self) -> None:
        for name in ("a.csv", "a.json", "a.jsonl"):
            self.assertEqual(self.codes(self.run_check(name, "")), ["SRM000"])
        self.assertEqual(self.codes(self.run_check("b.jsonl", "\n \n")), ["SRM000"])

    def test_header_only_csv(self) -> None:
        self.assertEqual(self.codes(self.run_check("a.csv", "unit_id,variant\n")), ["SRM000"])

    def test_csv_missing_variant_column(self) -> None:
        found = self.run_check("a.csv", "unit_id,arm\nu1,a\n")
        self.assertEqual((found[0].code, found[0].line), ("SRM000", 1))

    def test_bad_json(self) -> None:
        self.assertEqual(self.codes(self.run_check("a.json", "{nope")), ["SRM000"])
        self.assertEqual(self.codes(self.run_check("b.json", '"str"')), ["SRM000"])
        self.assertEqual(self.codes(self.run_check("c.json", '{"records": 3}')), ["SRM000"])

    def test_bad_jsonl_line_number(self) -> None:
        found = self.run_check("a.jsonl", '{"variant": "a"}\n\n{oops\n')
        self.assertEqual((found[0].code, found[0].line), ("SRM000", 3))

    def test_no_variant_anywhere(self) -> None:
        found = self.run_check("a.json", json.dumps([{"unit_id": "x"}, 3]))
        self.assertEqual(self.codes(found), ["SRM000"])

    def test_deep_nesting_does_not_raise(self) -> None:
        with unittest.mock.patch.object(json, "loads", side_effect=RecursionError):
            self.assertEqual(self.codes(self.run_check("a.json", "[]")), ["SRM000"])
            self.assertEqual(self.codes(self.run_check("a.jsonl", "{}")), ["SRM000"])
        deep = "[" * 100000 + "]" * 100000
        self.assertEqual(self.codes(self.run_check("b.json", deep)), ["SRM000"])

    def test_non_utf8_and_binary(self) -> None:
        path = self.dir / "a.csv"
        path.write_bytes(b"unit_id,variant\n\xff\xfe,a\n")
        self.assertEqual(self.codes(kind_srm.check([path], {})), ["SRM000"])

    def test_missing_file(self) -> None:
        found = kind_srm.check([self.dir / "nope.csv"], {})
        self.assertEqual(self.codes(found), ["SRM000"])

    def test_too_large_file(self) -> None:
        text = "unit_id,variant\n" + "u,a\n" * (xt_checks.MAX_BYTES // 4)
        found = self.run_check("a.csv", text)
        self.assertEqual((found[0].code, found[0].line), ("SRM000", 0))

    def test_csv_strict_error(self) -> None:
        found = self.run_check("a.csv", 'unit_id,variant\nu1,"a"x\n')
        self.assertEqual((found[0].code, found[0].line), ("SRM000", 2))

    def test_csv_huge_field_and_limit_untouched(self) -> None:
        limit = csv.field_size_limit()
        text = "unit_id,variant\nu1," + "x" * 400000 + "\n"
        found = self.run_check("a.csv", text)
        self.assertEqual(self.codes(found), ["SRM000"])
        self.assertEqual(csv.field_size_limit(), limit)

    def test_huge_jsonl_line(self) -> None:
        text = json.dumps({"unit_id": "u1", "variant": "a" * 400000, "x": 1}) + "\n"
        found = self.run_check("a.jsonl", text)
        self.assertEqual(self.codes(found), ["SRM006"])

    def test_multiple_files_independent(self) -> None:
        good = self.put("g.csv", csv_text(balanced(100)))
        bad = self.put("b.csv", "unit_id,arm\n")
        found = kind_srm.check([good, bad], {})
        self.assertEqual([(Path(f.path).name, f.code) for f in found], [("b.csv", "SRM000")])


class OptionTest(Base):
    def test_bad_options(self) -> None:
        text = csv_text(balanced(40))
        for opts in (
            {"alpha": "x"},
            {"alpha": "0"},
            {"alpha": "1.5"},
            {"alpha": "nan"},
            {"ratio": "a:b"},
            {"ratio": "1"},
            {"ratio": "1:0"},
            {"ratio": "1:-1"},
            {"ratio": "1:inf"},
            {"ratio": "1:nan"},
            {"ratio": "1e308:1e308"},
            {"variant": ""},
            {"unit": ""},
            {"exposed": ""},
        ):
            with self.subTest(opts=opts), self.assertRaises(CheckError):
                self.run_check("a.csv", text, **opts)

    def test_alpha_one_is_allowed(self) -> None:
        self.assertEqual(self.codes(self.run_check("a.csv", csv_text(balanced(40)), alpha="1")), [])


class LinearTimeTest(Base):
    def test_records_linear(self) -> None:
        def work(n: int) -> None:
            text = csv_text([(f"u{i}", "ab"[i % 2]) for i in range(n)])
            path = self.put("big.csv", text)
            kind_srm.check([path], {})

        assert_not_quadratic(self, work, 50000)

    def test_all_duplicate_units_linear(self) -> None:
        recs = [kind_srm._Rec(i, "ab"[i % 2], f"u{i % 7}", None) for i in range(200000)]
        assert_not_quadratic(self, lambda n: kind_srm._units(recs[:n]), 50000)

    def test_unique_units_linear(self) -> None:
        recs = [kind_srm._Rec(i, "ab"[i % 2], f"u{i}", None) for i in range(200000)]
        assert_not_quadratic(self, lambda n: kind_srm._unit_findings("p", recs[:n]), 50000)

    def test_many_variants_linear(self) -> None:
        def work(n: int) -> None:
            text = csv_text([(f"u{i}", f"v{i}") for i in range(n)])
            kind_srm.check([self.put("v.csv", text)], {})

        assert_not_quadratic(self, work, 10000)

    def test_long_line_linear(self) -> None:
        def work(n: int) -> None:
            line = json.dumps({"unit_id": "u", "variant": "a" * n})
            kind_srm.check([self.put("l.jsonl", line + "\n")], {})

        assert_not_quadratic(self, work, 100000)


class MutationTest(Base):
    """Số phép băm và so sánh phân biệt cách đếm bằng bảng băm với `list.count` theo từng đơn vị."""

    def unit_operations(self, units_for: Callable[[list[kind_srm._Rec]], dict[str, list[object]]], n: int) -> int:
        count = 0

        class CountedStr(str):
            def __hash__(self) -> int:
                nonlocal count
                count += 1
                return super().__hash__()

            def __eq__(self, other: object) -> bool:
                nonlocal count
                count += 1
                return super().__eq__(other)

        recs = [kind_srm._Rec(i, "a", CountedStr(f"u{i}"), None) for i in range(n)]
        with unittest.mock.patch.object(kind_srm, "_units", units_for):
            self.assertEqual(kind_srm._unit_findings("p", recs), [])
        self.assertGreater(count, 0, "chưa quan sát được phép băm hoặc so sánh mã đơn vị")
        return count

    def test_list_count_mutant_is_detected(self) -> None:
        def slow(recs: list[kind_srm._Rec]) -> dict[str, list[object]]:
            units = [r.unit for r in recs]
            return {str(u): [1, units.count(u), None, False] for u in units}

        for units_for, linear in ((kind_srm._units, True), (slow, False)):
            with self.subTest(units_for=units_for.__name__):
                small = self.unit_operations(units_for, 128)
                big = self.unit_operations(units_for, 512)
                self.assertEqual(big < MUTANT_RATIO * small, linear, f"{small} → {big} phép băm và so sánh")


if __name__ == "__main__":
    unittest.main()
