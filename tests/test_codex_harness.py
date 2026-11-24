"""Harness Codex sinh từ `.claude/` (ADR-0082, T-3966): `.agents/skills/<tên>/SKILL.md` là bản sao byte của
`.claude/skills/<tên>/SKILL.md`, `.codex/agents/<tên>.toml` sinh từ `.claude/agents/<tên>.md`, `.codex/hooks.json` từ mẫu
`framework/templates/harness/codex-hooks.json`. Một bộ sinh trong `scripts/install.py`, hai nơi dùng: `--harness codex` ở
dự án đích và `--sync-codex` ở repo khung (tệp đã commit phải trùng từng byte với đầu ra sinh lại)."""

from __future__ import annotations

import io
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
import unittest.mock as mock
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import install

sys.path.insert(0, str(ROOT / "tests"))
from nonet import isolate_network

SKILLS = ROOT / ".claude" / "skills"
AGENTS = ROOT / ".claude" / "agents"
SKILL_NAMES = sorted(p.parent.name for p in SKILLS.glob("*/SKILL.md"))
AGENT_NAMES = sorted(p.stem for p in AGENTS.glob("*.md"))
AGENT_KEYS = {"name", "description", "model_reasoning_effort", "developer_instructions"}


# Giá trị kỳ vọng viết tay theo 5 agent của khung (không tính lại bằng bộ đọc frontmatter của mã): `effort` khai ở
# executor-deep (high) và reviewer-alt (max); ba agent còn lại không khai.
EXPECTED_EFFORT = {
    "acceptance-author": None,
    "executor": None,
    "executor-deep": "high",
    "explore": None,
    "researcher": None,
    "reviewer": None,
    "reviewer-alt": "max",
}
DESCRIPTION_HEAD = {
    "acceptance-author": "Viết bài nghiệm thu độc lập",
    "executor": "Thực thi một task RÕ PHẠM VI",
    "executor-deep": "Tầng thực thi SÂU (ADR-0029)",
    "explore": "Tra cứu và đọc nhiều tệp CHỈ ĐỌC",
    "researcher": "Xác minh dữ kiện từ NGUỒN SỐNG",
    "reviewer": "Review độc lập diff/PR",
    "reviewer-alt": "Reviewer độc lập NĂNG LỰC CAO NHẤT",
}
BODY_HEAD = {
    "acceptance-author": "Bạn viết bài nghiệm thu",
    "executor": "Bạn là người thực thi theo spec",
    "executor-deep": "Bạn là tầng thực thi sâu",
    "explore": "Bạn là người tra cứu chỉ đọc.",
    "researcher": "Bạn là người tra cứu.",
    "reviewer": "Bạn là người gác cổng",
    "reviewer-alt": "Bạn là người gác cổng",
}


def stored(data: bytes) -> str:
    """Hash đúng dạng install.py ghi vào manifest (`sha256:<hex>`)."""
    return install.hash_label(install.sha256(data))


def git_env() -> dict[str, str]:
    """Môi trường git không trỏ nhầm repo/index (test chạy trong git hook `pre-commit` có `GIT_INDEX_FILE`…)."""
    env = {k: v for k, v in os.environ.items() if k not in install.GIT_LOCATION_ENV}
    return env | {"GIT_CONFIG_NOSYSTEM": "1"}


def committed_codex_files(root: Path) -> list[str]:
    """Tệp dưới `.agents/`, `.codex/` mà git theo dõi (`git ls-files`, danh sách đối số, không shell). `root` không phải
    repo git (bản zip) → quét cây, bỏ `__pycache__` — chặt hơn chứ không bỏ kiểm."""
    top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True, env=git_env())
    # Chỉ tin `ls-files` khi gốc git (đường vật lý) đúng là `root`: thư mục con của repo khác (không `.git` riêng) thì
    # `ls-files` đọc index của repo cha — exit 0, rỗng — và bỏ sót tệp thừa (review lượt 3).
    if top.returncode == 0 and Path(os.fsdecode(top.stdout.strip())).resolve() == root.resolve():
        r = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--", ".agents", ".codex"],
            capture_output=True,
            env=git_env(),
            check=True,
        )
        return sorted(p.decode("utf-8") for p in r.stdout.split(b"\0") if p)
    found = (p for d in (".agents", ".codex") for p in (root / d).rglob("*") if p.is_symlink() or not p.is_dir())
    return sorted(p.relative_to(root).as_posix() for p in found if "__pycache__" not in p.parts)


