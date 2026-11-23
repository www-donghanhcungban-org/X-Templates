"""Release provenance checked on local Git objects; the external verifier is a strict digest/identity test double."""

from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from urllib.error import HTTPError
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import xt
import xt_distribution as dist


class ReleaseFixture(unittest.TestCase):
    def setUp(self):
        self.temp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.up = self.temp / "up"
        self.up.mkdir()
        self.real = dist.command
        self.enterContext(
            mock.patch.dict(
                os.environ,
                {
                    k: v
                    for k, v in (
                        ("GH_TOKEN", "fixture"),
                        ("GIT_AUTHOR_NAME", "fixture"),
                        ("GIT_COMMITTER_NAME", "fixture"),
                        ("GIT_AUTHOR_EMAIL", "fixture@example.invalid"),
                        ("GIT_COMMITTER_EMAIL", "fixture@example.invalid"),
                    )
                },
            )
        )
        self.git(self.up, "init", "-qb", "main")
        self.git(self.up, "remote", "add", "origin", "https://github.com/test/framework.git")
        (self.up / "VERSION").write_text("1.0.0\n")
        self.git(self.up, "add", ".")
        self.git(self.up, "commit", "-qm", "initial")
        self.git(self.up, "tag", "-am", "release", "v1.0.0")
        self.signed = {}
        self.has_promotion = True
        self.gh = []
        self.origin = None
        self.prs = []
        self.api_rc = 0
        self.assets = {}  # tệp release đã công bố (T-4018); rỗng = chưa có release → đường dựng lại
        self.enterContext(mock.patch.object(dist, "fetch_asset", lambda repo, tag, name: self.assets.get(name)))
        self.enterContext(mock.patch.object(dist, "command", self.dispatch))

    def git(self, cwd, *argv):
        return self.real(cwd, "git", *argv).stdout.strip()

    def sign(self, tag):
        path = self.temp / "expected.tgz"
        self.git(
            self.up, "archive", "--format=tar.gz", f"--prefix=X-Templates-{tag}/", "-o", str(path), f"{tag}^{{commit}}"
        )
        self.signed[tag] = hashlib.sha256(path.read_bytes()).hexdigest()

    def dispatch(self, cwd, *argv, check=True, env=None):
        if argv[:2] == ("gh", "attestation"):
            self.gh.append(argv)
            file = Path(argv[3])
            key = re.search(r"v\d+\.\d+\.\d+", file.name)[0]  # tiền tố theo tên repo hoặc X-Templates-
            if file.name.endswith(".promotion.json"):
                receipt = json.loads(file.read_bytes())
                good = (
                    receipt
                    == {
                        "repo": "test/framework",
                        "tag": receipt["tag"],
                        "commit": self.git(self.up, "rev-parse", f"{receipt['tag']}^{{commit}}"),
                        "sha256": self.signed.get(receipt["tag"]),
                        "promotion": "approved",
                    }
                    and self.has_promotion
                )
            else:
                good = self.signed.get(key) == hashlib.sha256(file.read_bytes()).hexdigest()
            self.assertIn("https://github.com/test/framework/.github/workflows/release-tag.yml@refs/heads/main", argv)
            self.assertEqual(argv[-2:], ("--source-ref", "refs/heads/main"))
            return subprocess.CompletedProcess(argv, 0 if good else 1, "", "" if good else "no attestations found")
        if argv[0] == "gh":
            self.gh.append(argv)
            if argv[1] == "api":
                return subprocess.CompletedProcess(argv, self.api_rc, json.dumps(self.prs), "HTTP 403" * self.api_rc)
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[0] == "git":  # clone and the authenticated push of the upgrade branch reach local fixture repositories
            repos = {
                "https://github.com/test/framework.git": self.up,
                "https://github.com/test/project.git": self.origin,
            }
            argv = tuple(str(repos[arg]) if arg in repos else arg for arg in argv)
        return self.real(cwd, *argv, check=check, env=env)


