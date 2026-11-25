"""Loại `sbom` của `static-check` (ADR-0099): fixture CycloneDX tốt/xấu trong thư mục tạm."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import xt_checks
from xt_checks import CheckError, kind_sbom

GOOD_COMP = {
    "name": "lib",
    "version": "1.0",
    "purl": "pkg:pypi/lib@1.0",
    "hashes": [{"alg": "SHA-256", "content": "ab"}],
    "licenses": [{"license": {"id": "MIT"}}],
}
GOOD = {
    "bomFormat": "CycloneDX",
    "specVersion": "1.7",
    "metadata": {
        "timestamp": "2026-11-24T00:00:00Z",
        "tools": {"components": [{"name": "syft"}]},
        "component": {"name": "app"},
    },
    "components": [GOOD_COMP],
    "dependencies": [{"ref": "app", "dependsOn": ["lib"]}],
}


class SbomTest(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def findings(self, doc: object, **opts: str) -> list[xt_checks.Finding]:
        path = self.base / "sbom.json"
        path.write_text(doc if isinstance(doc, str) else json.dumps(doc), encoding="utf-8")
        return kind_sbom.check([path], opts)

    def run_check(self, doc: object, **opts: str) -> list[str]:
        return [f.code for f in self.findings(doc, **opts)]

    def bom(self, **over: object) -> dict[str, object]:
        return {**GOOD, **over}

    def test_good_is_clean(self) -> None:
        self.assertEqual(self.run_check(GOOD, hashes="require"), [])

    def test_interface(self) -> None:
        self.assertTrue(kind_sbom.HELP)
        self.assertEqual(kind_sbom.SUFFIXES, (".json",))

    def test_sbm000_invalid(self) -> None:
        for doc in ("không phải json", "[]", '{"bomFormat": "SPDX"}', "{}"):
            with self.subTest(doc=doc):
                self.assertEqual(self.run_check(doc), ["SBM000"])

    def test_sbm000_unreadable_and_recursion(self) -> None:
        path = self.base / "bad.json"
        path.write_bytes(b"\xff\xfe")
        self.assertEqual([f.code for f in kind_sbom.check([path], {})], ["SBM000"])
        with unittest.mock.patch.object(kind_sbom.json, "loads", side_effect=RecursionError):
            self.assertEqual(self.run_check(GOOD), ["SBM000"])

    def test_sbm001_metadata(self) -> None:
        self.assertEqual(self.run_check(self.bom(metadata={"timestamp": "x"})), ["SBM001"])
        self.assert_shape(self.bom(metadata="sai"), "metadata")
        self.run_check(self.bom(metadata={}))
        found = kind_sbom.check([self.base / "sbom.json"], {})[0]
        self.assertIn("tools", found.message)
        self.assertEqual(found.line, 0)

    def test_sbm002_and_003(self) -> None:
        self.assertEqual(self.run_check(self.bom(components=[{**GOOD_COMP, "version": ""}])), ["SBM002"])
        codes = self.run_check(self.bom(components=[{"licenses": GOOD_COMP["licenses"], "bom-ref": "r"}]))
        self.assertEqual(sorted(codes), ["SBM002", "SBM003"])
        self.assertEqual(self.run_check(self.bom(components=[{**GOOD_COMP, "purl": None, "swid": {"tagId": "t"}}])), [])
        self.assertEqual(self.run_check(self.bom(components=[{**GOOD_COMP, "purl": None, "cpe": "cpe:2.3:a"}])), [])

    def test_nested_and_non_dict_components(self) -> None:
        nested = {**GOOD_COMP, "components": [{**GOOD_COMP, "purl": ""}, "rác"]}
        codes = self.run_check(self.bom(components=[nested, 5]))
        self.assertCountEqual(codes, ["SBM000", "SBM000", "SBM003"])
        self.assert_shape(self.bom(components=[nested, 5]), "components[0].components[1]", "components[1]")

    def assert_shape(self, doc: object, *fields: str) -> None:
        errors = [f.message for f in self.findings(doc) if f.code == "SBM000"]
        self.assertCountEqual([message.split(":")[0] for message in errors], fields)

    def test_malformed_containers(self) -> None:
        for bad in ("sai", 3, None, {}):
            with self.subTest(bad=bad):
                self.assert_shape(self.bom(components=bad), "components")
                self.assert_shape(self.bom(dependencies=bad), "dependencies")
                self.assert_shape(self.bom(components=[{**GOOD_COMP, "components": bad}]), "components[0].components")
        self.assert_shape(
            self.bom(dependencies=[None, {"dependsOn": ["ref", 3], "provides": {}}]),
            "dependencies[0]",
            "dependencies[1].dependsOn[1]",
            "dependencies[1].provides",
        )
        self.assert_shape(
            self.bom(components=[{**GOOD_COMP, "licenses": "MIT", "hashes": [3]}]),
            "components[0].licenses",
            "components[0].hashes[0]",
        )
        self.assert_shape(self.bom(components=[{**GOOD_COMP, "swid": []}]), "components[0].swid")

    def test_metadata_tools_shapes(self) -> None:
        meta = GOOD["metadata"]
        for tools in ([{"name": "syft"}], {"services": [{"name": "syft"}]}):
            self.assertEqual(self.run_check(self.bom(metadata={**meta, "tools": tools})), [])
        for tools, field in ((3, "tools"), ([False], "tools[0]"), ({"services": None}, "tools.services")):
            self.assert_shape(self.bom(metadata={**meta, "tools": tools}), f"metadata.{field}")
        self.assert_shape(self.bom(metadata={**meta, "component": "sai"}), "metadata.component")
        root = {"components": [{"licenses": [{"license": "MIT"}, {"expression": "MIT"}]}]}
        self.assert_shape(
            self.bom(metadata={**meta, "component": root}), "metadata.component.components[0].licenses[0].license"
        )
        self.assertEqual(self.run_check({k: v for k, v in GOOD.items() if k != "components"}), [])

    def test_sbm004_only_when_required(self) -> None:
        comp = {**GOOD_COMP, "hashes": []}
        self.assertEqual(self.run_check(self.bom(components=[comp])), [])
        self.assertEqual(self.run_check(self.bom(components=[comp]), hashes="require"), ["SBM004"])

    def test_sbm005_license_ratio(self) -> None:
        bare = {**GOOD_COMP, "licenses": []}
        comps = [GOOD_COMP, bare]
        self.assertEqual(self.run_check(self.bom(components=comps)), ["SBM005"])
        self.assertEqual(self.run_check(self.bom(components=comps), license_ratio="0.5"), [])
        self.assertEqual(self.run_check(self.bom(components=[GOOD_COMP] * 100)), [])

    def test_bad_opts_raise(self) -> None:
        for ratio in ("abc", "", "1.5", "-0.1", "nan", "inf"):
            with self.subTest(ratio=ratio), self.assertRaises(CheckError):
                self.run_check(GOOD, license_ratio=ratio)
        for mode in ("yes", "", "Require"):
            with self.subTest(mode=mode), self.assertRaises(CheckError):
                self.run_check(GOOD, hashes=mode)
        self.assertEqual(self.run_check(GOOD, hashes="ignore", license_ratio="1"), [])
        self.assertEqual(self.run_check(GOOD, license_ratio="0"), [])

    def test_sniff_and_opts(self) -> None:
        self.assertEqual(kind_sbom.OPTS, ("hashes", "license_ratio"))
        self.assertTrue(kind_sbom.SNIFF(json.dumps(GOOD)))
        self.assertFalse(kind_sbom.SNIFF('{"a": 1}'))

    def test_directory_scan_only_sbom(self) -> None:
        (self.base / "khac.json").write_text('{"a": 1}', encoding="utf-8")
        (self.base / "sbom.json").write_text(json.dumps(GOOD), encoding="utf-8")
        self.assertEqual(xt_checks.run("sbom", [str(self.base)], {}), [])
        found = xt_checks.run("sbom", [str(self.base / "khac.json")], {})
        self.assertEqual([f.code for f in found], ["SBM000"])

    def test_sbm006_ai_bom(self) -> None:
        model = {"type": "machine-learning-model", "name": "m", "purl": "pkg:huggingface/m"}
        codes = self.run_check(self.bom(components=[model, GOOD_COMP]), license_ratio="0.5")
        self.assertEqual(sorted(codes), ["SBM002", "SBM006"])
        full = {**GOOD_COMP, "type": "machine-learning-model"}
        self.assertEqual(self.run_check(self.bom(components=[full])), [])

    def test_sbm007_dependencies(self) -> None:
        self.assertEqual(self.run_check(self.bom(dependencies=[])), ["SBM007"])
        bare = dict(GOOD)
        del bare["dependencies"]
        self.assertEqual(self.run_check(bare), ["SBM007"])

    def test_empty_components_no_ratio_finding(self) -> None:
        self.assertEqual(self.run_check(self.bom(components=[])), [])


if __name__ == "__main__":
    unittest.main()
