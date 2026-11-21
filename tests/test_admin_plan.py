"""Read-only one-time owner checklist and protected GitHub fixture."""

import base64
import json
import os
from pathlib import Path
import sys
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_xt_cli import TmpRepoCase, run_main
import xt_ops_setup as ops_setup


class GithubFixture:
    def fake_github(self, deny=False):
        self.git("remote", "add", "origin", "git@github.com:factory/example.git")
        cfg = (
            "deploy_envs: dev prod\n"
            + "".join(f"{key}_prod: ./adapter {key}\n" for key in ("deploy", "smoke", "digest", "rollback"))
            + "worker_budget_usd: 5\nworker_max_turns: 10\ndeploy_secrets: XT_PRODUCT\n"
        )
        rules = [
            {
                "name": name,
                "target": target,
                "enforcement": "active",
                "bypass_actors": [],
                "conditions": {"ref_name": {"include": [pattern], "exclude": []}},
                "rules": [{"type": "deletion"}],
            }
            for name, target, pattern in (("main", "branch", "~DEFAULT_BRANCH"), ("tags", "tag", "refs/tags/v*"))
        ]
        sha = self.git("rev-parse", "HEAD")
        files = {
            "xt.yaml": cfg,
            "docs/autopilot/PLAN.md": "- grant: deploy | env=prod\n",
            ".github/workflows/worker.yml": "on: workflow_dispatch\n",
        }
        files.update({f".github/rulesets/{rule['name']}.json": json.dumps(rule) for rule in rules})
        docs = {
            "": {"default_branch": "main"},
            "commits/main": {"sha": sha},
            "actions/secrets?per_page=100&page=1": None
            if deny
            else {"secrets": [{"name": "XT_STEWARD_TOKEN"}, {"name": "XT_PRODUCT"}]},
            "automated-security-fixes": {"enabled": True},
            "rules/branches/main": [{"type": "deletion"}],
            "rulesets?per_page=100&page=1": [{**r, "id": i} for i, r in enumerate(rules)],
        }
        docs.update({f"rulesets/{i}": r for i, r in enumerate(rules)})
        docs.update(
            {
                f"contents/{key}?ref={sha}": {
                    "encoding": "base64",
                    "content": base64.b64encode(value.encode()).decode(),
                }
                for key, value in files.items()
            }
        )
        (self.tmp / "routes.json").write_text(json.dumps(docs))
        exe = self.tmp / "gh"
        exe.write_text(
            "#!"
            + sys.executable
            + "\n"
            + """import json, pathlib, sys
root = pathlib.Path(__file__).parent
args = sys.argv[1:]
assert args[:5] == ['api', '--hostname', 'github.com', '--method', 'GET']
assert args[5].startswith('repos/factory/example')
key = args[5].removeprefix('repos/factory/example').lstrip('/')
with (root / 'calls').open('a') as f: print(key, file=f)
doc = json.loads((root / 'routes.json').read_text()).get(key)
if doc is None: print('private-value', file=sys.stderr); sys.exit(1)
print(json.dumps(doc))
"""
        )
        exe.chmod(0o700)
        self.enterContext(mock.patch.dict(os.environ, {"PATH": str(self.tmp) + os.pathsep + os.environ["PATH"]}))


class SetupTest(GithubFixture, TmpRepoCase):
    def setUp(self):
        super().setUp()
        self.init_repo()
        self.commit_files(
            {"xt.yaml": "deploy_envs: dev\n", "BLUEPRINT.md": "- [x] `OPS-IR-006` **MUST** Đã diễn tập.\n"}, 1
        )
        self.enterContext(
            mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.repo), "GH_TOKEN": "private-value"})
        )

    def test_fresh_repo_no_remote_never_claims_setup(self):
        (self.repo / "xt.yaml").write_text("release_signoff: agent\nworker_budget_usd: 5\nworker_max_turns: 10")
        before = self.git("status", "--porcelain")
        rc, out, _ = run_main("admin-plan", "--json")
        self.assertEqual(rc, 1)
        items = {i["id"]: i for i in json.loads(out)["items"]}
        for key in ("repo", "bot-token", "worker-budget", "deploy-target"):
            self.assertEqual(items[key]["status"], ops_setup.MISSING)
        self.assertEqual(items["gated-keys"]["status"], ops_setup.OPTIONAL)
        self.assertEqual(items["field-workflow"]["status"], ops_setup.SKIP)
        self.assertEqual(len(items), 14)
        self.assertEqual(self.git("status", "--porcelain"), before)
        self.assertNotIn("private-value", out)
        self.assertEqual(run_main("admin-plan", "--out", "../outside.md")[0], 2)
        self.assertEqual(run_main("admin-plan", "--out", "BLUEPRINT.md")[0], 2)
        rc, script, _ = run_main("admin-plan", "--script", "--out", "docs/ops/SETUP-ONCE.md")
        self.assertEqual(rc, 1)
        self.assertIn("gh secret set", script)
        self.assertNotIn("private-value", (self.repo / "docs/ops/SETUP-ONCE.md").read_text())

    def test_secret_api_unreadable_is_distinct_and_sanitized(self):
        self.fake_github(deny=True)
        rc, text, _ = run_main("admin-plan", "--json")
        self.assertEqual(rc, 1)
        self.assertNotIn("private-value", text)
        responses = {r["id"]: r["status"] for r in json.loads(text)["items"]}
        self.assertEqual(responses["bot-token"], ops_setup.UNKNOWN)
        self.assertEqual(responses["deploy-secrets"], ops_setup.UNKNOWN)

    def test_complete_optional_permissions_and_get_only(self):
        self.fake_github()
        rc, text, err = run_main("admin-plan", "--json", "--out", "setup.md")
        self.assertEqual(rc, 0, (text, err))
        responses = {r["id"]: r["status"] for r in json.loads(text)["items"]}
        self.assertEqual(responses["gated-keys"], ops_setup.OPTIONAL)
        self.assertEqual(responses["repo-about"], ops_setup.OPTIONAL)  # WF-DOC-021: SHOULD — không làm rc đỏ
        self.assertEqual(responses["deploy-target"], ops_setup.OK)
        self.assertIn("Không còn việc thiết lập", (self.repo / "setup.md").read_text())

    def test_agent_guard_blocks_owner_only_script_statements_without_executing_them(self):
        _, script, _ = run_main("admin-plan", "--script")
        # Run the guard's classifier on the exact generated statements. No gh mutation is invoked.
        repo = Path(__file__).resolve().parents[1]
        commands = [
            line.strip().removesuffix(" ;;")
            for line in script.splitlines()
            if line.strip().startswith(("gh secret set ", "gh api --method POST "))
        ]
        self.assertEqual(len(commands), 2)
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(repo)}):
            for cmd in commands:
                self.assertEqual(run_main("guard-check", "--", cmd)[0], 126)
