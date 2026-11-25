"""Loại `i18n` (XC-I18N-009): so catalog JSON với nguồn; mã LOC000-LOC007, `--opt` và thời gian tuyến tính."""

from __future__ import annotations

import json
import os
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
from xt_checks import kind_i18n


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def put(self, name: str, data: object) -> Path:
        path = self.base / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data if isinstance(data, str) else json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def run_check(self, source: object, *targets: object, **opts: str) -> list[xt_checks.Finding]:
        src = self.put("en.json", source)
        files = [self.put(f"t{i}.json", t) for i, t in enumerate(targets)]
        return kind_i18n.check(files, {"source": str(src), **opts})

    def codes(self, source: object, target: object, **opts: str) -> list[str]:
        return [f.code for f in self.run_check(source, target, **opts)]


class OptsTest(Base):
    def test_interface(self) -> None:
        self.assertEqual(kind_i18n.SUFFIXES, (".json",))
        self.assertIs(kind_i18n.SNIFF, kind_i18n.sniff)
        self.assertIsInstance(kind_i18n.HELP, str)
        xt_checks.validate_opts(kind_i18n, {"source": "x", "min": "1", "ignore": "LOC001"})
        with self.assertRaisesRegex(xt_checks.CheckError, "--opt lạ"):
            xt_checks.validate_opts(kind_i18n, {"sourse": "x"})

    def test_source_is_required(self) -> None:
        with self.assertRaisesRegex(xt_checks.CheckError, "source"):
            kind_i18n.check([], {})
        with self.assertRaisesRegex(xt_checks.CheckError, "source"):
            kind_i18n.check([], {"source": ""})

    def test_source_must_exist_and_be_a_catalog(self) -> None:
        with self.assertRaisesRegex(xt_checks.CheckError, "không thấy"):
            kind_i18n.check([], {"source": str(self.base / "none.json")})
        with self.assertRaisesRegex(xt_checks.CheckError, "không thấy"):
            kind_i18n.check([], {"source": str(self.base)})
        real = self.put("real.json", {"a": "b"})
        link = self.base / "link.json"
        link.symlink_to(real)
        with self.assertRaisesRegex(xt_checks.CheckError, "không thấy"):
            kind_i18n.check([], {"source": str(link)})
        for body, why in (("{oops", "JSON"), ("[1]", "object"), ("", "JSON")):
            bad = self.put("bad.json", body)
            with self.subTest(body=body), self.assertRaisesRegex(xt_checks.CheckError, why):
                kind_i18n.check([], {"source": str(bad)})

    def test_min_must_be_a_number_between_0_and_100(self) -> None:
        src = self.put("en.json", {"a": "x"})
        for bad in ("abc", "101", "-1", "nan", "inf", ""):
            with self.subTest(min=bad), self.assertRaisesRegex(xt_checks.CheckError, "min"):
                kind_i18n.check([], {"source": str(src), "min": bad})
        self.assertEqual(kind_i18n.check([], {"source": str(src), "min": "0"}), [])
        self.assertEqual(kind_i18n.check([], {"source": str(src), "min": "99.5"}), [])


class SniffTest(Base):
    def test_sniff_accepts_only_objects(self) -> None:
        self.assertTrue(kind_i18n.sniff('{"a": "b"}'))
        self.assertTrue(kind_i18n.sniff(chr(0xFEFF) + '\r\n  {"a": 1}'))
        for text in ("[1]", "", "abc", '"{"'):
            self.assertFalse(kind_i18n.sniff(text))

    def test_directory_scan_skips_non_object_json(self) -> None:
        self.put("d/a.json", {"x": "y"})
        self.put("d/b.json", [1, 2])
        got = xt_checks.collect([str(self.base / "d")], kind_i18n.SUFFIXES, kind_i18n.SNIFF)
        self.assertEqual([p.name for p in got], ["a.json"])


