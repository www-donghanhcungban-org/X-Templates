"""ADR-0106 (D-619): khách duyệt thiết kế — sổ `docs/autopilot/DESIGN.json`, lệnh `stage design-*`/`approve --design`,
khoá task `ui: yes` ở `loop next`/`loop record`, guard chặn ghi tay sổ và duyệt bởi agent."""

import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
sys.path.insert(0, str(Path(__file__).resolve().parent))  # test_stage, test_xt_cli, test_stage_agent_approval
import guard
import test_stage_agent_approval as saa
import xt
import xt_design as d
from test_stage import human_env
from test_xt_cli import TmpRepoCase, run_main

SHA = "a" * 40
SHA2 = "b" * 40
PNG = hashlib.sha256(b"png").hexdigest()  # nội dung "png" của docs/m.png trong các repo tạm (ADR-0107)
AT = "2026-11-26T00:00:00+00:00"


def ev(kind, **extra):
    return {"event": kind, "at": AT, **extra}


def submit(sha=SHA, evidence="docs/m.png", digest=PNG):
    return ev("submit", sha=sha, evidence=evidence, evidence_sha256=digest)


def led(history, status, submitted=None):
    return {"schema": 1, "status": status, "submitted": submitted, "history": history}


def awaiting(history, sha=SHA, evidence="docs/m.png", digest=PNG):
    return led(history, "awaiting_approval", {"sha": sha, "evidence": evidence, "evidence_sha256": digest})


class DesignLedgerProblemTest(unittest.TestCase):
    def test_valid_histories(self):
        ok = [
            d.empty(),
            awaiting([submit()]),
            led([submit(), ev("reopen", reason="sửa màu")], "none"),
            led([submit(), ev("approve", sha=SHA, by="chu@x")], "approved"),
            awaiting([submit(), ev("approve", sha=SHA, by="chu@x"), submit(SHA2)], SHA2),  # trình lại = khoá lại
            led([submit(), ev("approve", sha=SHA, by="p"), submit(SHA2), ev("approve", sha=SHA2, by="p")], "approved"),
            awaiting([submit("c" * 64)], "c" * 64),  # repo `--object-format=sha256` (COMMIT_SHA_RE của xt)
        ]
        for case in ok:
            with self.subTest(case=case["history"][-1:] or "rỗng"):
                self.assertEqual(d.problem(xt, case), "")

    def test_shape_and_order_errors(self):
        bad = [
            ([], "schema"),
            ({**d.empty(), "schema": 2}, "schema"),
            ({**d.empty(), "status": "ok"}, "`status` phải"),
            ({**d.empty(), "history": {}}, "`history` phải là list"),
            (led(["x"], "none"), "object có `at`"),
            (led([{"event": "submit"}], "none"), "object có `at`"),
            (led([{"event": "submit", "at": ""}], "none"), "object có `at`"),
            (led([ev("tick")], "none"), "`event` lạ"),
            (awaiting([submit(), submit()]), "khi đang chờ duyệt"),
            (awaiting([submit(sha="abc")]), "SHA commit đầy đủ"),
            (awaiting([submit(sha="c" * 63)]), "SHA commit đầy đủ"),
            (awaiting([submit(evidence="/etc/x")]), "đường tương đối"),
            (awaiting([submit(evidence="../x")]), "đường tương đối"),
            (awaiting([submit(evidence="")]), "đường tương đối"),
            (awaiting([submit(evidence=3)]), "đường tương đối"),
            # ADR-0107: `submit` thiếu hay sai dạng `evidence_sha256` → sổ hỏng (fail-closed)
            (awaiting([ev("submit", sha=SHA, evidence="docs/m.png")]), "`evidence_sha256` 64 hex"),
            (awaiting([submit(digest=None)]), "`evidence_sha256` 64 hex"),
            (awaiting([submit(digest="c" * 40)]), "`evidence_sha256` 64 hex"),
            (awaiting([submit(digest="C" * 64)]), "`evidence_sha256` 64 hex"),
            (awaiting([submit()], digest="d" * 64), "lịch sử dựng ra"),  # sửa tay hash ở `submitted`
            (led([ev("reopen", reason="x")], "none"), "`reopen` chỉ"),
            (led([submit(), ev("reopen")], "none"), "`reopen` chỉ"),
            (led([submit(), ev("reopen", reason="")], "none"), "`reopen` chỉ"),
            (led([ev("approve", sha=SHA, by="p")], "approved"), "`approve` chỉ"),
            (led([submit(), ev("approve", sha=SHA2, by="p")], "approved"), "`approve` chỉ"),
            (led([submit(), ev("reopen", reason="x"), ev("approve", sha=SHA, by="p")], "approved"), "`approve` chỉ"),
            (led([submit(), ev("approve", sha=SHA)], "approved"), "không phải agent"),
            (led([submit(), ev("approve", sha=SHA, by=" ")], "approved"), "không phải agent"),
            (led([submit(), ev("approve", sha=SHA, by="Agent")], "approved"), "không phải agent"),
            (
                led([submit(), ev("approve", sha=SHA, by="p"), ev("approve", sha=SHA, by="p")], "approved"),
                "`approve` chỉ",
            ),
            (led([], "approved"), "lịch sử dựng ra `none`"),  # sửa tay status
            (awaiting([submit()], evidence="khac.png"), "lịch sử dựng ra"),  # sửa tay submitted
            (led([submit()], "none"), "lịch sử dựng ra"),
        ]
        for case, why in bad:
            with self.subTest(why=why, case=case):
                self.assertIn(why, d.problem(xt, case))


