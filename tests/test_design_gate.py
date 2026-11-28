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
from argparse import Namespace
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


# Review vòng 2 PR #845: ký tự mà `str.splitlines()` coi là ngắt dòng còn markdown thì không (U+2028/2029, VT, FF, NEL)
# từng giấu dòng khai thứ hai trong cùng dòng markdown — bản trước (tách bằng `splitlines()`) khoá, bản tách markdown mở.
SPLIT_DECLARATIONS = (
    "# Site - Duyệt thiết kế: khách\n",
    "Stack: Node\x0b- Duyệt thiết kế: khách\n",
    "Stack: Node\x0c- Duyệt thiết kế: khách\n",
    "Stack: Node\x85- Duyệt thiết kế: khách\n",
    "Stack: Node - Duyệt thiết kế: khách\n",
    "- Duyệt thiết kế: không - Duyệt thiết kế: có\n",
    "- Duyệt thiết kế: không\x0b- Duyệt thiết kế:\n",
)


def led(history, status, submitted=None):
    return {"schema": 1, "status": status, "submitted": submitted, "history": history}


def awaiting(history, sha=SHA, evidence="docs/m.png", digest=PNG):
    return led(history, "awaiting_approval", {"sha": sha, "evidence": evidence, "evidence_sha256": digest})