def run_main(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = install.main(list(argv))
    return rc, out.getvalue(), err.getvalue()


class CodexHarnessSyncTest(unittest.TestCase):
    """Gate của T-3966: tệp đã commit ở `.agents/skills/`, `.codex/agents/`, `.codex/hooks.json` = đầu ra sinh lại từ
    `.claude/skills/*/SKILL.md`, `.claude/agents/*.md` và `codex-hooks.json`; thiếu, thừa hay khác byte đều đỏ."""

    def test_committed_files_match_generator(self):
        want = install.codex_framework_files()
        problems = []
        for rel, data in sorted(want.items()):
            path = ROOT / rel
            if not path.is_file():
                problems.append(f"thiếu {rel}")
            elif path.read_bytes() != data:
                problems.append(f"khác {rel}")
        problems += [f"thừa {rel}" for rel in committed_codex_files(ROOT) if rel not in want]
        self.assertEqual(problems, [], f"tệp Codex lệch nguồn .claude/ — sinh lại: {install.CODEX_SYNC}")

    def test_committed_files_ignore_untracked_local_files(self):
        """Review lượt 2 🟢: tệp chưa track hợp lệ ở máy dev (`.DS_Store`, `.codex/config.toml` cục bộ, metadata skill
        `agents/openai.yaml`) không làm test đồng bộ đỏ; tệp ĐÃ track mà bộ sinh không tạo thì có. Ngoài repo git → quét
        cây (mọi tệp dưới `.agents/`, `.codex/` trừ `__pycache__`)."""
        repo = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        for rel in (".agents/skills/x/SKILL.md", ".codex/hooks.json", ".codex/__pycache__/a.pyc", "README.md"):
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (repo / rel).write_text("x\n", encoding="utf-8")
        scanned = [".agents/skills/x/SKILL.md", ".codex/hooks.json"]
        self.assertEqual(committed_codex_files(repo), scanned)  # chưa phải repo git: quét cây
        subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True, env=git_env())
        subprocess.run(["git", "-C", str(repo), "add", ".codex/hooks.json"], check=True, env=git_env())
        self.assertEqual(committed_codex_files(repo), [".codex/hooks.json"])
        self.assertEqual(install.git_tracked(repo, install.CODEX_ROOTS), {".codex/hooks.json"})
        # Review lượt 3 🟢: repo khung LỒNG trong repo cha, không có `.git` riêng — `ls-files` đọc index của repo cha
        # (exit 0, rỗng) nên không được tin: gốc git khác thư mục → quét cây như khi không có git.
        child = repo / "khung"
        for rel in scanned:
            (child / rel).parent.mkdir(parents=True, exist_ok=True)
            (child / rel).write_text("x\n", encoding="utf-8")
        self.assertEqual(committed_codex_files(child), scanned)
        self.assertIsNone(install.git_tracked(child, install.CODEX_ROOTS))

    def test_generator_covers_every_framework_skill_and_agent(self):
        want = sorted(install.codex_framework_files())
        expected = [
            ".codex/hooks.json",
            *(f".agents/skills/{n}/SKILL.md" for n in SKILL_NAMES),
            *(f".codex/agents/{n}.toml" for n in AGENT_NAMES),
        ]
        self.assertEqual(want, sorted(expected))
        # sàn, không ghim số: thêm skill ở `.claude/skills` (vd `factory`, #683) không phải sửa test — chỉ chặn bộ liệt kê rỗng/hụt
        self.assertGreaterEqual(len(SKILL_NAMES), 16)
        self.assertGreaterEqual(len(AGENT_NAMES), 5)

    def test_repo_hooks_json_uses_repo_adapter_and_only_pretooluse(self):
        doc = json.loads((ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(list(doc["hooks"]), ["PreToolUse"])
        command = doc["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        self.assertEqual(
            command, 'python3 -I -B "$(git rev-parse --show-toplevel)/scripts/xt_adapter.py" codex'
        )  # không đường tuyệt đối của máy, không `.xtemplates/`
        template = json.loads(install.adapter_src("codex").read_text(encoding="utf-8"))
        template["hooks"]["PreToolUse"][0]["hooks"][0]["command"] = command
        self.assertEqual(doc, template)  # khác mẫu đúng một chỗ: đường adapter

    def test_skill_copies_have_codex_frontmatter(self):
        """Codex đòi `name` và `description` ở frontmatter `SKILL.md` (research §2): mỗi bản sao mở bằng `---`, có
        `name: <tên thư mục>` và một dòng `description: ` không rỗng trước dòng `---` đóng."""
        for n in SKILL_NAMES:
            with self.subTest(skill=n):
                lines = (ROOT / ".agents" / "skills" / n / "SKILL.md").read_text(encoding="utf-8").split("\n")
                head = lines[1 : lines.index("---", 1)]
                self.assertEqual(lines[0], "---")
                self.assertIn(f"name: {n}", head)
                self.assertTrue(any(ln.startswith("description: ") and len(ln) > 14 for ln in head))

    def test_codex_paths_not_ignored_by_git(self):
        paths = (".agents/skills/gate/SKILL.md", ".codex/agents/executor.toml", ".codex/hooks.json")
        r = subprocess.run(
            ["git", "-C", str(ROOT), "check-ignore", "--no-index", "-v", *paths], capture_output=True, text=True
        )
        self.assertEqual(r.returncode, 1, r.stdout)  # 1 = không đường nào bị .gitignore chặn


class AgentTomlTest(unittest.TestCase):
    """`.claude/agents/<tên>.md` → TOML viết tay bằng stdlib: đọc lại bằng `tomllib` ra đúng từng trường của nguồn."""

    def test_framework_agents_round_trip(self):
        for name in AGENT_NAMES:
            with self.subTest(agent=name):
                text = (AGENTS / f"{name}.md").read_text(encoding="utf-8")
                doc = tomllib.loads((ROOT / ".codex" / "agents" / f"{name}.toml").read_text(encoding="utf-8"))
                self.assertLessEqual(set(doc), AGENT_KEYS)  # không `model`: tên model Claude vô nghĩa với Codex
                self.assertEqual(doc["name"], name)
                self.assertEqual(doc.get("model_reasoning_effort"), EXPECTED_EFFORT[name])
                self.assertTrue(doc["description"].startswith(DESCRIPTION_HEAD[name]))
                self.assertIn(f"\ndescription: {doc['description']}\n", text)  # nguyên dòng nguồn, không cắt/thêm
                body = doc["developer_instructions"]
                self.assertTrue(body.startswith(BODY_HEAD[name]))
                self.assertTrue(text.endswith(f"\n---\n\n{body}"))  # thân = phần đuôi tệp sau `---` và một dòng trống
                self.assertNotIn(".Codex/", doc["developer_instructions"])  # lỗi importer #40147 không lặp lại
        deep = tomllib.loads((ROOT / ".codex" / "agents" / "executor-deep.toml").read_text(encoding="utf-8"))
        self.assertIn("`.claude/agents/executor.md`", deep["developer_instructions"])  # đường `.claude/…` giữ nguyên

    def test_tricky_bodies_round_trip(self):
        bodies = (
            'mở """ giữa',
            "đơn ''' và '''",
            "gạch \\ ngược \\n \\u0041 cuối \\",
            'kết thúc bằng nháy "',
            'hai nháy cuối ""',
            'ba nháy cuối """',
            '""""""',
            "không xuống dòng ở cuối",
            "có xuống dòng\n",
            "tab\tCR\rCRLF\r\nNUL\x00DEL\x7fESC\x1bFF\x0cVT\x0bNEL\x85 U+2028  tiếng Việt: ằ ẩ ữ ỵ 🙂",
            '"\n"""\n"',
            "",
        )
        for body in bodies:
            with self.subTest(body=body):
                text = f"---\nname: x\ndescription: mô tả \"nháy\" \\ 'đơn' : hai chấm\neffort: max\n---\n\n{body}"
                out = install.agent_toml(text, ".claude/agents/x.md")
                assert out is not None
                doc = tomllib.loads(out)
                self.assertEqual(doc["developer_instructions"], body)
                self.assertEqual(doc["description"], "mô tả \"nháy\" \\ 'đơn' : hai chấm")
                self.assertEqual(doc["model_reasoning_effort"], "max")

    def test_strings_round_trip_fuzz(self):
        alphabet = ['"', "'", "\\", "\n", "\r", "\t", "a", "ế", "\x00", "\x1f", "\x7f", " ", "#", "=", "[", "u"]
        rng = random.Random(3966)
        for _ in range(600):
            s = "".join(rng.choice(alphabet) for _ in range(rng.randrange(0, 14)))
            with self.subTest(s=s):
                self.assertEqual(tomllib.loads(f"k = {install.toml_multiline(s)}")["k"], s)
                self.assertEqual(tomllib.loads(f"k = {install.toml_string(s)}")["k"], s)
        controls = "".join(map(chr, range(0x20))) + "\x7f"
        self.assertEqual(tomllib.loads(f"k = {install.toml_string(controls)}")["k"], controls)
        self.assertNotIn("\n", install.toml_string(controls))

    def test_effort_values(self):
        for effort, want in (("low", "low"), ("xhigh", "xhigh"), ("ultra", None), ("High", None), ("", None)):
            with self.subTest(effort=effort):
                out = install.agent_toml(f"---\nname: a\ndescription: d\neffort: {effort}\n---\nb\n", "s")
                assert out is not None
                self.assertEqual(tomllib.loads(out).get("model_reasoning_effort"), want)
        out = install.agent_toml("---\nname: a\ndescription: d\nmodel: opus\n---\nb\n", "s")
        assert out is not None
        self.assertEqual(set(tomllib.loads(out)), {"name", "description", "developer_instructions"})

    def test_frontmatter_variants(self):
        text = "---\r\nname: \"a\"\r\ndescription: 'b: c'\r\n# chú thích cả dòng\r\n\r\ntools:\r\n---\r\nthân\r\n"
        doc = tomllib.loads(install.agent_toml(text, "s"))
        self.assertEqual((doc["name"], doc["description"], doc["developer_instructions"]), ("a", "b: c", "thân\r\n"))
        doc = tomllib.loads(install.agent_toml("---\nname: a\ndescription: x#1 và a#b, \"q\" 'r'\n---\nb", "s"))
        self.assertEqual(doc["description"], "x#1 và a#b, \"q\" 'r'")  # `#` không sau khoảng trắng: chữ thường
        for text, why in (
            ("", "mở bằng `---`"),
            ("name: a\n", "mở bằng `---`"),
            ("---\nname: a\ndescription: d\n", "không có dòng `---` đóng"),
            ("---\nname: a\n---\nb\n", "thiếu `description`"),
            ("---\ndescription: d\n---\nb\n", "thiếu `name`"),
            ("---\nname: \ndescription: d\n---\nb\n", "thiếu `name`"),
        ):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, re.escape(why)):
                install.agent_toml(text, "s")
        self.assertIn("UTF-8", install.render_agent(b"\xff\xfe", "s"))

    def test_typed_plain_values_rejected_for_text_keys(self):
        """Review lượt 2 🟢: giá trị TRƠN có kiểu YAML (null, bool — cả dạng YAML 1.1 —, số, ngày) ở `name`/`description`/
        `effort` không phải chuỗi → từ chối; trong nháy vẫn là chuỗi; khoá khác (`maxTurns: 120`) không xét kiểu."""
        typed = (
            *("null", "Null", "NULL", "~", "true", "True", "TRUE", "false", "False", "FALSE"),
            *("yes", "No", "ON", "off", "y", "N"),
            *("0", "120", "-3", "+7", "1.5", "1.0e3", "1e3", "-2.5E-4", ".5", "1_000", "0x1F", "0o17", "0b101"),
            *(".inf", "-.Inf", "+.INF", ".nan", ".NaN", ".NAN", "1:20", "2026-11-19", "2026-11-19T10:00:00Z"),
            *("2026-11-19t10:00:00", "2026-11-19 10:00:00", "2026-1-9 1:02:03.5 +07:00", "2026-11-19  10:00:00-7"),
        )
        for key in ("name", "description", "effort"):
            for value in typed:
                fields = {"name": "a", "description": "d", "effort": "low"} | {key: value}
                text = "---\n" + "".join(f"{k}: {v}\n" for k, v in fields.items()) + "---\nb\n"
                with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, "có kiểu YAML"):
                    install.agent_toml(text, "s")
        doc = tomllib.loads(install.agent_toml("---\nname: \"null\"\ndescription: '120'\nmaxTurns: 120\n---\nb", "s"))
        self.assertEqual((doc["name"], doc["description"]), ("null", "120"))
        not_timestamp = ("2026-11-19 audit agent", "2026-11-19T10:00", "2026-1-9", "2026-11-19 10:00:00 giờ VN")
        for plain in ("v1.2", "1.2.3", "0x", "yes-no", "trueish", "10 phút", ".5x", "ON/OFF", *not_timestamp):
            with self.subTest(plain=plain):
                doc = tomllib.loads(install.agent_toml(f"---\nname: a\ndescription: {plain}\n---\nb", "s"))
                self.assertEqual(doc["description"], plain)

    def test_whitespace_and_line_breaks(self):
        """Review lượt 2 🟢: chỉ cắt dấu cách/tab hai đầu (YAML 1.2 chỉ coi hai ký tự này là khoảng trắng) — NBSP, U+3000
        là nội dung, giữ nguyên; ký tự ngắt dòng YAML 1.1 (U+0085, U+2028, U+2029), `\\r` lẻ và ký tự điều khiển khác →
        từ chối (bộ đọc YAML 1.1 tách dòng ở đó: nghĩa khác nhau tuỳ bộ đọc); CRLF cuối dòng vẫn nhận."""
        text = "---\r\nname: a\t\r\ndescription: \t nbsp giữ　  #x\t\r\n---\r\nb"
        doc = tomllib.loads(install.agent_toml(text, "s"))
        self.assertEqual((doc["name"], doc["description"]), ("a", " nbsp giữ　  #x"))
        for bad in ("d\x85x", "d x", "d x", "a\rb", "d\x01", "d\x0bx", "d\x7f", "d\x80", "d\x9bx", "d\x9f", "d﻿x"):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "dòng 3: ký tự điều khiển hoặc ngắt dòng"):
                install.agent_toml(f"---\nname: a\ndescription: {bad}\n---\nb", "s")
        for line in ("# chú thích name: b", " ", " "):
            with self.subTest(line=line), self.assertRaisesRegex(ValueError, "dòng 4: "):
                install.agent_toml(f"---\nname: a\ndescription: d\n{line}\n---\nb", "s")
        with self.assertRaisesRegex(ValueError, "dòng 2: ký tự điều khiển"):  # chỉ một `\r` cuối dòng là CRLF
            install.agent_toml("---\nname: a\r\r\ndescription: d\n---\nb", "s")

    def test_rejects_yaml_outside_flat_subset(self):
        """Fail-closed (review reviewer-alt 🔴): YAML hợp lệ nhưng ngoài tập con phẳng mà bộ đọc hiểu chắc → lỗi nêu dòng và
        lý do, không sinh TOML sai nghĩa. Kỳ vọng viết tay: từng ca nêu đoạn lý do phải có."""
        head = "---\nname: a\n"
        cases = (
            (head + "description: >-\n  gấp\n---\nb\n", "dòng 3: khối `|`/`>`"),
            (head + "description: |\n  giữ\n---\nb\n", "dòng 3: khối `|`/`>`"),
            (head + "description: d\nmetadata:\n  description: lồng\n  effort: max\n---\nb\n", "dòng 5: thụt lề"),
            (head + "\tdescription: d\n---\nb\n", "dòng 3: thụt lề"),
            (head + 'description: "a \\" b"\n---\nb\n', "dòng 3: nháy kép có ký tự thoát"),
            (head + 'description: "dòng\\nhai"\n---\nb\n', "dòng 3: nháy kép có ký tự thoát"),
            (head + "description: 'It''s'\n---\nb\n", "dòng 3: nháy đơn có `''`"),
            (head + "description: d # chú thích\n---\nb\n", "dòng 3: chú thích"),
            (head + "description: d\t# chú thích\n---\nb\n", "dòng 3: chú thích"),
            (head + 'description: "d" # c\n---\nb\n', "dòng 3: nháy không đóng hoặc có chữ sau nháy đóng"),
            (head + 'description: "mở\n---\nb\n', "dòng 3: nháy không đóng hoặc có chữ sau nháy đóng"),
            (head + "description: 'mở\n---\nb\n", "dòng 3: nháy không đóng hoặc có chữ sau nháy đóng"),
            (head + "description: d\nname: b\n---\nb\n", "dòng 4: khoá `name` lặp"),
            (head + "description: d\ntools:\n- Read\n---\nb\n", "dòng 5: không phải `khoá: giá trị`"),
            (head + "description: d\n...\n---\nb\n", "dòng 4: không phải `khoá: giá trị`"),
            (head + "description:d\n---\nb\n", "dòng 3: không phải `khoá: giá trị`"),
            (head + "description: [a, b]\n---\nb\n", "dòng 3: giá trị bắt đầu bằng ký tự YAML đặc biệt"),
            (head + "description: &x d\n---\nb\n", "dòng 3: giá trị bắt đầu bằng ký tự YAML đặc biệt"),
            (head + "description: - d\n---\nb\n", "dòng 3: giá trị bắt đầu bằng ký tự YAML đặc biệt"),
            (head + "description: d\n---\n---\nx: y\n---\nb\n", "nhiều tài liệu"),
            (head + "description: d\n---\n\n---\nb\n", "nhiều tài liệu"),
        )
        for text, why in cases:
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, re.escape(why)):
                install.agent_toml(text, ".claude/agents/a.md")
        self.assertEqual(
            install.render_agent(cases[0][0].encode(), ".claude/agents/a.md"),
            "frontmatter dòng 3: khối `|`/`>` (YAML ngoài tập con phẳng)",
        )


