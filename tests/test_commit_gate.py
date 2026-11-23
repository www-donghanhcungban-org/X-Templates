"""Test cổng commit nhanh: khoá `commit_gate: fast|full`, `xt.py test-select` (test liên quan file đổi) và
`dev-task.sh gate-fast`. Hook chọn cổng theo khoá: tests/test_hooks.py (`CommitGateFastHookTest`)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import xt
from test_merge import run_main


class CommitGateKeyTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(unittest.mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.base)}))

    def test_commit_gate_fast_error_values(self):
        for ok in ({}, {"commit_gate": ""}, {"commit_gate": "fast"}, {"commit_gate": "full"}):
            self.assertIsNone(xt.commit_gate_error(ok))
        err = xt.commit_gate_error({"commit_gate": "Fast"}) or ""
        self.assertIn("commit_gate 'Fast' không hợp lệ (fast|full — vắng = full)", err)

    def test_commit_gate_fast_rejected_by_doctor_and_ci_check(self):
        (self.base / "xt.yaml").write_text("lint: x\ntypecheck: x\ntest: x\nbuild: x\ncommit_gate: 'nhanh' # x\n")
        found = [f for f in xt._doctor_xt_yaml(self.base, self.base) if f.code == "xt-yaml" and f.level == "error"]
        self.assertEqual(len(found), 1)
        self.assertIn("commit_gate 'nhanh' không hợp lệ", found[0].msg)
        self.assertTrue(found[0].msg.endswith("sửa thành fast hoặc full"))
        rc, out, _ = run_main("ci-check")
        self.assertEqual(rc, 1)
        self.assertIn("✗ xt.yaml: commit_gate 'nhanh' không hợp lệ", out)
        for value in ("fast", '"full"', ""):
            (self.base / "xt.yaml").write_text(f"lint: x\ntypecheck: x\ntest: x\nbuild: x\ncommit_gate: {value}\n")
            self.assertFalse([f for f in xt._doctor_xt_yaml(self.base, self.base) if f.level == "error"], value)
            self.assertEqual(run_main("ci-check")[0], 0, value)

    def test_max_rethink_bad_value_warned_by_doctor(self):
        """AUD-HAR-175: `max_rethink` hỏng âm thầm về trần mặc định (`rethink_cap`) — `doctor` cảnh báo (warn, không
        error: trần vẫn chặt), giá trị hợp lệ (vắng, rỗng, số nguyên ≥ 0) không cảnh báo."""
        for ok in ({}, {"max_rethink": ""}, {"max_rethink": "0"}, {"max_rethink": "1"}, {"max_rethink": "007"}):
            self.assertIsNone(xt.max_rethink_error(ok), ok)
        for bad in ("abc", "-1", "+1", "1.0", " 2"):
            err = xt.max_rethink_error({"max_rethink": bad}) or ""
            self.assertIn(f"max_rethink '{bad}' không hợp lệ (số nguyên ≥ 0 — ADR-0061)", err)
        # cùng một luật đọc với `rethink_cap`: giá trị nó nhận (kể cả chữ số Unicode `int()` đọc được) không bị cảnh báo
        for v, cap in (("3", 3), ("１２", 12)):
            self.assertEqual(
                (xt.max_rethink_error({"max_rethink": v}), xt.rethink_cap({"max_rethink": v})), (None, cap)
            )
        head = "lint: x\ntypecheck: x\ntest: x\nbuild: x\n"
        (self.base / "xt.yaml").write_text(head + "max_rethink: 'abc'  # x\n")
        found = [f for f in xt._doctor_xt_yaml(self.base, self.base) if "max_rethink" in f.msg]
        self.assertEqual([(f.code, f.level) for f in found], [("xt-yaml", "warn")])
        self.assertTrue(found[0].msg.endswith(f"đang dùng trần mặc định {xt.MAX_RETHINK_DEFAULT}"))
        for value in ("2", '"0"', ""):
            (self.base / "xt.yaml").write_text(head + f"max_rethink: {value}\n")
            self.assertFalse([f for f in xt._doctor_xt_yaml(self.base, self.base) if "max_rethink" in f.msg], value)

    def test_commit_gate_cli_reads_like_doctor(self):
        """AUD-XFEAT-017: `xt.py commit-gate` (hook gọi) đọc khoá như `doctor`: dòng cuối thắng, `#` dính liền thuộc giá
        trị; chỉ đúng `fast` mới là fast, còn lại (vắng, full, lạ) → full."""
        cases = {
            "": "full",
            "commit_gate: fast\n": "fast",
            "commit_gate: 'fast'  # x\n": "fast",
            "commit_gate: full\ncommit_gate: fast\n": "fast",
            "commit_gate: fast\ncommit_gate: full\n": "full",
            "commit_gate: fast#x\n": "full",
            "commit_gate: Fast\n": "full",
        }
        for text, want in cases.items():
            with self.subTest(text=text):
                (self.base / "xt.yaml").write_text(text, encoding="utf-8")
                self.assertEqual(run_main("commit-gate"), (0, want + "\n", ""))
        (self.base / "xt.yaml").unlink()
        self.assertEqual(run_main("commit-gate")[1], "full\n")


class TestSelectTest(unittest.TestCase):
    """Ánh xạ file đổi → file test: chính file test, `test_<tên>.py`, test nhắc tên file, test quét theo đuôi; còn lại
    cả suite (None)."""

    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(unittest.mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.base)}))
        t = self.base / "tests"
        t.mkdir()
        (t / "test_alpha.py").write_text('SCRIPT = ROOT / "scripts" / "alpha.sh"\n', encoding="utf-8")
        (t / "test_beta.py").write_text('for p in ROOT.rglob("*.md"):\n    pass\n', encoding="utf-8")
        (t / "test_gamma.py").write_text("x = 1\n", encoding="utf-8")
        (t / "test_dev_task.py").write_text("x = 2\n", encoding="utf-8")
        (t / "helper.py").write_text('"gamma.py"\n', encoding="utf-8")  # không phải module test: không đọc

    def sel(self, *files: str) -> list[str] | None:
        return xt.test_select(self.base, "tests", files)

    def test_commit_gate_fast_select_mapping(self):
        cases = [
            (("tests/test_gamma.py",), ["tests/test_gamma.py"]),  # file test đổi → chính nó
            (("tests/test_da_xoa.py",), []),  # file test bị xoá → không còn gì để chạy
            (("src/gamma.py",), ["tests/test_gamma.py"]),  # test_<tên>.py
            (("scripts/_dev-task.sh",), ["tests/test_dev_task.py"]),  # `-` → `_`, bỏ `_` đầu
            (("scripts/alpha.sh",), ["tests/test_alpha.py"]),  # test nhắc tên file
            (("docs/moi.md",), ["tests/test_beta.py"]),  # test quét `*.md`
            (("scripts/alpha.sh", "./src/gamma.py"), ["tests/test_alpha.py", "tests/test_gamma.py"]),
            ((), []),
        ]
        for files, want in cases:
            with self.subTest(files=files):
                self.assertEqual(self.sel(*files), want)

    def test_commit_gate_fast_select_unmapped_runs_whole_suite(self):
        self.assertIsNone(self.sel("Makefile"))  # không đuôi, không ai nhắc
        self.assertIsNone(self.sel("scripts/alpha.sh", "src/delta.py"))  # một file không ánh xạ → cả suite
        self.assertIsNone(self.sel("scripts/ta.sh"))  # `ta.sh` nằm trong `alpha.sh` nhưng không phải tên đó
        self.assertIsNone(self.sel("tests/fixtures/khung.json"))  # file phụ trong thư mục test, không ai nhắc

    def test_commit_gate_fast_select_by_import(self):
        t = self.base / "tests"
        imports = {
            "test_i1.py": "import sys\nimport delta\n",
            "test_i2.py": "def f():\n    import os, delta as d  # lồng trong hàm\n",
            "test_i3.py": "from delta import x\n",
            "test_i4.py": "from delta.sub import y\nimport delta.sub\n",
            "test_i5.py": "from scripts import delta\n",
            "test_i6.py": "from test_gamma import helper\n",
        }
        for name, text in imports.items():
            (t / name).write_text(text, encoding="utf-8")
        for name, text in {"test_n1.py": "import deltax\n# import delta\n", "test_n2.py": "x = 'delta'\n"}.items():
            (t / name).write_text(text, encoding="utf-8")  # không phải import `delta`
        want = [f"tests/test_i{i}.py" for i in range(1, 6)]
        self.assertEqual(self.sel("scripts/delta.py"), want)
        self.assertEqual(self.sel(".claude/hooks/delta.py"), want)
        self.assertEqual(self.sel("tests/test_gamma.py"), ["tests/test_gamma.py", "tests/test_i6.py"])
        self.assertEqual(self.sel("tests/test_xoa.py"), [])  # test bị xoá, không ai import
        self.assertIsNone(self.sel("scripts/delta-x.py"))  # tên không phải định danh Python: không ánh xạ import
        self.assertIsNone(self.sel("scripts/delta.pyi"))

    def test_commit_gate_fast_select_covers_every_importer_in_repo(self):
        # Đối chiếu độc lập bằng ast (không dùng regex của test-select): mọi test import module của scripts/ hoặc
        # .claude/hooks/ phải được chọn khi module đó đổi — review #177 (test_delivery_phase `import xt` từng bị sót).
        import ast

        importers: dict[str, set[str]] = {}
        for test in sorted((ROOT / "tests").glob("test_*.py")):
            for node in ast.walk(ast.parse(test.read_text(encoding="utf-8"))):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else []
                names += [node.module or ""] if isinstance(node, ast.ImportFrom) else []
                for n in names:
                    importers.setdefault(n.split(".")[0], set()).add(f"tests/{test.name}")
        modules = sorted([*(ROOT / "scripts").glob("*.py"), *(ROOT / ".claude" / "hooks").glob("*.py")])
        checked = 0
        for mod in modules:
            want = importers.get(mod.stem, set())
            if want:
                checked += 1
                picked = xt.test_select(ROOT, "tests", [mod.relative_to(ROOT).as_posix()])
                got = want if picked is None else set(picked)  # None = cả suite: đủ
                self.assertEqual(want - got, set(), f"{mod.name}: test-select bỏ sót test import nó")
        self.assertGreaterEqual(checked, 3)  # xt, install, guard

    def test_commit_gate_fast_cli_paths(self):
        rc, out, err = run_main("test-select", "scripts/alpha.sh")
        self.assertEqual((rc, out), (0, "tests/test_alpha.py\n"))
        with unittest.mock.patch.dict(os.environ, {"XT_CHANGED_FILES": "src/gamma.py\n\n docs/a.md \n"}):
            rc, out, _ = run_main("test-select")
        self.assertEqual((rc, out.split()), (0, ["tests/test_beta.py", "tests/test_gamma.py"]))
        env = {k: v for k, v in os.environ.items() if k != "XT_CHANGED_FILES"}
        with unittest.mock.patch.dict(os.environ, env, clear=True):
            rc, out, err = run_main("test-select")  # không biết file đổi → cả suite
        self.assertEqual((rc, out), (0, "tests\n"))
        self.assertIn("cả suite (tests)", err)
        with unittest.mock.patch.dict(os.environ, {"XT_CHANGED_FILES": ""}):
            rc, out, err = run_main("test-select")
        self.assertEqual((rc, out), (0, ""))
        self.assertIn("không có test liên quan", err)


# Tệp test mẫu cho chọn theo LỚP (D-516): mỗi lớp nhắc một tệp/glob khác nhau.
CLASS_FIXTURE = """import unittest

