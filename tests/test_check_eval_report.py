"""Contract tests for synthetic evaluation reports and independent policy."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cpu_budget import assert_not_quadratic
from xt_checks import CheckError, MAX_BYTES, kind_eval_report
from xt_checks.kind_eval_report import check_report, evaluate, read_payload

FIXTURES = Path(__file__).parent / "fixtures" / "evaluation"
REVISION = "a" * 40
AT = "2026-11-28T15:00:00Z"


class EvalReportTests(unittest.TestCase):
    def setUp(self):
        self.report = read_payload(FIXTURES / "report.json")
        self.policy = read_payload(FIXTURES / "policy.json")

    def gate(self):
        return evaluate(self.report, self.policy, REVISION, AT)

    def assert_code(self, expected):
        self.assertEqual(self.gate()[0][0][0], expected)

    def test_malformed_calendar_and_json_fail(self):
        self.report["timestamp"] = "2026-02-30T15:00:00Z"
        self.assert_code("EVR000")
        self.report["timestamp"] = "2026-11-28T15:00:00.0000001Z"
        self.assert_code("EVR000")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{", encoding="utf-8")
            findings = check_report([path], {}).findings
            self.assertEqual([finding.code for finding in findings], ["EVR000"])
            with patch.object(kind_eval_report.json, "loads", side_effect=RecursionError):
                findings = check_report([path], {}).findings
            self.assertIn("lồng quá sâu", findings[0].message)

    def test_control_and_schema_only_failure(self):
        self.assertEqual(kind_eval_report.check([FIXTURES / "report.json"], {}), [])
        issues, counts, validated = self.gate()
        self.assertEqual(issues, [])
        self.assertEqual(counts, {"case_records": 1, "quality_gates": 1, "schema_only": 0})
        self.assertEqual(validated, self.report)
        self.report["cases"][0]["status"] = "fail"
        self.report["counts"].update({"pass": 0, "fail": 1})
        issues, counts, _ = evaluate(self.report)
        self.assertEqual(issues, [])
        self.assertEqual(counts["schema_only"], 1)
        self.policy["min_success_rate"] = 0
        self.assert_code("EVR001")

    def test_critical_manifest_check_scales_without_list_search(self):
        def work(size):
            ids = [f"case-{index}" for index in range(size)]
            first = self.report["cases"][0]
            cases = [dict(first, id=name) for name in ids]
            counts = dict(self.report["counts"], total=size, eligible=size, **{"pass": size})
            policy = dict(
                self.policy,
                case_ids=ids,
                critical_ids=ids,
                clusters=dict.fromkeys(ids, first["cluster"]),
            )
            issues, checked, _ = evaluate(dict(self.report, cases=cases, counts=counts), policy, REVISION, AT)
            self.assertEqual(issues, [])
            self.assertEqual(checked["case_records"], size)

        assert_not_quadratic(self, work, 1250)

    def test_identity_and_freshness_mismatches(self):
        changes = [
            ("revision", "e" * 40),
            ("content_sha256", "e" * 64),
            ("dirty", True),
            ("timestamp", "2026-11-28T15:00:01Z"),
            ("timestamp", "2026-11-28T12:59:59Z"),
        ]
        original = copy.deepcopy(self.report)
        for key, value in changes:
            with self.subTest(key=key, value=value):
                self.report = copy.deepcopy(original)
                self.report[key] = value
                self.assert_code("EVR001")
        for key in ("dataset_sha256", "scorer_sha256", "config_sha256", "environment_sha256"):
            self.report = copy.deepcopy(original)
            self.report["identity"][key] = "e" * 64
            self.assert_code("EVR001")
        self.report = copy.deepcopy(original)
        self.report["runtime"]["version"] = "2"
        self.assert_code("EVR001")

    def test_manifest_cluster_attempts_and_status(self):
        original = copy.deepcopy(self.report)
        for key, value in (("id", "other"), ("attempt", 2), ("cluster", "other")):
            self.report = copy.deepcopy(original)
            self.report["cases"][0][key] = value
            self.assert_code("EVR001")
        for status in ("error", "unscored", "skipped"):
            self.report = copy.deepcopy(original)
            self.report["cases"][0]["status"] = status
            self.report["counts"].update({"pass": 0, status: 1})
            self.policy["critical_ids"] = []
            self.assert_code("EVR001")
        self.report = copy.deepcopy(original)
        self.report["cases"].append(copy.deepcopy(self.report["cases"][0]))
        self.assert_code("EVR000")

    def test_schema_boundaries(self):
        original = copy.deepcopy(self.report)
        for field, value in (
            ("schema", True),
            ("run_id", " "),
            ("revision", "A" * 40),
            ("timestamp", "2026-11-28T14:00:00-00:00"),
            ("claim", []),
        ):
            with self.subTest(field=field):
                self.report = copy.deepcopy(original)
                self.report[field] = value
                self.assert_code("EVR000")
        self.report = copy.deepcopy(original)
        del self.report["cases"][0]["evidence_sha256"]
        self.assert_code("EVR000")
        self.report = copy.deepcopy(original)
        self.report["counts"]["pass"] = True
        self.assert_code("EVR000")
        self.report = copy.deepcopy(original)
        self.report["cases"] = [None] * 100001
        issues, counts, _ = self.gate()
        self.assertEqual(issues[0][0], "EVR000")
        self.assertEqual(counts["case_records"], 0)

    def test_policy_boundaries(self):
        original = copy.deepcopy(self.policy)
        changes = (
            ("case_ids", []),
            ("case_ids", ["one", "one"]),
            ("critical_ids", ["missing"]),
            ("clusters", {}),
            ("attempts_per_case", 0),
            ("attempts_per_case", True),
            ("min_success_rate", float("nan")),
            ("max_infra_rate", 1.01),
            ("max_age_seconds", 0),
            ("allowed_claims", ["asserted-not-measured"]),
            ("allowed_execution_modes", ["bad"]),
            ("cache", []),
        )
        for key, value in changes:
            with self.subTest(key=key, value=value):
                self.policy = copy.deepcopy(original)
                self.policy[key] = value
                self.assert_code("EVR000")

    def test_claim_and_replay(self):
        self.report["claim"] = "real-path"
        self.report["execution"].update(mode="replay", cache="replay")
        self.assert_code("EVR000")
        self.report["claim"] = "faithful-fixture"
        self.policy.update(allowed_claims=["faithful-fixture"], allowed_execution_modes=["replay"], cache="replay")
        self.assertEqual(self.gate()[0], [])
        self.report["execution"]["cache"] = "off"
        self.assert_code("EVR000")

    def test_infra_confirmation_and_zero_eligible(self):
        case = self.report["cases"][0]
        case.update(
            status="infra_failure",
            infra_confirmation={"confirmed": True, "reason": "network", "evidence_sha256": "e" * 64},
        )
        self.report["counts"].update({"pass": 0, "infra_failure": 1, "eligible": 0})
        self.policy.update(
            critical_ids=[],
            min_success_rate=0,
            max_infra_rate=1,
            infra_exclusions=[{"id": "one", "attempt": 1, "reason": "network", "evidence_sha256": "e" * 64}],
        )
        self.assert_code("EVR001")
        case["infra_confirmation"]["confirmed"] = False
        self.assert_code("EVR001")
        del case["infra_confirmation"]
        self.assert_code("EVR000")

    def test_independently_confirmed_infra_and_unused_exclusion(self):
        case = {
            "id": "two",
            "attempt": 1,
            "cluster": "two",
            "status": "infra_failure",
            "evidence_sha256": "d" * 64,
            "infra_confirmation": {"confirmed": True, "reason": "network", "evidence_sha256": "e" * 64},
        }
        self.report["cases"].append(case)
        self.report["counts"].update(total=2, infra_failure=1)
        self.policy["case_ids"].append("two")
        self.policy["clusters"]["two"] = "two"
        self.policy["max_infra_rate"] = 0.5
        self.policy["infra_exclusions"] = [
            {"id": "two", "attempt": 1, "reason": "network", "evidence_sha256": "e" * 64}
        ]
        self.assertEqual(self.gate()[0], [])
        case["infra_confirmation"]["reason"] = "other"
        self.assert_code("EVR001")
        case.update(status="pass")
        del case["infra_confirmation"]
        self.report["counts"].update(total=2, eligible=2, infra_failure=0)
        self.report["counts"]["pass"] = 2
        self.assert_code("EVR001")

    def test_read_and_wrapper(self):
        opts = {"mode": "gate", "policy": str(FIXTURES / "policy.json"), "revision": REVISION, "at": AT}
        self.assertEqual(check_report([FIXTURES / "report.json"], opts).findings, [])
        self.assertEqual(check_report([], {}).findings[0].code, "EVR000")
        for bad in ({"ignore": "x"}, {"mode": "gate"}, {**opts, "revision": "abc"}, {**opts, "at": "bad"}):
            with self.subTest(bad=bad), self.assertRaises(CheckError):
                check_report([FIXTURES / "report.json"], bad)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b"\xef\xbb\xbf{}", b"x" * (MAX_BYTES + 1)):
                path.write_bytes(raw)
                with self.assertRaises(ValueError):
                    read_payload(path)
            path.write_text(json.dumps(self.report), encoding="utf-8")
            link = Path(tmp) / "link.json"
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                read_payload(link)


if __name__ == "__main__":
    unittest.main()
