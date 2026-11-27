"""Consumer waves, withdrawal, failure to obtain provenance, and updating one review branch."""

from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_promotion_gate import ROOT, ReleaseFixture, dist, xt
import install


class ProjectFixture(ReleaseFixture):
    def setUp(self):
        super().setUp()
        self.project = self.temp / "product"
        self.project.mkdir()
        self.git(self.project, "init", "-qb", "main")
        self.git(self.project, "remote", "add", "origin", "https://github.com/test/project.git")
        (self.project / ".xtemplates").mkdir()
        (self.project / dist.MANIFEST).write_text(json.dumps({"source": {"repo": "test/framework"}, "packs": {}}))
        (self.project / ".xtemplates/VERSION").write_text("1.0.0 (abcdef)\n")
        (self.project / "xt.yaml").write_text("upgrade_wave: canary\n")
        self.git(self.project, "add", ".")
        self.git(self.project, "commit", "-qm", "project")
        self.origin = self.temp / "origin.git"
        self.git(self.temp, "clone", "--bare", str(self.project), str(self.origin))
        self.enterContext(contextlib.chdir(self.project))

    def tag_release(self, version, days):
        (self.up / "VERSION").write_text(version + "\n")
        day = dt.datetime.now(dt.UTC) - dt.timedelta(days=days, minutes=2)
        self.git(self.up, "add", ".")
        with mock.patch.dict(os.environ, {"GIT_COMMITTER_DATE": day.isoformat()}):
            self.git(self.up, "commit", "-qm", version)
            self.git(self.up, "tag", "-am", version, "v" + version)
        self.sign("v" + version)