class KeysTest(Base):
    def test_identical_catalogs_are_clean_flat_and_nested(self) -> None:
        self.assertEqual(self.run_check({"a": "x", "b": "y"}, {"b": "Y", "a": "X"}), [])
        nested = {"home": {"title": "T", "deep": {"k": "v"}}, "bye": "B"}
        self.assertEqual(self.run_check(nested, {"home": {"title": "Tt", "deep": {"k": "vv"}}, "bye": "Bb"}), [])

    def test_flat_dotted_key_equals_nested(self) -> None:
        self.assertEqual(self.run_check({"a": {"b": "x"}}, {"a.b": "y"}), [])

    def test_missing_keys_are_listed_and_capped(self) -> None:
        found = self.run_check({"a": "1", "b": "2", "c": "3"}, {"a": "1"})
        self.assertEqual([f.code for f in found if f.code == "LOC001"], ["LOC001"])
        message = next(f.message for f in found if f.code == "LOC001")
        self.assertIn("thiếu so với nguồn 2 khoá: b, c", message)
        many = {f"k{i:02d}": "x" for i in range(25)}
        found = self.run_check(many, {}, min="0")
        text = next(f.message for f in found if f.code == "LOC001")
        self.assertIn("k19", text)
        self.assertNotIn("k20", text)
        self.assertIn("và 5 khoá nữa", text)

    def test_extra_keys(self) -> None:
        found = self.run_check({"a": "1"}, {"a": "1", "z": "2", "y": {"w": "3"}})
        self.assertEqual([f.code for f in found], ["LOC002"])
        self.assertIn("y.w, z", found[0].message)

    def test_long_key_is_shortened_and_unicode_keys_work(self) -> None:
        key = "chào." + "x" * 200
        found = self.run_check({key: "a", "Việt": "b"}, {"Việt": "b"}, min="0")
        self.assertEqual([f.code for f in found], ["LOC001"])
        self.assertLess(len(found[0].message), 200)
        self.assertEqual(self.run_check({"Việt": "b"}, {"Việt": "c"}), [])

    def test_empty_key_and_empty_nested_object(self) -> None:
        self.assertEqual(self.run_check({"": "a", "x": {}}, {"": "b", "x": {}}), [])

    def test_ignore_drops_codes(self) -> None:
        self.assertEqual(self.codes({"a": "1"}, {"a": "1", "z": "2"}, ignore="LOC002"), [])


class FileProblemsTest(Base):
    def test_unreadable_or_wrong_shape_is_i18n000(self) -> None:
        src = self.put("en.json", {"a": "x"})
        bad = {
            "syntax.json": "{oops",
            "array.json": "[1, 2]",
            "empty.json": "",
            "bom.json": chr(0xFEFF) + '{"a": "x"}',
            "scalar.json": '"text"',
        }
        files = [self.put(n, b) for n, b in bad.items()]
        raw = self.base / "latin.json"
        raw.write_bytes(b'{"a": "\xff"}')
        files.append(raw)
        files.append(self.base / "missing.json")
        found = kind_i18n.check(files, {"source": str(src)})
        self.assertEqual({f.code for f in found}, {"LOC000"})
        self.assertEqual(len(found), len(files))
        self.assertTrue(all(f.line == 0 for f in found))

    def test_symlink_and_fifo_targets_are_reported_not_hung(self) -> None:
        src = self.put("en.json", {"a": "x"})
        other = self.put("other.json", {"a": "x"})
        link = self.base / "l.json"
        link.symlink_to(other)
        fifo = self.base / "f.json"
        os.mkfifo(fifo)
        found = kind_i18n.check([link, fifo], {"source": str(src)})
        self.assertEqual([f.code for f in found], ["LOC000", "LOC000"])

    def test_deep_json_recursion_error_is_i18n000(self) -> None:
        src = self.put("en.json", {"a": "x"})
        target = self.put("deep.json", "[" * 10 + "]" * 10)
        real = json.loads

        def loads(text: str) -> object:
            if text.startswith("[["):
                raise RecursionError
            return real(text)

        with unittest.mock.patch.object(kind_i18n.json, "loads", loads):
            found = kind_i18n.check([target], {"source": str(src)})
        self.assertEqual([f.code for f in found], ["LOC000"])
        self.assertIn("sâu", found[0].message)

    def test_source_recursion_error_is_a_usage_error(self) -> None:
        src = self.put("en.json", {"a": "x"})
        with (
            unittest.mock.patch.object(kind_i18n.json, "loads", side_effect=RecursionError),
            self.assertRaisesRegex(xt_checks.CheckError, "sâu"),
        ):
            kind_i18n.check([], {"source": str(src)})

    def test_source_in_the_file_list_is_not_compared_with_itself(self) -> None:
        src = self.put("en.json", {"a": "x"})
        self.assertEqual(kind_i18n.check([src], {"source": str(src)}), [])

    def test_crlf_and_pretty_json(self) -> None:
        src = self.put("en.json", '{\r\n  "a": "x"\r\n}\r\n')
        target = self.put("vi.json", '{\r\n  "a": "y"\r\n}\r\n')
        self.assertEqual(kind_i18n.check([target], {"source": str(src)}), [])


