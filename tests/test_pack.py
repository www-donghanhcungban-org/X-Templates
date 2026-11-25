"""P1 (ADR-0097): artefact `.pyz` dựng tất định, kiểm được, chạy được từ zip với đủ lệnh con của hợp đồng."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
import xt
import xt_pack

GOLDEN = json.loads((ROOT / "tests" / "fixtures" / "contract-surface.json").read_text(encoding="utf-8"))
# Sha256 của artefact dựng từ `fake_scripts()` (đã kiểm giống nhau trên CPython 3.11–3.15): đổi bố cục thì phải đổi.
FAKE_SHA256 = "9232f617cde1fb70a17b749a37725663faf00725ecdeb57263a4a742b255eca0"


def run_pyz(pyz: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(pyz), *args], capture_output=True, text=True, check=False, cwd=ROOT
    )


def choices(text: str) -> set[str]:
    found = re.search(r"\{([a-z0-9,-]+)\}", text)
    return set(found[1].split(",")) if found else set()


class PackTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def fake_scripts(self) -> Path:
        s = self.tmp / "scripts"
        (s / "xt_app").mkdir(parents=True)
        (s / "xt.py").write_text("def main():\n    return 0\n", encoding="utf-8")
        (s / "xt_flow.py").write_text("X = 1\n", encoding="utf-8")
        (s / "xt_app" / "__init__.py").write_text("", encoding="utf-8")
        (s / "xt_app" / "server.py").write_text("Y = 2\n", encoding="utf-8")
        (s / "install.py").write_text("# không vào artefact\n", encoding="utf-8")
        (self.tmp / "VERSION").write_text("9.9.9\n", encoding="utf-8")
        return s

    def test_two_builds_have_the_same_sha256_and_bytes(self):
        s = self.fake_scripts()
        a = xt_pack.build(s, self.tmp / "a" / "xt.pyz")
        b = xt_pack.build(s, self.tmp / "b" / "xt.pyz")
        self.assertEqual(a, b)
        self.assertEqual(a, hashlib.sha256((self.tmp / "a" / "xt.pyz").read_bytes()).hexdigest())
        self.assertEqual((self.tmp / "a" / "xt.pyz").read_bytes(), (self.tmp / "b" / "xt.pyz").read_bytes())
        self.assertEqual(list((self.tmp / "a").iterdir()), [self.tmp / "a" / "xt.pyz"])  # không để tệp tạm

    def test_golden_sha256_of_the_fake_tree(self):
        self.assertEqual(xt_pack.build(self.fake_scripts(), self.tmp / "xt.pyz"), FAKE_SHA256)

    def test_layout_is_sorted_stored_and_fixed(self):
        s = self.fake_scripts()
        out = self.tmp / "xt.pyz"
        xt_pack.build(s, out)
        self.assertTrue(out.read_bytes().startswith(xt_pack.SHEBANG))
        with zipfile.ZipFile(out) as z:
            names = [i.filename for i in z.infolist()]
            self.assertEqual(names, sorted(names))
            self.assertEqual(
                names, ["VERSION", "__main__.py", "xt.py", "xt_app/__init__.py", "xt_app/server.py", "xt_flow.py"]
            )
            for i in z.infolist():
                self.assertEqual((i.compress_type, i.date_time), (zipfile.ZIP_STORED, xt_pack.FIXED_TIME))
                self.assertEqual(i.external_attr, xt_pack.FILE_MODE)
        self.assertTrue(out.stat().st_mode & 0o111)

    def test_missing_xt_py_or_strict_modules_are_errors(self):
        s = self.tmp / "empty"
        s.mkdir()
        with self.assertRaises(xt_pack.PackError):
            xt_pack.build_bytes(s)
        full = self.fake_scripts()
        xt_pack.build_bytes(full)  # tuỳ chọn vắng thì được
        with self.assertRaisesRegex(xt_pack.PackError, "thiếu module"):
            xt_pack.build_bytes(full, strict=True)

    def test_version_is_optional(self):
        s = self.fake_scripts()
        (self.tmp / "VERSION").unlink()
        names = [n for n, _ in xt_pack.entries(s)]
        self.assertNotIn("VERSION", names)
        self.assertIn("__main__.py", names)

    def test_symlinks_are_refused(self):
        s = self.fake_scripts()
        outside = self.tmp / "secret.txt"
        outside.write_text("bí mật\n", encoding="utf-8")
        os.symlink(outside, s / "xt_app" / "leak.py")
        with self.assertRaisesRegex(xt_pack.PackError, "liên kết tượng trưng"):
            xt_pack.build_bytes(s)
        (s / "xt_app" / "leak.py").unlink()
        os.symlink(self.tmp / "absent", s / "xt_flow.py.new")
        os.symlink(self.tmp / "absent", s / "xt_scale.py")  # liên kết hỏng của module tuỳ chọn
        with self.assertRaisesRegex(xt_pack.PackError, "liên kết tượng trưng"):
            xt_pack.build_bytes(s)
        link = self.tmp / "out-link.pyz"
        os.symlink(outside, link)
        (s / "xt_scale.py").unlink()
        with self.assertRaisesRegex(xt_pack.PackError, "đích là liên kết"):
            xt_pack.build(s, link)
        self.assertEqual(outside.read_text(encoding="utf-8"), "bí mật\n")

    def test_package_directory_symlink_is_refused(self):
        s = self.fake_scripts()
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "leak.py").write_text("SECRET = 1\n", encoding="utf-8")
        for p in sorted((s / "xt_app").iterdir()):
            p.unlink()
        (s / "xt_app").rmdir()
        os.symlink(outside, s / "xt_app")
        with self.assertRaisesRegex(xt_pack.PackError, "liên kết tượng trưng"):
            xt_pack.build_bytes(s)

    def strict_scripts(self) -> Path:
        s = self.fake_scripts()
        for name in xt_pack.ARTIFACT_SCRIPTS[1:]:
            (s / name).write_text("X = 1\n", encoding="utf-8")
        (s / "xt_checks").mkdir()
        (s / "xt_checks" / "__init__.py").touch()
        return s

    def test_strict_requires_each_package_directory_and_initializer(self):
        s = self.strict_scripts()
        for pkg in xt_pack.PACKAGES:
            root = s / pkg
            saved = self.tmp / pkg
            root.rename(saved)
            with self.subTest(pkg=pkg, case="absent"), self.assertRaisesRegex(xt_pack.PackError, pkg):
                xt_pack.build_bytes(s, strict=True)
            root.touch()
            with self.subTest(pkg=pkg, case="file"), self.assertRaisesRegex(xt_pack.PackError, pkg):
                xt_pack.build_bytes(s, strict=True)
            root.unlink()
            saved.rename(root)
            (root / "__init__.py").unlink()
            with self.subTest(pkg=pkg, case="initializer"), self.assertRaisesRegex(xt_pack.PackError, "__init__"):
                xt_pack.build_bytes(s, strict=True)
            (root / "__init__.py").touch()

    def test_strict_also_requires_version(self):
        s = self.strict_scripts()
        xt_pack.build_bytes(s, strict=True)
        (self.tmp / "VERSION").unlink()
        with self.assertRaisesRegex(xt_pack.PackError, "VERSION"):
            xt_pack.build_bytes(s, strict=True)

    def test_failed_build_leaves_no_temp_file(self):
        s = self.fake_scripts()
        out = self.tmp / "dist" / "xt.pyz"
        out.mkdir(parents=True)  # đích là thư mục: os.replace lỗi
        with self.assertRaises(OSError):
            xt_pack.build(s, out)
        self.assertEqual(sorted(p.name for p in (self.tmp / "dist").iterdir()), ["xt.pyz"])
        self.assertEqual(xt_pack.main(["--scripts", str(s), "build", "--out", str(out)]), 2)

    def test_verify_pin_rules(self):
        s = self.fake_scripts()
        out = self.tmp / "xt.pyz"
        pin = xt_pack.build(s, out)
        self.assertEqual(xt_pack.verify(out, s), [])
        self.assertEqual(xt_pack.verify(out, s, pin), [])
        self.assertEqual(xt_pack.verify(out, s, pin.upper()), [])
        for bad in ("", "abc", "g" * 64, pin + "0"):
            with self.subTest(pin=bad), self.assertRaises(xt_pack.PackError):
                xt_pack.verify(out, s, bad)
        raw = bytearray(out.read_bytes())
        raw[-30] ^= 0x01  # một byte trong thư mục trung tâm của zip
        out.write_bytes(bytes(raw))
        errors = xt_pack.verify(out, s, pin)
        self.assertEqual(len(errors), 2)
        self.assertIn("sha256", errors[0])
        self.assertEqual(len(xt_pack.verify(out, s)), 1)

    def test_verify_reports_failure_from_each_packaged_command(self):
        s = self.fake_scripts()
        out = self.tmp / "xt.pyz"
        for pkg, arg in (("xt_app", "app"), ("xt_checks", "static-check")):
            with self.subTest(pkg=pkg):
                (s / "xt.py").write_text(f"import sys\ndef main():\n    return 9 if {arg!r} in sys.argv else 0\n")
                pin = xt_pack.build(s, out)
                errors = xt_pack.verify(out, s, pin)
                self.assertTrue(any(pkg in error and "9" in error for error in errors), errors)
                self.assertEqual(xt_pack.main(["--scripts", str(s), "verify", str(out)]), 1)

    def test_verify_smoke_uses_verified_bytes_and_isolated_environment(self):
        s = self.fake_scripts()
        out = self.tmp / "xt.pyz"
        pin = xt_pack.build(s, out)
        data = out.read_bytes()
        launches = []
        run = subprocess.run

        def replace_artifact(scripts):
            out.write_bytes(b"changed after reading")
            return data

        def check_launch(argv, **kwargs):
            archive = Path(argv[3])
            work = Path(kwargs["cwd"])
            self.assertEqual(argv[:3], [sys.executable, "-I", "-S"])
            self.assertNotEqual(archive, out)
            self.assertEqual(archive.read_bytes(), data)
            self.assertEqual(Path(kwargs["env"]["CLAUDE_PROJECT_DIR"]), work)
            self.assertEqual(list(Path(kwargs["env"]["PATH"]).iterdir()), [])
            self.assertGreater(kwargs["timeout"], 0)
            launches.append(argv[4:])
            if "static-check" in argv:
                self.assertTrue((work / argv[-2]).is_file())
            return run(argv, **kwargs)

        with mock.patch.object(xt_pack, "build_bytes", side_effect=replace_artifact):
            with mock.patch.object(subprocess, "run", side_effect=check_launch):
                self.assertEqual(xt_pack.verify(out, s, pin), [])
        self.assertEqual(len(launches), len(xt_pack.PACKAGES))
        self.assertEqual(launches[0], ["--framework", str(self.tmp / "framework"), "app", "--smoke"])
        self.assertEqual(launches[1][:2], ["static-check", "nfc"])
        self.assertEqual(launches[1][-1], "--json")

    def test_verify_reports_smoke_timeout_and_skips_execution_on_mismatch(self):
        s = self.fake_scripts()
        out = self.tmp / "xt.pyz"
        xt_pack.build(s, out)
        with mock.patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired("xt.pyz", 1)) as run:
            self.assertTrue(xt_pack.verify(out, s, "0" * 64))
            out.write_bytes(out.read_bytes() + b"x")
            self.assertTrue(xt_pack.verify(out, s))
            run.assert_not_called()
            xt_pack.build(s, out)
            errors = xt_pack.verify(out, s)
            self.assertEqual(errors, [f"{pkg}: lệnh kiểm quá hạn" for pkg in xt_pack.PACKAGES])
        with mock.patch.object(subprocess, "run", side_effect=OSError("launch failed")):
            self.assertEqual(xt_pack.main(["--scripts", str(s), "verify", str(out)]), 1)

    def test_cli_exit_codes(self):
        s = self.fake_scripts()
        out = self.tmp / "dist" / "xt.pyz"
        base = ["--scripts", str(s)]
        self.assertEqual(xt_pack.main([*base, "build", "--out", str(out)]), 0)
        self.assertEqual(xt_pack.main([*base, "verify", str(out)]), 0)
        self.assertEqual(xt_pack.main([*base, "build", "--out", str(out), "--strict"]), 2)
        self.assertEqual(xt_pack.main([*base, "verify", str(self.tmp / "absent.pyz")]), 2)
        self.assertEqual(xt_pack.main([*base, "verify", str(out), "--sha256", ""]), 2)
        self.assertEqual(xt_pack.main([*base, "verify", str(out), "--sha256", "0" * 64]), 1)
        out.write_bytes(out.read_bytes() + b"x")
        self.assertEqual(xt_pack.main([*base, "verify", str(out)]), 1)

    def test_runs_as_a_script_even_with_optimized_docstrings(self):
        s = self.fake_scripts()
        out = self.tmp / "xt.pyz"
        r = subprocess.run(
            [sys.executable, "-OO", str(SCRIPTS / "xt_pack.py"), "--scripts", str(s), "build", "--out", str(out)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual((r.returncode, r.stdout.strip()), (0, hashlib.sha256(out.read_bytes()).hexdigest()))

    def test_real_artifact_has_the_contract_commands_and_version(self):
        out = self.tmp / "xt.pyz"
        xt_pack.build(SCRIPTS, out, strict=True)
        self.assertEqual(xt_pack.verify(out, SCRIPTS), [])
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        r = run_pyz(out, "--version")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, f"xt.py {version}"))
        in_zip = choices(run_pyz(out, "--help").stdout)
        in_tree = choices(
            subprocess.run(
                [sys.executable, "-I", str(SCRIPTS / "xt.py"), "--help"], capture_output=True, text=True, check=False
            ).stdout
        )
        self.assertLessEqual(set(GOLDEN["commands"]), in_zip)
        # khác biệt chỉ là lệnh của repo khung (không thuộc tập cài) hoặc cần tệp tĩnh cạnh mã
        self.assertEqual(in_tree - in_zip, {"derived"}, f"zip thiếu: {sorted(in_tree - in_zip)}")
        for cmd, sub in (("upgrade", "check"), ("perf", "field-check"), ("acceptance", "check")):
            r = run_pyz(out, cmd, "--help")
            self.assertEqual(r.returncode, 0, (cmd, r.stderr))
            self.assertIn(sub, r.stdout + r.stderr)

    def test_real_artifact_runs_state_commands(self):
        out = self.tmp / "xt.pyz"
        xt_pack.build(SCRIPTS, out)
        r = run_pyz(out, "loop", "status")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = run_pyz(out, "doctor", "--offline")
        text = r.stdout + r.stderr
        self.assertIn(r.returncode, (0, 1))  # 1 khi thiếu thư mục framework cạnh artefact; không phải lỗi sập
        self.assertIn("artefact .pyz", text)
        self.assertNotIn("xt.pyz/dev-task.sh", text)  # không báo "thiếu" sai chỗ

    def test_real_artifact_runs_perf_trial_and_mutate_guard(self):
        out = self.tmp / "xt.pyz"
        xt_pack.build(SCRIPTS, out)
        r = run_pyz(out, "perf", "trial", "status")
        self.assertNotIn("Not a directory", r.stdout + r.stderr)  # tới được logic thật, không vấp đường zip
        r = run_pyz(out, "mutate-guard", "--guard", str(ROOT / ".claude" / "hooks" / "guard.py"), "--list")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.strip())

    def test_artifact_scripts_match_what_install_copies(self):
        text = (SCRIPTS / "install.py").read_text(encoding="utf-8")
        start = text.index("optional_scripts = (")
        block = text[start : text.index(")", start)]
        listed = {line.strip().strip('",') for line in block.splitlines()[1:] if line.strip().startswith('"')}
        self.assertEqual(set(xt_pack.ARTIFACT_SCRIPTS) - {"xt.py"}, listed)


class ArtifactHelpersTest(unittest.TestCase):
    """Các hàm của xt.py nhận ra mã anh em ở trong artefact (ADR-0097)."""

    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.pyz = self.tmp / "tool.pyz"
        with zipfile.ZipFile(self.pyz, "w") as z:
            z.writestr("xt_flow.py", "VALUE = 41\n")
            z.writestr("VERSION", "7.7.7\n")
        xt._zip_names.cache_clear()
        self.addCleanup(xt._zip_names.cache_clear)

    def at(self, path: Path):
        return mock.patch.object(xt, "SCRIPT_DIR", path)

    def test_directory_layout_is_unchanged(self):
        (self.tmp / "xt_flow.py").write_text("VALUE = 1\n", encoding="utf-8")
        with self.at(self.tmp):
            self.assertFalse(xt.in_artifact())
            self.assertTrue(xt.sibling_exists("xt_flow.py"))
            self.assertFalse(xt.sibling_exists("xt_field.py"))
            self.assertIsNone(xt.artifact_member("xt_flow.py"))

    def test_zip_layout_finds_members(self):
        with self.at(self.pyz):
            self.assertTrue(xt.in_artifact())
            self.assertTrue(xt.sibling_exists("xt_flow.py"))
            self.assertFalse(xt.sibling_exists("xt_field.py"))
            self.assertEqual(xt.artifact_member("VERSION"), b"7.7.7\n")
            self.assertIsNone(xt.artifact_member("absent.py"))
            self.assertEqual(xt.framework_version(), "7.7.7")

    def test_corrupt_zip_has_no_members(self):
        bad = self.tmp / "bad.pyz"
        bad.write_bytes(b"not a zip")
        with self.at(bad):
            self.assertFalse(xt.sibling_exists("xt_flow.py"))
            self.assertIsNone(xt.artifact_member("VERSION"))

    def corrupt(self, needle: bytes) -> Path:
        """Bản sao của zip với một byte của nội dung `needle` bị đổi (sai CRC, tiêu đề vẫn đọc được)."""
        raw = bytearray(self.pyz.read_bytes())
        raw[raw.index(needle)] ^= 0x01
        bad = self.tmp / "bad-member.pyz"
        bad.write_bytes(bytes(raw))
        return bad

    def test_corrupt_member_is_missing_not_a_crash_and_never_falls_back_to_disk(self):
        (self.tmp / "VERSION").write_text("1.1.1\n", encoding="utf-8")  # VERSION cạnh zip không được thay thế
        with self.at(self.corrupt(b"7.7.7")):
            self.assertIsNone(xt.artifact_member("VERSION"))
            self.assertEqual(xt.framework_version(), "unknown")
            found = xt._doctor_scripts()
        self.assertEqual([f.level for f in found], ["warn", "error"])

    def test_corrupt_module_raises_instead_of_reading_the_disk(self):
        import types

        bad = self.corrupt(b"VALUE = 41")
        with self.at(bad), self.assertRaisesRegex(OSError, "thiếu hoặc hỏng"):
            xt._exec_source(bad / "xt_flow.py", types.ModuleType("m"))

    def test_self_source_and_entry(self):
        with zipfile.ZipFile(self.pyz, "a") as z:
            z.writestr("xt.py", "MAIN = 1\n")
        xt._zip_names.cache_clear()
        with self.at(self.pyz):
            self.assertEqual(xt.self_source(), b"MAIN = 1\n")
            self.assertEqual(xt.self_entry(), str(self.pyz))
        self.assertEqual(xt.self_source(), Path(xt.__file__).read_bytes())
        self.assertTrue(xt.self_entry().endswith("xt.py"))

    def test_exec_source_reads_sibling_from_zip(self):
        import types

        mod = types.ModuleType("m")
        with self.at(self.pyz):
            xt._exec_source(self.pyz / "xt_flow.py", mod)
        self.assertEqual(mod.VALUE, 41)

    def test_doctor_says_it_skips_checks_that_need_siblings_on_disk(self):
        with self.at(self.pyz):
            found = xt._doctor_scripts()
        self.assertEqual([(f.level, "artefact .pyz" in f.msg) for f in found], [("warn", True)])


if __name__ == "__main__":
    unittest.main()