class DesignDeclareTest(TmpRepoCase):
    def setUp(self):
        super().setUp()
        self.init_repo()

    def declare(self, text):
        (self.repo / "PROJECT.md").write_text(text, encoding="utf-8")
        return d.declared(xt, self.repo)

    def test_declaration_forms(self):
        self.assertEqual(d.declared(xt, self.repo), (False, ""))  # vắng PROJECT.md = không
        client = [
            "Duyệt thiết kế: khách\n",
            "# Dự án\n- Duyệt thiết kế: khách\n",
            "* **Duyệt thiết kế:** Khách\n",
            "**Duyệt thiết kế: KHÁCH**\n",
            "  duyệt thiết kế :  khách  \n",
            "Duyệt thiết kế: khách\n",  # dấu tách rời (NFD) vẫn khớp sau NFC
            "Duyệt thiết kế: khách\nDuyệt thiết kế: khách\n",  # trùng cùng giá trị
            "```\nDuyệt thiết kế: không\n```\nDuyệt thiết kế: khách\n",
            # Review PR #844: nhận dòng theo NHÃN, giá trị = chữ đầu sau `:` — các dạng điền tự nhiên không được nới khoá.
            "- Duyệt thiết kế: khách — `khách` khi hợp đồng đòi khách duyệt bản thiết kế\n",
            "- Duyệt thiết kế: khách hàng\n",
            "- Duyệt thiết kế: khách.\n",
            "- Duyệt thiết kế: khách (HĐ 12)\n",
            "> Duyệt thiết kế: khách\n",
            "> - **Duyệt thiết kế:** khách\n",
            "1. Duyệt thiết kế: khách\n",
            "2) Duyệt thiết kế: khách\n",
            "+ Duyệt thiết kế: khách\n",
            "| Duyệt thiết kế: khách |\n",
            "| Duyệt thiết kế | khách |\n",
            "- Duyệt thiết kế: khách\n",  # NBSP trong nhãn
            "﻿Duyệt thiết kế: khách\n",  # BOM đầu tệp
            "​- Duyệt thiết kế: khách\n",  # ZWSP
            "- Duyệt thiết​kế: khách\n",
            "_Duyệt thiết kế:_ khách\n",
            "## Duyệt thiết kế: khách\n",
            "- [x] Duyệt thiết kế: khách\n",
            "- Duyệt  thiết   kế\t: khách\n",  # nhiều khoảng trắng trong nhãn
            "- DUYỆT THIẾT KẾ：`khách`\n",  # dấu hai chấm toàn khổ (NFKC), giá trị trong backtick
        ]
        for text in client:
            with self.subTest(text=text):
                self.assertEqual(self.declare(text), (True, ""))
        human = [
            "Duyệt thiết kế: không\n",
            "- **Duyệt thiết kế:** không\n",
            "# Dự án\n",
            "- Duyệt thiết kế: không — dự án nội bộ\n",
            "- Duyệt thiết kế: Không.\n",
            "> 1. _Duyệt thiết kế:_ **không** (HĐ 12)\n",
            "| Duyệt thiết kế | không |\n",
            "Ghi chú: Duyệt thiết kế: khách\n",  # nhãn không ở đầu dòng: không phải dòng khai
            "```\nDuyệt thiết kế: khách\n```\n",
            "~~~\n```\nDuyệt thiết kế: khách\n~~~\n",  # fence khác loại bên trong không đóng fence ngoài
            "﻿```\nDuyệt thiết kế: khách\n```\n",  # BOM trước fence: vẫn là fence
        ]
        for text in human:
            with self.subTest(text=text):
                self.assertEqual(self.declare(text), (False, ""))

    def test_odd_value_means_client_with_note(self):
        for text, shown in (
            ("- Duyệt thiết kế:\n", "``"),
            ("- Duyệt thiết kế: <không | khách>\n", "``"),  # mẫu chưa điền
            ("- Duyệt thiết kế: khong\n", "`khong`"),
            ("- Duyệt thiết kế: có\n", "`có`"),
        ):
            with self.subTest(text=text):
                client, note = self.declare(text)
                self.assertTrue(client)
                self.assertIn(f"giá trị lạ {shown}", note)
        client, note = self.declare("- Duyệt thiết kế: không\n- Duyệt thiết kế: khách hàng\n")
        self.assertEqual((client, "mâu thuẫn" in note), (True, True))

    def test_template_line_parses(self):
        """Mẫu `PROJECT.md`: dòng khai chỉ còn `không`; đổi thành `khách` là khoá (giải thích ở dòng riêng)."""
        whole = (ROOT / "framework/templates/PROJECT.md").read_text(encoding="utf-8")
        text = whole.split("```markdown\n", 1)[1].rsplit("```", 1)[0]  # thân mẫu người chép (trong fence của tệp mẫu)
        self.assertIn("\n- Duyệt thiết kế: không\n", text)
        self.assertEqual(self.declare(text), (False, ""))
        self.assertEqual(self.declare(text.replace("Duyệt thiết kế: không", "Duyệt thiết kế: khách")), (True, ""))

    def test_conflict_and_unreadable_mean_client(self):
        client, note = self.declare("Duyệt thiết kế: không\n- Duyệt thiết kế: khách\n")
        self.assertTrue(client)
        self.assertIn("mâu thuẫn", note)
        (self.repo / "PROJECT.md").write_bytes(b"\xff\xfe")
        client, note = d.declared(xt, self.repo)
        self.assertTrue(client)
        self.assertIn("không đọc được PROJECT.md", note)
        self.declare("Duyệt thiết kế: không\nDuyệt thiết kế: khách\n")
        self.assertIn("mâu thuẫn", d.lock_reason(xt, self.repo))  # ghi chú đi kèm lý do khoá


