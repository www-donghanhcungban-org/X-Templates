"""T-4018 (AUD-CI-036): nơi dùng tải đúng bytes archive và biên nhận đã attest từ release, rồi kiểm digest, nguồn, danh tính
ký, liên kết tag và commit — sửa một byte, thay biên nhận, thiếu một tệp đều bị từ chối; release chưa có (tag cũ) mới dùng
đường dựng lại duy nhất."""

from __future__ import annotations

import hashlib
import io
import json
import re
import sys
import tarfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_promotion_gate import ReleaseFixture, dist, xt

TAG = "v1.0.0"
NAME = f"framework-{TAG}"
ARCHIVE, RECEIPT = f"{NAME}.tar.gz", f"{NAME}.promotion.json"


class BytesFixture(ReleaseFixture):
    def setUp(self):
        super().setUp()
        self.head = self.git(self.up, "rev-parse", f"{TAG}^{{commit}}")
        built = self.temp / "served.tgz"
        self.git(self.up, "archive", "--format=tar.gz", f"--prefix={NAME}/", "-o", str(built), self.head)
        self.archive = built.read_bytes()
        self.publish(self.archive)

    def receipt(self, **over) -> bytes:
        body = {
            "repo": "test/framework",
            "tag": TAG,
            "commit": self.head,
            "sha256": hashlib.sha256(self.archive).hexdigest(),
            "promotion": "approved",
        } | over
        return (json.dumps(body, separators=(",", ":")) + "\n").encode()

    def publish(self, archive: bytes, receipt: bytes | None = None) -> None:
        """Release công bố: các tệp được phục vụ; bản được attest là `self.archive` (digest ghi ở `signed`)."""
        self.assets = {ARCHIVE: archive, RECEIPT: receipt if receipt is not None else self.receipt()}
        self.signed[TAG] = hashlib.sha256(self.archive).hexdigest()

    def verify(self) -> int:
        return xt.main(["release-verify", "--tag", TAG, "--repo", "test/framework"])