class UpgradeTest(ProjectFixture):
    def release(self, version, days=0):
        (self.up / "CHANGELOG.md").write_text(f"## [{version}] - 2026-11-20\n\n- Framework update\n")
        scripts = self.up / "scripts"
        scripts.mkdir(exist_ok=True)
        (scripts / "install.py").write_text(
            "from pathlib import Path\n"
            "d=Path('.xtemplates/scripts');d.mkdir(exist_ok=True)\n"
            "(d/'xt.py').write_text('from pathlib import Path\\nassert Path(\\\"BLUEPRINT.md\\\").exists()\\n')\n"
            "(Path('.xtemplates')/'VERSION').write_text(Path(__file__).parents[1].joinpath('VERSION').read_text())\n"
            "Path('BLUEPRINT.md').write_text('verified release fixture')\n"
        )
        self.tag_release(version, days)

    def test_select_newest_aged_and_skip_withdrawn(self):
        self.assertEqual(xt.main(["upgrade", "check"]), 0)
        self.release("1.1.0", 5)
        self.release("1.2.0", 1)
        now = int(dt.datetime.now(dt.UTC).timestamp())
        self.assertEqual(dist.tags_for_wave(self.up, "1.0.0", "after-canary", 3, now), (True, ["v1.1.0"]))
        self.assertEqual(xt.main(["upgrade", "check"]), 10)
        withdrawn = self.up / dist.WITHDRAWN
        withdrawn.parent.mkdir(parents=True)
        withdrawn.write_text("# Reason\n\n1.1.0 — withdrawn\n")
        self.git(self.up, "add", ".")
        self.git(self.up, "commit", "-qm", "withdraw")
        (self.project / "xt.yaml").write_text("upgrade_wave: after-canary\n")
        self.assertEqual(xt.main(["upgrade", "check"]), 11)
        self.assertEqual(dist.tags_for_wave(self.up, "1.0.0", "canary", 3, now), (True, ["v1.2.0"]))
        withdrawn.write_text("unparseable withdrawal")
        self.git(self.up, "commit", "-qam", "invalid list")
        self.assertEqual(xt.main(["upgrade", "check"]), 3)

    def test_network_failure_unsigned_and_invalid_configuration_never_install(self):
        self.release("1.1.0")
        self.signed.clear()
        with mock.patch.object(dist, "publish_upgrade") as publish:
            self.assertEqual(xt.main(["upgrade", "open-pr"]), 11)
            with mock.patch.object(dist, "verified_archive", side_effect=dist.DistributionError("network")):
                self.assertEqual(xt.main(["upgrade", "open-pr"]), 3)
            publish.assert_not_called()
        (self.project / "xt.yaml").write_text("upgrade_wave: invalid\n")
        self.assertEqual(xt.main(["upgrade", "check"]), 2)
        (self.project / dist.MANIFEST).write_text("[]")
        self.assertEqual(xt.main(["upgrade", "check"]), 3)

    def test_target_changes_configuration_or_identity_before_publication(self):
        self.release("1.1.0")
        self.git(self.up, "tag", "notes")
        (self.project / ".xtemplates/VERSION").write_text("0.9.0")
        self.assertEqual(xt.main(["upgrade", "open-pr"]), 3)
        (self.project / ".xtemplates/VERSION").write_text("1.0.0")
        for packs, result in [(False, 2), ({"tool": {}}, 0)]:
            manifest = {"source": {"repo": "test/framework"}, "packs": packs, "adapters": [".codex/hooks.json"]}
            (self.project / dist.MANIFEST).write_text(json.dumps(manifest))
            self.git(self.project, "add", ".")
            self.git(self.project, "commit", "-qm", "update project manifest")
            self.git(self.project, "push", str(self.origin), "HEAD:main")
            self.assertEqual(xt.main(["upgrade", "open-pr"]), result)
        self.git(self.origin, "symbolic-ref", "HEAD", "refs/heads/" + dist.UPGRADE_BRANCH)
        self.assertEqual(xt.main(["upgrade", "open-pr"]), 3)

    def test_historical_attestation_without_promotion_receipt_is_not_auto_installed(self):
        self.release("1.1.0")
        self.has_promotion = False
        self.assertEqual(xt.main(["release-verify", "--tag", "v1.1.0", "--repo", "test/framework"]), 0)
        self.assertEqual(xt.main(["upgrade", "open-pr"]), 11)
        self.assertFalse(any(cmd[:3] == ("gh", "pr", "create") for cmd in self.gh))

    def test_pr_contains_verified_tree_and_retry_updates_same_pr(self):
        self.release("1.1.0")
        (self.up / "VERSION").write_text("1.2.0-dev")
        self.git(self.up, "commit", "-qam", "default branch is ahead")
        self.assertEqual(xt.main(["upgrade", "open-pr"]), 0)
        ref = "refs/heads/" + dist.UPGRADE_BRANCH
        old = self.git(self.origin, "rev-parse", ref)
        receipt = json.loads(self.git(self.origin, "show", f"{ref}:{dist.MANIFEST}"))["source"]
        self.assertEqual(
            receipt,
            {
                "repo": "test/framework",
                "tag": "v1.1.0",
                "commit": self.git(self.up, "rev-parse", "v1.1.0^{commit}"),
                "verified": True,
            },
        )
        self.assertEqual(self.git(self.origin, "show", f"{ref}:.xtemplates/VERSION"), "1.1.0")
        self.prs = [{"number": 17}]
        self.assertEqual(xt.main(["upgrade", "open-pr"]), 0)
        self.assertEqual(self.git(self.origin, "rev-parse", ref), old)
        self.release("1.2.0")
        self.assertEqual(xt.main(["upgrade", "open-pr"]), 0)
        self.assertEqual(self.git(self.origin, "merge-base", ref, old), old)
        self.assertEqual(sum(a[:3] == ("gh", "pr", "create") for a in self.gh), 1)
        self.assertEqual(sum(a[:3] == ("gh", "pr", "edit") for a in self.gh), 2)

    def test_branch_moved_by_a_concurrent_run_is_never_overwritten(self):
        self.release("1.1.0")
        self.assertEqual(xt.main(["upgrade", "open-pr"]), 0)
        self.release("1.2.0")
        ref = "refs/heads/" + dist.UPGRADE_BRANCH
        raced = self.git(self.origin, "commit-tree", "main^{tree}", "-m", "another run")
        forward = dist.command
        calls = len(self.gh)

        def race(cwd, *argv, check=True, env=None):
            if argv[1:3] == ("init", "--quiet"):  # the other run publishes between this run's clone and its push
                self.git(self.origin, "update-ref", ref, raced)
            return forward(cwd, *argv, check=check, env=env)

        with mock.patch.object(dist, "command", race):
            self.assertEqual(xt.main(["upgrade", "open-pr"]), 3)
        self.assertEqual(self.git(self.origin, "rev-parse", ref), raced)
        self.assertFalse([a for a in self.gh[calls:] if a[:2] == ("gh", "pr")])

    def closed(self):
        return [a[3:] for a in self.gh if a[:3] == ("gh", "pr", "close")]

    def test_version_withdrawn_after_its_pr_opened_closes_that_pr(self):
        """Audit delta 3.35.0: a withdrawal after the PR opened left it open; check/open-pr only answered 11."""
        self.release("1.1.0")
        self.assertEqual(xt.main(["upgrade", "open-pr"]), 0)
        title = dist.TITLE.format("1.1.0")
        self.assertIn(title, self.gh[-1])
        self.prs = ["unexpected", {"number": 9, "title": "feat: other"}, {"number": 17, "title": title}]
        withdrawn = self.up / dist.WITHDRAWN
        withdrawn.parent.mkdir(parents=True)
        withdrawn.write_text("1.1.0 — broken\n")
        self.git(self.up, "add", ".")
        self.git(self.up, "commit", "-qm", "withdraw 1.1.0")
        self.assertEqual(xt.main(["upgrade", "check"]), 10)  # the workflow then runs open-pr with the project's token
        self.assertEqual(self.closed(), [])
        self.assertEqual(xt.main(["upgrade", "open-pr"]), 0)
        self.assertEqual([c[:3] for c in self.closed()], [("17", "--repo", "test/project")])
        self.assertIn("v1.1.0", self.closed()[0][-1])
        ref = f"refs/heads/{dist.UPGRADE_BRANCH}"
        self.assertEqual(self.git(self.origin, "show", f"{ref}:.xtemplates/VERSION"), "1.1.0")  # reopenable
        self.prs = [{"number": 18, "title": dist.TITLE.format("1.0.5")}]
        self.assertEqual(xt.main(["upgrade", "open-pr"]), 11)
        self.api_rc = 1  # a token that cannot list PRs only warns: upgrades keep flowing
        self.assertEqual(xt.main(["upgrade", "check"]), 11)
        self.assertEqual(len(self.closed()), 1)
        self.api_rc = 0
        self.prs = [{"number": 17, "title": title}]
        self.release("1.2.0")  # a newer valid release replaces the withdrawn tree in the same PR
        self.assertEqual(xt.main(["upgrade", "open-pr"]), 0)
        self.assertEqual(self.git(self.origin, "show", f"{ref}:.xtemplates/VERSION"), "1.2.0")
        self.assertEqual((len(self.closed()), self.gh[-1][:4]), (1, ("gh", "pr", "edit", "17")))

    def test_reinstall_keeps_recorded_adapters_and_harness_choice(self):
        base = ["--with-github", "--no-git-hooks"]
        cases = [
            ({}, base),
            ({"adapters": "broken", "files": []}, base),
            ({"adapters": [".cursor/hooks.json", 5, ".codex/hooks.json", "x"]}, [*base, "--harness", "codex,cursor"]),
            ({"codex_files": {".agents/skills/a/SKILL.md": "sha256:0"}}, [*base, "--harness", "codex"]),
            ({"files": {".claude/settings.json": "sha256:0", "AGENTS.md": "sha256:0"}}, base),
            ({"files": {"AGENTS.md": "sha256:0"}}, [*base, "--no-harness"]),
        ]
        for manifest, options in cases:
            with self.subTest(manifest=manifest):
                self.assertEqual(dist.install_options(manifest), options)
        self.assertEqual(dist.ADAPTER_HOSTS, {dst: host for host, (_src, dst) in install.ADAPTERS.items()})

    def test_legacy_model_selection_requires_an_unchanged_managed_agent(self):
        rel = ".codex/agents/executor.toml"
        agent_path = self.project / rel
        agent_path.parent.mkdir(parents=True)
        for body, expected in ((b'model = "test"', True), (b"model = 2", False), (b"invalid TOML", False)):
            with self.subTest(body=body):
                agent_path.write_bytes(body)
                manifest = {"codex_files": {rel: f"sha256:{hashlib.sha256(body).hexdigest()}"}}
                self.assertIs(dist.codex_models_selected(manifest, self.project), expected)
                self.assertFalse(dist.codex_models_selected({"codex_files": {rel: "sha256:stale"}}, self.project))
        self.assertFalse(dist.codex_models_selected({"codex_files": {rel: None}}, self.project))
        self.assertFalse(dist.codex_models_selected({"codex_models": False}, self.project))
        pinned = b'model = "test"'
        proposed = agent_path.with_suffix(".toml.xtemplates-new")
        proposed.write_bytes(pinned)
        self.assertTrue(
            dist.codex_models_selected({"codex_files": {rel: hashlib.sha256(pinned).hexdigest()}}, self.project)
        )
        proposed.unlink()
        agent_path.unlink()
        agent_path.symlink_to(self.temp / "outside.toml")
        self.assertFalse(dist.codex_models_selected(manifest, self.project))
        agent_path.parent.rename(agent_path.parent.with_name("agents-old"))
        agent_path.parent.symlink_to(agent_path.parent.with_name("agents-old"), target_is_directory=True)
        self.assertFalse(dist.codex_models_selected(manifest, self.project))