class DesignUiTagTest(unittest.TestCase):
    def ui(self, line):
        return d.is_ui(xt, xt._parse_plan_lines([line])[0])

    def test_ui_tag(self):
        yes = [
            "- [ ] `T-001` Trang chủ (ui: yes) — Gate: `true`",
            "- [ ] `T-001` Trang chủ (sau: T-000; ui: yes; files: a.html) — Gate: `true`",
            "- [ ] `T-001` Trang chủ (UI: Yes)",
            "- [ ] `T-001` Trang chủ (topo: self, ui: yes",  # ngoặc chưa đóng vẫn tính (chặt hơn)
            "- [ ] `T-001` Trang chủ (ui: true) — Gate: `true`",  # giá trị lạ: mọi giá trị khác `no` là giao diện
            "- [ ] `T-001` Trang chủ (ui: có) — Gate: `true`",
            "- [ ] `T-001` Trang chủ (ui:) — Gate: `true`",
            "- [ ] `T-001` Trang chủ (ui: none) — Gate: `true`",
        ]
        no = [
            "- [ ] `T-001` Trang chủ — Gate: `true`",
            "- [ ] `T-001` Trang chủ (ui: no) — Gate: `true`",
            "- [ ] `T-001` Trang chủ (UI : NO; files: a.html) — Gate: `true`",
            "- [ ] `T-001` Trang chủ (files: gui: a.html) — Gate: `true`",  # `gui:` không phải thẻ `ui:`
            "- [ ] `T-001` Trang chủ ui: yes — Gate: `true`",  # ngoài nhóm ngoặc
            "- [ ] `T-001` Trang chủ `(ui: yes)` — Gate: `true`",  # chữ trích
            "- [ ] `T-001` Trang chủ — Gate: `echo '(ui: yes)'`",  # trong lệnh Gate
        ]
        for line in yes:
            with self.subTest(line=line):
                self.assertTrue(self.ui(line))
        for line in no:
            with self.subTest(line=line):
                self.assertFalse(self.ui(line))
        self.assertFalse(d.is_ui(xt, {"id": "T-1"}))


class DesignRepoCase(TmpRepoCase):
    """Repo tạm có user git, ngoài phiên agent; `loop_root` = repo."""

    def setUp(self):
        super().setUp()
        self.init_repo()
        self.git("config", "user.email", "chu@example.invalid")
        self.git("config", "user.name", "chu")
        self.git("config", "commit.gpgsign", "false")
        self.enterContext(human_env(CLAUDE_PROJECT_DIR=str(self.repo)))
        self.enterContext(unittest.mock.patch.object(xt, "loop_root", lambda base: base))

    def write(self, rel, text):
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def commit(self, msg="c"):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)
        return self.git("rev-parse", "HEAD").strip()

    def stage(self, *args, agent=False):
        env = {"CLAUDE_CODE_SESSION_ID": "s-1"} if agent else {}
        with unittest.mock.patch.dict(os.environ, env):
            return run_main("stage", *args)

    def ledger(self):
        return json.loads((self.repo / d.LEDGER).read_text(encoding="utf-8"))


