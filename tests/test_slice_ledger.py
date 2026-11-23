"""T-4009 (SPEC-slice-ledger): ghi sổ lát từ lệnh có sẵn và đọc số đo — mỗi số là giá trị hoặc null kèm mã lý do."""

from __future__ import annotations

import datetime as dt
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
import xt
import xt_flow
from test_merge import run_main

PLAN = """# PLAN

- [ ] `T-0001` Việc trước mọi lát — Gate: `true`

### Lát A
- [x] `T-0010` Đầu lát A — Gate: `true`
- [ ] `T-0011` Sau trong lát A — Gate: `true`

### Lát B
Văn xuôi.
- [ ] `T-0020` Đầu lát B — Gate: `true`
"""
NOW = "2026-11-23T00:00:00+00:00"


def ev(kind: str, ref: str, at: str, slice_id: str = "P/T-1", **data) -> dict:
    return {"schema": 1, "slice": slice_id, "kind": kind, "at": at, "source": "test", "ref": ref, "data": data}


def days_ago(n: float) -> str:
    return (dt.datetime(2026, 11, 23, tzinfo=dt.timezone.utc) - dt.timedelta(days=n)).isoformat()


class SliceWriteTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.enterContext(unittest.mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.base)}))
        self.plan = self.base / "docs" / "autopilot" / "PLAN-x.md"
        self.plan.parent.mkdir(parents=True)
        self.plan.write_text(PLAN, encoding="utf-8")

    def lines(self, slice_id: str) -> list[dict]:
        path = xt.state_dir(self.base) / xt.SLICES_SUBDIR / f"{slice_id.replace('/', '__')}.jsonl"
        return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]

    def test_slice_of_uses_first_task_of_heading(self):
        self.assertEqual(xt.slice_of(self.plan, "T-0001"), "PLAN-x/T-0001")
        self.assertEqual(xt.slice_of(self.plan, "T-0010"), "PLAN-x/T-0010")
        self.assertEqual(xt.slice_of(self.plan, "T-0011"), "PLAN-x/T-0010")
        self.assertEqual(xt.slice_of(self.plan, "T-0020"), "PLAN-x/T-0020")
        self.assertEqual(xt.slice_of(self.plan, "T-9999"), "PLAN-x/T-9999")
        self.assertEqual(xt.slice_of(self.base / "missing.md", "T-0011"), "missing/T-0011")

    def test_append_validates_and_never_raises(self):
        self.assertFalse(xt.slice_append(self.base, "PLAN-x/T-0010", "nope", "t", "r", {}))
        self.assertFalse(xt.slice_append(self.base, "../etc/T-1", "cost", "t", "r", {}))
        self.assertTrue(xt.slice_append(self.base, "PLAN-x/T-0010", "cost", "t", "c1", {"usd": 1}))
        self.assertTrue(xt.slice_append(self.base, "PLAN-x/T-0010", "cost", "t", "c2", {"usd": 2}))
        got = self.lines("PLAN-x/T-0010")
        self.assertEqual([x["ref"] for x in got], ["c1", "c2"])
        self.assertEqual((got[0]["schema"], got[0]["kind"], got[0]["slice"]), (1, "cost", "PLAN-x/T-0010"))
        self.assertIsNotNone(xt._deploy_utc(got[0]["at"]))
        blocker = self.base / "other"
        blocker.write_text("x", encoding="utf-8")
        self.assertFalse(xt.slice_append(blocker, "PLAN-x/T-0010", "cost", "t", "c3", {}))

    def test_symlink_at_the_final_component_is_never_followed(self):
        """Review lô C (🟠): `Path.open("a")` đi theo liên kết; `O_NOFOLLOW` như `runs.jsonl`."""
        outside = self.base / "outside.txt"
        outside.write_text("giữ nguyên\n", encoding="utf-8")
        folder = xt.state_dir(self.base) / xt.SLICES_SUBDIR
        folder.mkdir(parents=True)
        os.symlink(outside, folder / "PLAN-x__T-0010.jsonl")
        self.assertFalse(xt.slice_append(self.base, "PLAN-x/T-0010", "cost", "t", "c1", {"usd": 1}))
        self.assertEqual(outside.read_text(encoding="utf-8"), "giữ nguyên\n")

    def test_file_is_private_and_secrets_in_values_keep_the_line_valid_json(self):
        """Review lô C (🟢): `redact()` trên chuỗi JSON đã tuần tự hoá làm hỏng dòng; che từng giá trị trước khi tuần tự hoá."""
        self.assertTrue(
            xt.slice_append(self.base, "PLAN-x/T-0010", "requirement", "t", "r", {"text": "set token=abc123 rồi chạy"})
        )
        (row,) = self.lines("PLAN-x/T-0010")
        self.assertNotIn("abc123", row["data"]["text"])
        self.assertEqual(row["kind"], "requirement")
        path = xt.state_dir(self.base) / xt.SLICES_SUBDIR / "PLAN-x__T-0010.jsonl"
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(len(xt_flow.read_slices(self.base)[0]), 1)  # bộ đọc vẫn nhận dòng

    def test_redact_values_walks_lists_inside_dicts(self):
        out = xt._redact_values({"items": ["token=abc123", {"k": "password=hunter2"}], "n": 3})
        self.assertNotIn("abc123", repr(out))
        self.assertNotIn("hunter2", repr(out))
        self.assertEqual(out["n"], 3)

    def test_task_green_goes_to_task_slice_only_with_plan(self):
        green = {"task": "T-0011", "head": "abc", "cmd_sha256": "d"}
        xt._slice_task_green(self.base, {}, green)
        self.assertFalse((xt.state_dir(self.base) / xt.SLICES_SUBDIR).exists())
        xt._slice_task_green(self.base, {"plan": "docs/autopilot/PLAN-x.md"}, green)
        (row,) = self.lines("PLAN-x/T-0010")
        self.assertEqual((row["kind"], row["ref"], row["data"]["head"]), ("task_green", "T-0011", "abc"))

    def test_current_slice_follows_newest_evidence(self):
        self.assertIsNone(xt.current_slice(self.base))
        xt.write_state({"active": True, "plan": "docs/autopilot/PLAN-x.md"}, self.base)
        self.assertIsNone(xt.current_slice(self.base))
        evidence = xt.state_dir(self.base) / "evidence"
        evidence.mkdir(parents=True)
        (evidence / "T-0020.json").write_text("{}", encoding="utf-8")
        os.utime(evidence / "T-0020.json", (1, 1))
        (evidence / "T-0011.json").write_text("{}", encoding="utf-8")
        self.assertEqual(xt.current_slice(self.base), "PLAN-x/T-0010")

    def test_pr_reviewed_records_reason_and_findings_once(self):
        head = "b" * 40
        argv = ("pr", "reviewed", "--pr", "7", "--head", head, "--blocking", "--no-publish")
        extra = ("--slice", "PLAN-x/T-0010", "--why", "suspect", "--confirmed", "2", "--rejected", "1")
        self.assertEqual(run_main(*argv, *extra)[0], 0)
        self.assertEqual(run_main(*argv, *extra)[0], 0)  # cùng kết quả ở cùng head: không ghi thêm
        (row,) = self.lines("PLAN-x/T-0010")
        self.assertEqual((row["kind"], row["ref"]), ("review", "7"))
        self.assertEqual(row["data"], {"why": "suspect", "confirmed": 2, "rejected": 1, "clean": False})
        self.assertEqual(run_main("pr", "reviewed", "--pr", "8", "--head", head, "--blocking", "--no-publish")[0], 0)
        self.assertFalse(
            (xt.state_dir(self.base) / xt.SLICES_SUBDIR / "PLAN-x__T-0020.jsonl").exists()
        )  # không có lát mặc định


class SliceReadTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.dir = xt.state_dir(self.base) / xt.SLICES_SUBDIR

    def put(self, name: str, *rows) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        text = "".join((r if isinstance(r, str) else json.dumps(r)) + "\n" for r in rows)
        (self.dir / name).write_text(text, encoding="utf-8")

    def test_read_skips_and_counts_bad_lines(self):
        self.assertEqual(xt_flow.read_slices(self.base), ([], 0))
        good = ev("cost", "c1", NOW, usd=1)
        bad = [
            "{not json",
            json.dumps([1]),
            json.dumps({**good, "schema": 2}),
            json.dumps({**good, "kind": "other"}),
            json.dumps({**good, "ref": 3}),
            json.dumps({**good, "data": []}),
            json.dumps({**good, "at": "2026-11-23T00:00:00"}),
        ]
        self.put("a.jsonl", good, "", *bad)
        (self.dir / "broken.jsonl").mkdir()
        events, invalid = xt_flow.read_slices(self.base)
        self.assertEqual((len(events), invalid), (1, len(bad) + 1))

    def test_cost_dedup_price_and_unpriced(self):
        self.assertEqual(xt_flow.cost_per_slice([]), (None, "no_source"))
        price = {"usd_per_mtok_in": 3, "usd_per_mtok_out": 15, "source": "bảng giá", "as_of": "2026-11-23"}
        events = [
            ev("cost", "c1", NOW, usd=1.5),
            ev("cost", "c1", NOW, usd=1.5),  # thử lại cùng cost_id
            ev("cost", "c2", NOW, "P/T-2", tokens={"in": 1_000_000, "out": 100_000}, price=price),
        ]
        self.assertEqual(xt_flow.cost_per_slice(events), ({"P/T-1": 1.5, "P/T-2": 4.5}, ""))
        for broken in (
            {**price, "as_of": ""},
            {**price, "usd_per_mtok_out": -1},
        ):
            with self.subTest(price=broken):
                rows = [ev("cost", "c3", NOW, tokens={"in": 1, "out": 1}, price=broken)]
                self.assertEqual(xt_flow.cost_per_slice(rows), (None, "unpriced"))
        self.assertEqual(xt_flow.cost_per_slice([ev("cost", "c4", NOW, usd=True)]), (None, "unpriced"))

    def test_conflicted_rate(self):
        self.assertEqual(xt_flow.conflicted_rate([]), (None, "no_events"))
        rows = [
            ev("pr", "1", NOW, mergeable="MERGEABLE"),
            ev("pr", "1", NOW, mergeable="CONFLICTING"),
            ev("pr", "1", NOW, mergeable="MERGEABLE"),
            ev("pr", "2", NOW, mergeable="MERGEABLE"),
        ]
        self.assertEqual(xt_flow.conflicted_rate(rows), (0.5, ""))

    def test_escaped_window(self):
        now = xt._deploy_utc(NOW)
        self.assertEqual(xt_flow.escaped([], now), (None, "no_events"))
        self.assertEqual(xt_flow.escaped([ev("merged", "1", days_ago(3))], now), (None, "window_open"))
        rows = [
            ev("merged", "1", days_ago(30)),
            ev("merged", "2", days_ago(3)),
            ev("incident", "pm1.md", days_ago(25), introduced_by="1", severity="sev2"),
            ev("incident", "pm2.md", days_ago(10), introduced_by="1", severity="sev1"),  # 20 ngày sau merge
            ev("incident", "pm3.md", days_ago(29), introduced_by="1"),
            ev("incident", "pm5.md", days_ago(29), introduced_by=["1"]),  # sai kiểu: bỏ qua, không ném
            ev("incident", "pm4.md", days_ago(1), introduced_by="2", severity="sev1"),  # PR 2 chưa đóng cửa sổ
        ]
        doc, why = xt_flow.escaped(rows, now)
        self.assertEqual(doc, {"closed_prs": 1, "open_prs": 1, "by_severity": {"sev2": 1, "unknown": 1}})
        self.assertEqual(why, "window_open")
        doc, why = xt_flow.escaped(rows[:1] + rows[2:3], now)
        self.assertEqual((doc["by_severity"], why), ({"sev2": 1}, ""))

    def test_lead_time_is_wall_clock(self):
        self.assertEqual(xt_flow.lead_time_hours([]), (None, "no_events"))
        rows = [
            ev("requirement", "P/T-1", "2026-11-20T00:00:00+00:00"),
            ev("task_green", "T-1", "2026-11-20T03:00:00+00:00"),
            ev("task_green", "T-2", "2026-11-20T03:00:00+00:00"),  # song song, không cộng
            ev("deployed", "staging", "2026-11-20T02:00:00+00:00"),
            ev("deployed", "production", "2026-11-20T05:00:00+00:00"),
            ev("deployed", "production", "2026-11-20T04:00:00+00:00"),
            ev("deployed", "production", "2026-11-20T01:00:00+00:00", "P/T-9"),  # lát không có yêu cầu
        ]
        self.assertEqual(xt_flow.lead_time_hours(rows), ({"P/T-1": 4.0}, ""))

    def test_slice_metrics_reports_values_and_reasons(self):
        values, cov = xt_flow.slice_metrics(self.base, NOW)
        self.assertEqual(
            values,
            {
                "cost_usd_per_slice": None,
                "ever_conflicted_pr_rate": None,
                "escaped_after_merge": None,
                "lead_time_hours": None,
            },
        )
        self.assertEqual(cov["null_or_partial"]["cost_usd_per_slice"], "no_source")
        self.put("P__T-1.jsonl", ev("cost", "c1", NOW, usd=2), ev("pr", "5", NOW, mergeable="CONFLICTING"), "x")
        values, cov = xt_flow.slice_metrics(self.base, NOW)
        self.assertEqual((values["cost_usd_per_slice"], values["ever_conflicted_pr_rate"]), ({"P/T-1": 2.0}, 1.0))
        self.assertEqual(cov["invalid_lines"], 1)
        self.assertNotIn("cost_usd_per_slice", cov["null_or_partial"])


if __name__ == "__main__":
    unittest.main()