class IcuTest(Base):
    def scan(self, text: str) -> str:
        return kind_i18n.scan_icu(text)[0]

    def test_balanced_forms_are_fine(self) -> None:
        for text in (
            "",
            "plain text",
            "Xin chào {name}",
            "{n, plural, one {# mục} other {# mục}}",
            "{g, select, male {{n, plural, one {a} other {b}}} other {c}}",
            "'{' literal '}'",
            "it''s fine",
            "l'été",
            "trail'",
            "'{{}}' ok",
            "'{a''b}' ok",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.scan(text), "")

    def test_broken_forms(self) -> None:
        cases = {
            "{name": "thiếu 1",
            "{a, plural, one {x}": "thiếu 1",
            "a}": "thừa",
            "{a}}": "thừa",
            "{}": "rỗng",
            "{ }": "rỗng",
            "{{x}}": "rỗng",
            "'{x": "chưa đóng",
            "'}": "chưa đóng",
            "'{ ''": "chưa đóng",
        }
        for text, why in cases.items():
            with self.subTest(text=text):
                self.assertIn(why, self.scan(text))

    def test_names_are_top_level_only(self) -> None:
        names = kind_i18n.scan_icu("{n, plural, one {{x} a} other {b}} và { m } và {0}")[1]
        self.assertEqual(names, frozenset({"n", "m", "0"}))

    def test_i18n003_reported_with_key(self) -> None:
        found = self.run_check({"a": "{n}", "b": "ok"}, {"a": "{n", "b": "ok"})
        self.assertEqual([f.code for f in found], ["LOC003"])
        self.assertIn("a: ICU hỏng", found[0].message)

    def test_broken_icu_in_source_does_not_add_param_noise(self) -> None:
        self.assertEqual(self.codes({"a": "{n"}, {"a": "{m}"}), [])

    def test_per_key_findings_are_capped(self) -> None:
        source = {f"k{i:02d}": "x" for i in range(25)}
        target = {f"k{i:02d}": "{" for i in range(25)}
        found = self.run_check(source, target)
        self.assertEqual(len(found), 21)
        self.assertEqual(found[-1].message, "và 5 khoá nữa")


class ParamsTest(Base):
    def test_same_set_any_order_and_plural(self) -> None:
        self.assertEqual(self.codes({"a": "{x} và {y}"}, {"a": "{y} rồi {x} {x}"}), [])
        self.assertEqual(
            self.codes({"a": "{n, plural, one {# a} other {# b}}"}, {"a": "{n, plural, other {# mục} one {# mục}}"}), []
        )

    def test_lost_renamed_and_added(self) -> None:
        found = self.run_check({"a": "{x} {y}", "b": "{n}", "c": "plain"}, {"a": "{x}", "b": "{m}", "c": "{z}"})
        self.assertEqual([f.code for f in found], ["LOC004"] * 3)
        texts = [f.message for f in found]
        self.assertIn("mất y", texts[0])
        self.assertIn("mất n; thêm m", texts[1])
        self.assertIn("thêm z", texts[2])

    def test_source_cache_shared_between_targets(self) -> None:
        src = self.put("en.json", {"a": "{x}"})
        one = self.put("one.json", {"a": "{y}"})
        two = self.put("two.json", {"a": "{z}"})
        found = kind_i18n.check([one, two], {"source": str(src)})
        self.assertEqual([f.code for f in found], ["LOC004", "LOC004"])

    def test_nested_branch_params_are_ignored(self) -> None:
        self.assertEqual(self.codes({"a": "{n, plural, one {{p} x} other {y}}"}, {"a": "{n, plural, other {z}}"}), [])