class DesignCliTest(DesignRepoCase):
    def test_full_flow_and_relock(self):
        self.write("PROJECT.md", "- Duyệt thiết kế: khách\n")
        self.write("docs/design/home.png", "png")
        sha = self.commit()
        rc, out, _ = self.stage("design-check")
        self.assertEqual(rc, 1)
        self.assertIn("design-submit", out)
        rc, out, err = self.stage("design-submit", "--evidence", "docs/design/home.png", agent=True)
        self.assertEqual(rc, 0, err)
        self.assertIn(f"bản {sha[:12]}: docs/design/home.png", out)
        self.assertEqual(
            self.ledger()["submitted"], {"sha": sha, "evidence": "docs/design/home.png", "evidence_sha256": PNG}
        )
        self.assertEqual(self.ledger()["history"][-1]["evidence_sha256"], PNG)
        rc, _, err = self.stage("design-submit", "--evidence", "docs/design/home.png")
        self.assertEqual(rc, 2)  # sổ chưa commit: cây bẩn
        self.commit("sổ")
        rc, _, err = self.stage("design-submit", "--evidence", "docs/design/home.png")
        self.assertEqual(rc, 2)
        self.assertIn("đang chờ người duyệt", err)
        rc, out, _ = self.stage("design-check")
        self.assertEqual(rc, 1)
        self.assertIn(f"--sha {sha[:12]}", out)
        for bad, why in (("abc", "≥ 7 ký tự"), ("1234567", "không phải ≥ 7")):
            rc, _, err = self.stage("approve", "--design", "--sha", bad, "--note", "ok")
            self.assertEqual(rc, 2)
            self.assertIn(why, err)
        rc, out, err = self.stage("approve", "--design", "--sha", sha[:7].upper(), "--note", "khách đồng ý")
        self.assertEqual(rc, 0, err)
        self.assertIn("approved", out)
        last = self.ledger()["history"][-1]
        self.assertEqual(
            (last["event"], last["sha"], last["by"], last["note"]),
            ("approve", sha, "chu@example.invalid", "khách đồng ý"),
        )
        self.assertFalse((self.repo / xt.STAGE_LEDGER).exists())  # không đụng STAGE.json
        rc, _, err = self.stage("approve", "--sha", sha[:7], "--note", "ok")  # không `--design`: sổ giai đoạn như cũ
        self.assertEqual(rc, 2)
        self.assertIn("không có giai đoạn chờ duyệt", err)
        rc, out, _ = self.stage("design-check", "--json")
        self.assertEqual(rc, 0)
        info = json.loads(out)
        self.assertEqual((info["ok"], info["client"], info["design"]["status"]), (True, True, "approved"))
        rc, _, err = self.stage("approve", "--design", "--sha", sha[:7], "--note", "x")
        self.assertEqual(rc, 2)
        self.assertIn("không có bản thiết kế chờ duyệt", err)
        self.write("docs/design/home.png", "png v2")
        sha2 = self.commit("bản 2")
        self.assertEqual(self.stage("design-submit", "--evidence", str(self.repo / "docs/design/home.png"))[0], 0)
        self.assertEqual(self.ledger()["submitted"]["sha"], sha2)
        self.assertEqual(self.stage("design-check")[0], 1)  # trình lại sau duyệt = khoá lại
        rc, out, err = self.stage("design-reopen", "--reason", "khách đổi ý")
        self.assertEqual(rc, 0, err)
        self.assertEqual(self.ledger()["status"], "none")
        rc, _, err = self.stage("design-reopen", "--reason", "lần hai")
        self.assertEqual(rc, 2)
        self.assertIn("chỉ mở lại", err)
        self.assertEqual(d.problem(xt, self.ledger()), "")

    def test_check_without_client_and_broken_ledger(self):
        rc, out, _ = self.stage("design-check")
        self.assertEqual(rc, 0)
        self.assertIn("Duyệt thiết kế: không", out)
        self.assertIn("không bị khoá", out)
        self.write(d.LEDGER, "{")
        rc, _, err = self.stage("design-check")
        self.assertEqual(rc, 2)
        self.assertIn("không đọc được", err)
        self.write(d.LEDGER, json.dumps(led([], "approved")))
        rc, _, err = self.stage("design-check", "--json")
        self.assertEqual(rc, 2)
        self.assertIn("hỏng", err)
        self.write("PROJECT.md", "Duyệt thiết kế: khách\n")
        self.assertIn("hỏng", d.lock_reason(xt, self.repo))
        rc, _, err = self.stage("design-reopen", "--reason", "x")
        self.assertEqual(rc, 2)  # sổ hỏng: lệnh ghi cũng chặn

    def test_submit_refusals(self):
        rc, _, err = self.stage("design-submit", "--evidence", "x.png")
        self.assertEqual(rc, 2)
        self.assertIn("không có commit", err)
        self.write("docs/m.png", "png")
        self.write(".gitignore", "bo-qua.png\n")
        self.commit()
        self.write("bẩn.txt", "x")
        rc, _, err = self.stage("design-submit", "--evidence", "docs/m.png")
        self.assertEqual(rc, 2)
        self.assertIn("chưa commit", err)
        (self.repo / "bẩn.txt").unlink()
        (self.repo / "docs/link.png").symlink_to(self.repo / "docs/m.png")
        self.commit("link")
        outside = self.tmp / "ngoai.png"
        outside.write_text("x", encoding="utf-8")
        self.write("bo-qua.png", "ignored")
        cases = [
            ("docs/khong-co.png", "không phải tệp thường"),
            ("docs", "không phải tệp thường"),
            ("docs/link.png", "không phải tệp thường"),
            (str(outside), "ngoài dự án"),
            ("../ngoai.png", "ngoài dự án"),
            ("bo-qua.png", "chưa commit"),  # bỏ qua bởi .gitignore: cây "sạch" nhưng tệp không có ở HEAD
        ]
        for raw, why in cases:
            with self.subTest(raw=raw):
                rc, _, err = self.stage("design-submit", "--evidence", raw)
                self.assertEqual(rc, 2)
                self.assertIn(why, err)
        self.assertFalse((self.repo / d.LEDGER).exists())

    def test_agent_never_approves_design(self):
        self.write("docs/m.png", "png")
        sha = self.commit()
        self.assertEqual(self.stage("design-submit", "--evidence", "docs/m.png", agent=True)[0], 0)
        self.write("xt.yaml", "lint: ''\nstage_approval: agent\n")
        with unittest.mock.patch.object(xt, "stage_agent_approval", return_value=True):
            for env in ({"CLAUDE_CODE_SESSION_ID": "s-1"}, {"CLAUDECODE": ""}, {"AI_AGENT": "x"}):
                with self.subTest(env=env), unittest.mock.patch.dict(os.environ, env):
                    rc, _, err = run_main("stage", "approve", "--design", "--sha", sha, "--note", "ok")
                    self.assertEqual(rc, 2)
                    self.assertIn("chỉ người", err)
        self.assertEqual(self.ledger()["status"], "awaiting_approval")

    def test_approver_needs_git_identity(self):
        self.write("docs/m.png", "png")
        sha = self.commit()
        self.assertEqual(self.stage("design-submit", "--evidence", "docs/m.png")[0], 0)
        with unittest.mock.patch.object(xt, "_stage_by", side_effect=xt.StageError("không biết người duyệt")):
            rc, _, err = self.stage("approve", "--design", "--sha", sha, "--note", "ok")
        self.assertEqual(rc, 2)
        self.assertIn("không biết người duyệt", err)

    def test_concurrent_submit_sees_ledger_inside_lock(self):
        """Lệnh khác ghi sổ giữa kiểm trước khoá và lúc lấy khoá: kiểm lại trong khoá, không ghi đè."""
        self.write("docs/m.png", "png")
        sha = self.commit()
        original = xt._state_lock

        @contextlib.contextmanager
        def competing(base):
            with original(base):
                self.write(d.LEDGER, json.dumps(awaiting([submit(SHA2)], SHA2)))
                yield

        with unittest.mock.patch.object(xt, "_state_lock", competing):
            rc, _, err = self.stage("design-submit", "--evidence", "docs/m.png")
        self.assertEqual(rc, 2)
        self.assertIn(f"đã trình bản {SHA2[:12]}", err)
        self.assertEqual(self.ledger()["submitted"]["sha"], SHA2)
        self.assertNotEqual(sha, SHA2)