class PromotionGateTest(ReleaseFixture):
    def test_public_cli_verifies_exact_signed_bytes_and_signer(self):
        self.sign("v1.0.0")
        self.assertEqual(xt.main(["release-verify", "--tag", "v1.0.0", "--repo", "test/framework"]), 0)
        self.signed.clear()
        self.assertEqual(xt.main(["release-verify", "--tag", "v1.0.0", "--repo", "test/framework"]), 1)
        self.assertEqual(xt.main(["release-verify", "--tag", "v1.0.0", "--repo", "/bad"]), 2)
        self.assertEqual(xt.main(["release-verify", "--tag", "main", "--repo", "test/framework"]), 2)

    def test_version_ancestry_and_annotated_tag_are_checked_before_verification(self):
        self.git(self.up, "tag", "v2.0.0")
        self.git(self.up, "tag", "-am", "wrong version", "v3.0.0")
        self.git(self.up, "switch", "-qc", "other")
        (self.up / "VERSION").write_text("4.0.0")
        self.git(self.up, "commit", "-qam", "other branch")
        self.git(self.up, "tag", "-am", "other", "v4.0.0")
        self.git(self.up, "switch", "-q", "main")
        for tag in ("v2.0.0", "v3.0.0", "v4.0.0", "v5.0.0"):
            with self.subTest(tag=tag):
                self.assertEqual(xt.main(["release-verify", "--tag", tag, "--repo", "test/framework"]), 1)
        self.assertFalse(self.gh)

    def test_install_receipt_clean_dirty_unsigned_and_untagged(self):
        self.assertFalse(dist.install_source(self.up)["verified"])
        self.sign("v1.0.0")
        self.assertTrue(dist.install_source(self.up)["verified"])
        (self.up / "extra").write_text("local changes")
        self.assertFalse(dist.install_source(self.up)["verified"])
        self.git(self.up, "add", "extra")
        self.git(self.up, "commit", "-qm", "development")
        self.assertEqual(dist.install_source(self.up), {"untagged": self.git(self.up, "rev-parse", "HEAD")})
        self.assertEqual(dist.install_source(self.temp), {"untagged": "unknown"})
        (self.up / "nested").mkdir()
        self.assertEqual(dist.install_source(self.up / "nested"), {"untagged": "unknown"})

    def test_install_receipt_does_not_reuse_a_retargeted_tag_or_unavailable_verifier(self):
        self.sign("v1.0.0")
        with mock.patch.object(dist, "verified_archive", return_value=("0" * 40, self.temp / "unused")):
            self.assertFalse(dist.install_source(self.up)["verified"])
        with mock.patch.object(dist, "verified_archive", side_effect=FileNotFoundError("gh")):
            self.assertFalse(dist.install_source(self.up)["verified"])
            self.assertEqual(xt.main(["release-verify", "--tag", "v1.0.0", "--repo", "test/framework"]), 3)

    def test_anonymous_public_bundles_and_transport_errors(self):
        artifact = self.temp / "release"
        artifact.write_bytes(b"signed data")
        row = {"bundle": {"signed": "bundle"}}

        def response(data):
            return io.BytesIO(json.dumps(data).encode())

        cases = [
            ([], 3),
            ({"attestations": []}, 1),
            ({"attestations": None}, 3),
            ({"attestations": ["broken"]}, 3),
            ({"attestations": [{"bundle": False}]}, 3),
        ]
        for payload, code in cases:
            with (
                mock.patch.object(dist, "urlopen", return_value=response(payload)),
                self.assertRaises(dist.DistributionError) as err,
            ):
                dist.public_bundles(self.temp, "test/framework", artifact)
            self.assertEqual(err.exception.code, code)
        for status in (404, 403):
            failure = HTTPError("https://api.github.com", status, "error", None, None)
            with (
                mock.patch.object(dist, "urlopen", side_effect=failure),
                self.assertRaises((HTTPError, dist.DistributionError)) as err,
            ):
                dist.public_bundles(self.temp, "test/framework", artifact)
            self.assertEqual(err.exception.code, 1 if status == 404 else 403)
        results = [response({"attestations": [row] * 100}), response({"attestations": [row]})]
        with mock.patch.object(dist, "urlopen", side_effect=results) as fetch:
            path = dist.public_bundles(self.temp, "test/framework", artifact)
        self.assertEqual(len(path.read_text().splitlines()), 101)
        self.assertIn("page=2", fetch.call_args.args[0].full_url)
        with (
            mock.patch.dict(os.environ, {"GH_TOKEN": "", "GITHUB_TOKEN": ""}),
            mock.patch.object(dist, "public_bundles", return_value=path),
            mock.patch.object(dist, "command") as verified,
        ):
            verified.return_value.returncode = 0
            dist.verify_signature(self.temp, "test/framework", artifact)
            self.assertEqual(verified.call_args.args[-2:], ("--bundle", str(path)))

    def test_signed_archive_compares_bytes_and_symlinks(self):
        (self.up / "link").symlink_to("VERSION")
        self.git(self.up, "add", "link")
        self.git(self.up, "commit", "-qm", "source link")
        archive = self.temp / "files.tgz"
        self.git(self.up, "archive", "--format=tar.gz", "--prefix=X-Templates-v1.0.0/", "-o", str(archive), "HEAD")
        self.assertTrue(dist.matches_checkout(self.up, "v1.0.0", archive))
        (self.up / "link").unlink()
        (self.up / "link").symlink_to("some-other-file")
        self.assertFalse(dist.matches_checkout(self.up, "v1.0.0", archive))
        (self.up / "VERSION").write_text("different")
        self.assertFalse(dist.matches_checkout(self.up, "v1.0.0", archive))

    def test_guard_classifies_release_publication_and_allows_read_only_tag_listing(self):
        for argv in (
            ("git", "tag", "v4.0.0"),
            ("git", "push", "origin", "refs/tags/v4.0.0"),
            ("gh", "release", "create", "v4.0.0"),
            ("gh", "api", "-X", "POST", "repos/o/r/releases", "-f", "tag_name=v4.0.0"),
            ("gh", "api", "-X", "POST", "repos/o/r/git/refs", "-f", "ref=refs/tags/v4.0.0"),
        ):
            self.assertEqual(xt.main(["guard-check", "--", *argv]), 126)
        self.assertEqual(xt.main(["guard-check", "--", "git", "tag", "--list", "v4.0.0"]), 0)

    def test_receipt_doctor_and_source_forms(self):
        self.assertEqual(dist.repo_slug("git@github.com:owner/repo.git"), "owner/repo")
        for data in ("not-a-repo", "https://example.invalid/a/b", "a/b.git"):
            with self.assertRaises(dist.DistributionError):
                dist.repo_slug(data)
        base = self.temp / "target"
        path = base / dist.MANIFEST
        self.assertEqual(xt._doctor_distribution(base), [])
        path.parent.mkdir(parents=True)
        for raw, issues in [
            ("[]", 1),
            ("{}", 1),
            ("invalid", 1),
            ('{"source":{"untagged":"abc"}}', 1),
            ('{"source":{"verified":false}}', 1),
            ('{"source":{"verified":true}}', 0),
        ]:
            path.write_text(raw)
            self.assertEqual(len(xt._doctor_distribution(base)), issues)
        self.assertEqual(dist.framework_repo({}), dist.CANONICAL)
        for source in ("bad", {"repo": 42}):
            with self.assertRaises(dist.DistributionError):
                dist.framework_repo({"source": source})