class HtmlTest(Base):
    def test_risky_values_flagged_when_source_is_clean(self) -> None:
        for value, what in (
            ("<script>x</script>", "script"),
            ("<SCRIPT src=a>", "script"),
            ('<a onclick="x">', "handler"),
            ("<b ONLOAD = 1>", "handler"),
            ("javascript:void(0)", "jsuri"),
            ("JavaScript:x", "jsuri"),
        ):
            with self.subTest(value=value):
                found = self.run_check({"a": "clean"}, {"a": value})
                self.assertEqual([f.code for f in found], ["LOC005"])
                self.assertIn(what, found[0].message)

    def test_same_markup_in_source_is_allowed_but_new_kind_is_not(self) -> None:
        self.assertEqual(self.codes({"a": "<script>x</script>"}, {"a": "<script>y</script>"}), [])
        self.assertEqual(self.codes({"a": "<script>x</script>"}, {"a": "<script>y</script> javascript:z"}), ["LOC005"])

    def test_words_that_only_look_alike_are_clean(self) -> None:
        text = "Conditions=ok; một-onclick=1; on=2; <b>đậm</b>; javascript là ngôn ngữ"
        self.assertEqual(self.codes({"a": "x"}, {"a": text}), [])

    def test_non_string_source_value_counts_as_no_markup(self) -> None:
        self.assertEqual(self.codes({"a": 1}, {"a": "<script>"}), ["LOC005"])


class CompletenessTest(Base):
    def test_default_requires_full_coverage(self) -> None:
        found = self.run_check({"a": "1", "b": "2", "c": "3", "d": "4"}, {"a": "1", "b": "2", "c": "3"})
        self.assertEqual([f.code for f in found], ["LOC001", "LOC006"])
        self.assertIn("đủ 75.0%", found[1].message)
        self.assertIn("t0.json", found[1].message)

    def test_min_threshold_boundaries(self) -> None:
        source = {"a": "1", "b": "2", "c": "3", "d": "4"}
        target = {"a": "1", "b": "2", "c": "3"}
        self.assertEqual(self.codes(source, target, min="75"), ["LOC001"])
        self.assertEqual(self.codes(source, target, min="75.1"), ["LOC001", "LOC006"])
        self.assertEqual(self.codes(source, {}, min="0"), ["LOC001"])

    def test_empty_source_is_complete(self) -> None:
        self.assertEqual(self.codes({}, {}), [])
        self.assertEqual(self.codes({}, {"a": "x"}), ["LOC002"])

    def test_non_string_values_do_not_count_as_translated(self) -> None:
        found = self.run_check({"a": "x", "b": "y"}, {"a": "x", "b": None}, min="100")
        self.assertEqual([f.code for f in found], ["LOC007", "LOC006"])
        self.assertIn("đủ 50.0%", found[1].message)

    def test_ignore_removes_completeness_report(self) -> None:
        self.assertEqual(self.codes({"a": "x"}, {}, ignore="LOC001,LOC006"), [])


class NonStringTest(Base):
    def test_numbers_null_arrays_booleans(self) -> None:
        target = {"n": 1, "z": None, "l": ["a"], "t": True, "ok": "s", "o": {"in": 2.5}}
        source = {"n": "1", "z": "z", "l": "l", "t": "t", "ok": "s", "o.in": "i"}
        found = self.run_check(source, target, min="0")
        self.assertEqual([f.code for f in found], ["LOC007"] * 5)
        self.assertIn("giá trị không phải chuỗi", found[0].message)

    def test_non_string_in_source_is_not_compared(self) -> None:
        self.assertEqual(self.codes({"a": 1}, {"a": "x"}), [])
        self.assertEqual(self.codes({"a": 1}, {"a": 2}), ["LOC007"])


class OrderAndRegistryTest(Base):
    def test_run_through_registry_style_collect_and_sort(self) -> None:
        self.put("loc/vi.json", {"a": "x", "extra": "1"})
        self.put("loc/en.json", {"a": "x"})
        self.put("loc/fr.json", {})
        src = str(self.base / "loc" / "en.json")
        files = xt_checks.collect([str(self.base / "loc")], kind_i18n.SUFFIXES, kind_i18n.SNIFF)
        found = sorted(kind_i18n.check(files, {"source": src}), key=lambda f: (f.path, f.line, f.code))
        self.assertEqual(
            [(Path(f.path).name, f.code) for f in found],
            [("fr.json", "LOC001"), ("fr.json", "LOC006"), ("vi.json", "LOC002")],
        )


