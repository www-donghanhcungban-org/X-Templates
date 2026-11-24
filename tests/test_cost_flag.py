"""SPEC-slice-ledger §2.3: `loop record --cost` và `pr reviewed --cost` ghi sự kiện `cost` vào sổ lát; số đo đọc lại bằng
`xt_flow.cost_per_slice` (mỗi `cost_id` một lần, thiếu giá thì `unpriced`, sai đối số thì dừng trước khi chạy gì)."""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import xt
import xt_flow
from test_merge import run_main

PLAN = "# PLAN\n\n### Lát A\n- [ ] `T-0010` Đầu lát A — Gate: `true`\n"
HEAD = "c" * 40


class ParseCostTest(unittest.TestCase):
    def test_usd_and_priced_tokens(self):
        self.assertEqual(xt.parse_cost("id=a.1,usd=0.25"), ("a.1", {"usd": 0.25}))
        spec = "id=x,in=27518,out=1200,price_in=0.1,price_out=0.5,source=bảng giá,as_of=2026-11-24"
        self.assertEqual(
            xt.parse_cost(spec),
            (
                "x",
                {
                    "tokens": {"in": 27518, "out": 1200},
                    "price": {
                        "usd_per_mtok_in": 0.1,
                        "usd_per_mtok_out": 0.5,
                        "source": "bảng giá",
                        "as_of": "2026-11-24",
                    },
                },
            ),
        )

    def test_tokens_without_price_are_kept_unpriced(self):
        cid, data = xt.parse_cost("id=t,in=10,out=2")
        self.assertEqual((cid, data), ("t", {"tokens": {"in": 10, "out": 2}}))
        self.assertEqual(
            xt_flow.cost_per_slice([{"kind": "cost", "ref": cid, "slice": "P/T-1", "data": data}]), (None, "unpriced")
        )

    def test_rejects_bad_specs(self):
        for bad in (
            "",
            "usd=1",
            "id=,usd=1",
            "id=a b,usd=1",
            "id=a,usd=1,usd=2",
            "id=a,cost=1",
            "id=a,usd",
            "id=a,usd=",
            "id=a,usd=-1",
            "id=a,usd=abc",
            "id=a,usd=inf",
            "id=a,usd=1,in=2",
            "id=a,in=1",
            "id=a,out=1",
            "id=a,in=1,out=1,as_of=24/11/2026",
            "id=a,in=1,out=1,price_in=x",
        ):
            with self.subTest(spec=bad), self.assertRaises(ValueError):
                xt.parse_cost(bad)

    def test_cost_arg_reports_before_anything_runs(self):
        self.assertEqual(xt._cost_arg(argparse.Namespace()), (None, 0))
        self.assertEqual(xt._cost_arg(argparse.Namespace(cost=None)), (None, 0))
        self.assertEqual(xt._cost_arg(argparse.Namespace(cost="id=a,usd=1")), (("a", {"usd": 1}), 0))
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(xt._cost_arg(argparse.Namespace(cost="usd=1")), (None, 2))
        self.assertIn("--cost", err.getvalue())


class WriteCostTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.enterContext(unittest.mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.base)}))
        self.plan = self.base / "docs" / "autopilot" / "PLAN-x.md"
        self.plan.parent.mkdir(parents=True)
        self.plan.write_text(PLAN, encoding="utf-8")

    def rows(self, slice_id: str = "PLAN-x/T-0010") -> list[dict]:
        path = xt.state_dir(self.base) / xt.SLICES_SUBDIR / f"{slice_id.replace('/', '__')}.jsonl"
        return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []

    def test_pr_reviewed_records_cost_once_per_id(self):
        argv = ("pr", "reviewed", "--pr", "9", "--head", HEAD, "--clean", "--no-publish", "--slice", "PLAN-x/T-0010")
        argv += ("--reviewer-model", "claude-opus-5-5", "--author-model", "claude-sonnet-5-5")
        self.assertEqual(run_main(*argv, "--cost", "id=rev-9,usd=0.4")[0], 0)
        self.assertEqual(run_main(*argv, "--cost", "id=rev-9,usd=0.4")[0], 0)  # thử lại: cùng cost_id
        costs = [r for r in self.rows() if r["kind"] == "cost"]
        self.assertEqual([(r["ref"], r["data"], r["source"]) for r in costs][0], ("rev-9", {"usd": 0.4}, "pr reviewed"))
        self.assertEqual(xt_flow.cost_per_slice(costs), ({"PLAN-x/T-0010": 0.4}, ""))  # mỗi cost_id một lần

    def test_bad_cost_stops_pr_reviewed_before_writing(self):
        rc, _, err = run_main(
            "pr",
            "reviewed",
            "--pr",
            "9",
            "--head",
            HEAD,
            "--blocking",
            "--no-publish",
            "--slice",
            "PLAN-x/T-0010",
            "--cost",
            "usd=1",
        )
        self.assertEqual(rc, 2)
        self.assertIn("--cost", err)
        self.assertEqual(self.rows(), [])

    def test_no_slice_warns_but_does_not_fail(self):
        rc, _, err = run_main(
            "pr", "reviewed", "--pr", "9", "--head", HEAD, "--blocking", "--no-publish", "--cost", "id=n,usd=1"
        )
        self.assertEqual(rc, 0)
        self.assertIn("không ghi được chi phí n", err)

    def test_loop_record_cost_goes_to_the_task_slice_on_green_only(self):
        xt.write_state({"active": True, "plan": "docs/autopilot/PLAN-x.md"}, self.base)
        spec = "id=hk-1,in=27518,out=900,price_in=0.1,price_out=0.5,source=bảng giá,as_of=2026-11-24"
        rc = run_main("loop", "record", "--task", "T-0010", "--cost", spec, "--", "true")[0]
        self.assertEqual(rc, 0)
        (row,) = [r for r in self.rows() if r["kind"] == "cost"]
        self.assertEqual((row["ref"], row["source"]), ("hk-1", "loop record"))
        usd = xt_flow.cost_per_slice([row])[0]
        self.assertAlmostEqual(
            usd["PLAN-x/T-0010"], (27518 * 0.1 + 900 * 0.5) / 1_000_000, places=6
        )  # số đo làm tròn 6 chữ số
        self.assertNotEqual(
            run_main("loop", "record", "--task", "T-0010", "--cost", "id=red,usd=9", "--", "false")[0], 0
        )
        self.assertEqual([r["ref"] for r in self.rows() if r["kind"] == "cost"], ["hk-1"])  # lần đỏ không ghi

    def test_loop_record_bad_cost_runs_nothing(self):
        xt.write_state({"active": True, "plan": "docs/autopilot/PLAN-x.md"}, self.base)
        rc, _, err = run_main("loop", "record", "--task", "T-0010", "--cost", "id=a,usd=-1", "--", "true")
        self.assertEqual(rc, 2)
        self.assertIn("--cost", err)
        self.assertFalse((xt.state_dir(self.base) / "evidence" / "T-0010.json").exists())

    def test_loop_record_without_plan_warns(self):
        rc, _, err = run_main("loop", "record", "--task", "T-0010", "--cost", "id=p,usd=1", "--", "true")
        self.assertEqual(rc, 0)
        self.assertIn("không ghi được chi phí p", err)


if __name__ == "__main__":
    unittest.main()
