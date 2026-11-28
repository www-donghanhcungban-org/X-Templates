import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from xt_checks import CheckError
from xt_checks import kind_design_outcome as outcome


class DesignOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "evidence.json"
        self.policy_path = Path(self.tmp.name) / "policy.json"
        self.doc = {
            "schema": 1,
            "brief": {k: "x" for k in outcome.evidence.BRIEF_FIELDS},
            "options": [{"id": "a", "approach": "x", "tradeoffs": "x"}, {"id": "b", "approach": "x", "tradeoffs": "x"}],
            "decision": {"selected": "a", "reason": "x"},
            "trial": {
                "status": "tested",
                "participants": [
                    {"id": "a", "completed": True, "duration_seconds": 5, "errors": 0, "help_count": 0},
                    {"id": "b", "completed": False, "duration_seconds": 10, "errors": 2, "help_count": 1},
                ],
                "summary": {"participants": 2, "completed": 1},
            },
        }
        self.policy = {
            "schema": 1,
            "kind": "design-outcome-policy",
            "policy_id": "p",
            "revision": "a" * 40,
            "evidence_sha256": "",
            "observed_at": "2026-11-28T14:00:00Z",
            "max_age_seconds": 3600,
            "participant_ids": ["a", "b"],
            "required_completed_ids": ["a"],
            "min_completion_rate": 0.5,
            "min_unassisted_rate": 0.5,
            "max_error_rate": 0.5,
            "max_p95_duration_seconds": 10,
        }
        self.opts = {"policy": str(self.policy_path), "revision": "a" * 40, "at": "2026-11-28T15:00:00Z"}

    def run_check(self, pin=True):
        text = json.dumps(self.doc, ensure_ascii=False)
        self.path.write_text(text, encoding="utf-8")
        if pin:
            self.policy["evidence_sha256"] = hashlib.sha256(text.encode()).hexdigest()
        self.policy_path.write_text(json.dumps(self.policy), encoding="utf-8")
        return outcome.check_report([self.path], self.opts)

    def test_boundary_success(self):
        result = self.run_check()
        self.assertFalse(result.findings)
        self.assertEqual(
            result.checked,
            {"files": 1, "participants": 2, "completed": 1, "unassisted": 1, "errors": 1, "quality_gates": 1},
        )

    def test_quality_failures(self):
        changes = [
            lambda: self.policy.update(participant_ids=["a", "c"]),
            lambda: self.policy.update(required_completed_ids=["b"]),
            lambda: self.policy.update(revision="b" * 40),
            lambda: self.policy.update(max_age_seconds=3599),
            lambda: self.policy.update(observed_at="2026-11-28T15:00:01Z"),
            lambda: self.policy.update(min_completion_rate=0.6),
            lambda: self.policy.update(min_unassisted_rate=0.6),
            lambda: self.policy.update(max_error_rate=0.4),
            lambda: self.policy.update(max_p95_duration_seconds=9),
        ]
        original = copy.deepcopy(self.policy)
        for change in changes:
            with self.subTest(change=change):
                self.policy = copy.deepcopy(original)
                change()
                self.assertIn("DSO001", [f.code for f in self.run_check().findings])
        self.policy = copy.deepcopy(original)
        self.run_check()
        self.doc["brief"]["task"] = "đổi"
        self.assertIn("DSO001", [f.code for f in self.run_check(pin=False).findings])

    def test_structural_failures(self):
        cases = [
            lambda: self.doc.update(source="x"),
            lambda: self.doc["trial"]["summary"].update(completed=2),
            lambda: self.doc["trial"]["participants"][0].update(help_count=-1),
            lambda: self.doc["trial"]["participants"][0].update(id="b"),
            lambda: self.policy.update(participant_ids=[]),
            lambda: self.policy.update(required_completed_ids=["c"]),
            lambda: self.policy.update(min_completion_rate=True),
            lambda: self.policy.update(max_p95_duration_seconds=0),
            lambda: self.policy.update(extra=1),
        ]
        doc, policy = copy.deepcopy(self.doc), copy.deepcopy(self.policy)
        for change in cases:
            with self.subTest(change=change):
                self.doc, self.policy = copy.deepcopy(doc), copy.deepcopy(policy)
                change()
                self.assertIn("DSO000", [f.code for f in self.run_check().findings])

    def test_invocation_and_invalid_json(self):
        with self.assertRaises(CheckError):
            outcome.check_report([], self.opts)
        with self.assertRaises(CheckError):
            outcome.check_report([self.path], {**self.opts, "at": "bad"})
        self.run_check()
        self.policy_path.write_text('{"a":1,"a":2}')
        self.assertEqual(outcome.check([self.path], self.opts)[0].code, "DSO000")
        self.policy_path.write_text('{"a":NaN}')
        self.assertEqual(outcome.check([self.path], self.opts)[0].code, "DSO000")

    def test_invalid_values_and_limits(self):
        invalid = [
            dict(schema=True),
            dict(kind="bad"),
            dict(policy_id=" "),
            dict(revision="A" * 40),
            dict(evidence_sha256="bad"),
            dict(observed_at="2026-02-30T00:00:00Z"),
            dict(max_age_seconds=0),
            dict(participant_ids=["a", "a"]),
            dict(participant_ids=[""]),
            dict(participant_ids=[None]),
            dict(participant_ids=None),
            dict(min_completion_rate=None),
        ]
        original = copy.deepcopy(self.policy)
        for change in invalid:
            with self.subTest(change=change):
                self.policy = copy.deepcopy(original)
                self.policy.update(change)
                self.assertIn("DSO000", [f.code for f in self.run_check(pin="evidence_sha256" not in change).findings])
        self.assertFalse(outcome._number(10**1000, 0, 1))
        self.assertIsNone(outcome._date("2026-99-01T00:00:00Z"))
        self.assertIsNone(outcome._json(self.path.with_name("missing")))
        self.path.write_text("[]")
        self.assertIsNone(outcome._json(self.path))
        with patch.object(outcome, "LIMIT", 1):
            self.policy = copy.deepcopy(original)
            self.assertIn("DSO000", [f.code for f in self.run_check().findings])

    def test_invalid_shapes_and_status(self):
        doc = copy.deepcopy(self.doc)
        variants = [
            dict(options=None),
            dict(options=[None]),
            dict(trial=None),
            dict(brief=None),
            dict(trial={"status": "tested", "participants": [None], "summary": None}),
            dict(trial={"status": "not_tested", "reason": "x", "next_step": "x"}),
        ]
        for change in variants:
            with self.subTest(change=change):
                self.doc = copy.deepcopy(doc)
                self.doc.update(change)
                self.assertIn("DSO000", [f.code for f in self.run_check().findings])
        with self.assertRaises(CheckError):
            outcome.check_report([self.path], {**self.opts, "revision": "bad"})
        with self.assertRaises(CheckError):
            outcome.check_report([self.path], {})
