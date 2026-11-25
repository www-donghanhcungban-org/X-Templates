"""T-5015: fixture thiết kế trong thư mục tạm qua CLI static-check."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_static_check import TmpTest, run_cli
from xt_checks import kind_design_evidence

GOOD = {
    "schema": 1,
    "brief": {
        "primary_user": "Nhân viên lễ tân",
        "task": "Tìm đặt phòng theo mã và mở chi tiết",
        "device": "Điện thoại, màn hình rộng 375 CSS px",
        "long_data": "Mã đặt phòng dài 32 ký tự",
        "empty_data": "Không tìm thấy mã, có thể sửa truy vấn",
        "success_criteria": "Mở đúng chi tiết trong tối đa 30 giây",
    },
    "options": [
        {"id": "A", "approach": "Tìm trên màn hình danh sách", "tradeoffs": "Giữ được ngữ cảnh nhưng cần phần tiêu đề"},
        {"id": "B", "approach": "Tìm trên một màn hình riêng", "tradeoffs": "Thêm một bước nhưng có chỗ cho hướng dẫn"},
    ],
    "decision": {"selected": "A", "reason": "Đi thẳng vào tìm kiếm từ danh sách"},
    "trial": {
        "status": "tested",
        "participants": [
            {"id": "p01", "completed": True, "duration_seconds": 12.5, "errors": 0, "help_count": 0},
            {"id": "p02", "completed": False, "duration_seconds": 30, "errors": 2, "help_count": 1},
        ],
        "summary": {"participants": 2, "completed": 1},
    },
}
UNTESTED = {
    **GOOD,
    "trial": {"status": "not_tested", "reason": "Đang đặt lịch thử", "next_step": "Mời người dùng thử trên điện thoại"},
}
CHECKED = {"files": 1, "briefs": 1, "options": 2, "decisions": 1, "trials": 1, "participants": 2, "summaries": 1}


class DesignEvidenceTest(TmpTest):
    def report(self, data, *args):
        path = self.put("pilot.json", json.dumps(data))
        rc, out, err = run_cli("design-evidence", str(path), "--json", *args)
        self.assertEqual(err, "")
        result = json.loads(out)
        self.assertEqual(result["schema"], 1)
        self.assertEqual(result["kind"], "design-evidence")
        self.assertEqual(rc, bool(result["findings"]))
        return result

    def assert_fields(self, data, *fields, args=()):
        result = self.report(data, *args)
        found = result["findings"]
        self.assertTrue(found)
        self.assertTrue(all(f["code"] == "DES000" and f["line"] == 0 for f in found))
        self.assertCountEqual([f["message"].split(":", 1)[0] for f in found], fields)
        return result["checked"]

    def test_draft_and_pilot_with_measured_results(self):
        for args in ((), ("--opt", "mode=draft"), ("--opt", "mode=pilot")):
            with self.subTest(args=args):
                result = self.report({**GOOD, "source": {"extra": "envelope"}}, *args)
                self.assertEqual(result["findings"], [])
                self.assertEqual(result["checked"], CHECKED)
        first = self.put("measured.json", json.dumps(GOOD))
        second = self.put("draft.json", json.dumps(UNTESTED))
        rc, out, err = run_cli("design-evidence", str(first), str(second), "--json")
        self.assertEqual((rc, err), (0, ""))
        self.assertEqual(
            json.loads(out)["checked"],
            {**{key: 2 * n for key, n in CHECKED.items()}, "participants": 2, "summaries": 1},
        )
        self.assertEqual(kind_design_evidence.check([first], {}), [])

    def test_untested_draft_and_pilot(self):
        expected = {**CHECKED, "participants": 0, "summaries": 0}
        result = self.report(UNTESTED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["checked"], expected)
        result = self.report(UNTESTED, "--opt", "mode=pilot")
        self.assertEqual([f["code"] for f in result["findings"]], ["DES001"])
        self.assertEqual(result["checked"], expected)
        for bad in ({}, {"reason": None}, {"reason": "Chờ", "next_step": 1}):
            with self.subTest(bad=bad):
                fields = ("trial.reason", "trial.next_step") if not bad.get("reason") else ("trial.next_step",)
                self.assert_fields({**GOOD, "trial": {"status": "not_tested", **bad}}, *fields)
        conflicting = {**UNTESTED["trial"], "participants": [], "summary": None}
        self.assert_fields({**GOOD, "trial": conflicting}, "trial.participants", "trial.summary")

    def test_directory_and_usage(self):
        self.put("package.json", "{}")
        rc, out, err = run_cli("design-evidence", str(self.base), "--json")
        self.assertEqual((rc, err), (0, ""))
        self.assertEqual(json.loads(out)["checked"], dict.fromkeys(CHECKED, 0))
        rc, out, err = run_cli("design-evidence", str(self.base), "--opt", "mode=pilot")
        self.assertEqual((rc, out), (2, ""))
        self.assertIn("ít nhất một tệp", err)
        target = self.put("DESIGN-EVIDENCE.json", "{")
        rc, out, err = run_cli("design-evidence", str(self.base), "--json")
        self.assertEqual((rc, err), (1, ""))
        result = json.loads(out)
        self.assertEqual(result["checked"], {**dict.fromkeys(CHECKED, 0), "files": 1})
        self.assertEqual([(f["path"], f["code"]) for f in result["findings"]], [(str(target), "DES000")])
        for mode in ("", "production", "PILOT"):
            with self.subTest(mode=mode):
                rc, out, err = run_cli("design-evidence", str(target), "--opt", f"mode={mode}")
                self.assertEqual((rc, out), (2, ""))
                self.assertIn("mode nhận draft hoặc pilot", err)

    def test_malformed_documents_are_findings(self):
        for text in (
            b"\xff\xfe",
            "[",
            "[]",
            '{"schema":0,"schema":1}',
            "[" * 5000 + "]" * 5000,
        ):
            with self.subTest(start=text[:30]):
                target = self.put("wrong.json", text)
                rc, out, err = run_cli("design-evidence", str(target), "--json")
                self.assertEqual((rc, err), (1, ""))
                result = json.loads(out)
                self.assertEqual([f["code"] for f in result["findings"]], ["DES000"])
                self.assertEqual(result["checked"], {**dict.fromkeys(CHECKED, 0), "files": 1})

    def test_schema_and_required_brief(self):
        for schema in (None, True, 1.0, "1", 2):
            with self.subTest(schema=schema):
                self.assert_fields({**GOOD, "schema": schema}, "schema")
        data = copy.deepcopy(GOOD)
        del data["brief"]
        self.assertEqual(self.assert_fields({**data, "envelope": {"brief": GOOD["brief"]}}, "brief")["briefs"], 0)
        for field in GOOD["brief"]:
            for invalid in (None, 0, [], " \t\n"):
                with self.subTest(field=field, invalid=invalid):
                    data = {**GOOD, "brief": {**GOOD["brief"], field: invalid}}
                    self.assert_fields(data, f"brief.{field}")
            data = copy.deepcopy(GOOD)
            del data["brief"][field]
            self.assert_fields(data, f"brief.{field}")

    def test_choice_and_option_ids(self):
        first, second = GOOD["options"]
        self.assert_fields({**GOOD, "options": [first]}, "options")
        checked = self.assert_fields({**GOOD, "options": [False, first, second]}, "options[0]")
        self.assertEqual(checked["options"], 2)
        self.assert_fields({**GOOD, "options": [first, {**second, "id": " A "}]}, "options[1].id", "options")
        self.assert_fields(
            {**GOOD, "options": [first, {**second, "id": " ", "approach": None, "tradeoffs": {}}]},
            "options[1].id",
            "options[1].approach",
            "options[1].tradeoffs",
            "options",
        )
        for selected in (None, 3, "C"):
            with self.subTest(selected=selected):
                self.assert_fields(
                    {**GOOD, "decision": {"selected": selected, "reason": " "}}, "decision.selected", "decision.reason"
                )
        result = self.report({**GOOD, "decision": {**GOOD["decision"], "selected": " A "}})
        self.assertEqual(result["findings"], [])

    def test_tested_trial_requires_typed_measurements(self):
        for status in (None, "done", True, []):
            with self.subTest(status=status):
                self.assert_fields({**GOOD, "trial": {**GOOD["trial"], "status": status}}, "trial.status")
        trial = GOOD["trial"]
        self.assert_fields(
            {**GOOD, "trial": {**trial, "participants": [], "summary": {"participants": 0, "completed": 0}}},
            "trial.participants",
            args=("--opt", "mode=pilot"),
        )
        self.assert_fields({**GOOD, "trial": {"status": "tested"}}, "trial.participants", "trial.summary")
        duplicate = copy.deepcopy(GOOD)
        duplicate["trial"]["participants"][1]["id"] = " p01 "
        self.assert_fields(duplicate, "trial.participants[1].id", args=("--opt", "mode=pilot"))
        invalid_values = {
            "id": (None, 17),
            "duration_seconds": (None, "8", True, -1, -0.5, float("inf"), float("nan"), -(10**400)),
            "completed": (None, 1, "true"),
            "errors": (None, False, -1, 0.0, float("inf")),
            "help_count": (None, True, -1, 1.5),
        }
        for field, values in invalid_values.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    data = copy.deepcopy(GOOD)
                    data["trial"]["participants"][0][field] = value
                    self.assert_fields(data, f"trial.participants[0].{field}", args=("--opt", "mode=pilot"))
            data = copy.deepcopy(GOOD)
            del data["trial"]["participants"][0][field]
            self.assert_fields(data, f"trial.participants[0].{field}")
        result = self.report(
            {
                **GOOD,
                "trial": {
                    **trial,
                    "participants": [
                        {**trial["participants"][0], "duration_seconds": 0, "completed": False},
                        trial["participants"][1],
                    ],
                    "summary": {"participants": 2, "completed": 0},
                },
            },
            "--opt",
            "mode=pilot",
        )
        self.assertEqual(result["findings"], [])

    def test_measured_counts_and_summary_are_distinct(self):
        trial = GOOD["trial"]
        for key in ("participants", "completed"):
            for value in (None, -1, 0, False, 1.0, "1"):
                with self.subTest(key=key, value=value):
                    data = {**GOOD, "trial": {**trial, "summary": {**trial["summary"], key: value}}}
                    self.assert_fields(data, f"trial.summary.{key}")
        malformed = {**GOOD, "trial": {**trial, "participants": [None, trial["participants"][1]]}}
        self.assertEqual(self.assert_fields(malformed, "trial.participants[0]")["participants"], 1)
        self.assert_fields({**GOOD, "trial": {**trial, "participants": None}}, "trial.participants")
        checked = self.assert_fields({**GOOD, "trial": {**trial, "summary": None}}, "trial.summary")
        self.assertEqual((checked["participants"], checked["summaries"]), (2, 0))


if __name__ == "__main__":
    unittest.main()
