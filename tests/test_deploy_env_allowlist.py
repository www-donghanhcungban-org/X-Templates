"""T-5007: `deploy_env_pass` distinguishes an absent allowlist from an explicitly empty one."""

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
HOST = {
    "PATH": "/usr/bin:/bin",
    "HOME": "/home/x",
    "LANG": "C.UTF-8",
    "AWS_ACCESS_KEY_ID": "AKIAEXAMPLE",
    "AWS_SECRET_ACCESS_KEY": "s3cr3t-value",
    "GITHUB_TOKEN": "ghs_hostwide",
    "DEPLOY_TARGET": "prod-1",
    "PYTHONPATH": "/opt/lib",
}


class ParseTest(unittest.TestCase):
    def test_absent_and_explicit_empty_have_distinct_policies(self):
        self.assertIsNone(xt.deploy_env_pass({}))
        for blank in ("", "  ", '""', "''", " # tên tuỳ chọn"):
            with self.subTest(blank=blank):
                cfg = xt._yaml_keys("deploy_env_pass: " + blank)
                self.assertEqual(xt.deploy_env_pass(cfg), ())
                self.assertEqual(
                    xt.deploy_command_env(HOST, xt.deploy_env_pass(cfg)), {k: HOST[k] for k in ("HOME", "LANG", "PATH")}
                )

    def test_null_markers_are_invalid_and_never_enable_inheritance(self):
        for raw in ("null", "Null", "NULL", "~", '"null"', "'~'"):
            with self.subTest(raw=raw):
                cfg = xt._yaml_keys("deploy_env_pass: " + raw)
                self.assertIsNotNone(xt.deploy_env_pass_error(cfg))
                with self.assertRaises(xt.DeployError):
                    xt.deploy_env_pass(cfg)

    def test_quoted_punctuation_is_not_an_empty_allowlist(self):
        for raw in ("'\"\"'", '"# comment"', "[]", "{}"):
            with self.subTest(raw=raw), self.assertRaises(xt.DeployError):
                xt.deploy_env_pass(xt._yaml_keys("deploy_env_pass: " + raw))

    def test_names_split_on_space_and_comma_keep_order_no_duplicates(self):
        got = xt.deploy_env_pass(
            {"deploy_env_pass": "AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY  DEPLOY_TARGET AWS_ACCESS_KEY_ID"}
        )
        self.assertEqual(got, ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "DEPLOY_TARGET"))

    def test_bad_or_forbidden_names_rejected_with_name_in_message(self):
        for bad in (
            "1ABC",
            "A-B",
            "A=1",
            "BASH_ENV",
            "LD_PRELOAD",
            "DYLD_X",
            "BASH_FUNC_f",
            "XT_DEPLOY_ENV",
            "PS4",
            "ENV",
            "GIT_CONFIG",
            "GIT_CONFIG_PARAMETERS",
            "GIT_SSH_COMMAND",
            "GIT_EXEC_PATH",
            "GIT_CONFIG_KEY_1",
            "GIT_ASKPASS",
            "GIT_UNKNOWN",
        ):
            with self.subTest(bad=bad):
                err = xt.deploy_env_pass_error({"deploy_env_pass": f"GOOD {bad}"})
                self.assertIsNotNone(err)
                self.assertIn(bad, err)
                with self.assertRaises(xt.DeployError):
                    xt.deploy_env_pass({"deploy_env_pass": f"GOOD {bad}"})
        self.assertIsNone(xt.deploy_env_pass_error({"deploy_env_pass": "GOOD PYTHONPATH NODE_OPTIONS"}))
        self.assertIsNone(xt.deploy_env_pass_error({}))
        self.assertEqual(
            xt.deploy_env_pass({"deploy_env_pass": "GIT_SSL_CAINFO GIT_SSL_CAPATH"}),
            ("GIT_SSL_CAINFO", "GIT_SSL_CAPATH"),
        )


class FilterTest(unittest.TestCase):
    def test_none_keeps_step_one_behavior(self):
        out = xt.deploy_command_env(HOST)
        self.assertEqual(
            sorted(out),
            ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "DEPLOY_TARGET", "GITHUB_TOKEN", "HOME", "LANG", "PATH"],
        )

    def test_allowlist_keeps_system_plus_named_only(self):
        out = xt.deploy_command_env(HOST, ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "PYTHONPATH"))
        self.assertEqual(
            sorted(out), ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "HOME", "LANG", "PATH", "PYTHONPATH"]
        )  # GITHUB_TOKEN, DEPLOY_TARGET không được khai: không qua

    def test_empty_allowlist_tuple_is_allowlist_mode(self):
        self.assertEqual(sorted(xt.deploy_command_env(HOST, ())), ["HOME", "LANG", "PATH"])

    def test_missing_declared_name_stops_naming_it_without_values(self):
        with self.assertRaises(xt.DeployError) as ctx:
            xt.deploy_command_env({"PATH": "/bin"}, ("AWS_ACCESS_KEY_ID", "GITHUB_TOKEN"))
        msg = str(ctx.exception)
        self.assertIn("AWS_ACCESS_KEY_ID", msg)
        self.assertIn("GITHUB_TOKEN", msg)
        self.assertIn("deploy_env_pass", msg)

    def test_declared_but_empty_value_counts_as_present(self):
        out = xt.deploy_command_env({"PATH": "/bin", "FLAG": ""}, ("FLAG",))
        self.assertEqual(out["FLAG"], "")


class InvokeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        (self.tmp / "repo").mkdir()
        self.seen = self.tmp / "seen"

    def run_cmd(self, names, env):
        cmd = (
            f'printf "%s|%s|%s" "${{AWS_ACCESS_KEY_ID-unset}}" "${{GITHUB_TOKEN-unset}}" "$XT_DEPLOY_ENV" > {self.seen}'
        )
        commands = {k: cmd for k in xt.DEV_ACTIONS}
        driver = xt.DevPreview(
            self.tmp / "repo",
            self.tmp / "state",
            30,
            {"digest": DIGEST},
            "",
            commands=commands,
            artifacts=(),
            env_pass=names,
        )
        with unittest.mock.patch.dict(os.environ, env, clear=False):
            return driver.invoke("smoke")[0]

    def test_command_sees_only_declared_secret(self):
        env = {"AWS_ACCESS_KEY_ID": "AKIAEXAMPLE", "GITHUB_TOKEN": "ghs_hostwide"}
        self.assertEqual(self.run_cmd(("AWS_ACCESS_KEY_ID",), env)["exit_code"], 0)
        self.assertEqual(self.seen.read_text(encoding="utf-8"), "AKIAEXAMPLE|unset|dev")
        self.run_cmd(None, env)  # không khai: bước 1 — mọi biến thường vẫn qua
        self.assertEqual(self.seen.read_text(encoding="utf-8"), "AKIAEXAMPLE|ghs_hostwide|dev")
        self.run_cmd((), env)
        self.assertEqual(self.seen.read_text(encoding="utf-8"), "unset|unset|dev")

    def test_missing_name_raises_before_running_anything(self):
        env = {k: v for k, v in os.environ.items() if k != "AWS_ACCESS_KEY_ID"}
        with unittest.mock.patch.dict(os.environ, env, clear=True), self.assertRaises(xt.DeployError):
            xt.DevPreview(
                self.tmp / "repo",
                self.tmp / "state",
                30,
                {"digest": DIGEST},
                "",
                commands={"smoke": "true"},
                artifacts=(),
                env_pass=("AWS_ACCESS_KEY_ID",),
            ).invoke("smoke")
        self.assertFalse(self.seen.exists())


class DoctorTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()

    def warn(self, yaml: str):
        (self.base / "xt.yaml").write_text(yaml, encoding="utf-8")
        found = xt._doctor_deploy_env(self.base)
        return [f for f in found if f.level == "warn" and "deploy_env_pass" in f.msg], found

    def test_warns_only_when_deploy_is_enabled_and_pass_not_declared(self):
        warns, _ = self.warn("deploy_envs: dev\n")
        self.assertEqual(len(warns), 1)
        self.assertEqual(self.warn("deploy_envs: dev\ndeploy_env_pass: AWS_ACCESS_KEY_ID\n")[0], [])
        self.assertEqual(
            self.warn("deploy_envs: dev prod\ndeploy_env_pass: # không cần biến ngoài hệ thống\n"), ([], [])
        )
        self.assertEqual(self.warn("lint: true\n")[0], [])  # không bật deploy: không nhắc
        self.assertEqual(self.warn("deploy_envs: null\n")[0], [])

    def test_invalid_name_is_an_error(self):
        _, found = self.warn("deploy_envs: dev\ndeploy_env_pass: BASH_ENV\n")
        self.assertEqual([f.level for f in found if "BASH_ENV" in f.msg], ["error"])
        _, found = self.warn("deploy_envs: prod\ndeploy_env_pass: '# literal'\n")
        self.assertEqual([f.level for f in found], ["error"])

    def test_missing_xt_yaml_is_silent(self):
        self.assertEqual(xt._doctor_deploy_env(self.base), [])

    def test_unreadable_xt_yaml_is_silent(self):
        with unittest.mock.patch.object(xt, "_xt_keys", side_effect=OSError("không đọc được")):
            self.assertEqual(xt._doctor_deploy_env(self.base), [])


if __name__ == "__main__":
    unittest.main()