class DownloadedBytesTest(BytesFixture):
    def test_published_release_is_verified_by_its_own_bytes(self):
        self.assertEqual(self.verify(), 0)
        files = [Path(argv[3]).name for argv in self.gh if argv[:2] == ("gh", "attestation")]
        self.assertEqual(sorted(files), sorted([ARCHIVE, RECEIPT]))  # đúng tệp đã tải, không phải bản dựng lại

    def test_one_changed_byte_is_rejected(self):
        tampered = bytearray(self.archive)
        tampered[len(tampered) // 2] ^= 1
        self.publish(bytes(tampered))
        self.assertEqual(self.verify(), 1)

    def test_replaced_receipt_is_rejected(self):
        for field, value in (
            ("commit", "0" * 40),
            ("sha256", "0" * 64),
            ("repo", "evil/framework"),
            ("tag", "v9.9.9"),
            ("promotion", "pending"),
        ):
            with self.subTest(field=field):
                self.publish(self.archive, self.receipt(**{field: value}))
                self.assertEqual(self.verify(), 1)
        pretty = json.dumps(json.loads(self.receipt()), indent=1).encode() + b"\n"
        self.publish(self.archive, pretty)
        self.assertEqual(self.verify(), 1)  # cùng nội dung JSON nhưng khác từng byte so với dạng workflow ghi
        self.publish(self.archive, self.receipt() + b" ")
        self.assertEqual(self.verify(), 1)
        self.publish(self.archive, b"not json")
        self.assertEqual(self.verify(), 1)

    def test_missing_one_asset_is_rejected_not_rebuilt(self):
        for gone in (ARCHIVE, RECEIPT):
            with self.subTest(gone=gone):
                self.publish(self.archive)
                del self.assets[gone]
                self.sign(TAG)  # bản dựng lại SẼ được attest: nếu mã dựng lại thay vì từ chối thì ca này xanh nhầm
                self.assertEqual(self.verify(), 1)

    def test_wrong_signer_or_unattested_bytes_are_rejected(self):
        self.signed.clear()
        self.assertEqual(self.verify(), 1)

    def test_no_release_falls_back_to_the_single_rebuild_path(self):
        self.assets.clear()
        self.sign(TAG)  # bản dựng lại có tiền tố cũ X-Templates-
        self.assertEqual(self.verify(), 0)
        self.signed.clear()
        self.assertEqual(self.verify(), 1)

    def test_install_receipt_matches_checkout_with_repo_named_prefix(self):
        self.assertTrue(dist.install_source(self.up)["verified"])
        (self.up / "extra").write_text("local changes")
        self.assertFalse(dist.install_source(self.up)["verified"])


class FetchAssetTest(unittest.TestCase):
    def fetch(self, effect):
        with mock.patch.object(dist, "urlopen", side_effect=effect):
            return dist.fetch_asset("test/framework", TAG, ARCHIVE)

    def test_found_missing_and_errors(self):
        self.assertEqual(self.fetch(lambda *a, **k: io.BytesIO(b"data")), b"data")
        url = "https://github.com/test/framework/releases/download/v1.0.0/" + ARCHIVE
        self.assertIsNone(self.fetch(HTTPError(url, 404, "nf", {}, None)))
        for effect in (HTTPError(url, 500, "boom", {}, None), URLError("down"), TimeoutError("slow")):
            with self.subTest(effect=effect), self.assertRaises(dist.DistributionError) as ctx:
                self.fetch(effect)
            self.assertEqual(ctx.exception.code, 3)  # thử lại sau, không đoán là "chưa có release"

    def test_requests_only_the_release_download_url_of_the_repo(self):
        seen = []

        def opener(request, **kw):
            seen.append(request.full_url)
            return io.BytesIO(b"x")

        with mock.patch.object(dist, "urlopen", opener):
            dist.fetch_asset("test/framework", TAG, ARCHIVE)
        self.assertEqual(seen, [f"https://github.com/test/framework/releases/download/{TAG}/{ARCHIVE}"])
        for bad in ("../x", "a/b", "x y", ""):
            with self.assertRaises(dist.DistributionError):
                dist.fetch_asset("test/framework", TAG, bad)

    def test_oversize_body_is_refused(self):
        with mock.patch.object(dist, "ASSET_MAX", 3):
            with self.assertRaises(dist.DistributionError) as ctx:
                self.fetch(lambda *a, **k: io.BytesIO(b"four"))
        self.assertEqual(ctx.exception.code, 1)


class FetchAssetTransportTest(unittest.TestCase):
    """Review lô B (🟠): kết nối đóng sớm hay HTTP hỏng là lỗi mạng (mã 3), không phải "giả mạo" (1) hay traceback."""

    def fetch(self, effect):
        with mock.patch.object(dist, "urlopen", side_effect=effect):
            return dist.fetch_asset("test/framework", TAG, ARCHIVE)

    def test_http_client_errors_are_transport_errors(self):
        import http.client

        for effect in (
            http.client.IncompleteRead(b"ab"),
            http.client.BadStatusLine("x"),
            http.client.RemoteDisconnected(),
        ):
            with self.subTest(effect=type(effect).__name__), self.assertRaises(dist.DistributionError) as ctx:
                self.fetch(effect)
            self.assertEqual(ctx.exception.code, 3)

    def test_short_body_against_content_length_is_a_transport_error(self):
        class Response(io.BytesIO):
            headers = {"Content-Length": "100"}

        with self.assertRaises(dist.DistributionError) as ctx:
            self.fetch(lambda *a, **k: Response(b"0123456789"))
        self.assertEqual(ctx.exception.code, 3)

        class Exact(io.BytesIO):
            headers = {"Content-Length": "4"}

        self.assertEqual(self.fetch(lambda *a, **k: Exact(b"data")), b"data")

        class Bad(io.BytesIO):
            headers = {"Content-Length": "abc"}

        self.assertEqual(self.fetch(lambda *a, **k: Bad(b"data")), b"data")  # không tin tiêu đề hỏng, cũng không chặn


class ArchivePrefixTest(unittest.TestCase):
    def tar(self, tmp: Path, names: list[str]) -> Path:
        path = tmp / "a.tar.gz"
        with tarfile.open(path, "w:gz") as bundle:
            for name in names:
                info = tarfile.TarInfo(name)
                info.size = 1
                bundle.addfile(info, io.BytesIO(b"x"))
        return path

    def test_single_versioned_top_directory_only(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            self.assertEqual(dist.archive_prefix(self.tar(tmp, [f"{NAME}/VERSION", f"{NAME}/a/b"])), f"{NAME}/")
            for bad in (
                [f"{NAME}/a", "other-v1.0.0/b"],
                ["VERSION"],
                ["../evil-v1.0.0/x"],
                [f"{NAME}/a", f"{NAME}/../../x"],  # đúng thư mục gốc nhưng thoát ra ngoài: chỉ phép kiểm `..` bắt được
                ["/abs-v1.0.0/x"],
                ["framework/x"],
            ):
                with self.subTest(bad=bad), self.assertRaises(dist.DistributionError):
                    dist.archive_prefix(self.tar(tmp, bad))
            self.assertTrue(
                re.fullmatch(r"[\w.-]+-v\d+\.\d+\.\d+/", dist.archive_prefix(self.tar(tmp, ["x-v0.0.1/f"])))
            )


if __name__ == "__main__":
    unittest.main()