def icu_nested(total: int) -> str:
    unit = "{a, plural, one {"
    count = max(total // (len(unit) + 2), 1)
    return unit * count + "x" + "}}" * count


class LinearTimeTest(Base):
    def test_icu_nested_brackets_are_linear(self) -> None:
        text = icu_nested(400000)
        self.assertGreaterEqual(len(text), 399000)
        self.assertEqual(kind_i18n.scan_icu(text)[0], "")
        assert_not_quadratic(self, lambda n: kind_i18n.scan_icu(icu_nested(n)), 100000)

    def test_icu_long_quotes_and_unbalanced_are_linear(self) -> None:
        shapes = {
            "quote": lambda n: "'{" + "x" * n + "'",
            "doubled": lambda n: "'{" + "''" * (n // 2) + "'",
            "apostrophes": lambda n: "'" * n,
            "open": lambda n: "{a," * (n // 3),
            "unclosed": lambda n: "'{" * (n // 2),
        }
        for name, build in shapes.items():
            with self.subTest(shape=name):
                assert_not_quadratic(self, lambda n, b=build: kind_i18n.scan_icu(b(n)), 100000)

    def test_risky_regex_is_linear(self) -> None:
        for name, build in (
            ("on", lambda n: "on" * n),
            ("space", lambda n: "onab" + " " * n),
            ("lt", lambda n: "<" * n),
        ):
            with self.subTest(shape=name):
                assert_not_quadratic(self, lambda n, b=build: kind_i18n._risky(b(n)), 100000)

    def big_catalog(self, n: int) -> kind_i18n.Flat:
        return {f"k{i}": "v {x}" for i in range(n)}

    def test_catalog_of_200000_keys_is_linear(self) -> None:
        def work(n: int) -> None:
            src = self.big_catalog(n)
            tgt = {f"k{i}": "w {x}" for i in range(0, n, 2)}
            kind_i18n._compare(Path("t.json"), src, tgt, 0.0, {})

        work(200000)
        assert_not_quadratic(self, work, 50000)

    def test_deeply_nested_catalog_is_flattened_without_recursion(self) -> None:
        def build(n: int) -> dict[str, object]:
            root: dict[str, object] = {}
            node = root
            for i in range(n):
                child: dict[str, object] = {}
                node[f"l{i}"] = child
                node = child
            node["leaf"] = "x"
            return root

        flat = kind_i18n._flatten(build(3000))
        self.assertEqual(len(flat), 1)
        self.assertEqual(next(iter(flat)).count("."), 3000)

    def test_wide_nested_catalog_is_linear(self) -> None:
        def work(n: int) -> None:
            kind_i18n._flatten({f"g{i}": {"a": "1", "b": {"c": "2"}} for i in range(n)})

        assert_not_quadratic(self, work, 50000)


# Bản đột biến bậc hai tốn ~16 lần khi cỡ tăng 4 lần; ngưỡng 6 (> 4 của tuyến tính) cho biên rộng trên runner chậm,
# vì ngưỡng mặc định 10 chỉ hở ~1,5 lần (CI #783: AssertionError not raised).
MUTANT_RATIO = 6


class MutationTest(Base):
    """Bản bậc hai của bộ quét/làm phẳng PHẢI làm các test trên đỏ — chứng minh test nhạy với việc làm chậm."""

    def test_quadratic_icu_scanner_is_detected(self) -> None:
        real = kind_i18n.scan_icu

        def slow(text: str) -> tuple[str, frozenset[str]]:
            depth = 0
            for i in range(len(text)):
                depth = sum(1 for ch in text[:i] if ch == "{")
            return real(text)[0], frozenset({str(depth)})

        with unittest.mock.patch.object(kind_i18n, "scan_icu", slow), self.assertRaises(AssertionError):
            assert_not_quadratic(self, lambda n: kind_i18n.scan_icu("{" * n), 4000, ratio=MUTANT_RATIO)

    def test_quadratic_flatten_is_detected(self) -> None:
        def slow(root: dict[str, object]) -> kind_i18n.Flat:
            keys = list(root)
            return {key: sum(1 for other in keys if other == key) for key in keys}

        with unittest.mock.patch.object(kind_i18n, "_flatten", slow), self.assertRaises(AssertionError):
            assert_not_quadratic(
                self, lambda n: kind_i18n._flatten({f"k{i}": "v" for i in range(n)}), 3000, ratio=MUTANT_RATIO
            )


if __name__ == "__main__":
    unittest.main()