class DesignUpdateTest(DesignRepoCase):
    def test_symlink_parent_refused(self):
        real = self.tmp / "ngoai"
        real.mkdir()
        (self.repo / "docs").symlink_to(real)
        with self.assertRaisesRegex(d.DesignError, "symlink"):
            d.update(xt, self.repo, lambda led: led)

    def test_invalid_transition_not_written(self):
        with self.assertRaisesRegex(d.DesignError, "tạo sổ sai"):
            d.update(xt, self.repo, lambda led: {**led, "status": "approved"})
        self.assertFalse((self.repo / d.LEDGER).exists())

    def test_write_failure_leaves_no_empty_ledger(self):
        boom = unittest.mock.patch.object(xt, "write_atomic", side_effect=OSError("đầy đĩa"))
        with boom, self.assertRaises(OSError):
            d.update(xt, self.repo, lambda led: led)
        self.assertFalse((self.repo / d.LEDGER).exists())  # sổ mới: không để lại tệp rỗng
        d.update(xt, self.repo, lambda led: led)
        before = (self.repo / d.LEDGER).read_text(encoding="utf-8")
        with boom, self.assertRaises(OSError):
            d.update(xt, self.repo, lambda led: led)
        self.assertEqual((self.repo / d.LEDGER).read_text(encoding="utf-8"), before)  # sổ cũ giữ nguyên


