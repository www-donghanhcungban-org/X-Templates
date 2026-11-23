"""D-526: machine signoffs and human waivers carry distinct, subject-bound evidence."""

import datetime as dt
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_release_signoff as fixture
from test_stage import human_env
from test_xt_cli import run_main

import xt
import xt_scale

ROW20 = "| 20 | BLOCKER (M/L) | Người đã thử | — | real-path | <bản/URL đã thử, ngày> | <tên · ngày — bắt buộc> |"
HEX = "f" * 64


class ScaleSignTest(fixture.SignoffRepo):
    def prepare(self, scale="M", limit="M", row=ROW20):
        self.blueprint(scale)
        conf = self.proj / "xt.yaml"
        conf.write_text(f"release_signoff: agent\nrelease_signoff_scale: {limit}\n")
        self.doc.write_text(
            fixture.GO_DOC.replace("## 4.", row + "\n\n## 4.").replace("## 4.", f"subject: digest {HEX}\n\n## 4.")
        )
        self.git("add", "-A")
        self.git("commit", "-qm", "ứng viên ở nhánh chính")
        self.git("push", "-q", "origin", "main")
        head = self.git("rev-parse", "HEAD").strip()
        self.report = fixture.rc(subject={**fixture.SUBJECT, "head": head, "digest": HEX})
        self.report.update(
            head=head,
            rows=[xt._release_row(key, "PASS", f"{key} verified") for key, _ in xt.RELEASE_RUN_KEYS]
            + [xt._release_row("deploy", "PASS", HEX), xt._release_row("acceptance_lock", "PASS", "A-001, A-002")],
        )

    def sign(self):
        return xt.release_sign(self.proj, "", "kiểm đúng ứng viên", self.report)

    def rejects(self, why):
        original = self.doc.read_bytes()
        with self.assertRaisesRegex(xt.ReleaseSignError, why):
            self.sign()
        self.assertEqual(original, self.doc.read_bytes())

    def test_m_signs_and_binds_simulated_evidence(self):
        self.prepare()
        self.sign()
        doc = self.doc.read_text()
        for value in (
            "MÁY MÔ PHỎNG",
            "chưa có người dùng thật dùng thử",
            HEX,
            "A-001, A-002",
            "rollback PASS",
            "| agent | GO |",
        ):
            self.assertIn(value, doc)
        subject = self.report["subject"]
        result = xt._release_promotion(self.proj, [], [], subject)
        self.assertEqual((result["state"], result["by"], result.get("simulated")), ("approved", ["agent"], True))
        self.doc.write_text(doc.replace("A-001, A-002", "A-999"))
        # agent là người ký (`release_signoff: agent` có hiệu lực): chờ ký không còn gọi là "human" (T-4019)
        pending = xt._release_promotion(self.proj, [], [], subject)
        self.assertEqual((pending["state"], pending["signer"]), ("pending_signoff", "agent"))
        self.assertTrue(xt.promotion_pending(pending["state"]))

    def test_missing_or_waived_operational_evidence_and_partial_ids_refuse(self):
        self.prepare()
        for key in ("deploy", "acceptance_lock", *(key for key, _ in xt.RELEASE_RUN_KEYS)):
            row = next(r for r in self.report["rows"] if r["id"] == key)
            with self.subTest(key=key):
                row["result"] = "N/A"
                self.report["waived"] = {key: {"by": "Người thử"}}
                self.rejects(key)
                row["result"] = "PASS"
        self.report["rows"][-1]["evidence"] = "PASS"
        self.rejects("ID bộ nghiệm thu")

    def test_human_result_never_replaced_including_failure(self):
        self.prepare(row=ROW20.replace("| — |", "| FAIL |"))
        self.rejects("dòng 20 đã có kết quả của người")

    def test_unmerged_head_cannot_sign_and_remote_downgrade_wins(self):
        self.prepare()
        self.git("checkout", "-qb", "feature")
        (self.proj / "thing").write_text("chưa duyệt")
        self.git("add", "-A")
        self.git("commit", "-qm", "chưa merge")
        head = self.git("rev-parse", "HEAD").strip()
        self.report["head"] = self.report["subject"]["head"] = head
        self.rejects("chưa nằm trên nhánh chính")
        self.git("checkout", "-q", "main")
        conf = self.proj / "xt.yaml"
        conf.write_text(conf.read_text().replace("scale: M", "scale: S"))
        self.git("add", "-A")
        self.git("commit", "-qm", "chủ hạ trần")
        self.git("push", "-q", "origin", "main")
        self.git("checkout", "-q", "HEAD~1")
        self.report["head"] = self.report["subject"]["head"] = self.git("rev-parse", "HEAD").strip()
        self.rejects("ở nhánh chính")

    def test_l_closed_when_window_unmeasured(self):
        self.prepare("L", "L")
        self.rejects("đo được escaped trong 14 ngày")

    def test_human_waiver_requires_full_signed_reason_and_valid_subject(self):
        self.prepare()
        day = dt.datetime.now(dt.timezone.utc).date().isoformat()
        missing = [xt._release_row(key, "N/A", "chưa khai") for key in ("perf", "prod_switch")]
        waived = lambda: xt._human_na_waivers(self.proj, missing, self.report["subject"])
        raw = self.doc.read_text()
        for signer, dec, valid in [("agent", "GO", False), ("Human", "NO-GO", False), ("Human", "GO", True)]:
            with self.subTest(signer=signer, dec=dec):
                signature = f"| Miễn perf: thư viện chạy ngoại tuyến | {signer} | {dec} | {day} |"
                self.doc.write_text(xt._sign_insert(raw, signature, ""))
                result = waived()
                self.assertEqual(set(result), {"perf"} if valid else set())
                if valid:
                    self.assertEqual(result["perf"]["reason"], "thư viện chạy ngoại tuyến")
        self.doc.write_text(self.doc.read_text().replace(HEX, "0" * 64))
        self.assertEqual(waived(), {})

    def test_protect_partial_human_entry_hidden_or_duplicate_row(self):
        self.prepare()
        evidence = {r["id"]: r["evidence"] for r in self.report["rows"]}
        for row in (
            ROW20 + "\n" + ROW20,
            "<!--\n" + ROW20 + "\n-->",
            ROW20.replace("<bản/URL đã thử, ngày>", "người đang thử"),
        ):
            with self.subTest(row=row), self.assertRaises(ValueError):
                xt_scale.simulate(row, xt._markdown_shown(row), "M", HEX, evidence, "Agent")

    def test_l_requires_zero_over_fixed_window(self):
        self.prepare("L", "L")
        with mock.patch.object(xt, "_sign_escaped", return_value=[10]):
            self.rejects("#10")
        with mock.patch.object(xt, "_sign_escaped", return_value=[]):
            self.sign()
        self.assertIn("MÁY MÔ PHỎNG L", self.doc.read_text())

    def test_measured_defects_include_audit_and_reverts_not_reverted_revert(self):
        end = dt.datetime(2026, 11, 20, tzinfo=dt.timezone.utc)
        start = end - dt.timedelta(days=14)
        scan = "+| 4 | TEST | Tests | đã quét | " + "a" * 40 + " | 2026-11-19 | ok |"
        audit = "+| AUD-TEST-123 | 🟠 | mở | lỗi do #10 |"
        old = "-| AUD-TEST-125 | 🔴 | mở | do #14 |"
        revert = lambda n, body: dict(
            number=n, updated_at=end.isoformat(), merged_at=end.isoformat(), title='Revert "x"', body=body
        )
        api = {
            "repos/o/r/pulls?state=closed&sort=updated&direction=desc&per_page=100&page=1": [
                revert(13, "Reverts #12"),
                revert(12, "This reverts commit abcdef0."),
            ],
            "repos/o/r/commits/abcdef0/pulls": [{"number": 11}],
            "repos/o/r/pulls/11": {"number": 11, "title": "fix: original", "merged_at": start.isoformat()},
            "repos/o/r/pulls/12": revert(12, "Reverts #11"),
        }
        measure = lambda patch: xt_scale.escaped_window("o/r", api.get, xt.PR_REVERT_RE, patch, start, end)
        self.assertEqual(measure("\n".join((scan, audit, old))), [10, 11])
        self.assertIsNone(measure(audit))
        amended = "-| AUD-TEST-130 | 🟠 | mở | do #88 |\n+| AUD-TEST-130 | 🟠 | đã sửa | do #88 |"
        self.assertEqual(measure(scan + "\n" + amended), [11])
        api["repos/o/r/pulls?state=closed&sort=updated&direction=desc&per_page=100&page=1"] = []
        self.assertEqual(measure(scan), [])

    def test_l_measure_reads_real_remote_history_and_incomplete_github_is_unknown(self):
        self.prepare("L", "L")
        today = dt.datetime.now(dt.timezone.utc).date().isoformat()
        audit = self.proj / xt.RELEASE_SIGN_STATUS
        audit.write_text(
            "| 2 | TEST | Tests | đã quét | " + self.report["head"] + f" | {today} | ok |\n"
            "| AUD-TEST-126 | 🟠 | mở | do #21 |\n"
        )
        self.git("add", "-A")
        self.git("commit", "-qm", "audit đã quét")
        self.git("push", "-q", "origin", "main")
        with mock.patch.object(xt, "github_origin_slug", return_value="o/r"):
            with mock.patch.object(xt, "_gh_api_once", return_value=[[]]) as gets:
                self.assertEqual(xt._sign_escaped(self.proj), [21])
                self.assertEqual(gets.call_args.kwargs["host"], "github.com")
            with mock.patch.object(xt, "_gh_api_once", side_effect=xt.PrInputError("offline")):
                self.assertIsNone(xt._sign_escaped(self.proj))

    def test_invalid_blueprint_scale_or_unchecked_head_refuses(self):
        self.prepare()
        checked = self.report["head"]
        self.report["head"] = "0" * 40
        self.rejects("chưa kiểm đúng HEAD")
        self.report["head"] = checked
        self.blueprint("XL")
        self.rejects("quy mô blueprint không hợp lệ: XL")

    def owner_withdraws_on_origin(self):
        """The owner sets `release_signoff: human` on origin; this checkout's remote-tracking ref stays stale."""
        owner = self.tmp / "owner"
        subprocess.run(["git", "clone", "-q", str(self.origin), str(owner)], check=True)
        (owner / "xt.yaml").write_text("release_signoff: human\nrelease_signoff_scale: M\n")
        for args in (["add", "-A"], ["commit", "-qm", "chủ rút quyền ký"], ["push", "-q", "origin", "main"]):
            subprocess.run(
                ["git", "-c", "user.name=o", "-c", "user.email=o@example.invalid", *args], cwd=owner, check=True
            )

    def test_simulated_promotion_rereads_remote_authority_and_ceiling(self):
        self.prepare()
        self.sign()
        stale = self.git("rev-parse", "origin/main").strip()
        promote = lambda: xt._release_promotion(self.proj, [], [], self.report["subject"])
        agent = lambda: mock.patch.dict(os.environ, {"CLAUDECODE": "1"})
        with human_env():
            self.assertEqual(promote()["state"], "approved")
        with agent():
            self.assertEqual(promote()["state"], "approved")  # an agent fetches origin before trusting the key
        conf = self.proj / "xt.yaml"
        signed = conf.read_text()
        conf.write_text(signed.replace("release_signoff_scale: M", "release_signoff_scale: S"))
        with human_env():
            self.assertEqual(promote()["reasons"], ["quy mô M vượt `release_signoff_scale`"])
        conf.write_text(signed)
        self.blueprint("XL")  # an unknown scale is judged as the largest one
        with human_env():
            self.assertEqual(promote()["reasons"], ["quy mô L vượt `release_signoff_scale`"])
        self.blueprint("M")
        self.owner_withdraws_on_origin()
        with human_env():  # no fetch: the stale ref still says agent, but the fresh mirror of origin does not
            self.assertEqual(promote()["reasons"], ["chưa xác nhận quyền ký ở nhánh chính của remote"])
        with agent():
            self.assertIn("chưa có hiệu lực", promote()["reasons"][0])
        self.assertNotEqual(self.git("rev-parse", "origin/main").strip(), stale)
        self.git("update-ref", "refs/remotes/origin/main", stale)
        self.git("remote", "set-url", "origin", str(self.tmp / "missing.git"))
        with agent():  # origin unreachable: an agent cannot rely on the stale ref
            self.assertIn("chưa có hiệu lực", promote()["reasons"][0])
        with human_env():
            self.assertEqual(promote()["reasons"], ["không đọc được trần ký ở nhánh chính của remote"])

    def test_pr_stats_escaped_uses_listed_prs_and_origin_audit(self):
        self.prepare("L", "L")
        now = dt.datetime.now(dt.timezone.utc)
        (self.proj / xt.RELEASE_SIGN_STATUS).write_text(
            f"| 2 | TEST | Tests | đã quét | {self.report['head']} | {now.date().isoformat()} | ok |\n"
            "| AUD-TEST-126 | 🟠 | mở | do #21 |\n"
        )
        self.git("add", "-A")
        self.git("commit", "-qm", "audit đã quét")
        self.git("push", "-q", "origin", "main")
        at = lambda hours: (now - dt.timedelta(hours=hours)).isoformat()
        revert = {
            "number": 31,
            "title": 'Revert "fix: x"',
            "body": "Reverts #30",
            "created_at": at(2),
            "updated_at": at(0),
            "merged_at": at(1),
            "head": {"ref": "revert-30", "sha": "r" * 40},
            "labels": [],
        }
        original = {"number": 30, "title": "fix: x", "merged_at": at(3)}
        with (
            mock.patch.object(xt, "github_origin_slug", return_value="o/r"),
            mock.patch.object(xt, "_pr_stats_fetch", return_value=([revert], [], False)),
            mock.patch.object(xt, "_gh_api_once", return_value=[original]) as gets,
        ):
            rc, out, err = run_main("pr", "stats", "--escaped", "--json")
            self.assertEqual(rc, 0, err)
            self.assertEqual(
                {k: json.loads(out)[k] for k in ("escaped", "escaped_prs")}, {"escaped": 2, "escaped_prs": [21, 30]}
            )
            gets.assert_called_once_with("repos/o/r/pulls/30", host="github.com")  # the listing was not fetched again
            rc, out, err = run_main("pr", "stats", "--escaped", "--days", "14")
            self.assertEqual(rc, 0, err)
            self.assertIn("Lỗi lọt sau merge (14 ngày): 2", out)
            rc, out, err = run_main("pr", "stats", "--escaped", "--repo", "other/r")
            self.assertEqual(rc, 0, err)
            self.assertIn("ngày): chưa đo được", out)  # another repository's PRs never measure this origin

    def test_remote_human_result_written_after_candidate_is_preserved(self):
        self.prepare()
        self.doc.write_text(self.doc.read_text().replace("| — |", "| FAIL |"))
        self.git("add", "-A")
        self.git("commit", "-qm", "người thử vừa ghi FAIL")
        self.git("push", "-q", "origin", "main")
        self.git("checkout", "-q", "HEAD~1")
        self.rejects("GO-NO-GO đã đổi trên nhánh chính")


