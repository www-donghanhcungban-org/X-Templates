"""T-5096: phân loại đích ref bằng chuỗi, không gọi Git."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nonet import HOOKS

sys.path.insert(0, str(HOOKS))
import guard


class RefNamespaceTest(unittest.TestCase):
    def test_literal_non_tag_destination_uses_general_policy(self):
        for namespace in ("heads", "notes", "archive"):
            with self.subTest(namespace=namespace):
                ref = f"refs/{namespace}/v0.0.0/status-*"
                self.assertFalse(guard._release_ref_write("update-ref", ref))
                self.assertFalse(guard._release_ref_write("symbolic-ref", ref))
                self.assertFalse(guard._fetch_spec_tag(f"refs/heads/status-*:{ref}"))
                self.assertEqual(guard._push_ref_rule(f"HEAD:{ref}", False), ("", ""))

    def test_primary_branch_policy_still_applies(self):
        refspec = "HEAD:refs/heads/main"
        self.assertEqual(guard._push_ref_rule(refspec, False)[0], "ask")
        self.assertEqual(guard._push_ref_rule(refspec, True)[0], "deny")
