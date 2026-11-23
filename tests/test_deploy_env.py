"""T-4015: lệnh `deploy`/`smoke`/`rollback`/`digest` chạy không có biến khởi động trình thông dịch và nạp thư viện — script
khởi động đặt ngoài checkout không chạy, biến thường (PATH, HOME, khoá của dự án) giữ nguyên, log không chứa giá trị biến."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import xt

DIGEST = "d" * 64
STARTUP = (
    "BASH_ENV",
    "ENV",
    "SHELLOPTS",
    "BASHOPTS",
    "PS4",
    "BASH_FUNC_evil%%",
    "LD_PRELOAD",
    "LD_LIBRARY_PATH",
    "LD_AUDIT",
    "DYLD_INSERT_LIBRARIES",
    "PYTHONPATH",
    "PYTHONSTARTUP",
    "PYTHONHOME",
    "NODE_OPTIONS",
    "NODE_PATH",
    "PERL5OPT",
    "PERL5LIB",
    "RUBYOPT",
    "RUBYLIB",
    "JAVA_TOOL_OPTIONS",
    "_JAVA_OPTIONS",
    "JDK_JAVA_OPTIONS",
    # cùng lớp, lô C chứng minh lọt: perl nạp thư viện, `cd` bị dẫn đi, make nhận cờ, bộ chuyển mã, bí danh máy chủ
    "PERLLIB",
    "CDPATH",
    "MAKEFLAGS",
    "MAKEFILES",
    "GCONV_PATH",
    "HOSTALIASES",
    "RUBYGEMS_GEMDEPS",
)
KEEP = ("PATH", "HOME", "LANG", "AWS_REGION", "DEPLOY_TARGET", "MY_PYTHON_BIN", "NODEJS_VERSION", "LDAP_URL")


class FilterTest(unittest.TestCase):
    def test_startup_and_loader_variables_are_dropped(self):
        src = {**{k: "x" for k in STARTUP}, **{k: "keep" for k in KEEP}, "XT_DEPLOY_OLD": "y"}
        out = xt.deploy_command_env(src)
        self.assertEqual(sorted(out), sorted(KEEP))  # XT_DEPLOY_* cũng bị bỏ như trước (bước gán lại ở `invoke`)

    def test_prefix_families(self):
        src = {"PYTHONUTF8": "1", "LD_BIND_NOW": "1", "DYLD_FALLBACK_LIBRARY_PATH": "x", "BASH_FUNC_f%%": "() { :; }"}
        self.assertEqual(xt.deploy_command_env(src), {})

    def test_does_not_mutate_input_and_empty_ok(self):
        src = {"BASH_ENV": "/x", "PATH": "/bin"}
        self.assertEqual(xt.deploy_command_env(src), {"PATH": "/bin"})
        self.assertEqual(src, {"BASH_ENV": "/x", "PATH": "/bin"})
        self.assertEqual(xt.deploy_command_env({}), {})


class InvokeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.base = self.tmp / "repo"
        self.base.mkdir()
        self.out = self.tmp / "outside"
        self.out.mkdir()
        self.marker = self.out / "ran"
        startup = self.out / "startup.sh"
        startup.write_text(f"echo startup >> {self.marker}\n", encoding="utf-8")
        self.startup = startup

    def preview(self, cmd: str) -> xt.DevPreview:
        commands = {"deploy": cmd, "smoke": cmd, "digest": cmd, "rollback": cmd}
        return xt.DevPreview(self.base, self.tmp / "state", 30, {"digest": DIGEST}, "", commands=commands, artifacts=())

    def invoke(self, cmd: str, action: str = "smoke", **env: str):
        with unittest.mock.patch.dict(os.environ, env):
            return self.preview(cmd).invoke(action)

    def test_startup_script_outside_checkout_does_not_run(self):
        result, _ = self.invoke("true", BASH_ENV=str(self.startup), ENV=str(self.startup))
        self.assertEqual(result["exit_code"], 0)
        self.assertFalse(self.marker.exists())

    def test_project_variables_still_reach_the_command(self):
        seen = self.out / "seen"
        cmd = f'printf "%s|%s|%s" "$DEPLOY_TARGET" "$XT_DEPLOY_ENV" "${{LD_PRELOAD-unset}}" > {seen}'
        result, _ = self.invoke(cmd, DEPLOY_TARGET="staging-1", LD_PRELOAD="/tmp/evil.so")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(seen.read_text(encoding="utf-8"), "staging-1|dev|unset")

    def test_digest_command_also_clean_and_output_is_only_the_hash(self):
        cmd = f"echo {DIGEST}"
        result, digest = self.invoke(
            cmd, "digest", NODE_OPTIONS=f"--require {self.startup}", PYTHONSTARTUP=str(self.startup)
        )
        self.assertEqual((result["exit_code"], digest), (0, DIGEST))
        self.assertFalse(self.marker.exists())

    def test_result_never_carries_variable_values(self):
        secret = "valor-que-no-debe-aparecer"
        result, _ = self.invoke("true", BASH_ENV=secret, LD_PRELOAD=secret)
        self.assertNotIn(secret, repr(result))


if __name__ == "__main__":
    unittest.main()
