"""AUD-HAR-569: sổ audit không được ghi AUD-HAR-541 là `đã sửa` khi guard còn cho qua tag phiên bản viết bằng glob.

Bash bung các glob này thành `v1.2.0`; `release-check` và `audit check --strict` coi dòng `đã sửa` là hàng rào đã dựng.
Test đo guard thật bằng quyết định thô của `bash_decision` rồi đối chiếu trạng thái dòng 541 trong sổ.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nonet import HOOKS, isolate_network

sys.path.insert(0, str(HOOKS))
import guard

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "docs" / "ops" / "AUDIT-STATUS.md"
# Dạng glob mà bash bung ra `v1.2.0` (AUD-HAR-541); khi guard chặn hết thì bỏ khỏi danh sách này.
GLOB_TAGS = ("git tag [[=v=]]1.2.0", "git tag ??????+b", "git tag ?*")
CONTROL = ("git tag v1", "git tag [!x]?.?.?")  # tag major di động được qua; dạng đã sửa ở #815/#818 phải bị chặn


def status_of(finding: str) -> str:
    prefix = f"| {finding} |"
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            return line.split("|")[3].strip()
    raise AssertionError(f"{finding} không có trong sổ")


class LedgerTruthTest(unittest.TestCase):
    def setUp(self) -> None:
        isolate_network(self, None, guard)
        self.root = self.enterContext(tempfile.TemporaryDirectory())

    def denied(self, cmd: str) -> bool:
        return guard.apply_policy(guard.bash_decision(cmd, self.root))["decision"] == "deny"

    def test_fixed_glob_forms_stay_denied_and_control_passes(self) -> None:
        self.assertFalse(self.denied(CONTROL[0]))
        self.assertTrue(self.denied(CONTROL[1]))

    def test_har541_is_not_closed_while_a_glob_tag_form_still_passes(self) -> None:
        leaks = [cmd for cmd in GLOB_TAGS if not self.denied(cmd)]
        if leaks:
            self.assertEqual(status_of("AUD-HAR-541"), "mở", f"guard còn cho qua {leaks} mà sổ ghi 541 đã sửa")
        else:
            self.assertEqual(status_of("AUD-HAR-541"), "đã sửa", "guard đã chặn hết dạng glob: đóng dòng 541")


if __name__ == "__main__":
    unittest.main()