class InstallCodexHarnessTest(unittest.TestCase):
    """`install.py <đích> --harness codex`: `--plan` không ghi gì, cài lần đầu chép đủ, cài lại idempotent, manifest ghi
    hash `codex_files` và giữ qua lần cài không `--harness`."""

    def setUp(self):
        self.target = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()

    def install(self, *args: str) -> tuple[int, str, str]:
        return run_main(str(self.target), "--label", "t", *args)

    def snapshot(self) -> dict[str, bytes]:
        dirs = (self.target / ".agents", self.target / ".codex")
        return {
            p.relative_to(self.target).as_posix(): p.read_bytes() for d in dirs for p in d.rglob("*") if p.is_file()
        }

    def test_plan_install_reinstall(self):
        rc, out, err = self.install("--plan", "--harness", "codex")
        self.assertEqual(rc, 0, err)
        plan = json.loads(out)["codex_harness"]
        self.assertEqual(len(plan), len(SKILL_NAMES) + len(AGENT_NAMES))
        self.assertEqual({e["action"] for e in plan}, {"copied"})  # nguồn là bản `.claude/` mà bước harness sẽ chép
        self.assertIn(
            {"source": ".claude/agents/executor.md", "path": ".codex/agents/executor.toml", "action": "copied"}, plan
        )
        self.assertFalse((self.target / ".agents").exists() or (self.target / ".codex").exists())  # plan không ghi
        rc, _, err = self.install("--harness", "codex")
        self.assertEqual(rc, 0, err)
        self.assertIn("codex: .agents/skills + .codex/agents", err)
        files = self.snapshot()
        for n in SKILL_NAMES:
            self.assertEqual(files[f".agents/skills/{n}/SKILL.md"], (SKILLS / n / "SKILL.md").read_bytes())
        for n in AGENT_NAMES:
            self.assertEqual(tomllib.loads(files[f".codex/agents/{n}.toml"].decode())["name"], n)
        manifest = self.target / install.MANIFEST_V2
        recorded = json.loads(manifest.read_text(encoding="utf-8"))["codex_files"]
        want = {
            rel: install.hash_label(install.sha256(data)) for rel, data in files.items() if rel != ".codex/hooks.json"
        }
        self.assertEqual(recorded, want)
        rc, out, _ = self.install("--plan", "--harness", "codex")
        self.assertEqual({e["action"] for e in json.loads(out)["codex_harness"]}, {"kept"})
        self.assertEqual(self.install("--harness", "codex")[0], 0)
        self.assertEqual(self.snapshot(), files)  # cài lại: byte không đổi
        self.assertEqual(json.loads(self.install("--plan")[1])["codex_harness"], [])  # không codex: không có việc
        self.assertEqual(self.install()[0], 0)  # cài không `--harness`: manifest giữ `codex_files`
        self.assertEqual(json.loads(manifest.read_text(encoding="utf-8"))["codex_files"], want)


