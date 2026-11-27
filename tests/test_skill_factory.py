"""Kiểm cửa vào factory đã cài cho sản phẩm và những hành động có bằng chứng ở mỗi giai đoạn."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAUDE = Path(".claude/skills/factory/SKILL.md")
CODEX = Path(".agents/skills/factory/SKILL.md")


class FactoryEntryTest(unittest.TestCase):
    def test_one_install_creates_clean_codex_project_and_resumes_in_place(self):
        """Cài ngay harness trong commit đầu, rồi thử nâng repo hiện hữu."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "so-ghi-chu"
            idea = "Sổ ghi chú của nhóm thử nghiệm"
            env = {**os.environ, "CLAUDE_PROJECT_DIR": str(target)}

            def command(*argv, cwd=target):
                result = subprocess.run([sys.executable, *argv], cwd=cwd, env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-3000:])
                return result.stdout

            def install(*args):
                return command(str(ROOT / "scripts/install.py"), str(target), *args, cwd=ROOT)

            cli = ".xtemplates/scripts/xt.py"
            install("--new", "--pack", "web-api-ts", "--idea", idea, "--harness", "codex")
            self.assertEqual((target / CODEX).read_bytes(), (ROOT / CODEX).read_bytes())
            self.assertEqual(subprocess.check_output(["git", "status", "--porcelain"], cwd=target), b"")
            self.assertEqual(subprocess.check_output(["git", "rev-list", "--count", "HEAD"], cwd=target), b"1\n")
            original = json.loads(command(cli, "stage", "status", "--json"))["stage"]
            self.assertEqual((original["stage"], original["status"]), (1, "active"))
            project = (target / "PROJECT.md").read_text(encoding="utf-8")
            self.assertIn(idea, project)
            _, profile_example, remainder = project.split("~~~", 2)
            settings = json.loads(profile_example.removeprefix("json\n"))
            self.assertEqual(settings["schema"], 1)
            for field in ("profile", "use", "data_class", "money", "scale", "admin"):
                self.assertIsNone(settings[field], field)
            self.assertIn("## 10. Câu hỏi mở", remainder)
            install("--harness", "codex")
            self.assertEqual(json.loads(command(cli, "stage", "status", "--json"))["stage"], original)
            self.assertEqual((target / "PROJECT.md").read_text(encoding="utf-8"), project)
            for path in (CLAUDE, CODEX):
                self.assertEqual((target / path).read_bytes(), (ROOT / path).read_bytes(), path)
            self.assertTrue((target / "tests_e2e/preview.sh").is_file())
            self.assertTrue((target / ".xtemplates/scripts/xt_acceptance.py").is_file())
            flow = json.loads(command(".xtemplates/scripts/xt_flow.py", "--json"))
            self.assertEqual((flow["stage"]["stage"], flow["stage"]["status"]), (1, "active"))
            self.assertEqual(flow["next"]["owner"], "coordinator")
            self.assertEqual(json.loads(command(cli, "stage", "status", "--json"))["stage"], original)

    def test_offline_bundle_restores_exact_installed_product(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            original, bundle, restored = (base / n for n in ("so-ghi-chu", "so-ghi-chu.bundle", "ban-giao"))
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/install.py"),
                    str(original),
                    "--new",
                    "--pack",
                    "web-api-ts",
                    "--idea",
                    "Sổ ghi chú",
                ],
                check=True,
                capture_output=True,
            )
            # Clone mới mô phỏng máy bàn giao, chỉ mang lịch sử đã commit của sản phẩm.
            delivery = base / "checkout"
            subprocess.run(["git", "clone", "-q", str(original), str(delivery)], check=True)
            original = delivery
            checklist = Path("docs/ops/SETUP-ONCE.md")
            (original / checklist).parent.mkdir(parents=True, exist_ok=True)
            (original / checklist).write_text("Repo: thiếu remote\nBản dev: loopback của runner\n", encoding="utf-8")

            def git(root, *args):
                r = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
                self.assertEqual(r.returncode, 0, r.stderr.decode(errors="replace"))
                return r.stdout

            git(original, "add", checklist.as_posix())
            git(
                original,
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-qm",
                "docs(ops): ghi checklist bàn giao bản dev",
            )
            sha = git(original, "rev-parse", "HEAD")
            git(original, "bundle", "create", str(bundle), "HEAD")
            git(original, "bundle", "verify", str(bundle))
            git(base, "clone", str(bundle), str(restored))
            self.assertEqual(git(restored, "rev-parse", "HEAD"), sha)
            for rel in (checklist, Path("docs/autopilot/STAGE.json"), Path("PROJECT.md")):
                self.assertEqual((original / rel).read_bytes(), (restored / rel).read_bytes())
            self.assertFalse((restored / ".autopilot").exists())

    def test_each_stage_has_its_checks_and_handoff(self):
        """Chặn hồi quy về bản skill cũ chỉ nhắc tên hai giai đoạn sau ở cuối MVP."""
        body = (ROOT / CLAUDE).read_text(encoding="utf-8")
        first = body.index("## Giai đoạn 1")
        second = body.index("## Giai đoạn 2")
        third = body.index("## Giai đoạn 3")
        steps = (
            (
                body[:first],
                [
                    "--new",
                    "--harness codex",
                    "xt_flow.py --json",
                    "stage status --json",
                    "plan waves --plan <PLAN> --max 4 --handoff",
                    "Cấu hình ghép blueprint",
                    "compose --out <bản-tạm>",
                ],
            ),
            (
                body[first:second],
                [
                    "acceptance lock --spec",
                    "acceptance check --json",
                    "SETUP-ONCE.md",
                    "git bundle create <bundle> HEAD",
                    "git bundle verify <bundle>",
                    "ACCEPTANCE.paths",
                    "xt_acceptance.py check --base",
                    "--project <repo-sản-phẩm>",
                    "/autopilot",
                    "tests_e2e/preview.sh",
                    "deploy status --env dev --json",
                    "stage submit --evidence",
                    "awaiting_approval",
                    "stage reopen --reason",
                ],
            ),
            (
                body[second:third],
                ["/complete", "release-check --json", "rollout-drill", "stage submit", "chính sách giao hàng"],
            ),
            (
                body[third:],
                ["baseline field", "Gate E2E", "promotion.state", "approved", "ops-check --env", "completed"],
            ),
        )
        for section, actions in steps:
            for action in actions:
                with self.subTest(action=action):
                    self.assertIn(action, section)

        sequence = [
            "/optimize",
            "Gate E2E",
            "release-check --json",
            "promotion.state",
            "**tại đích**",
            "ops-check --env",
            "Thử nghiệm tăng trưởng",
        ]
        offsets = [body.index(action, third) for action in sequence]
        self.assertEqual(offsets, sorted(offsets))
