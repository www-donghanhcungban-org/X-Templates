"""ADR-0097 (P2): bộ phân giải `tool.json` — mặc định y nguyên, khoá và giá trị sai bị từ chối, đọc tệp do dự án đích commit
thì chặt (liên kết, tệp không thường, quá lớn, khoá trùng, JSON lồng sâu). Các ca tái hiện của rà #774 (AUD-HAR-498, 499, 500)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import unittest.mock
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

    def test_env_uses_the_prefix_and_falls_back_to_the_default_one(self):
        cfg = tc.parse({"env_prefix": "ACME_"})
        self.assertEqual(cfg.env("MODE", {"ACME_MODE": "x", "XT_MODE": "y"}), "x")
        self.assertEqual(cfg.env("GUARD_POLICY", {"XT_GUARD_POLICY": "strict"}), "strict")  # biến cũ không bị bỏ qua
        self.assertIsNone(cfg.env("OTHER", {}))
        self.assertIsNone(tc.ToolCfg().env("OTHER", {"ACME_OTHER": "z"}))
        self.assertEqual(tc.ToolCfg().env("MODE", {"XT_MODE": "y"}), "y")


class ParseTest(unittest.TestCase):
    def test_custom_values(self):
        cfg = tc.parse({"config": "acme.yaml", "env_prefix": "MY_TOOL_", "contract": 2, "min_contract": 2}, ".acme")
        self.assertEqual(
            (cfg.root, cfg.config, cfg.env_prefix, cfg.min_contract), (".acme", "acme.yaml", "MY_TOOL_", 2)
        )

    def test_rejects_non_object_and_unknown_keys(self):
        for bad in ([], "x", 3, None):
            with self.subTest(bad=bad), self.assertRaises(tc.ToolCfgError):
                tc.parse(bad)
        with self.assertRaisesRegex(tc.ToolCfgError, "khoá lạ"):
            tc.parse({"confg": "x.yaml"})

    def test_unknown_key_is_quoted_so_it_cannot_forge_output(self):
        with self.assertRaises(tc.ToolCfgError) as ctx:
            tc.parse({"x\n✓ checks: 5/5 xanh\x1b[2K": 1})
        self.assertNotIn("\n", str(ctx.exception))
        self.assertNotIn("\x1b", str(ctx.exception))

    def test_null_is_not_the_same_as_absent(self):
        for key in tc.KEYS:
            with self.subTest(key=key), self.assertRaisesRegex(tc.ToolCfgError, key):
                tc.parse({key: None})

    def test_rejects_bad_text_values(self):
        for key, bad in (
            ("config", "../x.yaml"),
            ("config", "a/b.yaml"),
            ("config", "x.json"),
            ("config", 5),
            ("env_prefix", "acme_"),
            ("env_prefix", "ACME"),
            ("env_prefix", "X__"),
            ("env_prefix", "_"),
            ("env_prefix", ""),
        ):
            with self.subTest(key=key, bad=bad), self.assertRaisesRegex(tc.ToolCfgError, key):
                tc.parse({key: bad})

    def test_root_must_be_a_private_dot_directory(self):
        for root in ("acme", "../x", ".", ".A", "/abs", ".git", ".github", ".claude", ".codex", ".autopilot"):
            with self.subTest(root=root), self.assertRaisesRegex(tc.ToolCfgError, "root"):
                tc.parse({}, root)
        self.assertEqual(tc.parse({}, ".my-tool").root, ".my-tool")

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

    def test_contract_relations(self):
        with self.assertRaisesRegex(tc.ToolCfgError, "nâng artefact"):
            tc.parse({"min_contract": tc.SUPPORTED_CONTRACT + 1})
        self.assertEqual(tc.parse({"min_contract": tc.SUPPORTED_CONTRACT}).min_contract, tc.SUPPORTED_CONTRACT)
        with self.assertRaisesRegex(tc.ToolCfgError, "thấp hơn"):
            tc.parse({"contract": 1, "min_contract": 2})
        self.assertEqual(tc.parse({"contract": 1}).contract, 1)


class LoadTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.base / ".xtemplates").mkdir()

    def path(self, root: str = ".xtemplates") -> Path:
        return self.base / root / tc.FILE_NAME

    def write(self, text: str | bytes, root: str = ".xtemplates") -> Path:
        target = self.path(root)
        target.parent.mkdir(exist_ok=True)
        if isinstance(text, bytes):
            target.write_bytes(text)
        else:
            target.write_text(text, encoding="utf-8")
        return target

    def test_missing_file_or_folder_gives_defaults(self):
        self.assertEqual(tc.load(self.base), tc.ToolCfg())
        self.assertEqual(tc.load(self.base / "absent"), tc.ToolCfg())

    def test_reads_the_file_under_the_given_root(self):
        self.write('{"config": "acme.yaml"}', ".acme")
        cfg = tc.load(self.base, ".acme")
        self.assertEqual((cfg.root, cfg.config), (".acme", "acme.yaml"))

    def test_invalid_json_utf8_and_duplicate_keys_are_errors(self):
        for body in (
            "{",
            b"\xff\xfe{}",
            '{"min_contract": 9, "min_contract": 1}',
            '{"config": "a.yaml", "config": "b.yaml"}',
        ):
            with self.subTest(body=body):
                self.write(body)
                with self.assertRaisesRegex(tc.ToolCfgError, "JSON hợp lệ"):
                    tc.load(self.base)

    def test_deeply_nested_json_is_a_clear_error_not_a_crash(self):
        for body in ("[" * 100000, '{"a":' * 100000):
            with self.subTest(head=body[:6]):
                self.write(body)  # tuỳ bản dựng: RecursionError hoặc JSONDecodeError — đều phải thành ToolCfgError
                with self.assertRaisesRegex(tc.ToolCfgError, "JSON hợp lệ"):
                    tc.load(self.base)

    def test_recursion_error_from_the_parser_becomes_a_clear_error(self):
        self.write("{}")  # giả lập để ca này không phụ thuộc kích thước ngăn xếp của bản Python
        with unittest.mock.patch.object(tc.json, "loads", side_effect=RecursionError("sâu")):
            with self.assertRaisesRegex(tc.ToolCfgError, "RecursionError"):
                tc.load(self.base)

    def test_oversize_file_is_refused(self):
        self.write(" " * (tc.MAX_BYTES + 1))
        with self.assertRaisesRegex(tc.ToolCfgError, "quá"):
            tc.load(self.base)
        self.write(" " * 10 + "{}")  # đúng cỡ vẫn đọc được
        self.assertEqual(tc.load(self.base), tc.ToolCfg())

    def test_file_that_grew_after_the_size_check_is_refused(self):
        self.write("{}")
        with unittest.mock.patch.object(tc, "_read_bytes", return_value=b" " * (tc.MAX_BYTES + 1)):
            with self.assertRaisesRegex(tc.ToolCfgError, "quá"):
                tc.load(self.base)

    def test_symlinked_file_is_refused(self):
        target = self.base / "real.json"
        target.write_text("{}", encoding="utf-8")
        self.path().symlink_to(target)
        with self.assertRaisesRegex(tc.ToolCfgError, "không mở được"):
            tc.load(self.base)

    def test_symlinked_root_directory_is_refused(self):
        real = self.base / "elsewhere"
        real.mkdir()
        (real / tc.FILE_NAME).write_text('{"config": "from-link.yaml"}', encoding="utf-8")
        (self.base / ".linked").symlink_to(real)
        with self.assertRaisesRegex(tc.ToolCfgError, "liên kết tượng trưng"):
            tc.load(self.base, ".linked")

    def test_fifo_and_directory_are_not_regular_files_and_do_not_hang(self):
        os.mkfifo(self.path())
        with self.assertRaisesRegex(tc.ToolCfgError, "không phải tệp thường"):
            tc.load(self.base)
        self.path().unlink()
        self.path().mkdir()
        with self.assertRaisesRegex(tc.ToolCfgError, "không phải tệp thường"):
            tc.load(self.base)

    def test_root_is_checked_before_anything_is_read(self):
        outside = self.base.parent / "outside"
        for bad in ("../outside", str(outside), ".git"):
            with self.subTest(root=bad), unittest.mock.patch.object(tc, "_read_bytes") as read:
                with self.assertRaisesRegex(tc.ToolCfgError, "root"):
                    tc.load(self.base, bad)
                read.assert_not_called()


if __name__ == "__main__":
    unittest.main()
