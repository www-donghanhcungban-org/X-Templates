"""Quyền tạo tag tách khỏi sửa/xoá; một hàng admin-plan không kiểm các hàng khác."""

import base64
from contextlib import redirect_stderr
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_admin_plan import GithubFixture
from test_install import install
from test_xt_cli import TmpRepoCase, run_main, xt
import xt_ops_setup as setup

ROOT = Path(__file__).resolve().parents[1]
APP = {"actor_id": 123, "actor_type": "Integration", "bypass_mode": "always"}


def template(filename):
    return json.loads((ROOT / ".github" / "rulesets" / filename).read_text())


class TagRulesetContract(unittest.TestCase):
    def test_creation_needs_real_app_and_cannot_bypass_tag_mutation(self):
        immutable, creation = template("tags.json"), template("tags-create.json")
        self.assertTrue(setup.tag_rules_configured("tags.json", immutable))
        self.assertFalse(setup.tag_rules_configured("tags-create.json", creation))
        self.assertEqual(immutable["conditions"], creation["conditions"])
        creation["bypass_actors"] = [APP]
        self.assertTrue(setup.tag_rules_configured("tags-create.json", creation))
        immutable["bypass_actors"] = [APP]
        self.assertFalse(setup.tag_rules_configured("tags.json", immutable))
        creation["rules"].append({"type": "deletion"})
        self.assertFalse(setup.tag_rules_configured("tags-create.json", creation))

    def test_actor_and_scope_are_validated_before_accepting_live_equality(self):
        creation = {**template("tags-create.json"), "bypass_actors": [APP]}
        actors = [None, {}, [], [1], [APP, APP], [{}]]
        actors += [[{**APP, "actor_id": value}] for value in (True, 0, -1, "123", 1.5, 123.0)]
        actors += [[{**APP, "actor_type": "RepositoryRole"}], [{**APP, "bypass_mode": "pull_request"}]]
        for actor in actors:
            with self.subTest(actor=actor):
                self.assertFalse(setup.tag_rules_configured("tags-create.json", {**creation, "bypass_actors": actor}))
        for change in (
            {"rules": None},
            {"rules": [{"type": "update"}]},
            {"target": "branch"},
            {"enforcement": "disabled"},
            {"conditions": {}},
        ):
            with self.subTest(change=change):
                self.assertFalse(setup.tag_rules_configured("tags-create.json", {**creation, **change}))

    def test_installer_keeps_project_release_app(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(io.StringIO()):
            target = Path(tmp)
            install.install_github(target)
            immutable = target / ".github/rulesets/tags.json"
            creation = target / ".github/rulesets/tags-create.json"
            self.assertEqual(json.loads(immutable.read_text()), template("tags.json"))
            configured = {**json.loads(creation.read_text()), "bypass_actors": [APP]}
            creation.write_text(json.dumps(configured))
            install.install_github(target)
            self.assertEqual(json.loads(creation.read_text()), configured)

    def test_owner_script_validates_each_ruleset_before_fake_post(self):
        """Chỉ chạy gh giả trong thư mục tạm, không gọi lệnh ghi tới GitHub thật."""
        script = setup.owner_script({"items": [{"id": "ruleset", "status": setup.MISSING}]})
        self.assertNotIn("gh secret set", script)
        self.assertNotIn("automated-security-fixes", script)
        valid = {**template("tags-create.json"), "bypass_actors": [APP]}
        cases = [
            ("main.json", template("main.json"), 0),
            ("main.json", None, 2),
            ("main.json", "{", 2),
            ("main.json", "[]", 2),
            ("main.json", {**template("main.json"), "target": "tag"}, 2),
            ("tags.json", template("tags.json"), 0),
            ("tags-create.json", valid, 0),
            ("tags-create.json", template("tags-create.json"), 2),
            ("tags.json", {**template("tags.json"), "bypass_actors": [APP]}, 2),
            ("tags-create.json", {**valid, "rules": [{"type": "update"}]}, 2),
            ("tags-create.json", {**valid, "conditions": {}}, 2),
            ("tags-create.json", {**valid, "bypass_actors": [{**APP, "actor_id": True}]}, 2),
            ("tags-create.json", {**valid, "bypass_actors": [{**APP, "actor_id": 123.0}]}, 2),
            ("unlisted.json", valid, 2),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / ".github/rulesets").mkdir(parents=True)
            (base / ".xtemplates").mkdir()
            (base / ".xtemplates/scripts").symlink_to(ROOT / "scripts", target_is_directory=True)
            bin_dir = base / "bin"
            bin_dir.mkdir()
            fake = bin_dir / "gh"
            fake.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$XT_TAG_TEST_CALLS"\n')
            fake.chmod(0o700)
            calls = base / "calls"
            for filename, doc, expected in cases:
                with self.subTest(filename=filename, doc=doc):
                    relative = ".github/rulesets/" + filename
                    if doc is None:
                        (base / relative).unlink(missing_ok=True)
                    else:
                        (base / relative).write_text(doc if isinstance(doc, str) else json.dumps(doc))
                    calls.write_text("")
                    env = {
                        **os.environ,
                        "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
                        "GH_REPO": "fixture/example",
                        "XT_NEW_RULESET_FILE": relative,
                        "XT_EXISTING_RULESET_ID": "",
                        "XT_TAG_TEST_CALLS": str(calls),
                    }
                    result = subprocess.run(
                        ["sh", "-c", script],
                        cwd=base,
                        env=env,
                        input="fixture/example\n",
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, expected, result.stderr)
                    self.assertEqual("--method POST" in calls.read_text(), expected == 0)
            # Cùng bộ kiểm ở repo khung; di trú cập nhật đúng ID cũ, không POST thêm bản trùng tên.
            (base / "framework/00-method").mkdir(parents=True)
            (base / "framework/00-method/README.md").write_text("# framework\n")
            (base / "scripts").symlink_to(ROOT / "scripts", target_is_directory=True)
            relative = ".github/rulesets/tags.json"
            (base / relative).write_text(json.dumps(template("tags.json")))
            for identifier, expected in (("321", 0), ("0", 2), ("123.0", 2), ("../321", 2)):
                with self.subTest(existing_id=identifier):
                    calls.write_text("")
                    result = subprocess.run(
                        ["sh", "-c", script],
                        cwd=base,
                        env={**env, "XT_NEW_RULESET_FILE": relative, "XT_EXISTING_RULESET_ID": identifier},
                        input="fixture/example\n",
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, expected, result.stderr)
                    self.assertNotIn("--method POST", calls.read_text())
                    self.assertEqual("--method PUT" in calls.read_text(), expected == 0)
                    if expected == 0:
                        self.assertIn("rulesets/321", calls.read_text())

    def test_tag_rule_order_is_semantic_but_scope_and_bypass_stay_exact(self):
        expected = template("tags.json")
        origin = mock.Mock(spec=setup.Origin)
        reversed_rules = {**expected, "rules": list(reversed(expected["rules"]))}
        origin.get.return_value = reversed_rules
        self.assertEqual(setup.match_rules(origin, 7, expected), setup.OK)
        for change in ({"bypass_actors": [APP]}, {"conditions": {}}, {"rules": None}):
            with self.subTest(change=change):
                origin.get.return_value = {**reversed_rules, **change}
                self.assertEqual(setup.match_rules(origin, 7, expected), setup.MISSING)
        for identifier, invalid in ((123, 123.0), (1, True)):
            creation = {**template("tags-create.json"), "bypass_actors": [{**APP, "actor_id": identifier}]}
            origin.get.return_value = {**creation, "bypass_actors": [{**APP, "actor_id": invalid}]}
            self.assertEqual(setup.match_rules(origin, 7, creation), setup.MISSING)

    def test_readmes_describe_every_installed_github_template(self):
        for relative in ("README.md", "framework/templates/README.md"):
            with self.subTest(relative=relative):
                text = (ROOT / relative).read_text()
                self.assertTrue(f"`--with-github` cài {len(install.GITHUB_FILES)} tệp" in text, relative)
                self.assertIn("tags-create.json", text)


class TagRulesetInventory(GithubFixture, TmpRepoCase):
    def setUp(self):
        super().setUp()
        self.init_repo()
        self.commit_files({"xt.yaml": "deploy_envs: dev\n"}, 1)
        self.enterContext(mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.repo)}))
        self.fake_github(deny=True)

    def test_only_ruleset_does_not_read_unrelated_setup_or_dev_ledger(self):
        with mock.patch.object(xt, "read_deploy_ledger", side_effect=AssertionError("unexpected ledger read")):
            rc, output, _ = run_main("admin-plan", "--only", "ruleset", "--json")
        self.assertEqual(rc, 0, output)
        doc = json.loads(output)
        self.assertEqual([(r["id"], r["status"]) for r in doc["items"]], [("ruleset", setup.OK)])
        self.assertEqual(doc["dev"], {"state": "not_checked", "digest": None})
        calls = (self.tmp / "calls").read_text()
        self.assertNotIn("actions/secrets", calls)
        self.assertNotIn("automated-security-fixes", calls)
        self.assertNotIn("worker.yml", calls)
        self.assertNotIn("PLAN.md", calls)
        self.assertNotIn("contents/xt.yaml?", calls)
        rc, output, _ = run_main("admin-plan", "--only", "ruleset", "--out", "setup.md")
        self.assertEqual(rc, 0, output)
        self.assertIn("| ruleset | đạt |", output)
        self.assertNotIn("bot-token", output)

    def test_only_isolated_local_or_missing_row_and_unknown_selection(self):
        with mock.patch.object(setup, "Origin", side_effect=AssertionError("unexpected remote read")):
            rc, output, _ = run_main("admin-plan", "--only", "deferred", "--json")
        self.assertEqual(rc, 0, output)
        self.assertEqual([r["id"] for r in json.loads(output)["items"]], ["deferred"])
        rc, output, _ = run_main("admin-plan", "--only", "bot-token", "--json")
        self.assertEqual(rc, 1, output)
        self.assertEqual([r["id"] for r in json.loads(output)["items"]], ["bot-token"])
        self.assertEqual(run_main("admin-plan", "--only", "does-not-exist")[0], 2)
        self.assertEqual(run_main("admin-plan", "--only", "")[0], 2)

    def test_each_tag_ruleset_is_required_and_empty_actor_never_passes(self):
        path = self.tmp / "routes.json"
        original = json.loads(path.read_text())
        endpoint = "rulesets?per_page=100&page=1"
        for missing in ("tags", "tags-create"):
            with self.subTest(missing=missing):
                changed = copy.deepcopy(original)
                changed[endpoint] = [r for r in changed[endpoint] if r["name"] != missing]
                path.write_text(json.dumps(changed))
                self.assertEqual(run_main("admin-plan", "--only", "ruleset")[0], 1)
        changed = copy.deepcopy(original)
        creation = changed["rulesets/2"]
        creation["bypass_actors"] = []
        file_key = next(k for k in changed if k.startswith("contents/.github/rulesets/tags-create.json?"))
        changed[file_key]["content"] = base64.b64encode(json.dumps(creation).encode()).decode()
        path.write_text(json.dumps(changed))
        self.assertEqual(run_main("admin-plan", "--only", "ruleset")[0], 1)
        rc, script, _ = run_main("admin-plan", "--only", "ruleset", "--script")
        self.assertEqual(rc, 1)
        self.assertIn("tags-create.json", script)
        self.assertNotIn("gh secret set", script)

    def test_existing_combined_ruleset_needs_update_and_duplicate_names_never_pass(self):
        path = self.tmp / "routes.json"
        original = json.loads(path.read_text())
        changed = copy.deepcopy(original)
        changed["rulesets/1"]["rules"].append({"type": "creation"})
        path.write_text(json.dumps(changed))
        self.assertEqual(run_main("admin-plan", "--only", "ruleset")[0], 1)
        # Dù mục đầu đúng, mục trùng tên phía sau vẫn giữ creation; không được báo xanh bằng found[0].
        changed = copy.deepcopy(original)
        old = {**changed["rulesets/1"], "id": 99, "rules": [{"type": "creation"}]}
        changed["rulesets?per_page=100&page=1"].append(old)
        path.write_text(json.dumps(changed))
        self.assertEqual(run_main("admin-plan", "--only", "ruleset")[0], 1)
        path.write_text(json.dumps(original))
        self.assertEqual(run_main("admin-plan", "--only", "ruleset")[0], 0)

    def test_malformed_expected_rule_and_missing_remote_sha_remain_unknown(self):
        origin = mock.Mock(spec=setup.Origin)
        origin.file.return_value = "[]"
        self.assertEqual(setup.rules_file_status(origin, [], "tags.json", "tag"), setup.UNKNOWN)
        origin.file.return_value = None
        origin.sha = None
        self.assertEqual(setup.rules_file_status(origin, [], "tags-create.json", "tag"), setup.UNKNOWN)