ROOT = "x"


class Mix:
    def helper(self):
        return "alpha.sh"


class A(Mix, unittest.TestCase):
    pass


class B(unittest.TestCase):
    pass


class C(A):
    pass


class D(C):
    pass


@unittest.skipIf(False, "gamma.cfg")
class E(unittest.TestCase):
    pass


class G(unittest.TestCase):
    PAT = "GO-NO-GO*.md"


class H(unittest.TestCase):
    PAT = "docs/ops/GO-NO-GO*.md"


class K(unittest.TestCase):
    PAT = "**/*.md"


class M(unittest.TestCase):
    PAT = "*.mdx"


class B(unittest.TestCase):
    PAT = "kappa.ini"
"""


class TestSelectClassTest(unittest.TestCase):
    """Chọn theo lớp (D-516): lớp trúng khi thân lớp (kể cả decorator) khớp tệp đổi hoặc nhắc tên lớp cùng tệp đã
    trúng (bắc cầu); cả tệp khi phần ngoài lớp khớp, import module đổi, `test_<tên>.py`, chính tệp test đổi, hoặc không parse được.
    `test_select_plan` trả {tệp test: lớp top-level BỎ QUA}."""

    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(unittest.mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.base)}))
        self.t = self.base / "tests"
        self.t.mkdir()
        (self.t / "test_cls.py").write_text(CLASS_FIXTURE, encoding="utf-8")
        self.names = {"Mix", "A", "B", "C", "D", "E", "G", "H", "K", "M"}

    def plan(self, *files: str) -> dict[str, set[str]] | None:
        return xt.test_select_plan(self.base, "tests", files)

    def picked(self, *files: str) -> set[str]:
        plan = self.plan(*files) or {}
        return self.names - plan["tests/test_cls.py"]

    def test_commit_gate_fast_class_hit_and_parent_chain(self):
        self.assertEqual(self.picked("scripts/alpha.sh"), {"Mix", "A", "C", "D"})  # Mix → A → C → D
        self.assertEqual(self.picked("etc/gamma.cfg"), {"E"})  # nhắc trong decorator
        self.assertEqual(self.picked("etc/kappa.ini"), {"B"})  # lớp trùng tên top-level: gộp thân
        self.assertEqual(self.picked("scripts/alpha.sh", "etc/gamma.cfg"), {"Mix", "A", "C", "D", "E"})
        self.assertIsNone(self.plan("scripts/omega.sh"))  # không lớp/phần nào khớp → cả suite
        self.assertEqual(xt.test_select(self.base, "tests", ["etc/gamma.cfg"]), ["tests/test_cls.py"])  # chế độ tệp

    def test_commit_gate_fast_class_helper_by_name(self):
        """Lớp phụ trợ không phải lớp cha (kiểu `FakeGh`) trúng → lớp nhắc TÊN nó cùng file cũng chạy, bắc cầu (D-516)."""
        helper = (
            "import unittest\n\n\nclass FakeGh:\n    def run(self):\n        return 'lambda.json'\n\n\n"
            "class UsesFake(unittest.TestCase):\n    def test_x(self):\n        FakeGh().run()\n\n\n"
            "class UsesUser(unittest.TestCase):\n    helper = UsesFake\n\n\n"
            "class FakeGhost(unittest.TestCase):\n    def test_x(self):\n        FakeGhx = 1\n\n\n"
            "class Other(unittest.TestCase):\n    pass\n"
        )
        (self.t / "test_helper.py").write_text(helper, encoding="utf-8")
        plan = self.plan("etc/lambda.json") or {}
        self.assertEqual(plan, {"tests/test_helper.py": {"FakeGhost", "Other"}})  # `FakeGhost`/`FakeGhx` ≠ `FakeGh`

    def test_commit_gate_fast_class_used_from_module_level(self):
        """Review #678 R1: lớp phụ trợ trúng mà phần ngoài lớp nhắc tên nó (`make_runner()` trả `FakeRunner`) → cả tệp;
        trước đây chỉ lớp phụ trợ (không phải TestCase) được chọn → 0 id, cổng xanh giả."""
        r1 = (
            "import unittest\n\n\nclass FakeRunner:\n    def cmd(self):\n        return ['bash', 'scripts/rho.sh']\n\n\n"
            "def make_runner():\n    return FakeRunner()\n\n\n"
            "class RunnerTest(unittest.TestCase):\n    def test_runs(self):\n        make_runner()\n\n\n"
            "class Other(unittest.TestCase):\n    pass\n"
        )
        (self.t / "test_r1.py").write_text(r1, encoding="utf-8")
        self.assertEqual(self.plan("scripts/rho.sh"), {"tests/test_r1.py": set()})
        # bắc cầu rồi mới xét phần ngoài lớp: `Mid` trúng nhờ nhắc `Leaf`, phần ngoài lớp nhắc `Mid`
        r1b = "class Leaf:\n    X = 'tau.sh'\n\n\nclass Mid:\n    y = Leaf\n\n\nZ = Mid\n\n\nclass T:\n    pass\n"
        (self.t / "test_r1b.py").write_text(r1b, encoding="utf-8")
        self.assertEqual(self.plan("scripts/tau.sh"), {"tests/test_r1b.py": set()})

    def test_commit_gate_fast_class_glob_tokens(self):
        self.assertEqual(self.picked("docs/ops/GO-NO-GO-2026-11-19.md"), {"G", "H", "K"})
        self.assertEqual(self.picked("khac/GO-NO-GO-1.md"), {"G", "H", "K"})  # chỉ so phần tên
        self.assertEqual(self.picked("PROGRESS.md"), {"K"})  # `GO-NO-GO*.md` không còn là "quét *.md"
        self.assertEqual(self.picked("docs/a.mdx"), {"M"})  # `*.md` không khớp đuôi `.mdx`
        self.assertIsNone(self.plan("docs/GO-NO-GO-1.txt"))
        cases = [
            ("a.md", 'p.rglob("*.md")', True),
            ("a.md", '"**/*.md"', True),
            ("GO-NO-GO-1.md", '"docs/ops/GO-NO-GO*.md"', True),
            ("DECISIONS-2026.md", '"DECISIONS-*.md"', True),
            ("PROGRESS.md", '"DECISIONS-*.md", "GO-NO-GO*.md"', False),
            ("a.md", '"*.mdx"', False),
            ("a.md", '"docs/*/README.md"', False),  # `*` không ở phần tên
            ("README.md", '"docs/*/README.md"', True),  # nhắc tên tệp
            ("Makefile", '"*"', False),  # không đuôi: không luật glob
            ("tài liệu.md", '"tài*.md"', True),  # Unicode, khoảng trắng trong tên
            ("PROGRESS.md", '"tài*.md"', False),
        ]
        for name, text, want in cases:
            with self.subTest(name=name, text=text):
                self.assertEqual(xt._test_matches(name, text), want)

    def test_commit_gate_fast_class_whole_file(self):
        (self.t / "test_rest.py").write_text(
            'import unittest\nCFG = "delta.toml"\n\n\nclass P(unittest.TestCase):\n    pass\n', encoding="utf-8"
        )
        (self.t / "test_imp.py").write_text(
            "import unittest\n\n\nclass Q(unittest.TestCase):\n    def test_x(self):\n        import clsmod\n",
            encoding="utf-8",
        )
        (self.t / "test_bad.py").write_text('"zeta.ini"\nclass (:\n', encoding="utf-8")
        self.assertEqual(self.plan("src/delta.toml"), {"tests/test_rest.py": set()})  # phần ngoài lớp khớp
        self.assertEqual(self.plan("scripts/clsmod.py"), {"tests/test_imp.py": set()})  # import lồng trong lớp
        self.assertEqual(self.plan("src/cls.py"), {"tests/test_cls.py": set()})  # test_<tên>.py
        self.assertEqual(self.plan("tests/test_cls.py"), {"tests/test_cls.py": set()})  # chính tệp test
        self.assertEqual(self.plan("tests/test_xoa.py"), {})  # tệp test bị xoá: không còn gì
        self.assertEqual(self.plan("etc/zeta.ini"), {"tests/test_bad.py": set()})  # không parse được: cả tệp
        self.assertNotIn("tests/test_bad.py", self.plan("scripts/alpha.sh") or {})
        self.assertIsNone(xt.test_select_plan(self.base, "tests", ["Makefile"]))


class UnittestClassIdsTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(unittest.mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.base)}))
        self.enterContext(unittest.mock.patch.object(sys, "path", list(sys.path)))
        self.enterContext(unittest.mock.patch.dict(sys.modules))
        self.t = self.base / "tests"
        self.t.mkdir()
        case = "class {0}(unittest.TestCase):\n    def test_x(self):\n        pass\n"
        one = "import unittest\n" + case.format("A") + case.format("B")
        (self.t / "test_cgf_one.py").write_text(one, encoding="utf-8")
        (self.t / "test_cgf_two.py").write_text("import unittest\n" + case.format("C"), encoding="utf-8")

    def test_commit_gate_fast_class_ids(self):
        ids = xt.unittest_class_ids(self.base, "tests", ["tests/test_cgf_one.py"])
        self.assertEqual(ids, ["tests.test_cgf_one.A", "tests.test_cgf_one.B"])
        everything = ["tests.test_cgf_one.A", "tests.test_cgf_one.B", "tests.test_cgf_two.C"]
        self.assertEqual(xt.unittest_class_ids(self.base, "tests", None), everything)
        self.assertEqual(xt.unittest_class_ids(self.base, "tests", []), [])
        self.assertEqual(xt.unittest_class_ids(self.t, ".", ["test_cgf_two.py"]), ["test_cgf_two.C"])  # không gói
        rc, out, _ = run_main("test-select", "--unittest", "tests/test_cgf_two.py")
        self.assertEqual((rc, out), (0, "tests.test_cgf_two.C\n"))

    def test_commit_gate_fast_class_ids_filtered_by_class(self):
        dyn = (
            "import unittest\n\n\nclass A(unittest.TestCase):\n    def test_x(self):\n        'omega.sh'\n\n\n"
            "class B(unittest.TestCase):\n    def test_x(self):\n        'kappa.sh'\n\n\n"
            "def _make():\n    return type('Dyn', (unittest.TestCase,), {'test_x': lambda self: None})\n\n\n"
            "Dyn = _make()\n"
        )
        (self.t / "test_cgf_dyn.py").write_text(dyn, encoding="utf-8")
        imp = "import unittest\nfrom test_cgf_dyn import B as Again\n\n\nclass Z(unittest.TestCase):\n"
        imp += "    def test_x(self):\n        'sigma.sh'\n"
        (self.t / "test_cgf_imp.py").write_text(imp, encoding="utf-8")
        cases = {
            "omega.sh": "tests.test_cgf_dyn.A\ntests.test_cgf_dyn.Dyn\n",  # lớp sinh động: chạy khi tệp trúng
            "kappa.sh": "tests.test_cgf_dyn.B\ntests.test_cgf_dyn.Dyn\n",
            "sigma.sh": "tests.test_cgf_dyn.B\ntests.test_cgf_imp.Z\n",  # lớp import từ module ngoài kế hoạch: giữ
        }
        for changed, want in cases.items():
            with self.subTest(changed=changed):
                self.assertEqual(run_main("test-select", "--unittest", f"scripts/{changed}")[:2], (0, want))
        rc, out, _ = run_main("test-select", "scripts/omega.sh")  # chế độ tệp: vẫn in tệp
        self.assertEqual((rc, out), (0, "tests/test_cgf_dyn.py\n"))
        env = {k: v for k, v in os.environ.items() if k != "XT_CHANGED_FILES"}
        with unittest.mock.patch.dict(os.environ, env, clear=True):
            rc, out, _ = run_main("test-select", "--unittest")  # không biết tệp đổi → mọi lớp
        want_all = ["A", "B", "Dyn"]
        got = out.split()
        self.assertEqual(rc, 0)
        self.assertEqual(
            [i for i in got if i.startswith("tests.test_cgf_dyn.")], [f"tests.test_cgf_dyn.{c}" for c in want_all]
        )
        self.assertIn("tests.test_cgf_one.A", got)

    def test_commit_gate_fast_class_filter_never_empties_related_files(self):
        """Review #678: có tệp liên quan mà lọc theo lớp ra 0 id (chỉ lớp phụ trợ trúng, không ai nhắc tên nó) → không
        lọc, chạy mọi lớp của tệp đó và nói rõ ở stderr — không bao giờ "có tệp liên quan mà 0 lớp" (xanh giả)."""
        text = "import unittest\n\n\nclass Unused:\n    X = 'nu.sh'\n\n\n"
        text += "class T(unittest.TestCase):\n    def test_x(self):\n        pass\n"
        (self.t / "test_cgf_unused.py").write_text(text, encoding="utf-8")
        self.assertEqual(
            xt.test_select_plan(self.base, "tests", ["scripts/nu.sh"]), {"tests/test_cgf_unused.py": {"T"}}
        )
        rc, out, err = run_main("test-select", "--unittest", "scripts/nu.sh")
        self.assertEqual((rc, out), (0, "tests.test_cgf_unused.T\n"))
        self.assertIn("[test-select] lọc theo lớp ra 0 lớp", err)
        rc, out, err = run_main("test-select", "--unittest", "tests/test_cgf_two.py")  # lọc ra ≥ 1 lớp: không báo
        self.assertEqual((rc, out), (0, "tests.test_cgf_two.C\n"))
        self.assertNotIn("lọc theo lớp ra 0 lớp", err)

    def test_commit_gate_fast_import_error_is_red(self):
        (self.t / "test_cgf_bad.py").write_text("import khong_co_module_nay_cgf\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "(?s)không nạp được test: .*khong_co_module_nay_cgf"):
            xt.unittest_class_ids(self.base, "tests", ["tests/test_cgf_bad.py"])
        rc, out, err = run_main("test-select", "--unittest", "tests/test_cgf_bad.py")
        self.assertEqual((rc, out), (1, ""))
        self.assertIn("✗ không nạp được test", err)


@unittest.skipIf(shutil.which("bash") is None or shutil.which("git") is None, "cần bash + git")
class DevTaskGateFastTest(unittest.TestCase):
    """`dev-task.sh gate-fast`: format_check → lint → typecheck → test_fast (XT_CHANGED_FILES); không build; test_fast
    trống/no-op hoặc không biết file đổi → `test`."""

    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.tmp / "scripts").mkdir()
        shutil.copy(ROOT / "scripts" / "dev-task.sh", self.tmp / "scripts" / "dev-task.sh")

    def run_task(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = {k: v for k, v in os.environ.items() if k not in ("XT_CHANGED_FILES", "XT_CHANGED_TRACKED_ONLY")}
        env["CLAUDE_PROJECT_DIR"] = str(self.tmp)
        return subprocess.run(
            ["bash", str(self.tmp / "scripts" / "dev-task.sh"), *args],
            capture_output=True,
            text=True,
            cwd=self.tmp,
            env=env,
        )

    def git(self, *args: str) -> None:
        subprocess.run(
            ["git", "-C", str(self.tmp), "-c", "user.email=t@t", "-c", "user.name=t", *args],
            check=True,
            capture_output=True,
        )

    def commit_init(self) -> None:
        (self.tmp / "README").write_text("x\n", encoding="utf-8")
        self.git("add", "README")
        self.git("commit", "-q", "-m", "init")

    def yaml(self, text: str) -> None:
        (self.tmp / "xt.yaml").write_text(text, encoding="utf-8")

    def test_commit_gate_fast_passes_changed_files(self):
        self.git("init", "-q")
        (self.tmp / "a.txt").write_text("1\n", encoding="utf-8")
        (self.tmp / ".gitignore").write_text("seen\nran-*\n", encoding="utf-8")
        self.yaml("lint: sh -c 'touch ran-lint'\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "init")
        (self.tmp / "a.txt").write_text("2\n", encoding="utf-8")
        (self.tmp / "moi.txt").write_text("x\n", encoding="utf-8")
        (self.tmp / "tài liệu.md").write_text("x\n", encoding="utf-8")  # Unicode + khoảng trắng: nguyên văn, không nháy
        self.yaml(
            "format_check: sh -c 'touch ran-fmt'\nlint: sh -c 'touch ran-lint'\ntypecheck: sh -c 'touch ran-type'\n"
            "build: sh -c 'touch ran-build'\ntest: sh -c 'touch ran-test'\n"
            'test_fast: sh -c \'printf "%s\\n" "$XT_CHANGED_FILES" > seen\'\n'
        )
        r = self.run_task("gate-fast")
        self.assertEqual(r.returncode, 0, r.stderr)
        seen = (self.tmp / "seen").read_text(encoding="utf-8").splitlines()
        self.assertEqual(sorted(seen), ["a.txt", "moi.txt", "tài liệu.md", "xt.yaml"])
        for name, ran in (("fmt", True), ("lint", True), ("type", True), ("build", False), ("test", False)):
            self.assertEqual((self.tmp / f"ran-{name}").exists(), ran, name)
        self.assertIn("GATE-FAST XANH (4 lệnh)", r.stderr)

    def test_commit_gate_fast_changed_files_keep_renamed_source(self):
        """`git mv` giữ cả tên cũ trong XT_CHANGED_FILES (`--no-renames`, review #321): test của file cũ vẫn được chọn."""
        self.git("init", "-q")
        (self.tmp / "old.txt").write_text("1\n", encoding="utf-8")
        (self.tmp / ".gitignore").write_text("seen\n", encoding="utf-8")
        self.yaml("lint: sh -c 'exit 0'\ntest_fast: sh -c 'printf \"%s\\n\" \"$XT_CHANGED_FILES\" > seen'\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "init")
        self.git("mv", "old.txt", "new.txt")
        r = self.run_task("gate-fast")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sorted((self.tmp / "seen").read_text(encoding="utf-8").splitlines()), ["new.txt", "old.txt"])

    def test_commit_gate_fast_red_stops(self):
        self.git("init", "-q")
        self.commit_init()
        self.yaml("lint: sh -c 'exit 0'\ntest_fast: sh -c 'exit 1'\ntest: sh -c 'touch ran-test'\n")
        r = self.run_task("gate-fast")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("GATE-FAST ĐỎ ở 'test_fast'", r.stderr)
        self.assertFalse((self.tmp / "ran-test").exists())

    def test_commit_gate_fast_falls_back_to_full_test(self):
        # Không phải repo git → không biết file đổi → `test`.
        self.yaml("test_fast: sh -c 'touch ran-fast'\ntest: sh -c 'touch ran-test'\n")
        r = self.run_task("gate-fast")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.tmp / "ran-test").exists())
        self.assertFalse((self.tmp / "ran-fast").exists())
        self.assertIn("không biết file nào đổi", r.stderr)
        # test_fast no-op/trống → `test`, kể cả khi biết file đổi.
        self.git("init", "-q")
        self.commit_init()
        for fast in ("true", '""', "echo bo-qua"):
            with self.subTest(fast=fast):
                (self.tmp / "ran-test").unlink(missing_ok=True)
                self.yaml(f"test_fast: {fast}\ntest: sh -c 'touch ran-test'\n")
                r = self.run_task("gate-fast")
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertTrue((self.tmp / "ran-test").exists())

    def test_commit_gate_fast_noop_and_autopilot(self):
        r = self.run_task("gate-fast")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("GATE-FAST KHÔNG CHẠY LỆNH NÀO", r.stderr)
        (self.tmp / ".autopilot").mkdir()
        (self.tmp / ".autopilot" / "state.json").write_text('{"active": true}', encoding="utf-8")
        self.yaml('lint: "test -d ."\ntest: ""\ntest_fast: ""\n')
        r = self.run_task("gate-fast")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ĐỎ: autopilot đang chạy mà 'test'", r.stderr)  # cổng nhanh không lách được ADR-0011

    def test_commit_gate_fast_listed_in_usage(self):
        for args in ((), ("khong-co",)):
            r = self.run_task(*args)
            self.assertEqual(r.returncode, 2)
            self.assertIn("gate|gate-fast", r.stderr)


if __name__ == "__main__":
    unittest.main()
