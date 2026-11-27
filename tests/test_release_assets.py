"""T-4017 (ADR-0095 §lớp tác động tức thì): `release-tag.yml` lưu archive và biên nhận promotion vào release bất biến theo phiên
bản — release nháp có đủ hai tệp, kiểm đúng bytes (digest tải về = digest đã attest = trường `sha256` của biên nhận) rồi mới
công bố; không ghi đè, không xoá; tag đã có thì chỉ báo trạng thái release."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "release-tag.yml"


def steps(text: str) -> list[str]:
    """Các bước của job `tag` (từ `  tag:` tới hết tệp), mỗi bước một khối bắt đầu ở `      - `."""
    job = text.split("\n  tag:\n", 1)[1]
    return [b for b in re.split(r"\n(?=      - )", job) if b.startswith("      - ")]


def find(blocks: list[str], needle: str) -> int:
    hits = [i for i, b in enumerate(blocks) if needle in b]
    assert len(hits) == 1, (needle, hits)
    return hits[0]


class ReleaseAssetsTest(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding="utf-8")
        self.blocks = steps(self.text)

    def test_draft_release_holds_archive_and_receipt_after_tag_push(self):
        push = find(self.blocks, "git push origin")
        publish = find(self.blocks, "gh release create")
        self.assertGreater(publish, push)
        block = self.blocks[publish]
        self.assertIn("--draft", block)
        self.assertIn("--verify-tag", block)
        self.assertRegex(block, r'"\$ARCHIVE"\s+"\$RECEIPT"')
        self.assertIn("steps.tag.outputs.archive != ''", block)
        self.assertIn("steps.receipt.outputs.file", block)
        self.assertIn("GH_TOKEN: ${{ github.token }}", block)

    def test_app_token_is_scoped_and_required_when_enabled(self):
        mint = find(self.blocks, "actions/create-github-app-token@")
        check = find(self.blocks, 'test -n "$APP_TOKEN"')
        checkout = find(self.blocks, "actions/checkout@")
        self.assertLess(mint, check)
        self.assertLess(check, checkout)
        app = self.blocks[mint]
        for line in (
            "if: vars.XT_RELEASE_APP_CLIENT_ID != ''",
            "actions/create-github-app-token@f418cff399f7aef4c2f0ad47e25ca7a6abbdd6fc",
            "client-id: ${{ vars.XT_RELEASE_APP_CLIENT_ID }}",
            "private-key: ${{ secrets.XT_RELEASE_APP_PRIVATE_KEY }}",
            "owner: ${{ github.repository_owner }}",
            "repositories: ${{ github.event.repository.name }}",
            "permission-contents: write",
            "permission-workflows: write",
        ):
            self.assertIn(line, app)
        self.assertIn("if: vars.XT_RELEASE_APP_CLIENT_ID != ''", self.blocks[check])
        self.assertIn("steps.release-app.outputs.token", self.blocks[check])
        self.assertIn("exit 1", self.blocks[check])
        self.assertIn(
            "steps.release-app.outputs.token || secrets.XT_RELEASE_TOKEN || github.token", self.blocks[checkout]
        )
        self.assertNotIn("continue-on-error", self.text)
        job = self.text.split("\n  tag:\n", 1)[1].split("    steps:", 1)[0]
        self.assertIn("needs.approve.outputs.approved == 'true'", job)
        self.assertIn("    environment:\n      name: xt-release\n      deployment: false\n", job)
        for needle in ("gh release create", "gh release view"):
            self.assertIn("GH_TOKEN: ${{ github.token }}", self.blocks[find(self.blocks, needle)])

    def test_bytes_are_verified_before_publishing(self):
        block = self.blocks[find(self.blocks, "gh release create")]
        order = [block.index(s) for s in ("gh release create", "gh release download", "sha256sum", "--draft=false")]
        self.assertEqual(order, sorted(order))
        self.assertIn("""grep -oE '"sha256":"[0-9a-f]{64}"'""", block)  # digest trong biên nhận = digest archive tải về
        self.assertNotIn("python3", block)  # job phát hành không dùng trình thông dịch (test_ci)
        self.assertRegex(
            block, r'test "\$downloaded" = "\$\(sha256sum "\$ARCHIVE"'
        )  # và = digest tệp đã attest ở runner

    def test_never_overwrites_or_deletes_release_assets(self):
        for bad in ("--clobber", "gh release delete", "gh release upload", "gh api -X DELETE", "--latest=false"):
            self.assertNotIn(bad, self.text)

    def test_existing_tag_requires_published_release_with_both_assets(self):
        """AUD-CI-042: chỉ `released` mới xanh; nháp, thiếu tệp, chưa có release đều đỏ; không còn câu "xoá bản nháp"."""
        block = self.blocks[find(self.blocks, "gh release view")]
        self.assertIn("steps.tag.outputs.archive == ''", block)
        self.assertNotIn("::warning::", block)
        self.assertNotIn("xoá bản nháp", self.text)
        self.assertIn('test "$state" != released', block)
        self.assertEqual(block.count("exit 1"), 1)
        self.assertIn(".promotion.json", block)

    def test_approve_checks_tag_sha_kind_and_release_before_early_exit(self):
        approve = self.text.split("\n  tag:\n", 1)[0]
        branch = approve.split('if git show-ref --verify --quiet "refs/tags/v$v"; then', 1)[1].split(
            "\n          fi\n", 1
        )[0]
        exit0 = branch.index("exit 0")
        for needle in (
            'git merge-base --is-ancestor "$tag_commit" "$target"',
            'git cat-file -t "refs/tags/v$v"',
            "gh release view",
        ):
            self.assertLess(branch.index(needle), exit0, needle)
        self.assertIn('echo "state=released"', branch[:exit0])
        # mọi `exit 0` của bước ứng viên đều có ghi `state=` ngay trước đó
        step = approve.split("id: candidate", 1)[1].split("- uses: actions/setup-python", 1)[0]
        for m in re.finditer(r"exit 0", step):
            self.assertIn('echo "state=', "\n".join(step[: m.start()].splitlines()[-3:]))
        self.assertNotIn("continue-on-error", self.text)

    def test_published_receipt_is_compared_byte_for_byte(self):
        block = self.blocks[find(self.blocks, "gh release create")]
        self.assertIn('cmp -s "$RECEIPT"', block)
        self.assertLess(block.index('cmp -s "$RECEIPT"'), block.index("--draft=false"))

    def test_asset_names_follow_repo_name_pattern_used_by_archive(self):
        self.assertIn('name="${GITHUB_REPOSITORY#*/}-v$V"', self.text)
        self.assertIn('receipt="$RUNNER_TEMP/${GITHUB_REPOSITORY#*/}-v$V.promotion.json"', self.text)
        block = self.blocks[find(self.blocks, "gh release create")]
        self.assertIn("--pattern '*.tar.gz' --pattern '*.promotion.json'", block)

    def test_job_has_contents_write_and_nothing_wider(self):
        job = self.text.split("\n  tag:\n", 1)[1].split("    steps:", 1)[0]
        perms = re.search(r"permissions:\n((?:      \w[\w-]*: \w+\n)+)", job)
        self.assertIsNotNone(perms)
        self.assertEqual(
            sorted(perms[1].split()), sorted("attestations: write contents: write id-token: write".split())
        )

    def test_release_steps_are_pinned_to_the_job_gate(self):
        for needle in ("gh release create", "gh release view"):
            block = self.blocks[find(self.blocks, needle)]
            self.assertRegex(block, r"\n        if: steps\.tag\.outputs\.archive (!=|==) ''")


if __name__ == "__main__":
    unittest.main()