class DesignLedgerProblemTest(unittest.TestCase):
    def test_resubmission_preserves_first_evidence_path(self):
        state = d.submit(xt, d.empty(), SHA, "docs/sample.png", PNG)
        state = d.reopen(xt, state, "new draft")
        with self.assertRaisesRegex(d.DesignError, "docs/sample.png"):
            d.submit(xt, state, SHA2, "docs/other.png", PNG)
        self.assertEqual(state["status"], "none")
        self.assertEqual(d.submit(xt, state, SHA2, "docs/sample.png", PNG)["submitted"]["sha"], SHA2)

    def test_submit_checks_head_again_after_hashing(self):
        args = Namespace(stage_cmd="design-submit", evidence="docs/sample.png")
        with (
            unittest.mock.patch.object(xt, "_stage_clean_head", side_effect=[SHA, SHA2]),
            unittest.mock.patch.object(d, "evidence_path", return_value="docs/sample.png"),
            unittest.mock.patch.object(d, "file_sha256", return_value=PNG),
        ):
            with self.assertRaises(d.DesignError):
                d._transition(xt, args, Path("."))

    def test_declaration_treats_unreadable_entry_as_review_required(self):
        with unittest.mock.patch.object(Path, "lstat", side_effect=PermissionError("fixture")):
            client, note = d._declared_line(Path("."))
        self.assertTrue(client)
        self.assertIn("PROJECT.md", note)
        with (
            unittest.mock.patch.object(d, "_declared_line", return_value=(False, "")),
            unittest.mock.patch.object(Path, "lstat", side_effect=PermissionError("fixture")),
        ):
            client, note = d.declared(xt, Path("."))
        self.assertTrue(client)
        self.assertIn(d.LEDGER, note)

    def test_design_hold_keeps_transitive_dependencies_and_unrelated_work(self):
        tasks = [
            {"id": "T-003", "state": " ", "after": ["T-001", "T-002"], "rest": ""},
            {"id": "T-001", "state": " ", "after": [], "rest": "(ui: yes)"},
            {"id": "T-002", "state": " ", "after": ["T-001"], "rest": ""},
            {"id": "T-004", "state": " ", "after": [], "rest": ""},
            {"id": "T-005", "state": " ", "after": ["T-003"], "rest": ""},
        ]
        manual = {"reason": "fixture", "at": AT}
        state = {"plan": "PLAN.md", "deferred": {"T-002": manual}}
        with (
            unittest.mock.patch.object(xt, "_plan_tasks", return_value=tasks),
            unittest.mock.patch.object(d, "lock_reason", return_value="review pending"),
        ):
            held = d.defer_held(xt, Path("."), state)
        self.assertEqual(set(held["deferred"]), {"T-001", "T-002", "T-003", "T-005"})
        self.assertEqual(held["deferred"]["T-002"], manual)
        self.assertEqual(state["deferred"], {"T-002": manual})

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
            "```\nDuyệt thiết kế: không\n```\n",  # rào giấu dòng `không` (dòng khác trong rào: `test_fences_…`)
            "~~~\n```\nDuyệt thiết kế: không\n~~~\n",  # fence khác loại bên trong không đóng fence ngoài
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
            # Review PR #845: `~` sau `:` không còn là dấu nhấn bỏ qua — giá trị gạch bỏ là rỗng (khách).
            ("- Duyệt thiết kế: ~~không~~ khách\n", "``"),
            ("- Duyệt thiết kế: ~~không~~ _khách_\n", "``"),
            ("- Duyệt thiết kế: ~~không~~ có\n", "``"),
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

    def test_unseparated_label_means_client_with_note(self):
        """Nợ review PR #844: dòng mở đầu bằng nhãn mà không tách giá trị bằng `:`/`|` → `khách` kèm ghi chú (chặt)."""
        for text in (
            "- Duyệt thiết kế - khách\n",
            "- Duyệt thiết kế — khách\n",
            "- Duyệt thiết kế = khách\n",
            "- Duyệt thiết kế khách\n",
            "- Duyệt thiết kế (`UX-DS-023`): khách\n",
            "- Duyệt thiết kế của khách: có\n",
            "- [Duyệt thiết kế](x.md): khách\n",
            "## Duyệt thiết kế\nkhách\n",
            "- Duyệt thiết kế (UX-DS-023): không\n",  # nhãn lệch thì không đọc giá trị, kể cả `không`
        ):
            with self.subTest(text=text):
                client, note = self.declare(text)
                self.assertTrue(client)
                self.assertIn("không tách nhãn và giá trị bằng `:` hay `|`", note)
        client, note = self.declare("## Duyệt thiết kế\n- Duyệt thiết kế: không\n")
        self.assertEqual((client, "mâu thuẫn" in note, "không tách" in note), (True, True, True))

    def test_no_with_client_word_means_client(self):
        """Nợ review PR #844: giá trị mở đầu `không` mà có chữ `khách` (không phân biệt hoa thường/dấu) → `khách`."""
        for value in (
            "không → khách",
            "không|khách",
            "không | khách",
            "không, khách",
            "không/khách",
            "không khách",
            "không hoặc khách",
            "không — nhưng khách duyệt trang chủ",
            "không — KHACH duyệt sau",
        ):
            with self.subTest(value=value):
                client, note = self.declare(f"- Duyệt thiết kế: {value}\n")
                self.assertTrue(client)
                self.assertIn("có chữ `khách`", note)

    def test_client_word_bounded_by_underscore(self):
        """Review PR #845: `_` là dấu nhấn, không phải chữ — `_khách_`, `không_khách` vẫn có chữ `khách`."""
        for value in (
            "không _khách_",
            "không __khách__",
            "không (_khách_)",
            "không, _khách hàng_ duyệt",
            "không_khách",
            "không *khách*",
        ):
            with self.subTest(value=value):
                client, note = self.declare(f"- Duyệt thiết kế: {value}\n")
                self.assertTrue(client)
                self.assertIn("có chữ `khách`", note)
        for value in ("không — dự án nội bộ", "không (_nội bộ_)", "không — kháchsạn"):  # `khách` phải là chữ riêng
            with self.subTest(value=value):
                self.assertEqual(self.declare(f"- Duyệt thiết kế: {value}\n"), (False, ""))

    def test_unicode_line_break_cannot_hide_declaration(self):
        """Review vòng 2 PR #845: dòng khai lấy theo CẢ tách markdown lẫn mỗi đoạn `str.splitlines()`, gộp hợp — đoạn
        sau U+2028/2029, VT, FF, NEL là dòng khai thì vẫn tính (thêm dòng khai không bao giờ mở khoá)."""
        for text in SPLIT_DECLARATIONS:
            with self.subTest(text=text):
                self.assertTrue(self.declare(text)[0])
        for sep in (" ", " ", "\x85", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e"):
            with self.subTest(sep=repr(sep)):
                self.assertEqual(self.declare(f"- Duyệt thiết kế:{sep}không\n")[0], True)  # đoạn đầu: giá trị rỗng
                self.assertEqual(self.declare(f"- Duyệt thiết kế: không{sep}- Duyệt thiết kế: không\n"), (False, ""))
                self.assertEqual(self.declare(f"Stack{sep}- Duyệt thiết kế: không\n"), (False, ""))
        client, note = self.declare("```\nx - Duyệt thiết kế: khách\n```\n")
        self.assertEqual((client, "trong code fence vẫn tính" in note), (True, True))
        self.assertEqual(self.declare("```\nx - Duyệt thiết kế: không\n```\n"), (False, ""))  # rào giấu `không`

    def test_lines_split_at_newlines(self):
        """Review PR #845: dòng markdown tách ở `\\r\\n`/`\\r`/`\\n` — `không<U+2028>khách` cũng là một dòng có chữ
        `khách`; rào nhận trên dòng gốc (ký tự vô hình trước ``` → không là rào)."""
        for sep in (" ", " ", "\x85", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e"):
            with self.subTest(sep=repr(sep)):
                client, note = self.declare(f"- Duyệt thiết kế: không{sep}khách\n")
                self.assertTrue(client)
                self.assertIn("có chữ `khách`", note)
        for text in ("a\r\nb\r- Duyệt thiết kế: khách\rc\n", "a\r- Duyệt thiết kế: không\r\n"):
            with self.subTest(text=text):
                self.assertEqual(self.declare(text)[0], "khách\r" in text)
        line = "- Duyệt thiết kế: khách\n"
        for text in ("​```\n" + line + "​```\n", "x ```\n" + line + "x ```\n"):
            with self.subTest(text=text):
                self.assertEqual(self.declare(text), (True, ""))  # không phải rào → dòng thường, không ghi chú

    def test_pathological_prefix_is_linear(self):
        """Review PR #845 (CodeQL py/redos): `[[]` lặp trước chữ thường từng làm `LABEL_RE` quay lui mũ (82 ký tự đã
        treo > 100 s). Ví dụ lớn tự bắt hồi quy: bản lỗi treo thay vì trả kết quả."""
        n = 5000
        text = "[[]" * n + "x\n" + "- Duyệt thiết kế: khách\n" + "[[]" * n + " Duyệt thiết kế: khách\n"
        self.assertEqual(self.declare(text), (True, ""))
        self.assertEqual(self.declare("1" * n + "x\n" + "[ ]" * n + "- " * n + "\n"), (False, ""))

    def test_fences_follow_commonmark(self):
        """Nợ review PR #844: rào đóng cùng ký tự, dài ≥ rào mở, không info string; thụt ≥ 4 cách không phải rào.
        Review PR #845 (fail-closed): rào chỉ GIẤU dòng giá trị `không` (ví dụ như mẫu); dòng trong rào có giá trị khác
        vẫn tính, kèm ghi chú — rào quên đóng, rào trong comment HTML hay `<pre>` không còn giấu được dòng khai thật."""
        line = "- Duyệt thiết kế: khách\n"
        for text in (
            "````md\n```\n````\n" + line,
            "```\n```python\n```\n" + line,
            "```x``` là cú pháp rào\n" + line,
            "    ```\n" + line + "    ```\n",
            "\t```\n" + line + "\t```\n",
            "```\n- Duyệt thiết kế: không\n```\n" + line,  # ví dụ `không` trong rào không gây mâu thuẫn
            "<!-- Duyệt thiết kế: khách -->\n",
            "<!--\n" + line + "-->\n",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.declare(text), (True, ""))
        fenced = (
            "```\n" + line,
            "```\n- Duyệt thiết kế: không\n```\n~~~\n" + line,
            "````\n```\n" + line + "```\n````\n",
            "~~~~\n~~~\n" + line + "~~~~\n",
            "   ```\n" + line + "``` \t\n",
            "```\n" + line + "```\n",
            "~~~\n```\n" + line + "~~~\n",
            "﻿```\n" + line + "```\n",
            "```Duyệt thiết kế: khách\n```\n",  # info string của rào mở cũng trong rào
            # (a) rào mở trong mục danh sách quên đóng, cuối tệp có code block bình thường
            "- Build:\n  ```bash\n  npm run build\n" + line + "\n## Lệnh\n```bash\nnpm test\n```\n",
            # (b) comment HTML cắt đôi một rào, rồi dòng khai, rồi code block
            "<!-- ví dụ cũ:\n```bash\nnpm run old\n-->\n" + line + "\n## Lệnh\n```bash\nnpm test\n```\n",
            # (c) `<pre>` chứa ``` — CommonMark hiển thị dòng khai phía sau
            "<pre>\n```\n</pre>\n" + line + "\n```\nx\n```\n",
        )
        for text in fenced:
            with self.subTest(text=text):
                client, note = self.declare(text)
                self.assertTrue(client)
                self.assertIn("trong code fence vẫn tính", note)
        for text in (
            "```js\n" + line.replace("khách", "không") + "   ```\n- Duyệt thiết kế: không\n",
            "```\n- Duyệt thiết kế: không\n",  # rào quên đóng chỉ giấu `không`
            "~~~\n- **Duyệt thiết kế:** Không.\n~~~\n",
            "<!-- Duyệt thiết kế: không -->\n",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.declare(text), (False, ""))

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

    def test_existing_ledger_makes_declaration_sticky(self):
        """ADR-0108 (D-622): sổ DESIGN.json đã có (kể cả hỏng, rỗng, symlink gãy) → khách bất kể dòng khai."""
        ledger = self.repo / d.LEDGER
        ledger.parent.mkdir(parents=True)
        # `d.empty()`: sổ hợp lệ chưa có `history` — chặt hơn bản đầu của ADR-0107 (chỉ tính sổ có `history`)
        for body in (json.dumps(awaiting([submit()])), json.dumps(d.empty()), "", "{"):
            ledger.write_text(body, encoding="utf-8")
            for text in ("Duyệt thiết kế: không\n", "# Dự án\n", None):
                with self.subTest(body=body, text=text):
                    (self.repo / "PROJECT.md").unlink(missing_ok=True)
                    client, note = self.declare(text) if text else d.declared(xt, self.repo)
                    self.assertEqual((client, note), (True, d.STICKY))
        self.assertEqual(self.declare("Duyệt thiết kế: khách hàng\n"), (True, ""))  # khai khách: không cần ghi chú
        self.assertIn("giá trị lạ", self.declare("Duyệt thiết kế: có\n")[1])  # ghi chú của dòng khai được giữ
        ledger.unlink()
        ledger.symlink_to(self.repo / "khong-co.json")
        self.assertEqual(self.declare("Duyệt thiết kế: không\n"), (True, d.STICKY))
        ledger.unlink()
        self.assertEqual(self.declare("Duyệt thiết kế: không\n"), (False, ""))  # chưa có sổ: như cũ


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
            "- [ ] `T-001` Trang chủ (ui: no review yet) — Gate: `true`",
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

    def test_unicode_line_break_declaration_locks_loop(self):
        """Review vòng 2 PR #845 qua CLI: dòng khai sau ngắt dòng Unicode vẫn khoá `design-check`, `loop next`, `record`."""
        for text in SPLIT_DECLARATIONS:
            with self.subTest(text=text):
                self.write("PROJECT.md", text)
                self.assertEqual(self.stage("design-check")[0], 1)
                ready, held = self.next_ids()
                self.assertEqual((ready, list(held)), (["T-002"], ["T-001"]))
                self.assertEqual(self.record("T-001")[0], 2)
        self.assertFalse((self.repo / ".autopilot" / "evidence" / "T-001.json").exists())

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

    def test_plain_waves_hold_ui_tasks(self):
        """Nợ review PR #844: `plan waves` không `--handoff` cũng giữ task `ui: yes` (lan sang `sau:`) như `--handoff`."""
        self.write(
            self.PLAN,
            "# PLAN\n\n- [ ] `T-001` Trang chủ (ui: yes; files: a.html) — Gate: `true`\n"
            "- [ ] `T-002` API (files: b.py) — Gate: `true`\n"
            "- [ ] `T-003` Trang con (sau: T-001; files: c.html) — Gate: `true`\n"
            "- [x] `T-004` Đã xong (ui: yes) — Gate: `true`\n",
        )

        def waves():
            rc, out, err = run_main("plan", "waves", "--json")
            self.assertEqual(rc, 0, err)
            info = json.loads(out)
            return [t["id"] for w in info["waves"] for t in w["tasks"]], {b["id"]: b["reason"] for b in info["blocked"]}

        self.assertEqual(waves(), (["T-001", "T-002", "T-003"], {}))  # không khai khách: như cũ
        self.write("PROJECT.md", "- Duyệt thiết kế: khách\n")
        tasks, blocked = waves()
        self.assertEqual((tasks, list(blocked)), (["T-002"], ["T-001", "T-003"]))
        self.assertIn("stage design-submit", blocked["T-001"])
        self.assertIn("chờ T-001 bị chặn", blocked["T-003"])
        rc, out, _ = run_main("plan", "waves")
        self.assertEqual(rc, 0)
        self.assertIn("⛔ T-001 — task giao diện", out)
        self.assertEqual(run_main("loop", "defer", "--task", "T-002", "--reason", "chờ API")[0], 0)
        self.assertEqual(waves()[1]["T-002"], "đã defer: chờ API")  # defer giữ lý do của nó
        with unittest.mock.patch.object(xt, "SCRIPT_DIR", self.tmp):  # bộ cài tối giản: như cũ
            self.assertEqual(waves()[0], ["T-001", "T-003"])

    def test_hint_without_loop_suggests_init(self):
        """Nợ review PR #844: chưa `loop init` thì `loop defer` cũng rc 2 — câu báo khoá gợi ý `loop init --plan`."""
        self.write("PROJECT.md", "- Duyệt thiết kế: khách\n")
        self.assertIn("loop defer --task <ID>", d.lock_reason(xt, self.repo))
        (self.repo / ".autopilot" / "state.json").unlink()
        for reason in (d.lock_reason(xt, self.repo), self.stage("design-check")[1]):
            with self.subTest(reason=reason):
                self.assertIn("`xt.py loop init --plan <PLAN>`", reason)
                self.assertNotIn("loop defer", reason)
        rc, out, err = run_main("plan", "waves", "--json", "--plan", self.PLAN)
        self.assertEqual(rc, 0, err)
        self.assertIn("loop init --plan <PLAN>", json.loads(out)["blocked"][0]["reason"])

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
        """ADR-0107 (lỗ B) qua cơ chế chung của ADR-0108: sổ đã có → đổi `PROJECT.md` sang `không` hay xoá nó không tắt
        khoá; lý do khoá là ghi chú `STICKY` của `declared` (không còn ghi chú riêng "đã có lịch sử trình")."""
        sha = self.submit_v1()
        for text in ("- Duyệt thiết kế: không\n", None):
            with self.subTest(project=text):
                if text is None:
                    (self.repo / "PROJECT.md").unlink()
                else:
                    self.write("PROJECT.md", text)
                rc, _, err = self.record("T-001")
                self.assertEqual(rc, 2)
                self.assertIn(d.STICKY, err)
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

    def test_declaration_cannot_loosen_after_submit(self):
        """Review vòng 2 PR #844 (ADR-0108, D-622): đã trình bản thiết kế thì sửa/xoá dòng khai không mở khoá."""
        self.write("PROJECT.md", "Duyệt thiết kế: không\n")
        self.assertEqual(self.next_ids(), (["T-001", "T-002"], {}))  # chưa có sổ + `không`: như cũ
        self.write("PROJECT.md", "Duyệt thiết kế: khách\n")
        self.write("docs/m.png", "png")
        sha = self.commit()
        self.assertEqual(self.stage("design-submit", "--evidence", "docs/m.png", agent=True)[0], 0)
        self.write("PROJECT.md", "Duyệt thiết kế: không\n")  # chưa commit
        for loosen in ("không", "xoá"):
            with self.subTest(loosen=loosen):
                ready, held = self.next_ids()
                self.assertEqual(ready, ["T-002"])
                self.assertIn(d.STICKY, held["T-001"])
                rc, out, _ = self.stage("design-check")
                self.assertEqual(rc, 1)
                self.assertIn("Duyệt thiết kế: khách", out)
                self.assertIn(d.STICKY, out)
                self.assertEqual(self.record("T-001")[0], 2)
                (self.repo / "PROJECT.md").unlink(missing_ok=True)
        good = (self.repo / d.LEDGER).read_text(encoding="utf-8")
        self.write("PROJECT.md", "Duyệt thiết kế: không\n")
        self.write(d.LEDGER, "{")
        self.assertEqual(self.stage("design-check")[0], 2)
        ready, held = self.next_ids()
        self.assertEqual(ready, ["T-002"])
        self.assertIn(d.STICKY, held["T-001"])
        self.write(d.LEDGER, good)
        self.assertEqual(self.stage("approve", "--design", "--sha", sha, "--note", "ok")[0], 0)
        self.assertEqual(self.next_ids(), (["T-001", "T-002"], {}))  # đã duyệt + `không`: mở như cũ
        self.assertEqual(self.stage("design-check")[0], 0)
        self.assertEqual(self.record("T-001")[0], 0)
        self.write(d.LEDGER, "{")
        with unittest.mock.patch.object(xt, "SCRIPT_DIR", self.tmp):  # bộ cài tối giản: không có module, như cũ
            self.assertEqual(self.next_ids(), (["T-001", "T-002"], {}))

    def test_in_process_forge_is_real_and_guard_denies(self):
        """Review PR #849: script nạp `xt_design` không chữ rủi ro ngoài tên mô-đun ghi được lời duyệt trong phiên
        agent (chạy thật dưới đây) — guard phải chặn chính script này (ADR-0108)."""
        self.write("PROJECT.md", "Duyệt thiết kế: khách\n")
        self.write("docs/m.png", "png")
        self.commit()
        self.assertEqual(self.stage("design-submit", "--evidence", "docs/m.png", agent=True)[0], 0)
        script = saa.XtInProcessGuardTest.DESIGN_FORGE
        out = dict(guard.apply_policy(guard.bash_decision(f"python3 - <<'PY'\n{script}PY", str(ROOT), str(ROOT))))
        self.assertEqual((out.get("decision"), out.get("code")), ("deny", "STAGE_APPROVE"))
        env = {**os.environ, "PYTHONPATH": str(ROOT / "scripts"), "CLAUDE_CODE_SESSION_ID": "s-1"}
        run = subprocess.run(
            [sys.executable, "-"], input=script, text=True, capture_output=True, cwd=self.repo, env=env
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(self.ledger()["status"], "approved")  # lớp chặn là guard, không phải xt_design

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