class CodexMirrorInstallTest(unittest.TestCase):
    """Cài thật: dự án đã cài khung (chưa `--harness codex`) và tự làm gương `.agents/skills` từ bản khung cũ → lần đầu
    `--harness codex` cập nhật gương tại chỗ (bản cũ chứng minh bằng hash manifest harness), `--plan` báo `updated`."""

    def setUp(self):
        self.target = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()

    def install(self, *args: str) -> tuple[int, str, str]:
        return run_main(str(self.target), "--label", "t", *args)

    def test_first_codex_install_updates_old_framework_mirror(self):
        self.assertEqual(self.install()[0], 0)
        old = b"---\nname: gate\ndescription: old\n---\nold\n"
        (self.target / ".claude" / "skills" / "gate" / "SKILL.md").write_bytes(old)  # bản khung cũ, chưa sửa
        manifest = self.target / install.MANIFEST
        doc = json.loads(manifest.read_text(encoding="utf-8"))
        doc[".claude/skills/gate/SKILL.md"] = stored(old)
        manifest.write_text(json.dumps(doc), encoding="utf-8")
        mirror = self.target / ".agents" / "skills" / "gate" / "SKILL.md"
        mirror.parent.mkdir(parents=True)
        mirror.write_bytes(old)
        rc, out, err = self.install("--plan", "--harness", "codex")
        self.assertEqual(rc, 0, err)
        planned = {e["path"]: e["action"] for e in json.loads(out)["codex_harness"]}
        self.assertEqual(planned[".agents/skills/gate/SKILL.md"], "updated")
        self.assertEqual(self.install("--harness", "codex")[0], 0)
        self.assertEqual(mirror.read_bytes(), (SKILLS / "gate" / "SKILL.md").read_bytes())
        self.assertFalse(mirror.with_name("SKILL.md.xtemplates-new").exists())

    def project_mirror(self, own_skill: bool) -> tuple[Path, bytes]:
        """Dự án đã cài khung; `.claude/skills/review/SKILL.md` là bản DỰ ÁN (tự sửa; `own_skill` = skill riêng trùng tên
        skill khung mới — manifest harness không có tệp này) và gương `.agents/skills/review/SKILL.md` chép đúng bản đó."""
        self.assertEqual(self.install()[0], 0)
        own = "---\nname: review\ndescription: bản dự án\n---\nquy trình riêng\n".encode()
        (self.target / ".claude" / "skills" / "review" / "SKILL.md").write_bytes(own)
        if own_skill:
            manifest = self.target / install.MANIFEST
            doc = json.loads(manifest.read_text(encoding="utf-8"))
            del doc[".claude/skills/review/SKILL.md"]
            manifest.write_text(json.dumps(doc), encoding="utf-8")
        mirror = self.target / ".agents" / "skills" / "review" / "SKILL.md"
        mirror.parent.mkdir(parents=True)
        mirror.write_bytes(own)
        return mirror, own

    def test_first_codex_install_with_force_harness_keeps_project_mirror(self):
        """Review lượt 2 🟠, phạm vi LẦN CÀI CODEX ĐẦU (chưa có `codex_files`): `--force-harness --harness codex` thay
        `.claude/` bằng bản khung, nhưng gương trùng bản DỰ ÁN (không phải bản khung theo manifest harness) không được ghi
        đè — ra `.xtemplates-new`, giữ nguyên gương."""
        for own_skill in (False, True):
            with self.subTest(own_skill=own_skill):
                self.target = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
                mirror, own = self.project_mirror(own_skill)
                rc, out, err = self.install("--plan", "--force-harness", "--harness", "codex")
                self.assertEqual(rc, 0, err)
                planned = {e["path"]: e["action"] for e in json.loads(out)["codex_harness"]}
                self.assertEqual(planned[".agents/skills/review/SKILL.md"], "updated-new")
                self.assertEqual(self.install("--force-harness", "--harness", "codex")[0], 0)
                self.assertEqual(mirror.read_bytes(), own)
                fresh = (SKILLS / "review" / "SKILL.md").read_bytes()
                self.assertEqual(mirror.with_name("SKILL.md.xtemplates-new").read_bytes(), fresh)
                self.assertEqual((self.target / ".claude" / "skills" / "review" / "SKILL.md").read_bytes(), fresh)

    def test_recorded_mirror_follows_claude_after_force_harness(self):
        """D-520 (review lượt 3 🟠): tệp Codex trùng đầu ra sinh được ghi nhận vào `codex_files` và đi theo `.claude/` ở
        lần cài sau, kể cả khi `--force-harness` thay nguồn; tệp dự án sửa KHÁC bản đã ghi nhận được giữ + `.xtemplates-new`.
        Lượt 1 `--harness codex`: gương = bản sinh từ `.claude/` dự án đã sửa → `kept`, ghi nhận. Lượt 2
        `--force-harness --harness codex`: `.claude/` thành bản khung, gương `review` đi theo (`updated`); gương `adr` mà dự
        án đã sửa sau lượt 1 → giữ + `.xtemplates-new`."""
        self.assertEqual(self.install()[0], 0)
        skills, mirrors = self.target / ".claude" / "skills", self.target / ".agents" / "skills"
        own = {n: f"---\nname: {n}\ndescription: bản dự án\n---\nriêng {n}\n".encode() for n in ("review", "adr")}
        for n, data in own.items():
            (skills / n / "SKILL.md").write_bytes(data)
            (mirrors / n).mkdir(parents=True)
            (mirrors / n / "SKILL.md").write_bytes(data)
        rc, out, err = self.install("--plan", "--harness", "codex")
        self.assertEqual(rc, 0, err)
        planned = {e["path"]: e["action"] for e in json.loads(out)["codex_harness"]}
        self.assertEqual([planned[f".agents/skills/{n}/SKILL.md"] for n in own], ["kept", "kept"])
        self.assertEqual(self.install("--harness", "codex")[0], 0)
        recorded = install.codex_recorded(self.target)
        self.assertEqual([recorded[f".agents/skills/{n}/SKILL.md"] for n in own], [stored(d) for d in own.values()])
        (mirrors / "adr" / "SKILL.md").write_text("dự án sửa gương sau lượt 1\n", encoding="utf-8")
        rc, out, err = self.install("--plan", "--force-harness", "--harness", "codex")
        self.assertEqual(rc, 0, err)
        planned = {e["path"]: e["action"] for e in json.loads(out)["codex_harness"]}
        self.assertEqual([planned[f".agents/skills/{n}/SKILL.md"] for n in own], ["updated", "updated-new"])
        self.assertEqual(self.install("--force-harness", "--harness", "codex")[0], 0)
        for n in own:
            self.assertEqual((skills / n / "SKILL.md").read_bytes(), (SKILLS / n / "SKILL.md").read_bytes())
        self.assertEqual((mirrors / "review" / "SKILL.md").read_bytes(), (SKILLS / "review" / "SKILL.md").read_bytes())
        self.assertFalse((mirrors / "review" / "SKILL.md.xtemplates-new").exists())
        self.assertEqual((mirrors / "adr" / "SKILL.md").read_text(encoding="utf-8"), "dự án sửa gương sau lượt 1\n")
        new = (mirrors / "adr" / "SKILL.md.xtemplates-new").read_bytes()
        self.assertEqual(new, (SKILLS / "adr" / "SKILL.md").read_bytes())

    def test_own_skill_named_like_new_framework_skill_kept(self):
        """Không `--force-harness`: skill riêng trùng tên skill khung mới — bước harness để `.claude/` của dự án (bản khung
        ra `.xtemplates-new`), gương vẫn trùng nguồn nên giữ nguyên (`kept`)."""
        mirror, own = self.project_mirror(own_skill=True)
        rc, out, _ = self.install("--plan", "--harness", "codex")
        planned = {e["path"]: e["action"] for e in json.loads(out)["codex_harness"]}
        self.assertEqual(planned[".agents/skills/review/SKILL.md"], "kept")
        self.assertEqual(self.install("--harness", "codex")[0], 0)
        self.assertEqual(mirror.read_bytes(), own)
        self.assertFalse(mirror.with_name("SKILL.md.xtemplates-new").exists())


