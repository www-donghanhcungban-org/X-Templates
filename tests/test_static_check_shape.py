"""T-5002: thay từng container hoặc phần tử mảng trong đầu vào sạch qua API công khai."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
sys.path.insert(0, str(HERE))
import xt_checks
from test_check_design_evidence import GOOD as DESIGN, UNTESTED
from test_check_sbom import GOOD as SBOM, GOOD_COMP
from test_check_trace import S1, doc, span
from test_check_vex import GOOD as VEX, STMT

# Các loại này đọc văn bản hay tên media, kể cả khi phần mở rộng là .json.
TEXT = {
    "ac-trace": ("spec.md", "# Tiêu chí\n"),
    "credits": ("asset.png", ""),
    "llms-txt": ("llms.txt", "# Tài liệu\n> Mô tả\n## Ví dụ\n- [Mẫu](/mau)\n"),
    "motion": ("motion.css", "p { opacity: 1; }"),
    "nfc": ("text.json", "null"),
    "pii-vn": ("sample.json", "null"),
    "tokens": ("main.css", "p { color: var(--color); }"),
}
SAMPLES = ("sai", 3, True, None, [], {})


def nodes(value, path=()):
    """Các container và phần tử mảng trong fixture. Phần tử đầu đại diện cho mảng đồng nhất."""
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            yield from nodes(child, (*path, key))
    elif isinstance(value, list):
        yield path, value
        if value:
            yield from nodes(value[0], (*path, 0))
    elif path and isinstance(path[-1], int):
        yield path, value


def replace(doc, path, value):
    if not path:
        return value
    result = copy.deepcopy(doc)
    target = result
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    return result


class ShapeTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def put(self, name, text):
        path = self.base / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    def codes(self, kind, data, opts=None):
        path = self.put("input.json", json.dumps(data))
        return [f.code for f in xt_checks.run(kind, [path], opts or {})]

    def matrix(self, kind, good, code, *, opts=None, alternatives=None):
        self.assertEqual(self.codes(kind, good, opts), [])
        for path, original in nodes(good):
            allowed = (type(original), *(alternatives or {}).get(path, ()))
            for sample in SAMPLES:
                if type(sample) in allowed:
                    continue
                with self.subTest(kind=kind, path=path, sample=sample):
                    codes = self.codes(kind, replace(good, path, sample), opts)
                    if kind == "trace" and sample is None and path and isinstance(path[-1], str):
                        self.assertEqual(codes, [])  # ProtoJSON: null trên trường = chưa khai
                    else:
                        self.assertIn(code, codes)

    def test_registry(self):
        structured = {"sbom", "vex", "trace", "srm", "i18n", "dedup-leak", "design-evidence"}
        self.assertEqual(set(xt_checks.KINDS), TEXT.keys() | structured)
        for kind in structured:
            self.assertTrue(hasattr(self, "test_" + kind.replace("-", "_")))

    def test_text_inputs(self):
        options = {
            "ac-trace": {"tests": str(self.base)},
            "credits": {"credits": self.put("CREDITS.md", "| asset.png | Tác giả | MIT |\n")},
            "tokens": {"tokens": self.put("tokens.css", ":root { --color: #fff; }")},
        }
        for kind, (name, content) in TEXT.items():
            with self.subTest(kind=kind):
                self.assertEqual(xt_checks.run(kind, [self.put(name, content)], options.get(kind, {})), [])

    def test_sbom(self):
        child = {**GOOD_COMP, "swid": {"tagId": "abc"}}
        comp = {**child, "components": [child]}
        tools = {"components": [child], "services": [{"name": "scanner"}]}
        meta = {**SBOM["metadata"], "component": comp, "tools": tools}
        data = {
            **SBOM,
            "metadata": meta,
            "components": [comp],
            "dependencies": [{"ref": "a", "dependsOn": ["b"], "provides": ["x"]}],
        }
        tools_path = ("metadata", "tools")
        self.matrix("sbom", data, "SBM000", alternatives={tools_path: (list,)})
        old_tools = replace(data, tools_path, [{"name": "scanner"}])
        self.assertEqual(self.codes("sbom", old_tools), [])
        for sample in SAMPLES:
            if not isinstance(sample, dict):
                self.assertIn("SBM000", self.codes("sbom", replace(old_tools, (*tools_path, 0), sample)))
        self.assertEqual(self.codes("sbom", replace(data, ("components",), [])), [])
        self.assertEqual(self.codes("sbom", replace(data, ("dependencies",), [])), ["SBM007"])

    def test_vex(self):
        sub = {"hashes": {}, "identifiers": {}}
        stmt = {
            **STMT,
            "products": [{**sub, "subcomponents": [sub]}],
            "vulnerability": {"name": "CVE-1", "aliases": ["ALT"]},
        }
        data = {**VEX, "statements": [stmt]}
        self.matrix("vex", data, "VEX000")
        self.assertEqual(self.codes("vex", replace(data, ("statements", 0, "products"), [])), ["VEX002"])

    def test_trace(self):
        # Thuộc tính ngoài GenAI hợp lệ và không kích các luật TRC002.
        data = doc(span(S1, attrs=["http.method"]))
        self.matrix("trace", data, "TRC000")
        for path, original in nodes(data):
            if isinstance(original, list):
                self.assertEqual(self.codes("trace", replace(data, path, [])), [])

    def test_i18n(self):
        catalog = {"nav": {"home": "Trang chủ"}}
        opts = {"source": self.put("source.json", json.dumps(catalog))}
        self.assertEqual(self.codes("i18n", catalog, opts), [])
        for value in SAMPLES:
            if not isinstance(value, dict):
                self.assertIn("LOC000", self.codes("i18n", value, opts))
                self.assertIn("LOC001", self.codes("i18n", {"nav": value}, opts))
            if not isinstance(value, str):
                self.assertTrue(self.codes("i18n", {"nav": {"home": value}}, opts))
        self.assertEqual(self.codes("i18n", {}, {"source": self.put("empty.json", "{}")}), [])

    def test_srm(self):
        records = [{"variant": "ab"[i % 2]} for i in range(20)]
        self.assertEqual(self.codes("srm", records), [])
        self.assertEqual(self.codes("srm", {"records": records}), [])
        for sample in SAMPLES:
            if not isinstance(sample, (dict, list)):
                self.assertIn("SRM000", self.codes("srm", sample))
            if not isinstance(sample, list):
                self.assertIn("SRM000", self.codes("srm", {"records": sample}))
            if not isinstance(sample, dict):
                self.assertIn("SRM004", self.codes("srm", {"records": [sample, *records]}))

    def test_design_evidence(self):
        self.matrix("design-evidence", DESIGN, "DES000", opts={"mode": "pilot"})
        self.matrix("design-evidence", UNTESTED, "DES000")
        for path in (("options",), ("trial", "participants")):
            self.assertIn("DES000", self.codes("design-evidence", replace(DESIGN, path, [])))

    def test_dedup_leak(self):
        opts = {"train": "train", "eval": "eval"}
        train = self.put("train.jsonl", '{"text":"train"}')
        for sample in SAMPLES:
            path = self.put("eval.jsonl", json.dumps(sample))
            self.assertEqual(xt_checks.run("dedup-leak", [train, path], opts), [])
            found = xt_checks.run("dedup-leak", [train, path], {**opts, "field": "text"})
            self.assertIn("DDL002", [f.code for f in found])
            self.put("eval.jsonl", json.dumps({"text": sample}))
            self.assertEqual(xt_checks.run("dedup-leak", [train, path], {**opts, "field": "text"}), [])


if __name__ == "__main__":
    unittest.main()