class DesignLoopTest(DesignRepoCase):
    PLAN = "docs/autopilot/PLAN.md"

    def setUp(self):
        super().setUp()
        self.write(
            self.PLAN,
            "# PLAN\n\n- [ ] `T-001` Trang chủ (ui: yes; files: a.html) — Gate: `true`\n"
            "- [ ] `T-002` API (files: b.py) — Gate: `true`\n",
        )
        self.assertEqual(run_main("loop", "init", "--plan", self.PLAN)[0], 0)

    def next_ids(self):
        rc, out, err = run_main("loop", "next", "--json")
        self.assertEqual(rc, 0, err)
        info = json.loads(out)
        return [t["id"] for t in info["ready"]], info["design_hold"]

    def record(self, task):
        return run_main("loop", "record", "--task", task, "--no-tick", "--", "true")

    def test_no_client_no_change(self):
        self.assertEqual(self.next_ids(), (["T-001", "T-002"], {}))
        self.assertEqual(self.record("T-001")[0], 0)

    def test_client_locks_ui_tasks_until_approved(self):
        self.write("PROJECT.md", "Duyệt thiết kế: khách\n")
        ready, held = self.next_ids()
        self.assertEqual(ready, ["T-002"])
        self.assertIn("stage design-submit", held["T-001"])
        rc, out, _ = run_main("loop", "next")
        self.assertEqual(rc, 0)
        self.assertIn("⛔ T-001 — task giao diện", out)
        rc, _, err = self.record("T-001")
        self.assertEqual(rc, 2)
        self.assertIn("stage design-submit", err)
        self.assertFalse((self.repo / ".autopilot" / "evidence" / "T-001.json").exists())
        self.assertEqual(self.record("T-002")[0], 0)  # task không thẻ: không đổi
        self.write("docs/m.png", "png")
        sha = self.commit()
        self.assertEqual(self.stage("design-submit", "--evidence", "docs/m.png", agent=True)[0], 0)
        rc, _, err = self.record("T-001")
        self.assertEqual(rc, 2)
        self.assertIn(f"stage approve --design --sha {sha[:12]}", err)
        self.assertEqual(self.stage("approve", "--design", "--sha", sha, "--note", "ok")[0], 0)
        self.assertEqual(self.next_ids(), (["T-001", "T-002"], {}))
        self.assertEqual(self.record("T-001")[0], 0)

    def test_lock_reason_names_defer_exit(self):
        self.write("PROJECT.md", "Duyệt thiết kế: khách\n")
        self.assertIn("loop defer --task <ID> --reason", self.next_ids()[1]["T-001"])
        self.write("docs/m.png", "png")
        self.commit()
        self.assertEqual(self.stage("design-submit", "--evidence", "docs/m.png", agent=True)[0], 0)
        self.assertIn("loop defer --task <ID> --reason", self.record("T-001")[2])

    def handoff(self):
        rc, out, err = run_main("plan", "waves", "--handoff")
        self.assertEqual(rc, 0, err)
        info = json.loads(out)
        return [t["task"] for t in info["tasks"]], {b["id"]: b["reason"] for b in info["blocked"]}

    def test_handoff_holds_ui_tasks_like_defer(self):
        """Review PR #844: `plan waves --handoff` (đường của /factory) không giao task `ui: yes` khi khách chưa duyệt."""
        self.write(
            self.PLAN,
            "# PLAN\n\n- [ ] `T-001` Trang chủ (ui: yes; files: a.html) — Gate: `true`\n"
            "- [ ] `T-002` API (files: b.py) — Gate: `true`\n"
            "- [ ] `T-003` Trang con (sau: T-001; files: c.html) — Gate: `true`\n",
        )
        self.assertEqual(self.handoff(), (["T-001", "T-002"], {}))  # không khai khách: như cũ
        self.write("PROJECT.md", "- Duyệt thiết kế: khách\n")
        tasks, blocked = self.handoff()
        self.assertEqual((tasks, list(blocked)), (["T-002"], ["T-001", "T-003"]))
        self.assertIn("stage design-submit", blocked["T-001"])
        self.assertIn("chờ T-001 bị chặn", blocked["T-003"])  # lan chặn như task defer
        self.write("docs/m.png", "png")
        sha = self.commit()
        self.assertEqual(self.stage("design-submit", "--evidence", "docs/m.png", agent=True)[0], 0)
        self.assertIn(f"--sha {sha[:12]}", self.handoff()[1]["T-001"])
        self.assertEqual(self.stage("approve", "--design", "--sha", sha, "--note", "ok")[0], 0)
        self.assertEqual(self.handoff(), (["T-001", "T-002"], {}))
        with unittest.mock.patch.object(xt, "SCRIPT_DIR", self.tmp):  # bộ cài tối giản: không có module, như cũ
            self.write("PROJECT.md", "- Duyệt thiết kế: khách\n- Duyệt thiết kế: không\n")
            self.assertEqual(self.handoff(), (["T-001", "T-002"], {}))

    def test_record_refuses_when_plan_unreadable(self):
        """Review PR #844: khai khách, chưa duyệt, PLAN không đọc được → không biết task có `ui: yes` → chặn."""
        self.write("PROJECT.md", "Duyệt thiết kế: khách\n")
        (self.repo / self.PLAN).write_bytes(b"\xff\xfe- [ ] `T-002` API\n")
        rc, _, err = self.record("T-002")
        self.assertEqual(rc, 2)
        self.assertIn("PLAN của vòng không đọc được", err)
        self.assertFalse((self.repo / ".autopilot" / "evidence" / "T-002.json").exists())
        self.assertIn("không đọc được", d.record_problem(xt, self.repo, {}, "T-002"))  # vòng không khai PLAN
        (self.repo / self.PLAN).unlink()
        self.assertIn("không đọc được", d.record_problem(xt, self.repo, {"plan": self.PLAN}, "T-002"))
        self.write("PROJECT.md", "Duyệt thiết kế: không\n")
        self.assertEqual(d.record_problem(xt, self.repo, {"plan": self.PLAN}, "T-002"), "")  # không khai khách: như cũ

    def submit_v1(self):
        self.write("PROJECT.md", "- Duyệt thiết kế: khách\n")
        self.write("docs/design/DESIGN-REVIEW.md", "bản 1")
        sha = self.commit("bản 1")
        self.assertEqual(self.stage("design-submit", "--evidence", "docs/design/DESIGN-REVIEW.md", agent=True)[0], 0)
        self.commit("trình")
        return sha

    def approve_v1(self):
        sha = self.submit_v1()
        self.assertEqual(self.stage("approve", "--design", "--sha", sha, "--note", "ok")[0], 0)
        self.commit("duyệt")
        self.assertEqual(self.record("T-001")[0], 0)
        return sha

    def test_revert_ledger_to_old_approval_relocks(self):
        """ADR-0107 (lỗ A): trình bản 2 rồi `git revert` commit ghi sổ → sổ về `approved` của bản 1 trong khi mockup bản 2
        vẫn ở cây — lời duyệt gắn với hash nội dung nên khoá lại."""
        self.approve_v1()
        self.write("docs/design/DESIGN-REVIEW.md", "bản 2")
        self.commit("bản 2")
        self.assertEqual(self.stage("design-submit", "--evidence", "docs/design/DESIGN-REVIEW.md", agent=True)[0], 0)
        self.commit("trình 2")
        self.git("revert", "--no-edit", "HEAD")
        self.assertEqual(self.ledger()["status"], "approved")
        rc, _, err = self.record("T-001")
        self.assertEqual(rc, 2)
        self.assertIn("đã đổi sau khi trình/duyệt", err)
        self.assertEqual(self.stage("design-check")[0], 1)

    def test_evidence_edited_deleted_or_symlinked_after_approval_relocks(self):
        self.approve_v1()
        self.write("docs/design/DESIGN-REVIEW.md", "bản 1 sửa lén")
        self.commit("sửa mockup")
        rc, _, err = self.record("T-001")
        self.assertEqual(rc, 2)
        self.assertIn("bản bằng chứng docs/design/DESIGN-REVIEW.md đã đổi sau khi trình/duyệt", err)
        self.assertIn("stage design-submit", err)
        self.write("docs/design/DESIGN-REVIEW.md", "bản 1")  # trả đúng nội dung đã duyệt → mở lại
        self.assertEqual(self.record("T-001")[0], 0)
        (self.repo / "docs/design/DESIGN-REVIEW.md").unlink()
        self.assertIn("tệp mất", self.record("T-001")[2])
        target = self.repo / "docs/design/that.md"
        target.write_text("bản 1", encoding="utf-8")
        (self.repo / "docs/design/DESIGN-REVIEW.md").symlink_to(target)  # cùng nội dung qua symlink: không tính
        self.assertEqual(self.record("T-001")[0], 2)

    def test_squash_merge_keeps_approval(self):
        """Hash nội dung chịu được squash: nhánh orphan cùng cây, SHA đã duyệt không còn là tổ tiên → vẫn `approved`."""
        sha = self.approve_v1()
        self.git("checkout", "-q", "--orphan", "main-squash")
        squashed = self.commit("squash")
        ancestor = subprocess.run(
            ["git", "-C", str(self.repo), "merge-base", "--is-ancestor", sha, "HEAD"], check=False
        )
        self.assertEqual(ancestor.returncode, 1)
        self.assertNotEqual(squashed, sha)
        self.assertEqual(self.record("T-001")[0], 0)
        self.assertEqual(self.stage("design-check")[0], 0)

    def test_shallow_clone_sha_missing_keeps_approval(self):
        """Clone nông giả: SHA trong sổ không có trong repo; hash khớp → mở, lệch → khoá; không gọi git."""
        self.write("PROJECT.md", "Duyệt thiết kế: khách\n")
        self.write("docs/m.png", "png")
        self.write(d.LEDGER, json.dumps(led([submit(digest=PNG), ev("approve", sha=SHA, by="p")], "approved")))
        with unittest.mock.patch.object(xt, "_stage_git", side_effect=AssertionError("không được gọi git")):
            self.assertEqual(d.lock_reason(xt, self.repo), "")
            self.write("docs/m.png", "png khác")
            self.assertIn("hash nội dung lệch", d.lock_reason(xt, self.repo))

    def test_approve_refuses_evidence_changed_after_submit(self):
        sha = self.submit_v1()
        self.write("docs/design/DESIGN-REVIEW.md", "bản 1 sửa sau khi trình")
        self.commit("sửa sau trình")
        rc, out, _ = self.stage("design-check")
        self.assertEqual(rc, 1)
        self.assertIn("design-reopen", out)
        rc, _, err = self.stage("approve", "--design", "--sha", sha, "--note", "ok")
        self.assertEqual(rc, 2)
        self.assertIn("đã đổi sau khi trình/duyệt", err)
        self.assertEqual(self.ledger()["status"], "awaiting_approval")

    def test_concurrent_edit_inside_lock_refuses_approve(self):
        """Bằng chứng đổi giữa kiểm trước khoá và lúc lấy khoá: `approve` kiểm hash TRONG khoá, không duyệt bản đã đổi."""
        sha = self.submit_v1()
        original = xt._state_lock

        @contextlib.contextmanager
        def competing(base):
            with original(base):
                self.write("docs/design/DESIGN-REVIEW.md", "bản 1 đổi lúc duyệt")
                yield

        with unittest.mock.patch.object(xt, "_state_lock", competing):
            rc, _, err = self.stage("approve", "--design", "--sha", sha, "--note", "ok")
        self.assertEqual(rc, 2)
        self.assertIn("đã đổi sau khi trình/duyệt", err)
        self.assertEqual(self.ledger()["status"], "awaiting_approval")

    def test_file_sha256_unreadable_and_submit_without_hash_refused(self):
        self.write("docs/m.png", "png")
        self.assertEqual(d.file_sha256(self.repo, "docs/m.png"), PNG)
        self.assertEqual(d.file_sha256(self.repo, "docs"), "")
        self.commit()
        with unittest.mock.patch("builtins.open", side_effect=PermissionError("cấm")):
            self.assertEqual(d.file_sha256(self.repo, "docs/m.png"), "")
        with unittest.mock.patch.object(d, "file_sha256", return_value=""):
            rc, _, err = self.stage("design-submit", "--evidence", "docs/m.png")
        self.assertEqual(rc, 2)
        self.assertIn("tạo sổ sai", err)  # không ghi sổ thiếu hash
        self.assertFalse((self.repo / d.LEDGER).exists())

    def test_old_ledger_without_hash_locks(self):
        self.write("PROJECT.md", "Duyệt thiết kế: khách\n")
        old = led([ev("submit", sha=SHA, evidence="docs/m.png"), ev("approve", sha=SHA, by="p")], "approved")
        self.write(d.LEDGER, json.dumps(old))
        self.assertIn("evidence_sha256", d.lock_reason(xt, self.repo))
        self.assertEqual(self.record("T-001")[0], 2)

    def test_project_flip_or_delete_keeps_lock_once_submitted(self):
        """ADR-0107 (lỗ B): sổ đã có `history` → đổi `PROJECT.md` sang `không` hay xoá nó không tắt khoá."""
        sha = self.submit_v1()
        for text in ("- Duyệt thiết kế: không\n", None):
            with self.subTest(project=text):
                if text is None:
                    (self.repo / "PROJECT.md").unlink()
                else:
                    self.write("PROJECT.md", text)
                rc, _, err = self.record("T-001")
                self.assertEqual(rc, 2)
                self.assertIn("đã có lịch sử trình", err)
                self.assertEqual(self.next_ids()[0], ["T-002"])
        rc, out, _ = self.stage("design-check", "--json")
        self.assertEqual((rc, json.loads(out)["client"]), (1, True))
        self.assertEqual(self.stage("approve", "--design", "--sha", sha, "--note", "ok")[0], 0)
        self.assertEqual(self.record("T-001")[0], 0)  # đã duyệt, hash khớp: mở như thường dù không còn PROJECT.md
        (self.repo / d.LEDGER).unlink()  # chỉ người xoá sổ mới tắt khoá
        self.assertEqual(d.lock_reason(xt, self.repo), "")

    def test_verdict_skips_held_ui_task(self):
        """Lỗ C: verdict không dẫn agent vào task giao diện đang bị giữ (rồi `loop record` exit 2); chỉ còn chúng →
        `done-pending-human` kèm lý do khoá."""
        self.write("PROJECT.md", "Duyệt thiết kế: khách\n")
        v = xt.loop_verdict(self.repo)
        self.assertEqual((v["verdict"], v.get("task")), ("continue", "T-002"))
        self.assertEqual(run_main("loop", "record", "--task", "T-002", "--", "true")[0], 0)
        v = xt.loop_verdict(self.repo)
        self.assertEqual(v["verdict"], xt.PENDING_HUMAN)
        self.assertEqual([p["id"] for p in v["pending_human"]], ["T-001"])
        self.assertIn("stage design-submit", v["pending_human"][0]["reason"])
        self.write("PROJECT.md", "Duyệt thiết kế: không\n")
        self.assertEqual(xt.loop_verdict(self.repo).get("task"), "T-001")  # không khai khách: như cũ
        self.assertNotIn("deferred", xt.read_state(self.repo) or {})  # chỉ trong bộ nhớ, không ghi state

    def test_minimal_install_without_module(self):
        """Bộ cài tối giản (không có xt_design.py): không có lệnh con, vòng như cũ."""
        self.write("PROJECT.md", "Duyệt thiết kế: khách\n")
        with unittest.mock.patch.object(xt, "SCRIPT_DIR", self.tmp):
            self.assertIsNone(xt.design_module())
            self.assertEqual(self.next_ids(), (["T-001", "T-002"], {}))
            self.assertEqual(self.record("T-001")[0], 0)
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                xt.build_parser().parse_args(["stage", "design-check"])
        self.assertIs(xt.design_module(), d)