class CodexInstallCasesTest(unittest.TestCase):
    """Luật sẵn có của install.py áp cho tệp Codex: không ghi đè tệp dự án tự có, cập nhật tại chỗ khi còn là bản khung,
    không ghi/đọc xuyên symlink, skill riêng và skill bị lệnh dự án che không đụng."""

    def setUp(self):
        tmp = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.target, self.outside = tmp / "proj", tmp / "outside"
        self.outside.mkdir()
        for d in ("skills", "agents"):
            shutil.copytree(ROOT / ".claude" / d, self.target / ".claude" / d)

    def run_codex(self, baseline: dict[str, set[str]] | None = None) -> str:
        err = io.StringIO()
        with redirect_stderr(err):
            install.install_codex_harness(self.target, ["codex"], baseline)
        return err.getvalue()

    def plan(self) -> dict[str, str]:
        return {e["path"]: e["action"] for e in install.codex_plan(self.target, [], ["codex"])}

    def recorded(self) -> dict[str, str]:
        return install.codex_recorded(self.target)

    def test_project_files_kept_and_ours_updated(self):
        own = self.target / ".agents" / "skills" / "mine" / "SKILL.md"
        own.parent.mkdir(parents=True)
        own.write_text("skill riêng của dự án\n", encoding="utf-8")
        theirs = self.target / ".agents" / "skills" / "gate" / "SKILL.md"
        theirs.parent.mkdir(parents=True)
        theirs.write_text("bản dự án tự có\n", encoding="utf-8")
        self.assertEqual(self.plan()[".agents/skills/gate/SKILL.md"], "updated-new")
        self.assertIn(".xtemplates-new", self.run_codex())
        self.assertEqual(theirs.read_text(encoding="utf-8"), "bản dự án tự có\n")  # không ghi đè
        self.assertEqual(
            theirs.with_name("SKILL.md.xtemplates-new").read_bytes(), (SKILLS / "gate" / "SKILL.md").read_bytes()
        )
        self.assertEqual(own.read_text(encoding="utf-8"), "skill riêng của dự án\n")
        self.assertNotIn(".agents/skills/mine/SKILL.md", self.recorded())
        # nguồn `.claude/` của dự án đổi, bản sao còn đúng hash khung đã ghi → cập nhật tại chỗ
        src = self.target / ".claude" / "agents" / "executor.md"
        src.write_text(src.read_text(encoding="utf-8") + "Dòng thêm của dự án.\n", encoding="utf-8")
        dst = self.target / ".codex" / "agents" / "executor.toml"
        self.assertEqual(self.plan()[".codex/agents/executor.toml"], "updated")
        self.run_codex()
        self.assertTrue(tomllib.loads(dst.read_text(encoding="utf-8"))["developer_instructions"].endswith("dự án.\n"))
        # dự án sửa bản sao, nguồn không đổi → `kept-own` im lặng, giữ hash cũ
        old = self.recorded()[".codex/agents/executor.toml"]
        dst.write_text(dst.read_text(encoding="utf-8") + "# sửa tay\n", encoding="utf-8")
        self.assertEqual(self.plan()[".codex/agents/executor.toml"], "kept-own")
        self.run_codex()
        self.assertTrue(dst.read_text(encoding="utf-8").endswith("# sửa tay\n"))
        self.assertFalse(dst.with_name("executor.toml.xtemplates-new").exists())
        self.assertEqual(self.recorded()[".codex/agents/executor.toml"], old)
        # cả hai đổi → `.xtemplates-new`
        src.write_text(src.read_text(encoding="utf-8") + "Thêm nữa.\n", encoding="utf-8")
        self.assertEqual(self.plan()[".codex/agents/executor.toml"], "updated-new")
        self.run_codex()
        self.assertTrue(dst.with_name("executor.toml.xtemplates-new").is_file())

    def test_shadowed_skill_not_generated(self):
        (self.target / ".claude" / "commands").mkdir()
        (self.target / ".claude" / "commands" / "gate.md").write_text("lệnh riêng\n", encoding="utf-8")
        self.assertNotIn(".agents/skills/gate/SKILL.md", self.plan())
        self.run_codex()
        self.assertFalse((self.target / ".agents" / "skills" / "gate").exists())
        self.assertTrue((self.target / ".agents" / "skills" / "review" / "SKILL.md").is_file())

    def clear(self) -> None:
        for d in (".agents", ".codex"):
            shutil.rmtree(self.target / d, ignore_errors=True)

    def test_symlinked_destinations_not_followed(self):
        for rel in (".agents", ".codex/agents", ".agents/skills/gate"):
            with self.subTest(rel=rel):
                self.clear()  # mỗi ca bắt đầu từ chưa có tệp Codex nào (ca trước đã ghi bản thật)
                link = self.target / rel
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(self.outside)
                actions = self.plan()
                self.assertTrue(any(a == "skipped-symlink" for p, a in actions.items() if p.startswith(rel + "/")))
                self.assertIn("bỏ qua symlink", self.run_codex())
                self.assertEqual(list(self.outside.iterdir()), [])
                link.unlink()
        victim = self.outside / "x.toml"
        victim.write_text("ngoài\n", encoding="utf-8")
        self.clear()
        link = self.target / ".codex" / "agents" / "executor.toml"
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(victim)
        self.assertEqual(self.plan()[".codex/agents/executor.toml"], "skipped-symlink")
        self.run_codex()
        self.assertEqual(victim.read_text(encoding="utf-8"), "ngoài\n")

    def test_missing_symlinked_or_invalid_source_skipped(self):
        self.run_codex()
        before = self.recorded()
        shutil.rmtree(self.target / ".claude" / "skills" / "adr")
        secret = self.outside / "khoá.md"
        secret.write_text("---\nname: lộ\ndescription: lộ\n---\nnội dung ngoài dự án\n", encoding="utf-8")
        src = self.target / ".claude" / "agents" / "executor.md"
        src.unlink()
        src.symlink_to(secret)
        (self.target / ".claude" / "agents" / "researcher.md").write_text("không frontmatter\n", encoding="utf-8")
        reviewer = self.target / ".claude" / "agents" / "reviewer.md"
        reviewer.write_text("---\nname: reviewer\ndescription: >-\n  gấp dòng\n---\nthân\n", encoding="utf-8")
        old = (self.target / ".codex" / "agents" / "reviewer.toml").read_bytes()
        entries = {e["path"]: e for e in install.codex_plan(self.target, [], ["codex"])}
        for rel in (".agents/skills/adr/SKILL.md", ".codex/agents/executor.toml", ".codex/agents/researcher.toml"):
            self.assertEqual(entries[rel]["action"], "skipped-source")
        self.assertEqual(
            entries[".codex/agents/reviewer.toml"],
            {
                "source": ".claude/agents/reviewer.md",
                "path": ".codex/agents/reviewer.toml",
                "action": "skipped-source",
                "reason": "frontmatter dòng 3: khối `|`/`>` (YAML ngoài tập con phẳng)",
            },
        )
        self.assertNotIn("reason", entries[".agents/skills/gate/SKILL.md"])
        err = self.run_codex()
        self.assertIn("bỏ qua .codex/agents/executor.toml — nguồn .claude/agents/executor.md: thiếu, là symlink", err)
        self.assertIn(
            "bỏ qua .codex/agents/reviewer.toml — nguồn .claude/agents/reviewer.md: frontmatter dòng 3: khối", err
        )
        self.assertEqual((self.target / ".codex" / "agents" / "reviewer.toml").read_bytes(), old)  # không ghi đè
        self.assertNotIn("lộ", (self.target / ".codex" / "agents" / "executor.toml").read_text(encoding="utf-8"))
        self.assertEqual(self.recorded(), before)  # nguồn vắng: giữ hash cũ để lần sau còn cập nhật được

    def test_existing_mirror_of_old_framework_updated_in_place(self):
        """Review 🟢 mục 5 + lượt 2 🟠: dự án tự làm gương trước khi khung sinh (chưa có `codex_files`). Gương chỉ được coi
        là bản khung khi NGUỒN là bản khung theo manifest harness: skill — gương trùng hash manifest của nguồn; agent —
        nguồn `.md` trước bước harness còn đúng hash manifest và gương trùng bản sinh từ nguồn đó. Gương trùng bản DỰ ÁN
        (nguồn tự sửa / không có trong manifest) không chứng minh gì → `.xtemplates-new`."""
        claude, agents_dir = self.target / ".claude", self.target / ".agents" / "skills"
        old_gate = "---\nname: gate\ndescription: bản khung cũ\n---\ncũ\n".encode()  # bản khung cũ, dự án chưa sửa
        old_review = "---\nname: reviewer\ndescription: cũ\n---\nthân cũ\n"
        old_adr = b"ban khung adr cu\n"  # bản khung lần cài trước; dự án đã sửa nguồn
        own_research = "---\nname: researcher\ndescription: dự án sửa\n---\nriêng\n"
        sources = {
            "skills/gate/SKILL.md": old_gate,
            "skills/adr/SKILL.md": "dự án sửa adr\n".encode(),
            "skills/review/SKILL.md": "skill review của dự án\n".encode(),  # không có trong manifest
            "agents/reviewer.md": old_review.encode(),
            "agents/researcher.md": own_research.encode(),
            "agents/executor-deep.md": b"khung cu khong frontmatter\n",  # đúng hash manifest nhưng không sinh được
        }
        for rel, data in sources.items():
            (claude / rel).write_bytes(data)
        (claude / "agents" / "executor.md").unlink()  # nguồn vắng trước bước harness, manifest vẫn ghi
        recorded = {
            "skills/gate/SKILL.md": old_gate,
            "skills/adr/SKILL.md": old_adr,
            "agents/reviewer.md": old_review.encode(),
            "agents/researcher.md": b"ban khung cu\n",
            "agents/executor-deep.md": sources["agents/executor-deep.md"],
            "agents/executor.md": b"ban khung cu\n",
        }
        manifest = self.target / install.MANIFEST
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({f".claude/{k}": stored(v) for k, v in recorded.items()}), encoding="utf-8")
        mirrors = {
            ".agents/skills/gate/SKILL.md": old_gate,
            ".agents/skills/adr/SKILL.md": old_adr,
            ".agents/skills/review/SKILL.md": sources["skills/review/SKILL.md"],
            ".codex/agents/reviewer.toml": install.agent_toml(old_review, ".claude/agents/reviewer.md").encode(),
            ".codex/agents/researcher.toml": install.agent_toml(own_research, ".claude/agents/researcher.md").encode(),
            ".codex/agents/executor.toml": b"# cu\n",
            ".codex/agents/executor-deep.toml": b"# cu\n",
        }
        for rel, data in mirrors.items():
            (self.target / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.target / rel).write_bytes(data)
        forced = ("skills/gate/SKILL.md", "skills/review/SKILL.md", *(f"agents/{n}.md" for n in AGENT_NAMES))
        files = [{"path": f".claude/{p}", "action": "copied"} for p in forced]  # như `--force-harness`
        planned = {e["path"]: e["action"] for e in install.codex_plan(self.target, files, ["codex"])}
        updated = (".agents/skills/gate/SKILL.md", ".agents/skills/adr/SKILL.md", ".codex/agents/reviewer.toml")
        kept_new = (
            ".agents/skills/review/SKILL.md",
            *(f".codex/agents/{n}.toml" for n in ("executor", "executor-deep", "researcher")),
        )
        want = {rel: "updated" for rel in updated} | {rel: "updated-new" for rel in kept_new}
        self.assertEqual({rel: planned[rel] for rel in want}, want)
        baseline = install.codex_baseline(self.target)  # cài thật: đọc trước bước harness
        for rel in forced:  # bước harness `--force-harness` ghi bản khung
            shutil.copy2(ROOT / ".claude" / rel, claude / rel)
        self.assertIn("updated 3 · updated-new 4", self.run_codex(baseline))
        self.assertEqual((agents_dir / "gate" / "SKILL.md").read_bytes(), (SKILLS / "gate" / "SKILL.md").read_bytes())
        self.assertEqual((agents_dir / "adr" / "SKILL.md").read_text(encoding="utf-8"), "dự án sửa adr\n")
        toml = tomllib.loads((self.target / ".codex" / "agents" / "reviewer.toml").read_text(encoding="utf-8"))
        self.assertTrue(toml["developer_instructions"].startswith(BODY_HEAD["reviewer"]))
        for rel in kept_new:
            self.assertEqual((self.target / rel).read_bytes(), mirrors[rel])  # bản dự án giữ nguyên
            self.assertTrue((self.target / f"{rel}.xtemplates-new").is_file())
        self.assertFalse((agents_dir / "gate" / "SKILL.md.xtemplates-new").exists())

    def test_unreadable_source_is_none(self):
        src = self.target / ".claude" / "agents" / "executor.md"
        with mock.patch.object(Path, "read_bytes", side_effect=PermissionError("không đọc được")):
            self.assertIsNone(install.read_regular(src))
        self.assertIsNotNone(install.read_regular(src))

    def test_plan_reads_source_the_harness_step_will_write(self):
        (self.target / ".claude" / "skills" / "gate" / "SKILL.md").write_text("bản cũ\n", encoding="utf-8")
        rel = ".claude/skills/gate/SKILL.md"
        self.run_codex()
        self.assertEqual(self.plan()[".agents/skills/gate/SKILL.md"], "kept")
        entries = install.codex_plan(self.target, [{"path": rel, "action": "updated"}], ["codex"])
        self.assertEqual({e["path"]: e["action"] for e in entries}[".agents/skills/gate/SKILL.md"], "updated")
        self.assertEqual(install.codex_plan(self.target, [], ["gemini"]), [])

    def test_bad_manifest_shapes(self):
        manifest = self.target / install.MANIFEST_V2
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"codex_files": []}), encoding="utf-8")
        self.assertEqual(self.recorded(), {})
        manifest.write_text(json.dumps({"codex_files": {"a": 1, "b": "sha256:00"}, "khác": 1}), encoding="utf-8")
        self.assertEqual(self.recorded(), {"b": "sha256:00"})  # giá trị không phải chuỗi: bỏ
        self.run_codex()
        doc = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(doc["khác"], 1)  # giữ mọi khoá khác của manifest
        self.assertNotIn("b", doc["codex_files"])  # chỉ ghi đường của bộ sinh hiện tại
        before = manifest.read_bytes()
        install.install_codex_harness(self.target, ["gemini"])  # không có codex: không đụng gì
        self.assertEqual(manifest.read_bytes(), before)


