"""Kiểm policy và giới hạn đọc artefact bằng dữ liệu tổng hợp."""

from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from xt_checks import CheckError, run_report
from xt_checks import kind_eval_evidence as evidence


class EvalEvidenceTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name).resolve()
        self.store = self.root / "evidence"
        self.store.mkdir()
        self.bytes = b"synthetic measurement"
        self.digest = sha256(self.bytes).hexdigest()
        (self.store / self.digest).write_bytes(self.bytes)
        self.report_path = self.root / "report.json"
        self.policy_path = self.root / "policy.json"
        identity = {"suite": "sample", "eval_version": "1-A"}
        for name in ("dataset", "scorer", "config", "environment"):
            identity[f"{name}_sha256"] = self.digest
        common = {
            "schema": 1,
            "identity": identity,
            "content_sha256": self.digest,
            "runtime": {"implementation": "cpython", "version": "3.13", "platform": "linux"},
        }
        self.report = {
            **common,
            "kind": "eval-report",
            "run_id": "example",
            "timestamp": "2026-11-28T00:00:00Z",
            "revision": "a" * 40,
            "dirty": False,
            "claim": "synthetic-fixture",
            "execution": {"mode": "fresh", "cache": "off", "attempts_per_case": 1},
            "cases": [{"id": "a", "attempt": 1, "cluster": "a", "status": "pass", "evidence_sha256": self.digest}],
            "counts": dict(total=1, eligible=1, **{"pass": 1}, fail=0, infra_failure=0, error=0, unscored=0, skipped=0),
        }
        self.policy = {
            **common,
            "kind": "eval-policy",
            "policy_id": "sample",
            "case_ids": ["a"],
            "critical_ids": ["a"],
            "clusters": {"a": "a"},
            "attempts_per_case": 1,
            "min_success_rate": 1,
            "max_infra_rate": 0,
            "max_age_seconds": 3600,
            "allowed_claims": ["synthetic-fixture"],
            "allowed_execution_modes": ["fresh"],
            "cache": "off",
            "infra_exclusions": [],
        }
        self.options = {
            "policy": str(self.policy_path),
            "revision": "a" * 40,
            "at": "2026-11-28T00:01:00Z",
            "artifacts": str(self.store),
        }

    def check(self, **opts):
        self.report_path.write_text(json.dumps(self.report))
        self.policy_path.write_text(json.dumps(self.policy))
        return run_report("eval-evidence", [str(self.report_path)], self.options | opts)

    def test_store_reads_each_digest_once(self):
        result = self.check()
        self.assertEqual(result.findings, [])
        self.assertEqual(evidence.check([self.report_path], self.options), result.findings)
        self.assertEqual(result.checked["report_policy_gates"], 1)
        self.assertEqual(result.checked["quality_gates"], 1)
        self.assertEqual(result.checked["artifacts_expected"], 1)
        self.assertEqual(result.checked["artifacts_verified"], 1)
        self.assertEqual(result.checked["artifact_bytes_read"], len(self.bytes))

    def test_confirmed_infra_records_require_confirmation_bytes(self):
        detail = b"synthetic runner note"
        details = sha256(detail).hexdigest()
        (self.store / details).write_bytes(detail)
        confirmation = {"reason": "fixture timeout", "evidence_sha256": details}
        self.report["cases"].append(
            dict(
                self.report["cases"][0],
                id="b",
                cluster="b",
                status="infra_failure",
                infra_confirmation={"confirmed": True, **confirmation},
            )
        )
        self.report["counts"].update(total=2, infra_failure=1)
        self.policy.update(
            case_ids=["a", "b"],
            clusters={"a": "a", "b": "b"},
            max_infra_rate=0.5,
            infra_exclusions=[{"id": "b", "attempt": 1, **confirmation}],
        )
        result = self.check()
        self.assertEqual(result.findings, [])
        self.assertEqual(result.checked["artifacts_verified"], 2)
        self.assertEqual(result.checked["artifact_bytes_read"], len(self.bytes) + len(detail))

    def test_unreadable_policy_stops_before_checking_blobs(self):
        self.report_path.write_text(json.dumps(self.report))
        self.policy_path.write_text("bad JSON")
        result = evidence.check_report([self.report_path], self.options)
        self.assertEqual([f.code for f in result.findings], ["EVR000"])
        self.assertEqual(result.checked["artifact_bytes_read"], 0)

    def test_different_or_missing_blob_fails_after_policy(self):
        path = self.store / self.digest
        path.write_bytes(b"different")
        mismatch = self.check()
        self.assertEqual([f.code for f in mismatch.findings], ["EVA001"])
        self.assertEqual(mismatch.checked["report_policy_gates"], 1)
        self.assertEqual(mismatch.checked["quality_gates"], 0)
        path.unlink()
        self.assertEqual([f.code for f in self.check().findings], ["EVA000"])
        path.mkdir()
        self.assertEqual([f.code for f in self.check().findings], ["EVA000"])

    def test_caps_stop_at_one_byte_of_lookahead(self):
        for cap in ("MAX_BLOB", "MAX_TOTAL"):
            with self.subTest(cap=cap), patch.object(evidence, cap, 4):
                result = self.check()
            self.assertEqual([f.code for f in result.findings], ["EVA002"])
            self.assertEqual(result.checked["artifact_bytes_read"], 5)
        with patch.object(evidence, "MAX_DIGESTS", 0):
            self.assertEqual([f.code for f in self.check().findings], ["EVA002"])

    def test_bad_policy_and_options(self):
        self.assertEqual([f.code for f in self.check(revision="b" * 40).findings], ["EVR001"])
        self.policy["kind"] = "wrong"
        self.assertEqual([f.code for f in self.check().findings], ["EVR000"])
        for opts in ({"revision": "a"}, {"at": "today"}, {"ignore": "EVA001"}, {"artifacts": ""}):
            with self.subTest(opts=opts), self.assertRaises(CheckError):
                self.check(**opts)

    def test_artifact_directory_is_pinned_and_requires_host_primitives(self):
        alias = self.root / "alias"
        alias.symlink_to(self.store, target_is_directory=True)
        self.assertEqual([f.code for f in self.check(artifacts=str(alias)).findings], ["EVA000"])
        path = self.store / self.digest
        path.unlink()
        original = self.root / "report-copy.txt"
        original.write_bytes(self.bytes)
        path.symlink_to(original)
        self.assertEqual([f.code for f in self.check().findings], ["EVA000"])
        with self.assertRaises(CheckError):
            self.check(artifacts="./evidence")
        with patch.object(os, "supports_dir_fd", set()), self.assertRaises(CheckError):
            self.check()
