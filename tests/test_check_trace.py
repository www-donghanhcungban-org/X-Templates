"""ADR-0099: loại `trace` — trace OTLP của agent (fixture tốt/xấu)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import xt_checks
from xt_checks import kind_trace

T1 = "a" * 32
T2 = "b" * 32
S1, S2, S3 = "1" * 16, "2" * 16, "3" * 16


def span(sid: str, parent: str | None = None, trace: str = T1, attrs: list[str] | None = None, **extra: object) -> dict:
    data: dict = {"traceId": trace, "spanId": sid, "name": "chat"}
    if parent is not None:
        data["parentSpanId"] = parent
    data["attributes"] = [{"key": k, "value": {"stringValue": "x"}} for k in (attrs or [])]
    data.update(extra)
    return data


def doc(*spans: dict) -> dict:
    return {"resourceSpans": [{"scopeSpans": [{"spans": list(spans)}]}]}


GOOD = ["gen_ai.operation.name", "gen_ai.provider.name"]


class TraceTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def run_check(self, text: str | bytes, opts: dict[str, str] | None = None, name: str = "t.json"):
        path = self.base / name
        path.write_bytes(text if isinstance(text, bytes) else text.encode("utf-8"))
        return kind_trace.check([path], opts or {})

    def codes(self, text: str | bytes, opts: dict[str, str] | None = None, name: str = "t.json") -> list[str]:
        return [f.code for f in self.run_check(text, opts, name)]

    def test_interface(self):
        self.assertTrue(kind_trace.HELP)
        self.assertEqual(kind_trace.SUFFIXES, (".json", ".jsonl", ".ndjson"))

    def test_good_trace_is_clean(self):
        d = doc(span(S1, attrs=GOOD), span(S2, S1, attrs=["gen_ai.operation.name", "gen_ai.system"]), span(S3, S1))
        self.assertEqual(self.run_check(json.dumps(d)), [])

    def test_pretty_printed_and_jsonl(self):
        self.assertEqual(self.codes(json.dumps(doc(span(S1)), indent=2)), [])
        lines = json.dumps(doc(span(S1))) + "\n\n" + json.dumps(doc(span(S2, S1))) + "\n"
        self.assertEqual(self.codes(lines, name="t.jsonl"), [])

    def test_jsonl_preserves_unicode_in_string_values(self):
        first = json.dumps(doc(span(S1, name="a\u2028b")), ensure_ascii=False)
        found = self.run_check(first + "\n" + json.dumps(doc(span(S2, S3))), name="t.jsonl")
        self.assertEqual([(f.code, f.line) for f in found], [("TRC001", 2)])

    def test_jsonl_only_lf_separates_documents(self):
        first = json.dumps(doc(span(S1)))
        for char in ("\u2028", "\f"):
            with self.subTest(char=char):
                self.assertEqual(self.codes(first + char + first, name="t.jsonl"), ["TRC000"])

    def test_invalid_inputs_are_trc000(self):
        bad = [
            b"\xff\xfe",
            "",
            "  \n",
            "{khong",
            "[1]",
            "{}",
            '{"resourceSpans": 1}',
            '{"resourceSpans": [1]}',
            '{"resourceSpans": [{"scopeSpans": [{"spans": ["x"]}]}]}',
            '"x"\n{"resourceSpans": []}',
        ]
        for text in bad:
            with self.subTest(text=text):
                self.assertEqual(self.codes(text), ["TRC000"])

    def test_missing_file_content_reported_line_zero(self):
        self.assertEqual(self.run_check(b"\xff")[0].line, 0)

    def test_recursion_error_is_trc000(self):
        with unittest.mock.patch.object(kind_trace.json, "loads", side_effect=RecursionError):
            found = self.run_check("{}")
        self.assertEqual([(f.code, f.line) for f in found], [("TRC000", 1)])
        self.assertIn("quá sâu", found[0].message)

    def test_span_cap(self):
        text = json.dumps(doc(span(S1), span(S2)))
        with unittest.mock.patch.object(kind_trace, "MAX_SPANS", 1):
            found = self.run_check(text)
        self.assertEqual([f.code for f in found], ["TRC000"])
        self.assertIn("quá 1 span", found[0].message)
        with unittest.mock.patch.object(kind_trace, "MAX_SPANS", 2):
            self.assertEqual(self.codes(text), [])

    def test_orphan_and_empty_parent(self):
        self.assertEqual(self.codes(json.dumps(doc(span(S1, S3)))), ["TRC001"])
        self.assertEqual(self.codes(json.dumps(doc(span(S1, "")))), [])
        self.assertEqual(self.codes(json.dumps(doc(span(S1, parentSpanId=5)))), ["TRC001"])

    def test_cross_trace_parent(self):
        d = doc(span(S1, trace=T1), span(S2, S1, trace=T2))
        self.assertEqual(sorted(self.codes(json.dumps(d))), ["TRC001", "TRC003"])

    def test_bad_hex(self):
        for trace, sid in (
            ("a" * 31, S1),
            ("A" * 33, S1),
            ("0" * 32, S1),
            (T1, "G" * 16),
            ("0" * 32, S1),
            (T1, "g" * 16),
            (T1, "0" * 16),
            (5, S1),
        ):
            with self.subTest(trace=trace, sid=sid):
                self.assertEqual(self.codes(json.dumps(doc(span(sid, trace=trace)))), ["TRC004"])

    def test_uppercase_hex_valid_and_case_insensitive_links(self):
        up_trace, up_sid = "ABCDEF" + "0" * 26, "ABCDEF0123456789"
        self.assertEqual(self.codes(json.dumps(doc(span(up_sid, trace=up_trace)))), [])
        child = span(S2, up_sid.lower(), trace=up_trace.lower())
        self.assertEqual(self.codes(json.dumps(doc(span(up_sid, trace=up_trace), child))), [])
        child = span(S2, up_sid, trace=up_trace)
        self.assertEqual(self.codes(json.dumps(doc(span(up_sid.lower(), trace=up_trace.lower()), child))), [])

    def test_sniff_and_opts(self):
        self.assertEqual(kind_trace.OPTS, ("required",))
        self.assertTrue(kind_trace.SNIFF(json.dumps(doc(span(S1)))))
        self.assertFalse(kind_trace.SNIFF('{"a": 1}'))

    def test_directory_scan_only_otlp(self):
        (self.base / "khac.json").write_text('{"a": 1}', encoding="utf-8")
        (self.base / "t.json").write_text(json.dumps(doc(span(S1, S3))), encoding="utf-8")
        found = xt_checks.run("trace", [str(self.base)], {})
        self.assertEqual([(Path(f.path).name, f.code) for f in found], [("t.json", "TRC001")])
        found = xt_checks.run("trace", [str(self.base / "khac.json")], {})
        self.assertEqual([f.code for f in found], ["TRC000"])

    def test_genai_required_defaults(self):
        for attrs in (["gen_ai.operation.name"], ["gen_ai.system"], ["gen_ai.request.model"]):
            with self.subTest(attrs=attrs):
                self.assertEqual(self.codes(json.dumps(doc(span(S1, attrs=attrs)))), ["TRC002"])
        self.assertEqual(self.codes(json.dumps(doc(span(S1, attrs=["http.method"])))), [])
        self.assertEqual(self.codes(json.dumps(doc(span(S1, attrs=["gen_ai.operation.name", "gen_ai.system"])))), [])

    def test_genai_custom_required(self):
        text = json.dumps(doc(span(S1, attrs=["gen_ai.operation.name"])))
        self.assertEqual(self.codes(text, {"required": "gen_ai.operation.name"}), [])
        self.assertEqual(
            self.codes(text, {"required": "gen_ai.operation.name, gen_ai.agent.name|gen_ai.tool.name"}), ["TRC002"]
        )
        self.assertEqual(self.codes(text, {"required": ""}), [])

    def test_attributes_report_shape_and_keep_valid_siblings(self):
        attrs = [1, {"key": 3}, {"key": "gen_ai.operation.name"}, {"key": None, "value": None}]
        text = json.dumps(doc(span(S1))) + "\n" + json.dumps(doc(span(S2, attributes=attrs)))
        found = self.run_check(text)
        self.assertEqual([(f.code, f.line) for f in found], [("TRC000", 2), ("TRC000", 2), ("TRC002", 2)])
        self.assertIn("attributes[1].key", found[1].message)

    def test_jsonl_line_numbers(self):
        text = json.dumps(doc(span(S1))) + "\n\n" + json.dumps(doc(span(S2, S3))) + "\n"
        found = self.run_check(text, name="t.ndjson")
        self.assertEqual([(f.code, f.line) for f in found], [("TRC001", 3)])
        self.assertEqual(self.run_check(json.dumps(doc(span(S2, S3))))[0].line, 1)


if __name__ == "__main__":
    unittest.main()