class RealInstallerTest(ProjectFixture):
    """Audit delta 3.35.0, reproduced with the framework's own install.py: the bot clone got the framework git hooks, so
    the commit ran the product commit gate on a runner without dependencies (exit 3, no PR); a project without
    BLUEPRINT.md failed `blueprint-status --run`; and the push ran hooks registered in the clone with the bot's token."""

    def setUp(self):
        super().setUp()
        self.enterContext(mock.patch.dict(os.environ))
        os.environ.pop("CLAUDECODE", None)  # the framework git hook skips itself inside an agent session
        (self.project / "xt.yaml").write_text("upgrade_wave: canary\ncommit_gate: fast\nlint: exit 1\ntest: exit 1\n")
        self.git(self.project, "commit", "-qam", "commit gate that is red without dependencies")
        self.git(self.project, "push", "-q", str(self.origin), "HEAD:main")
        self.seen = self.temp / "seen"
        self.seen.mkdir()
        self.calls = []
        self.plant = False
        forward = dist.command

        def record(cwd, *argv, check=True, env=None):
            self.calls.append((Path(cwd), argv, env))
            if self.plant and argv[-2:] == ("add", "--all"):
                self.plant_hooks(Path(cwd))
            return forward(cwd, *argv, check=check, env=env)

        self.enterContext(mock.patch.object(dist, "command", record))

    def plant_hooks(self, clone):
        """Stand-in for product code that ran in the clone: every hook it can register records the token it sees."""
        script = f'#!/bin/sh\nprintf %s "${{GH_TOKEN-none}}" > "{self.seen}/$(basename "$0")"\n'
        for hooks in (clone / ".git/hooks", clone / ".git/husky"):
            hooks.mkdir(exist_ok=True)
            for name in ("pre-commit", "commit-msg", "post-commit", "pre-push", "reference-transaction"):
                (hooks / name).write_text(script)
                (hooks / name).chmod(0o755)
        self.git(clone, "config", "core.hooksPath", ".git/husky")

    def release(self, version, days=0):
        """Tag the framework's tracked files (working-tree bytes) at `version`."""
        if not (self.up / "scripts/install.py").exists():
            for rel in self.real(ROOT, "git", "ls-files", "-z").stdout.split("\0"):
                src, dst = ROOT / rel, self.up / rel
                if rel and not rel.startswith("tests/") and os.path.lexists(src):
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst, follow_symlinks=False)
        self.tag_release(version, days)

    def test_real_installer_opens_pr_without_hooks_product_checks_or_token(self):
        self.release("1.1.0")
        self.assertEqual(xt.main(["upgrade", "open-pr"]), 0)
        ref = "refs/heads/" + dist.UPGRADE_BRANCH
        files = self.git(self.origin, "ls-tree", "-r", "--name-only", ref).splitlines()
        for path in (".claude/settings.json", ".github/workflows/xt-upgrade.yml", ".xtemplates/scripts/xt.py"):
            self.assertIn(path, files)
        self.assertNotIn("BLUEPRINT.md", files)
        self.assertEqual(self.git(self.origin, "show", f"{ref}:.xtemplates/VERSION").split()[0], "1.1.0")
        installs = [argv for _, argv, _ in self.calls if argv[1:2] and argv[1].endswith("scripts/install.py")]
        self.assertEqual([a[2:] for a in installs], [(".", "--with-github", "--no-git-hooks")])
        first = self.git(self.origin, "rev-parse", ref)
        # Product code later registers hooks in the clone; a blueprint check command is product code too.
        self.plant = True
        (self.project / "BLUEPRINT.md").write_text(f"- [x] `BASE-X-001` **MUST** a — Kiểm: `touch {self.seen}/kiem`\n")
        self.git(self.project, "add", "BLUEPRINT.md")
        self.git(self.project, "commit", "-qm", "blueprint")
        self.git(self.project, "push", "-q", str(self.origin), "HEAD:main")
        self.release("1.2.0")
        self.assertEqual(xt.main(["upgrade", "open-pr"]), 0)
        self.assertEqual(sorted(path.name for path in self.seen.iterdir()), [])  # no hook, no `— Kiểm:` command ran
        self.assertEqual(self.git(self.origin, "show", f"{ref}:.xtemplates/VERSION").split()[0], "1.2.0")
        self.assertEqual(self.git(self.origin, "merge-base", ref, first), first)
        blueprint = [argv for _, argv, _ in self.calls if "blueprint-status" in argv]
        self.assertEqual([a[2:] for a in blueprint], [("blueprint-status", "BLUEPRINT.md")])
        for (
            cwd,
            argv,
            env,
        ) in self.calls:  # allowed: only the authenticated push holds the token, nothing else in clones
            if cwd.name == "project":
                self.assertNotIn("GH_TOKEN", env, argv)
        pushes = [(cwd, argv, env) for cwd, argv, env in self.calls if "https://github.com/test/project.git" in argv]
        pushes = [p for p in pushes if "push" in p[1]]
        self.assertEqual(len(pushes), 2)
        for cwd, argv, env in pushes:
            self.assertEqual((cwd.name, env["GH_TOKEN"]), ("publish.git", "fixture"))
            self.assertLessEqual(set(env), dist.PUSH_ENV | {"GIT_TERMINAL_PROMPT"})
            self.assertTrue(any(arg.startswith("core.hooksPath=") for arg in argv))

    def test_real_upgrade_keeps_pinned_models_from_a_legacy_manifest(self):
        result = self.real(
            self.project,
            sys.executable,
            str(ROOT / "scripts/install.py"),
            ".",
            "--harness",
            "codex",
            "--codex-models",
            "--no-git-hooks",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest_path = self.project / dist.MANIFEST
        manifest = json.loads(manifest_path.read_text())
        original_selection = manifest.pop("codex_models", None)
        manifest["source"] = {"repo": "test/framework"}
        manifest_path.write_text(json.dumps(manifest))
        (self.project / ".xtemplates/VERSION").write_text("1.0.0 (abcdef)\n")
        agent = ".codex/agents/executor.toml"
        pinned = (self.project / agent).read_text()
        self.assertIn("\nmodel = ", pinned)
        custom = ".codex/agents/reviewer.toml"
        (self.project / custom).write_text((self.project / custom).read_text() + "# project override\n")
        self.git(self.project, "add", ".")
        self.git(self.project, "commit", "-qm", "install Codex before the selection was recorded")
        self.git(self.project, "push", "-q", str(self.origin), "HEAD:main")

        self.release("1.1.0")
        self.assertEqual(xt.main(["upgrade", "open-pr"]), 0)
        ref = "refs/heads/" + dist.UPGRADE_BRANCH
        self.assertEqual(self.git(self.origin, "show", f"{ref}:{agent}"), pinned.rstrip())
        self.assertIn("# project override", self.git(self.origin, "show", f"{ref}:{custom}"))
        upgraded = json.loads(self.git(self.origin, "show", f"{ref}:{dist.MANIFEST}"))
        self.assertIs(original_selection, True)
        self.assertIs(upgraded["codex_models"], True)
