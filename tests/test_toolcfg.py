"""ADR-0097 (P2): bộ phân giải `tool.json` — mặc định y nguyên, khoá và giá trị sai bị từ chối, không đọc xuyên liên kết."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import xt_toolcfg as tc


class DefaultsTest(unittest.TestCase):
    def test_defaults_match_the_current_framework(self):
        cfg = tc.parse({})
        self.assertEqual((cfg.root, cfg.config, cfg.env_prefix), (".xtemplates", "xt.yaml", "XT_"))
        self.assertEqual((cfg.contract, cfg.min_contract), (tc.SUPPORTED_CONTRACT, 1))

    def test_supported_contract_matches_the_frozen_surface(self):
        surface = json.loads((ROOT / "tests" / "fixtures" / "contract-surface.json").read_text(encoding="utf-8"))
        self.assertEqual(surface["contract"], tc.SUPPORTED_CONTRACT)

    def test_env_uses_the_prefix(self):
        cfg = tc.parse({"env_prefix": "ACME_"})
        self.assertEqual(cfg.env("MODE", {"ACME_MODE": "x", "XT_MODE": "y"}), "x")
        self.assertIsNone(cfg.env("OTHER", {"XT_OTHER": "y"}))


class ParseTest(unittest.TestCase):
    def test_custom_values(self):
        cfg = tc.parse({"config": "acme.yaml", "env_prefix": "ACME_", "contract": 2, "min_contract": 2}, ".acme")
        self.assertEqual((cfg.root, cfg.config, cfg.env_prefix, cfg.min_contract), (".acme", "acme.yaml", "ACME_", 2))

    def test_rejects_non_object_and_unknown_keys(self):
        for bad in ([], "x", 3, None):
            with self.subTest(bad=bad), self.assertRaises(tc.ToolCfgError):
                tc.parse(bad)
        with self.assertRaisesRegex(tc.ToolCfgError, "khoá lạ"):
            tc.parse({"confg": "x.yaml"})

    def test_rejects_bad_text_values(self):
        for key, bad in (
            ("config", "../x.yaml"),
            ("config", "a/b.yaml"),
            ("config", "x.json"),
            ("config", 5),
            ("env_prefix", "acme_"),
            ("env_prefix", "ACME"),
            ("env_prefix", ""),
        ):
            with self.subTest(key=key, bad=bad), self.assertRaisesRegex(tc.ToolCfgError, key):
                tc.parse({key: bad})
        for root in ("acme", "../x", ".", ".A"):
            with self.subTest(root=root), self.assertRaisesRegex(tc.ToolCfgError, "root"):
                tc.parse({}, root)

    def test_rejects_bad_numbers(self):
        for key, bad in (
            ("contract", 0),
            ("contract", "2"),
            ("contract", True),
            ("min_contract", -1),
            ("min_contract", 1.5),
        ):
            with self.subTest(key=key, bad=bad), self.assertRaisesRegex(tc.ToolCfgError, key):
                tc.parse({key: bad})

    def test_min_contract_above_supported_fails_closed(self):
        with self.assertRaisesRegex(tc.ToolCfgError, "nâng artefact"):
            tc.parse({"min_contract": tc.SUPPORTED_CONTRACT + 1})
        self.assertEqual(tc.parse({"min_contract": tc.SUPPORTED_CONTRACT}).min_contract, tc.SUPPORTED_CONTRACT)


class LoadTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.base / ".xtemplates").mkdir()

    def write(self, text: str, root: str = ".xtemplates") -> Path:
        path = self.base / root / tc.FILE_NAME
        path.parent.mkdir(exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_missing_file_gives_defaults(self):
        self.assertEqual(tc.load(self.base), tc.ToolCfg())
        self.assertEqual(tc.load(self.base / "absent"), tc.ToolCfg())

    def test_reads_the_file_under_the_given_root(self):
        self.write('{"config": "acme.yaml"}', ".acme")
        cfg = tc.load(self.base, ".acme")
        self.assertEqual((cfg.root, cfg.config), (".acme", "acme.yaml"))

    def test_invalid_json_and_unreadable_are_errors(self):
        self.write("{")
        with self.assertRaisesRegex(tc.ToolCfgError, "không đọc được"):
            tc.load(self.base)
        path = self.base / ".xtemplates" / tc.FILE_NAME
        path.unlink()
        path.mkdir()  # tên có thật nhưng là thư mục → OSError khi đọc
        with self.assertRaisesRegex(tc.ToolCfgError, "không đọc được"):
            tc.load(self.base)

    def test_symlink_is_refused(self):
        target = self.base / "real.json"
        target.write_text("{}", encoding="utf-8")
        (self.base / ".xtemplates" / tc.FILE_NAME).symlink_to(target)
        with self.assertRaisesRegex(tc.ToolCfgError, "liên kết"):
            tc.load(self.base)


if __name__ == "__main__":
    unittest.main()
