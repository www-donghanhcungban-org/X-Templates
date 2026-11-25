"""Loại `vex` của `static-check` (ADR-0099): fixture OpenVEX tốt/xấu trong thư mục tạm."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import xt_checks
from xt_checks import kind_vex

STMT = {
    "vulnerability": {"name": "CVE-2026-0001"},
    "products": [{"@id": "pkg:pypi/lib@1.0"}],
    "status": "not_affected",
    "justification": "component_not_present",
}
GOOD = {
    "@context": "https://openvex.dev/ns/v0.2.0",
    "@id": "https://example.org/vex/1",
    "author": "Nhóm bảo mật",
    "timestamp": "2026-11-24T00:00:00Z",
    "version": 1,
    "statements": [STMT],
}


class VexTest(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def findings(self, doc: object) -> list[xt_checks.Finding]:
        path = self.base / "vex.json"
        path.write_text(doc if isinstance(doc, str) else json.dumps(doc), encoding="utf-8")
        return kind_vex.check([path], {})

    def run_check(self, doc: object) -> list[str]:
        return [f.code for f in self.findings(doc)]

    def one(self, **over: object) -> list[str]:
        return self.run_check({**GOOD, "statements": [{**STMT, **over}]})

    def test_good_is_clean(self) -> None:
        self.assertEqual(self.run_check(GOOD), [])
        self.assertEqual(self.one(status="fixed"), [])
        self.assertEqual(self.one(status="under_investigation"), [])

    def test_interface(self) -> None:
        self.assertTrue(kind_vex.HELP)
        self.assertEqual(kind_vex.SUFFIXES, (".json",))

    def test_vex000_invalid(self) -> None:
        for doc in ("không phải json", "[]", "{}", '{"@context": "https://khac.example/"}'):
            with self.subTest(doc=doc):
                self.assertEqual(self.run_check(doc), ["VEX000"])

    def test_context_strict(self) -> None:
        for ctx in (
            "http://openvex.dev/ns",
            "x//openvex.dev/ns",
            "//openvex.dev/ns",
            "https://openvex.dev.evil.example/ns",
            "https://evil.example/openvex.dev/ns",
            "https://openvex.dev/other",
            "https://[openvex.dev/ns",
            5,
            None,
            ["https://openvex.dev/ns"],
        ):
            with self.subTest(ctx=ctx):
                self.assertEqual(self.run_check({**GOOD, "@context": ctx}), ["VEX000"])
        self.assertEqual(self.run_check({**GOOD, "@context": "https://openvex.dev/ns"}), [])

    def test_sniff_and_opts(self) -> None:
        self.assertEqual(kind_vex.OPTS, ())
        self.assertTrue(kind_vex.SNIFF(json.dumps(GOOD)))
        self.assertFalse(kind_vex.SNIFF('{"name": "package"}'))
        self.assertFalse(kind_vex.SNIFF('{"@context": "x"}'))

    def test_directory_scan_only_vex(self) -> None:
        (self.base / "khac.json").write_text('{"name": "x"}', encoding="utf-8")
        (self.base / "vex.json").write_text(json.dumps(GOOD), encoding="utf-8")
        found = xt_checks.run("vex", [str(self.base)], {})
        self.assertEqual(found, [])
        (self.base / "bad.json").write_text('{"@context": "openvex"}', encoding="utf-8")
        self.assertEqual([Path(f.path).name for f in xt_checks.run("vex", [str(self.base)], {})], ["bad.json"])
        self.assertEqual(
            [Path(f.path).name for f in xt_checks.run("vex", [str(self.base / "khac.json")], {})], ["khac.json"]
        )

    def test_vex000_unreadable_and_recursion(self) -> None:
        path = self.base / "bad.json"
        path.write_bytes(b"\xff\xfe")
        self.assertEqual([f.code for f in kind_vex.check([path], {})], ["VEX000"])
        with unittest.mock.patch.object(kind_vex.json, "loads", side_effect=RecursionError):
            self.assertEqual(self.run_check(GOOD), ["VEX000"])

    def test_vex001_document_fields(self) -> None:
        for key in ("author", "timestamp", "version"):
            with self.subTest(key=key):
                doc = {k: v for k, v in GOOD.items() if k != key}
                self.assertEqual(self.run_check(doc), ["VEX001"])
        self.assertEqual(self.run_check({**GOOD, "author": ""}), ["VEX001"])
        self.assertEqual(self.run_check({**GOOD, "version": 0}), [])

    def test_statements_not_a_list_or_item_not_dict(self) -> None:
        for value in (None, [], "sai", 3, {}):
            self.assert_shape({**GOOD, "statements": value}, "statements")
        self.assert_shape({k: v for k, v in GOOD.items() if k != "statements"}, "statements")
        mixed = {**GOOD, "statements": [3, {**STMT, "status": "unknown"}]}
        self.assertCountEqual(self.run_check(mixed), ["VEX000", "VEX003"])
        self.assert_shape(mixed, "statements[0]")

    def assert_shape(self, doc: object, *fields: str) -> None:
        errors = [f.message for f in self.findings(doc) if f.code == "VEX000"]
        self.assertCountEqual([message.split(":")[0] for message in errors], fields)

    def test_product_shapes(self) -> None:
        for bad in (None, 3, "sai", {}):
            self.assert_shape({**GOOD, "statements": [{**STMT, "products": bad}]}, "statements[0].products")
        entries = [None, {"identifiers": [], "hashes": [], "subcomponents": [3, {"hashes": 4}]}]
        self.assert_shape(
            {**GOOD, "statements": [{**STMT, "products": entries}]},
            "statements[0].products[0]",
            *(
                "statements[0].products[1]." + key
                for key in ("identifiers", "hashes", "subcomponents[0]", "subcomponents[1].hashes")
            ),
        )
        self.assertEqual(self.one(products=[{"hashes": {}, "identifiers": {}, "subcomponents": []}]), [])

    def test_vex002_vulnerability_and_products(self) -> None:
        self.assertEqual(self.one(vulnerability={"@id": "https://nvd.nist.gov/vuln/detail/CVE-1"}), [])
        for bad in (None, "CVE-1"):
            self.assert_shape({**GOOD, "statements": [{**STMT, "vulnerability": bad}]}, "statements[0].vulnerability")
        alias = {**STMT, "vulnerability": {"name": "CVE-1", "aliases": ["ALT", 3]}}
        self.assert_shape({**GOOD, "statements": [alias]}, "statements[0].vulnerability.aliases[1]")
        for bad in ({"vulnerability": {}}, {"products": []}):
            self.assertEqual(self.one(**bad), ["VEX002"])
        self.assertEqual(self.run_check({**GOOD, "statements": [{"status": "fixed"}]}), ["VEX002"])

    def test_vex003_status(self) -> None:
        self.assertEqual(self.one(status="sai"), ["VEX003"])
        self.assertEqual(self.one(status=["affected"]), ["VEX003"])
        self.assertEqual(self.one(status=None), ["VEX003"])

    def test_vex004_not_affected(self) -> None:
        self.assertEqual(self.one(justification="tuỳ ý"), ["VEX004"])
        self.assertEqual(self.one(justification=None), ["VEX004"])
        self.assertEqual(self.one(justification=None, impact_statement="Không gọi tới hàm lỗi"), [])
        self.assertEqual(self.one(justification="inline_mitigations_already_exist"), [])

    def test_vex005_affected(self) -> None:
        self.assertEqual(self.one(status="affected", justification=None), ["VEX005"])
        self.assertEqual(self.one(status="affected", action_statement="Nâng lên 1.1"), [])


if __name__ == "__main__":
    unittest.main()