class SyncCodexTest(unittest.TestCase):
    """`install.py . --sync-codex` ở repo khung (SRC giả): ghi đúng đầu ra bộ sinh, không xoá tệp thừa mà báo và thoát 1;
    từ chối đích khác repo khung và mọi cờ khác."""

    def setUp(self):
        tmp = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.src, self.outside = tmp / "khung", tmp / "outside"
        self.outside.mkdir()
        for d in ("skills", "agents"):
            shutil.copytree(ROOT / ".claude" / d, self.src / ".claude" / d)
        harness = self.src / "framework" / "templates" / "harness"
        harness.mkdir(parents=True)
        shutil.copy2(install.adapter_src("codex"), harness / "codex-hooks.json")
        self.enterContext(mock.patch.object(install, "SRC", self.src))

    def sync(self, *extra: str, target: Path | None = None) -> tuple[int, str]:
        rc, _, err = run_main(str(target or self.src), "--sync-codex", *extra)
        return rc, err

    def test_sync_writes_rewrites_and_reports_extras(self):
        rc, err = self.sync()
        self.assertEqual(rc, 0, err)
        want = install.codex_framework_files()
        for rel, data in want.items():
            self.assertEqual((self.src / rel).read_bytes(), data)
        self.assertIn(f"{len(want)} tệp", err)
        toml = self.src / ".codex" / "agents" / "reviewer.toml"
        toml.write_text("sửa tay\n", encoding="utf-8")
        rc, err = self.sync()
        self.assertEqual((rc, toml.read_bytes()), (0, want[".codex/agents/reviewer.toml"]))
        self.assertIn("1 tệp", err)
        extra = self.src / ".agents" / "skills" / "cũ" / "SKILL.md"
        extra.parent.mkdir()
        extra.write_text("x\n", encoding="utf-8")
        (self.src / ".codex" / "agents" / "lạ.toml").write_text("x\n", encoding="utf-8")
        for rel in (".codex/hooks/guard.py", ".agents/ghi-chú.txt", ".codex/__pycache__/x.pyc"):
            (self.src / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.src / rel).write_text("x\n", encoding="utf-8")
        rc, err = self.sync()
        self.assertEqual(rc, 1)
        line = next(ln for ln in err.splitlines() if "thừa" in ln)
        for rel in (
            ".agents/skills/cũ/SKILL.md",
            ".codex/agents/lạ.toml",
            ".codex/hooks/guard.py",
            ".agents/ghi-chú.txt",
        ):
            self.assertIn(rel, line)
        self.assertNotIn("__pycache__", line)
        self.assertTrue(extra.is_file())  # không tự xoá

    def test_sync_untracked_extras_warn_tracked_extras_fail(self):
        """Review lượt 2 🟢: ở repo git, tệp thừa CHƯA track (`.DS_Store`, `.codex/config.toml` cục bộ, metadata skill) chỉ
        cảnh báo, exit 0; tệp thừa ĐÃ track (sẽ lên repo) → exit 1. Không xoá gì."""
        git = ["git", "-C", str(self.src)]
        subprocess.run([*git, "init", "-q"], check=True, env=git_env())
        self.assertEqual(self.sync()[0], 0)
        local = (".DS_Store", ".codex/config.toml", ".agents/skills/gate/agents/openai.yaml")
        for rel in (".agents/.DS_Store", ".codex/config.toml", ".agents/skills/gate/agents/openai.yaml"):
            (self.src / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.src / rel).write_text("x\n", encoding="utf-8")
        rc, err = self.sync()
        self.assertEqual(rc, 0, err)
        self.assertIn("chưa track", err)
        self.assertTrue(all(rel in err for rel in local))
        self.assertNotIn("✗ thừa", err)
        subprocess.run([*git, "add", ".codex/config.toml"], check=True, env=git_env())
        rc, err = self.sync()
        self.assertEqual(rc, 1)
        tracked = next(ln for ln in err.splitlines() if "✗ thừa" in ln)
        self.assertIn(".codex/config.toml", tracked)
        self.assertNotIn(".DS_Store", tracked)
        self.assertTrue((self.src / ".codex" / "config.toml").is_file())
        with mock.patch.object(install.subprocess, "run", side_effect=OSError("không có git")):
            self.assertIsNone(install.git_tracked(self.src, install.CODEX_ROOTS))

    def test_sync_refuses_wrong_target_other_flags_and_broken_sources(self):
        rc, err = self.sync(target=self.outside)
        self.assertEqual(rc, 2)
        self.assertIn("chỉ chạy ở gốc repo khung", err)
        for flags in (("--plan",), ("--harness", "codex"), ("--no-harness",), ("--new",)):
            with self.subTest(flags=flags):
                self.assertEqual(self.sync(*flags)[0], 2)
        self.assertFalse((self.src / ".agents").exists())
        (self.src / ".claude" / "agents" / "researcher.md").write_text("hỏng\n", encoding="utf-8")
        rc, err = self.sync()
        self.assertEqual(rc, 1)
        self.assertIn(".claude/agents/researcher.md", err)
        shutil.copy2(AGENTS / "researcher.md", self.src / ".claude" / "agents" / "researcher.md")
        template = self.src / "framework" / "templates" / "harness" / "codex-hooks.json"
        template.write_text('{"hooks": {}}\n', encoding="utf-8")
        rc, err = self.sync()
        self.assertEqual(rc, 1)
        self.assertIn("xt_adapter.py", err)

    def test_sync_does_not_write_through_symlink(self):
        (self.src / ".codex").symlink_to(self.outside)
        rc, err = self.sync()
        self.assertEqual(rc, 1)
        self.assertIn("symlink", err)
        self.assertEqual(list(self.outside.iterdir()), [])
        self.assertTrue((self.src / ".agents" / "skills" / "gate" / "SKILL.md").is_file())