class DesignGuardTest(TmpRepoCase):
    """Guard: sổ DESIGN.json chỉ `xt.py stage` ghi; `stage approve --design` luôn chặn, kể cả khi khoá ADR-0069 có hiệu
    lực (xt.yaml ở cây VÀ bản commit ở nhánh chính khai `stage_approval: agent`)."""

    project = saa.StageAgentApprovalGuardTest.project
    decide = saa.StageAgentApprovalGuardTest.decide

    def setUp(self):
        super().setUp()
        guard._STAGE_AGENT.clear()
        self.addCleanup(guard._STAGE_AGENT.clear)
        self.enterContext(unittest.mock.patch.dict(os.environ, {"XT_GUARD_POLICY": "", "XT_GUARD_PHASE": ""}))

    def edit(self, proj, tool, **extra):
        payload = {"tool_name": tool, "tool_input": {"file_path": str(proj / d.LEDGER), **extra}}
        return dict(guard.apply_policy(guard._rule_decision("edit", payload, str(proj)))).get("decision")

    def test_ledger_is_machine_only(self):
        proj = self.project("agent")
        self.assertEqual(guard.classify_path(d.LEDGER), "evidence")
        self.assertEqual(guard.classify_path("docs/autopilot/DESIG?.json"), "evidence")
        self.assertEqual(self.edit(proj, "Write", content="{}"), "deny")
        self.assertEqual(self.edit(proj, "Edit", old_string="none", new_string="approved"), "deny")
        for cmd in (
            "echo '{}' > docs/autopilot/DESIGN.json",
            "sed -i 's/none/approved/' docs/autopilot/DESIGN.json",
            "cp /tmp/x.json docs/autopilot/DESIGN.json",
        ):
            with self.subTest(cmd=cmd):
                self.assertEqual(self.decide(proj, cmd), "deny")

    def test_design_approve_denied_even_with_agent_key(self):
        proj = self.project("agent")
        self.assertTrue(guard.agent_stage_approval(str(proj)))
        self.assertNotEqual(self.decide(proj, saa.StageAgentApprovalGuardTest.PLAIN), "deny")  # đối chứng ADR-0069
        for cmd in (
            "python3 scripts/xt.py stage approve --design --sha abcdef1 --note ok",
            "python3 scripts/xt.py stage approve --sha abcdef1 --design --note ok",
            "python3 .xtemplates/scripts/xt.py stage approve --design --sha abcdef1 --note ok",
        ):
            with self.subTest(cmd=cmd):
                self.assertEqual(self.decide(proj, cmd), "deny")
        self.assertEqual(
            dict(guard.apply_policy(guard.bash_decision(cmd, str(proj), str(proj))))
            .get("reason", "")
            .count("duyệt giai đoạn sản phẩm"),
            1,
        )
        reason = str(dict(guard.apply_policy(guard.bash_decision(cmd, str(proj), str(proj)))).get("reason", ""))
        self.assertIn("trừ `--design`", reason)  # lỗ D: lý do không hứa `--design` chạy được khi khoá agent bật
        for cmd in (
            "python3 scripts/xt.py stage design-submit --evidence docs/m.png",
            "python3 scripts/xt.py stage design-check",
            "python3 scripts/xt.py stage design-check --json",
            "python3 scripts/xt.py stage design-reopen --reason 'khách đổi ý'",
        ):
            with self.subTest(cmd=cmd):
                self.assertNotEqual(self.decide(proj, cmd), "deny")


if __name__ == "__main__":
    unittest.main()