class ScaleEvidenceTest(unittest.TestCase):
    """Pure xt_scale rules: a bound simulation row and a complete, verifiable fourteen-day GitHub window."""

    END = dt.datetime(2026, 11, 20, tzinfo=dt.timezone.utc)
    START = END - dt.timedelta(days=14)
    SCAN = "+| 4 | TEST | Tests | đã quét | " + "a" * 40 + " | 2026-11-19 | ok |"
    PAGE = "repos/o/r/pulls?state=closed&sort=updated&direction=desc&per_page=100&page={}"

    def pr(self, n, updated=None, merged=None, title="fix: x", body=""):
        stamp = lambda t: None if t is None else t.isoformat()
        return dict(number=n, title=title, body=body, updated_at=stamp(updated or self.END), merged_at=stamp(merged))

    def measure(self, api, patch=SCAN):
        return xt_scale.escaped_window("o/r", api.get, xt.PR_REVERT_RE, patch, self.START, self.END)

    def test_simulation_signature_binds_scale_and_single_visible_row(self):
        text = ROW20 + "\n"
        role = f"Agent · {xt_scale.SIMULATION} M {xt_scale._digest(ROW20)}"
        self.assertTrue(xt_scale.verify_simulation(text, text, role, "M"))
        self.assertFalse(xt_scale.verify_simulation(text, text, role, "L"))
        self.assertFalse(xt_scale.verify_simulation(text, text, "Agent", "M"))
        self.assertFalse(xt_scale.verify_simulation(text + text, text + text, role, "M"))

    def test_scan_row_needs_iso_date_inside_window(self):
        for day in ("2026-11-19", "19/11/2026", "2026-10-01"):
            with self.subTest(day=day):
                found = xt_scale.audit_window(self.SCAN.replace("2026-11-19", day), self.START, self.END)
                self.assertEqual(found, set() if day == "2026-11-19" else None)

    def test_unresolvable_revert_origin_refuses(self):
        revert = lambda body: self.pr(13, merged=self.END, title='Revert "x"', body=body)
        for body, extra, why in (
            ("This reverts commit abcdef0.", {"repos/o/r/commits/abcdef0/pulls": []}, "commit revert"),
            ("This reverts commit abcdef0.", {"repos/o/r/commits/abcdef0/pulls": [{}, {}]}, "commit revert"),
            ("hoàn tác thay đổi", {}, "chưa chỉ rõ"),
            ("Reverts #12", {"repos/o/r/pulls/12": self.pr(12)}, "PR gốc"),
            ("Reverts #12", {"repos/o/r/pulls/12": {**self.pr(12, merged=self.END), "number": 99}}, "PR gốc"),
        ):
            with self.subTest(body=body, extra=extra), self.assertRaisesRegex(ValueError, why):
                self.measure({self.PAGE.format(1): [revert(body)], **extra})

    def test_listing_must_be_complete_and_well_formed(self):
        for listing, why in (
            (None, "trang GitHub"),
            ([self.pr(n) for n in range(101)], "trang GitHub"),
            ([{"number": 1}], "thiếu trường"),
        ):
            with self.subTest(why=why, size=len(listing or ())), self.assertRaisesRegex(ValueError, why):
                self.measure({self.PAGE.format(1): listing})
        full = [self.pr(n) for n in range(100)]
        with self.assertRaisesRegex(ValueError, "phân trang"):
            self.measure({self.PAGE.format(p): full for p in range(1, 51)})

    def test_pages_until_older_update_and_counts_only_merged_reverts_in_window(self):
        before = self.START - dt.timedelta(days=1)
        page1 = [self.pr(n) for n in range(200, 299)]  # closed without merge
        page1.append(self.pr(13, merged=before, title='Revert "x"', body="Reverts #11"))  # merged before the window
        page2 = [
            self.pr(14, merged=self.END, title="fix: ordinary"),
            self.pr(15, merged=self.END, title='Revert "y"', body="Reverts #12"),
            self.pr(16, updated=before, merged=self.END, title='Revert "z"', body="Reverts #10"),
        ]
        api = {
            self.PAGE.format(1): page1,
            self.PAGE.format(2): page2,
            "repos/o/r/pulls/12": self.pr(12, merged=self.START),
        }
        self.assertEqual(self.measure(api), [12])
