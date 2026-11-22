"""Trạng thái chưa biết, dữ liệu bị cắt và chỉ dẫn cho chủ repo của admin-plan."""

import json
import os
from pathlib import Path
import subprocess
import sys
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_admin_plan import GithubFixture
from test_xt_cli import TmpRepoCase, run_main, xt
import xt_ops_setup as setup


class SetupEvidenceEdges(GithubFixture, TmpRepoCase):
    def setUp(self):
        super().setUp()
        self.init_repo()
        self.commit_files({"xt.yaml": "deploy_envs: dev\n"}, 1)
        self.enterContext(mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.repo)}))

    def test_isolated_python_can_load_the_cli_companions(self):
        cmd = subprocess.run(
            [sys.executable, "-I", str(xt.SCRIPT_DIR / "xt.py"), "admin-plan", "--json"],
            cwd=self.repo,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(cmd.returncode, 1, cmd.stderr)
        self.assertEqual(json.loads(cmd.stdout)["dev"], {"state": "absent", "digest": None})

    def test_unavailable_api_cached_and_truncated_lists_never_confirm(self):
        self.fake_github()
        origin = setup.Origin(xt, self.repo)
        with mock.patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired("gh", 15)) as get:
            self.assertIsNone(origin.get("temporarily-unavailable"))
            self.assertIsNone(origin.get("temporarily-unavailable"))
            get.assert_called_once()
        for response in (None, {"encoding": "base64", "content": 7}, {"encoding": "base64", "content": "%%%"}):
            with self.subTest(response=response), mock.patch.object(origin, "get", return_value=response):
                self.assertIsNone(origin.file("xt.yaml"))
        full_page = [{"name": str(i)} for i in range(100)]
        with mock.patch.object(origin, "get", side_effect=[full_page, [{"name": "last"}]]) as api:
            self.assertEqual(origin.pages("rulesets"), [*full_page, {"name": "last"}])
            self.assertEqual(api.call_args_list[-1].args, ("rulesets?per_page=100&page=2",))
        with mock.patch.object(origin, "get", return_value=full_page) as api:
            self.assertIsNone(origin.pages("rulesets"))
            self.assertEqual(api.call_count, 50)
        self.assertEqual(setup.names_status(origin, set(), None), setup.SKIP)
        self.assertEqual(setup.deploy_secret_status(origin, {"deploy_secrets": "bad-name"}), setup.UNKNOWN)

    def test_ruleset_missing_unreadable_and_inactive_remain_distinct(self):
        origin = mock.Mock(spec=setup.Origin)
        origin.has_origin = True
        origin.sha = "a" * 40
        origin.branch = "main"
        origin.pages.return_value = None
        self.assertEqual(setup.rules_status(origin), setup.UNKNOWN)
        origin.pages.return_value = [{"name": "main", "target": "branch", "id": 7}]
        for raw, expected in [(None, setup.MISSING), ("{", setup.UNKNOWN), ('{"name":"absent"}', setup.MISSING)]:
            with self.subTest(raw=raw):
                origin.file.return_value = raw
                self.assertEqual(setup.rules_status(origin), expected)
        rule = {
            "name": "main",
            "target": "branch",
            "conditions": {},
            "rules": [],
            "bypass_actors": [],
            "enforcement": "active",
        }
        origin.file.return_value = json.dumps(rule)
        origin.get.return_value = {"name": "main"}
        self.assertEqual(setup.rules_status(origin), setup.UNKNOWN)
        self.assertEqual(setup.match_rules(origin, None, rule), setup.UNKNOWN)
        origin.get.return_value = rule
        self.assertEqual(setup.match_rules(origin, 7, {**rule, "enforcement": "disabled"}), setup.MISSING)
        self.assertEqual(setup.match_rules(origin, 7, {**rule, "bypass_actors": [{"actor_id": 5}]}), setup.MISSING)

    def test_incomplete_blueprint_machine_state_and_corrupt_ledger(self):
        def statuses():
            return {item["id"]: item for item in setup.local_items(xt, self.repo)}

        self.assertEqual(statuses()["human-musts"]["status"], setup.UNKNOWN)
        blueprint = self.repo / "BLUEPRINT.md"
        blueprint.write_text("Chưa có checklist hợp lệ.\n")
        self.assertEqual(statuses()["human-musts"]["status"], setup.UNKNOWN)
        blueprint.write_text("- [ ] `OPS-IR-006` **MUST** Diễn tập ứng cứu.\n")
        self.assertEqual(statuses()["human-musts"]["ids"], ["OPS-IR-006"])
        self.assertEqual(statuses()["human-musts"]["status"], setup.MISSING)
        state = xt.state_dir(self.repo) / "state.json"
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text("{")
        self.assertEqual(statuses()["deferred"]["status"], setup.UNKNOWN)
        state.write_text(json.dumps({"deferred": {"T-123": {}, "misc": {}}}))
        self.assertEqual(statuses()["deferred"]["ids"], ["T-123"])
        self.assertEqual(statuses()["deferred"]["status"], setup.MISSING)
        state.write_text("{}")
        self.assertEqual(statuses()["deferred"]["status"], setup.OK)
        ledger = self.repo / xt.DEPLOY_LEDGER
        ledger.parent.mkdir(parents=True)
        ledger.write_text("{")
        rc, output, _ = run_main("admin-plan", "--json")
        self.assertEqual(rc, 1)
        self.assertEqual(json.loads(output)["dev"], {"state": "unreadable", "digest": None})

    def test_owner_script_proposes_only_missing_operations(self):
        self.fake_github()
        routing = self.tmp / "routes.json"
        routes = json.loads(routing.read_text())
        routes["automated-security-fixes"] = {"enabled": False}
        routing.write_text(json.dumps(routes))
        rc, script, _ = run_main("admin-plan", "--script")
        self.assertEqual(rc, 1)
        self.assertIn('gh api --method PUT "repos/$GH_REPO/automated-security-fixes"', script)
        self.assertNotIn("gh secret set", script)
        self.assertNotIn("--method POST", script)

    def test_repo_about_describes_project_and_stays_optional(self):
        """WF-DOC-021: About/homepage/topics trống, chưa đọc được hoặc nhắc khung ngoài ghi chú nguồn → tuỳ chọn kèm
        `gh repo edit` (không làm admin-plan đỏ); mô tả dự án → đạt; không origin/repo khung → không áp."""
        origin = mock.Mock(spec=setup.Origin)
        origin.has_origin, origin.base = False, self.repo
        self.assertEqual(setup.about_status(origin), (setup.SKIP, []))
        origin.has_origin = True
        note = "Áp dụng từ phiên bản v3.34.0 của dự án X-Templates"
        cases = [
            (None, setup.OPTIONAL),
            ({"description": "Quản lý khách sạn", "topics": ["hotel"], "homepage": None}, setup.OK),
            ({"description": f"Quản lý khách sạn. {note}", "topics": "bad"}, setup.OK),
            ({"description": "  ", "topics": []}, setup.OPTIONAL),
            ({"description": None}, setup.OPTIONAL),
            ({"description": "Bản sao X-Templates"}, setup.OPTIONAL),
            ({"description": "Khách sạn", "homepage": "https://github.com/o/X-Templates"}, setup.OPTIONAL),
            # AUD-XFEAT-053: homepage là URL khung ngay sau description chứa đầu ghi chú nguồn không phải dòng bị ngắt.
            ({"description": note, "homepage": "https://github.com/o/X-Templates"}, setup.OPTIONAL),
            ({"description": "Khách sạn", "topics": ["x-templates"]}, setup.OPTIONAL),
        ]
        for doc, expected in cases:
            with self.subTest(doc=doc):
                origin.get.return_value = doc
                status, changes = setup.about_status(origin)
                self.assertEqual(status, expected)
                self.assertEqual(bool(changes), expected == setup.OPTIONAL)
                if changes and doc is not None:
                    self.assertIn('gh repo edit --description "<mô tả dự án>"', changes[0])
        # AUD-CODE-066: API không đọc được thì nói "chưa đọc được", không nói "đang trống".
        origin.get.return_value = None
        unreadable = setup.about_status(origin)[1][0]
        self.assertIn("chưa đọc được", unreadable)
        self.assertNotIn("đang trống", unreadable)
        # AUD-CODE-067: lỗi API tạm thời không được gợi ý ghi đè mô tả đang có.
        self.assertNotIn("gh repo edit --description", unreadable)
        self.assertIn("gh repo view", unreadable)
        origin.get.return_value = {"description": "  "}
        self.assertIn("đang trống", setup.about_status(origin)[1][0])
        (self.repo / "framework" / "00-method").mkdir(parents=True)
        (self.repo / "framework" / "00-method" / "README.md").write_text("# khung\n")
        self.assertEqual(setup.about_status(origin), (setup.SKIP, []))

    def test_repo_about_row_renders_once_under_optional_heading(self):
        self.fake_github()
        _, text, _ = run_main("admin-plan", "--json")
        items = {i["id"]: i for i in json.loads(text)["items"]}
        self.assertEqual(items["repo-about"]["status"], setup.OPTIONAL)  # không vào BLOCKS: test_admin_plan rc 0
        _, markdown, _ = run_main("admin-plan")
        self.assertEqual(markdown.count("## Tuỳ chọn — chủ dự án quyết"), 1)
        self.assertIn('- gh repo edit --description "<mô tả dự án>"', markdown)
        done = {"dev": {"state": "absent", "digest": None}, "at": "2026-11-21", "head": None}
        items = [{"id": "repo-about", "status": setup.OK, "changes": []}]
        self.assertNotIn("## Tuỳ chọn", setup.markdown({**done, "items": items}))
        routing = self.tmp / "routes.json"
        routes = json.loads(routing.read_text())
        routes[""]["description"] = "Sổ ghi chú cho nhóm"
        routing.write_text(json.dumps(routes))
        _, text, _ = run_main("admin-plan", "--json")
        self.assertEqual({i["id"]: i["status"] for i in json.loads(text)["items"]}["repo-about"], setup.OK)

    def test_core_protocol_covers_every_referenced_attribute_on_xt(self):
        """AUD-ARCH-015: xt_ops_setup, xt_release_ops, xt_deploy dùng Core(Protocol) thay vì ModuleType; mọi thuộc tính
        truy cập qua core trong AST đều khai trên Protocol và có thật trên module xt."""
        import ast
        import xt_deploy
        import xt_release_ops

        for mod in (setup, xt_release_ops, xt_deploy):
            declared = {k for cls in mod.Core.__mro__ for k in getattr(cls, "__annotations__", {})}
            tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
            used = {
                node.attr
                for node in ast.walk(tree)
                if isinstance(node, ast.Attribute)
                and (
                    (isinstance(node.value, ast.Name) and node.value.id == "core")
                    or (isinstance(node.value, ast.Attribute) and node.value.attr == "core")
                )
            }
            self.assertTrue(used <= declared, f"{mod.__name__}: thiếu trong Core Protocol: {sorted(used - declared)}")
            missing = [name for name in declared if not hasattr(xt, name)]
            self.assertEqual(missing, [], f"{mod.__name__}: tên không có trên xt: {missing}")

    def test_field_workflow_status_checks_environment_only(self):
        """AUD-CI-037, AUD-CI-040: không có xt-field.yml → SKIP; không origin có file → MISSING; có environment
        `xt-field-read` (không phân biệt hoa thường, không xét quyền tạo PR của Actions) → OK; thiếu → MISSING."""
        origin = mock.Mock(spec=setup.Origin)
        origin.has_origin, origin.base, origin.sha = False, self.repo, None
        self.assertEqual(setup.field_workflow_status(origin), setup.SKIP)
        wf = self.repo / ".github" / "workflows" / "xt-field.yml"
        wf.parent.mkdir(parents=True, exist_ok=True)
        wf.write_text("name: xt-field\n", encoding="utf-8")
        self.assertEqual(setup.field_workflow_status(origin), setup.MISSING)

        origin.has_origin = True
        self.assertEqual(setup.field_workflow_status(origin), setup.UNKNOWN)

        origin.sha = "a" * 40
        origin.file.return_value = None
        self.assertEqual(setup.field_workflow_status(origin), setup.SKIP)

        origin.file.return_value = "name: xt-field\n"
        origin.pages.return_value = [{"name": "xt-field-read"}]
        self.assertEqual(setup.field_workflow_status(origin), setup.OK)

        # AUD-CI-040: PR mở bằng XT_STEWARD_TOKEN nên không xét quyền của GITHUB_TOKEN; tên không phân biệt hoa thường.
        origin.pages.return_value = [{"name": "XT-Field-Read"}]
        self.assertEqual(setup.field_workflow_status(origin), setup.OK)

        origin.pages.return_value = [{"name": "other"}]
        self.assertEqual(setup.field_workflow_status(origin), setup.MISSING)

        origin.pages.return_value = None
        self.assertEqual(setup.field_workflow_status(origin), setup.UNKNOWN)
