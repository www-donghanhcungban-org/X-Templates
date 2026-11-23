"""T-4014 (D-550): dấu review v2 mang `base` và `scope`; mọi nơi đọc nhận cả v1 lẫn v2; scope chỉ siết điều kiện mang review
sang head mới — không bao giờ nới."""

from __future__ import annotations

import re
import sys
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
import guard
import xt

H1, H2, BASE = "a" * 40, "b" * 40, "c" * 40
SCOPE = "d" * 64
CHANGES = {("a.py", "", "modified", "1" * 40), ("b.py", "", "added", "2" * 40)}


def comment(body: str, at: str = "2026-11-23T10:00:00Z", assoc: str = "OWNER") -> dict:
    return {"body": body, "created_at": at, "updated_at": at, "author_association": assoc, "user": {"login": "boss"}}


class ScopeDigestTest(unittest.TestCase):
    def test_digest_is_order_free_and_sensitive(self):
        a = xt.scope_digest(CHANGES)
        self.assertRegex(a, r"^[0-9a-f]{64}$")
        self.assertEqual(a, xt.scope_digest(set(reversed(sorted(CHANGES)))))
        self.assertNotEqual(a, xt.scope_digest(CHANGES | {("c.py", "", "added", "3" * 40)}))
        self.assertNotEqual(a, xt.scope_digest({("a.py", "", "modified", "9" * 40), *list(CHANGES)[1:]}))
        self.assertEqual(xt.scope_digest(None), "")
        self.assertEqual(xt.scope_digest(set()), "")


class MarkFormatTest(unittest.TestCase):
    def test_v1_when_no_scope_v2_with_scope(self):
        v1 = xt.review_comment_body(H1, True)
        self.assertIn(f"<!-- xt-review v1 head={H1} verdict=clean -->", v1)
        v2 = xt.review_comment_body(H1, True, base=BASE, scope=SCOPE)
        self.assertIn(f"<!-- xt-review v2 head={H1} verdict=clean base={BASE} scope={SCOPE} -->", v2)
        self.assertIn("verdict=debt", xt.review_comment_body(H1, True, debt=["AUD-X-1"], base=BASE, scope=SCOPE))

    def test_scope_without_base_still_valid_and_bad_values_dropped(self):
        body = xt.review_comment_body(H1, True, base="xyz", scope="nope")
        self.assertIn("xt-review v1", body)  # giá trị không hợp lệ: không đăng v2
        self.assertIn("xt-review v2", xt.review_comment_body(H1, True, scope=SCOPE))

    def test_both_versions_parse_to_rows(self):
        rows = xt.published_reviews(
            [
                comment(xt.review_comment_body(H1, True), "2026-11-23T10:00:00Z"),
                comment(xt.review_comment_body(H2, False, base=BASE, scope=SCOPE), "2026-11-23T11:00:00Z"),
            ]
        )
        self.assertEqual([(r["head"], r["clean"]) for r in rows], [(H1, True), (H2, False)])
        self.assertNotIn("scope", rows[0])
        self.assertEqual((rows[1]["scope"], rows[1]["base"]), (SCOPE, BASE))

    def test_malformed_v2_is_not_a_review(self):
        for tail in (f"base={BASE} scope=short", f"base=short scope={SCOPE}", "scope="):
            body = f"<!-- xt-review v2 head={H1} verdict=clean {tail} -->"
            self.assertEqual(xt.published_reviews([comment(body)]), [], tail)
        self.assertEqual(xt.published_reviews([comment(f"<!-- xt-review v3 head={H1} verdict=clean -->")]), [])


class ReadersAcceptBothTest(unittest.TestCase):
    def test_guard_regex_catches_v1_and_v2_handwritten_marks(self):
        for version in ("v1", "v2", "v10"):
            self.assertTrue(
                guard.REVIEW_MARK_RE.search(f"<!-- xt-review {version} head={H1} verdict=clean -->"), version
            )
            self.assertTrue(
                guard.REVIEW_MARK_RE.search(f"<!-- xt-review {version} head=$(git rev-parse HEAD) verdict=clean")
            )
        self.assertIsNone(guard.REVIEW_MARK_RE.search("xt-review v2 head={head}"))  # nhắc dạng dấu: không khớp

    def test_steward_filter_accepts_v1_and_v2(self):
        text = (ROOT / ".github" / "workflows" / "pr-steward.yml").read_text(encoding="utf-8")
        self.assertIsNotNone(re.search(r"contains\(github\.event\.comment\.body, 'xt-review v'\)", text))
        self.assertNotIn("'xt-review v1'", text)