class FrameworkCodexHookTest(unittest.TestCase):
    """Lệnh hook trong `.codex/hooks.json` của repo khung chạy được từ gốc repo (đúng chuỗi lệnh, `$(git rev-parse
    --show-toplevel)` thay bằng gốc): adapter tìm guard ở `.claude/hooks/guard.py`, chặn lệnh nguy hiểm, cho lệnh lành."""

    def setUp(self):
        isolate_network(self)
        doc = json.loads((ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
        self.entry = doc["hooks"]["PreToolUse"][0]
        self.command = self.entry["hooks"][0]["command"].replace("$(git rev-parse --show-toplevel)", str(ROOT))

    def hook(self, tool: str, command: str) -> tuple[int, str]:
        payload = {
            "session_id": "s",
            "hook_event_name": "PreToolUse",
            "tool_name": tool,
            "tool_input": {"command": command},
            "cwd": str(ROOT),
        }
        env = {**os.environ, "PATH": f"{Path(sys.executable).parent}{os.pathsep}{os.environ.get('PATH', '')}"}
        r = subprocess.run(
            ["sh", "-c", self.command],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=ROOT,
            env=env,
            timeout=self.entry["hooks"][0]["timeout"] * 4,
        )
        return r.returncode, r.stdout

    def test_denies_dangerous_allows_benign(self):
        for tool, command in (("Bash", "git push origin main"), ("exec_command", "rm -rf ~")):
            with self.subTest(command=command):
                self.assertTrue(re.fullmatch(self.entry["matcher"], tool))
                rc, out = self.hook(tool, command)
                self.assertEqual(rc, 0)
                self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "deny", out)
        self.assertEqual(self.hook("shell", "ls -la"), (0, ""))


if __name__ == "__main__":
    unittest.main()