class CarryScopeTest(unittest.TestCase):
    def gate(self, last: dict, head_scope: str = "", chain=(H1,)):
        d = {"head": H2, "lane": "chuẩn", "base_merge_of": list(chain), "head_scope": head_scope}
        return xt.review_gate(d, [last])["state"]

    def test_v1_review_still_carried_through_update_chain(self):
        self.assertEqual(self.gate({"head": H1, "clean": True, "at": "x"}), "ok")

    def test_v2_review_carried_only_when_scope_matches(self):
        mark = {"head": H1, "clean": True, "at": "x", "scope": SCOPE}
        self.assertEqual(self.gate(mark, SCOPE), "ok")
        self.assertEqual(self.gate(mark, "e" * 64), "missing")  # đã đổi phạm vi: rà lại
        self.assertEqual(self.gate(mark, ""), "missing")  # không chứng minh được: chặt

    def test_scope_never_widens(self):
        mark = {"head": H1, "clean": True, "at": "x", "scope": SCOPE}
        self.assertEqual(
            self.gate(mark, SCOPE, chain=()), "missing"
        )  # không có chuỗi cập nhật: scope khớp cũng không đủ
        # review KHÔNG sạch ở head cũ không bao giờ được mang sang, dù scope khớp
        self.assertEqual(self.gate({**mark, "clean": False}, SCOPE), "missing")

    def test_review_at_current_head_ignores_scope(self):
        d = {"head": H1, "lane": "chuẩn", "base_merge_of": [], "head_scope": ""}
        self.assertEqual(xt.review_gate(d, [{"head": H1, "clean": True, "at": "x", "scope": SCOPE}])["state"], "ok")


class MergedCleanScopeTest(unittest.TestCase):
    """Review lô A (🟠): `_merged_clean` (trả nợ review sau merge) phải áp cùng điều kiện scope như `merge-check`."""

    def run_case(self, mark: dict, changes=CHANGES) -> str:
        pull = {"merged": True, "merge_commit_sha": "m" * 40, "head": {"sha": H2}, "base": {"sha": BASE}}
        patches = (
            mock.patch.object(xt, "_gh_one", return_value=pull),
            mock.patch.object(xt, "_published_marks", return_value=[mark]),
            mock.patch.object(xt, "_base_merge_chain", return_value=[H1]),
            mock.patch.object(xt, "_pr_change_set", return_value=changes),
        )
        with patches[0], patches[1], patches[2], patches[3]:
            return xt._merged_clean("o/r", "m" * 40, "feat: x (#12)", "")

    def test_v1_mark_carried_through_update_chain_pays_the_debt(self):
        self.assertEqual(self.run_case({"head": H1, "clean": True, "at": "x"}), "12")

    def test_v2_mark_with_matching_scope_pays_the_debt(self):
        mark = {"head": H1, "clean": True, "at": "x", "scope": xt.scope_digest(CHANGES)}
        self.assertEqual(self.run_case(mark), "12")

    def test_v2_mark_with_changed_scope_does_not(self):
        mark = {"head": H1, "clean": True, "at": "x", "scope": SCOPE}
        self.assertEqual(self.run_case(mark), "")
        self.assertEqual(self.run_case({**mark, "scope": xt.scope_digest(CHANGES)}, changes=None), "")


class PublishScopeTest(unittest.TestCase):
    def test_review_scope_reads_base_and_digest(self):
        calls = []

        def fake_one(path: str):
            calls.append(path)
            return {"base": {"sha": BASE}}

        orig_one, orig_set = xt._gh_one, xt._pr_change_set
        xt._gh_one, xt._pr_change_set = fake_one, lambda repo, base, sha: CHANGES if (base, sha) == (BASE, H1) else None
        try:
            self.assertEqual(xt.review_scope("o/r", "7", H1), (BASE, xt.scope_digest(CHANGES)))
            self.assertEqual(xt.review_scope("o/r", "7", H2), (BASE, ""))
            xt._gh_one = lambda path: (_ for _ in ()).throw(xt.PrInputError("boom"))
            self.assertEqual(xt.review_scope("o/r", "7", H1), ("", ""))
        finally:
            xt._gh_one, xt._pr_change_set = orig_one, orig_set
        self.assertEqual(calls, ["o/r/pulls/7", "o/r/pulls/7"])


if __name__ == "__main__":
    unittest.main()
