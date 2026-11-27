"""T-5039 (LOOP-CTX-004): cổng commit ĐỎ không đổ nguyên output vào ngữ cảnh agent.

`pre-bash-guard.sh` gom stdout+stderr của cổng vào `<thư mục git>/xt-commit-gate.log` (quyền 600) và khi đỏ chỉ in bước
đỏ, khối lỗi trích được, đuôi log và đường dẫn log — tổng ≤ 8 000 ký tự, exit 2. Không tạo được log → hành vi cũ (cả
output ra stderr), vẫn exit 2. Cổng xanh: stderr như cũ. Gọi hook thật bằng payload giả như `tests/test_hooks.py`."""

from __future__ import annotations

import concurrent.futures
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_hooks import ROOT, decision, run_hook

LOG = "xt-commit-gate.log"
CAP = 8000

# Cổng giả in ~200 000 ký tự kiểu nhiều shard: shard xanh (`ok`/`OK`) trước và sau, lỗi nằm GIỮA (khối FAIL của unittest
# kèm traceback, một traceback trần, một dòng lint `tệp:dòng:cột:`), một dòng rất dài có chữ UTF-8 nhiều byte. Đuôi chỉ
# còn `OK` — chỉ in đuôi thì mất lỗi.
GEN = r"""
import sys
def ok(shard, n):
    for i in range(n):
        print(f"test_case_{shard}_{i:04d} (tests.test_mod.Lop.test_case_{i:04d}) ... ok", file=sys.stderr)
    print("-" * 70 + f"\nRan {n} tests in 0.5s\n\nOK", file=sys.stderr)
ok(1, 1500)
print("Traceback (most recent call last):\n  File \"x.py\", line 3, in <module>\n    boom()\nValueError: TRACEBACK-TRAN")
print("scripts/a.py:12:5: F401 `os` imported but unused LINT-MARK")
print("=" * 70 + "\nFAIL: test_giua (tests.test_mod.Lop.test_giua)\n" + "-" * 70, file=sys.stderr)
print("Traceback (most recent call last):\n  File \"t.py\", line 9, in test_giua\n    self.assertEqual(1, 2)",
      file=sys.stderr)
print("AssertionError: MARKER-GIUA 1 != 2", file=sys.stderr)
print("=" * 70 + "\nERROR: test_hai (tests.test_mod.Lop.test_hai)\n" + "-" * 70, file=sys.stderr)
print("Traceback (most recent call last):\nKeyError: 'MARKER-HAI'", file=sys.stderr)
print("-" * 70 + "\nRan 2 tests in 0.1s\n\nFAILED (failures=1, errors=1)", file=sys.stderr)
print("error: Ổ dài " + "Ổ" * 20000)
ok(2, 1500)
print("CUOI-LOG " + "Ổ" * 5000)
sys.exit(1)
"""


def _awks() -> list[str]:
    """Các awk có trên máy (hook phải chạy với awk POSIX: mawk/BSD awk không có `{n,}`)."""
    return [a for a in ("gawk", "mawk", "busybox") if shutil.which(a)] or ["awk"]


@unittest.skipIf(shutil.which("bash") is None or shutil.which("git") is None, "cần bash + git")
class GateOutputCapTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.repo = self.tmp / "proj"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        (self.repo / "scripts").mkdir()
        shutil.copy(ROOT / "scripts" / "dev-task.sh", self.repo / "scripts" / "dev-task.sh")
        (self.tmp / "gen.py").write_text(GEN, encoding="utf-8")
        self.gitdir = self.repo / ".git"

    def xt(self, test_cmd: str = "") -> None:
        test_cmd = test_cmd or f"python3 -u {self.tmp / 'gen.py'}"  # -u: stdout/stderr xen đúng thứ tự như test thật
        (self.repo / "xt.yaml").write_text(f"test: {test_cmd}\n", encoding="utf-8")

    def hook(self, env: dict[str, str] | None = None, cmd: str = "git commit -m x") -> tuple[int, str, str]:
        payload = {"tool_input": {"command": cmd}, "cwd": str(self.repo)}
        return run_hook("pre-bash-guard.sh", payload, self.repo, extra_env={"XT_GUARD_POLICY": "", **(env or {})})

    def bin_with(self, name: str, body: str) -> dict[str, str]:
        """PATH có lệnh `name` thay thế bằng script sh `body`."""
        b = Path(tempfile.mkdtemp(dir=self.tmp))
        (b / name).write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        (b / name).chmod(0o755)
        return {"PATH": f"{b}{os.pathsep}{os.environ['PATH']}"}

    @staticmethod
    def awk_body(awk: str) -> str:
        path = shutil.which(awk)
        return f'exec {path} awk "$@"' if awk == "busybox" else f'exec {path} "$@"'

    def leftovers(self) -> list[str]:
        return sorted(p.name for p in self.gitdir.iterdir() if p.name.startswith("xt-commit-gate.") and p.name != LOG)

    def test_red_huge_output_trimmed_error_from_middle_kept(self) -> None:
        self.xt()
        for awk in _awks():
            with self.subTest(awk=awk):
                code, out, err = self.hook(self.bin_with("awk", self.awk_body(awk)))
                self.assertEqual((code, out), (2, ""), err[-2000:])
                self.assertLessEqual(len(err), CAP, err[:3000])
                for mark in (
                    "GATE ĐỎ ở 'test'",  # bước đỏ của dev-task
                    "AssertionError: MARKER-GIUA",  # khối FAIL nằm giữa output
                    "test_giua",
                    "KeyError: 'MARKER-HAI'",
                    "ValueError: TRACEBACK-TRAN",
                    "LINT-MARK",
                    "FAILED (failures=1, errors=1)",
                    "dòng cuối của log",
                    "Cổng trước commit ĐỎ (gate: build/typecheck/lint/test)",
                    f"{self.gitdir.resolve() / LOG}",
                ):
                    self.assertIn(mark, err)
                self.assertNotIn("test_case_1_0005", err)  # shard xanh không vào ngữ cảnh
                self.assertIn("Ổ [...]", err)  # dòng dài bị cắt, không xé chữ UTF-8 (text=True giải mã chặt)
                log = self.gitdir / LOG
                self.assertEqual(stat.S_IMODE(log.stat().st_mode), 0o600)
                full = log.read_text(encoding="utf-8")
                self.assertGreater(len(full), 200_000)
                self.assertIn("test_case_1_0005", full)
                self.assertIn("CUOI-LOG", full)
                self.assertEqual(self.leftovers(), [])
                st = subprocess.run(
                    ["git", "-C", str(self.repo), "status", "--porcelain", "--ignored"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self.assertNotIn(LOG, st.stdout)  # log nằm trong thư mục git, không thể bị commit

    def test_red_worst_case_every_line_matches_still_capped(self) -> None:
        # mọi dòng đều khớp mẫu lỗi và dài: các ngăn (bước đỏ, khối lỗi, dòng lẻ, đuôi) đều chạm trần riêng
        worst = self.tmp / "worst.py"
        worst.write_text(
            "import sys\n"
            "for i in range(300):\n"
            "    print('=' * 70 + f'\\nFAIL: t{i}\\n' + '-' * 70)\n"
            "    print(f'AssertionError: {i} ' + 'Ổ' * 400)\n"
            "    print(f'error: dong-le {i} ' + 'x' * 900)\n"
            "    print(f'[dev-task] ĐỎ: gia {i} ' + 'y' * 900)\n"
            "sys.exit(1)\n",
            encoding="utf-8",
        )
        self.xt(f"python3 -u {worst}")
        code, _, err = self.hook()
        self.assertEqual(code, 2)
        self.assertLessEqual(len(err), CAP)
        self.assertIn("AssertionError: 0 ", err)
        self.assertIn("(còn nữa, xem log)", err)
        self.assertIn(str(self.gitdir.resolve() / LOG), err)

    def test_log_unwritable_falls_back_to_full_output_and_blocks(self) -> None:
        self.xt()
        # chỉ mktemp của hook (tệp log) hỏng — như thư mục git chỉ đọc/đĩa đầy; dev-task vẫn dùng mktemp thật. Không dùng
        # chmod: chạy bằng root thì quyền thư mục không chặn được.
        real = shutil.which("mktemp")
        body = f'case "$*" in *xt-commit-gate*) exit 1 ;; esac\nexec {real} "$@"'
        code, out, err = self.hook(self.bin_with("mktemp", body))
        self.assertEqual((code, out), (2, ""))
        self.assertGreater(len(err), 200_000)  # hành vi cũ: cả output
        self.assertIn("AssertionError: MARKER-GIUA", err)
        self.assertIn("Cổng trước commit ĐỎ", err)
        self.assertNotIn("Log đầy đủ", err)
        self.assertFalse((self.gitdir / LOG).exists())

    def test_not_a_git_repo_keeps_old_behaviour(self) -> None:
        shutil.rmtree(self.gitdir)
        self.xt("sh -c 'echo NGOAI-GIT; exit 1'")
        code, out, err = self.hook()
        self.assertEqual((code, out), (2, ""))
        self.assertIn("NGOAI-GIT", err)
        self.assertNotIn("Log đầy đủ", err)

    def test_green_unchanged(self) -> None:
        self.xt("sh -c 'echo XANH-STDOUT; echo XANH-STDERR >&2'")
        code, out, err = self.hook()
        self.assertEqual((code, decision(out)), (0, None), err)
        self.assertIn("XANH-STDOUT", err)
        self.assertIn("XANH-STDERR", err)
        self.assertNotIn("ĐỎ", err)
        self.assertNotIn("Log đầy đủ", err)
        self.assertIn("XANH-STDOUT", (self.gitdir / LOG).read_text(encoding="utf-8"))
        # commit kèm hành động cần hỏi: cổng xanh vẫn chạy trước, stdout chỉ còn JSON
        code, out, err = self.hook(env={"XT_GUARD_POLICY": "strict"}, cmd="git commit -am x && git push origin main")
        self.assertEqual((code, decision(out)), (0, "ask"), err)
        self.assertIn("XANH-STDOUT", err)

    def test_red_small_output_shown_whole(self) -> None:
        self.xt("sh -c 'echo NHO-1; echo NHO-2 >&2; exit 1'")
        code, _, err = self.hook()
        self.assertEqual(code, 2)
        # cả hai luồng vào log; thứ tự giữa chúng do dev-task (`run_counted` tee riêng từng luồng), không do hook
        self.assertIn("NHO-1", err)
        self.assertIn("NHO-2", err)

    def test_symlink_or_dir_at_log_path(self) -> None:
        self.xt("sh -c 'echo AssertionError: SYM; exit 1'")
        victim = self.tmp / "victim.txt"
        victim.write_text("giu-nguyen\n", encoding="utf-8")
        (self.gitdir / LOG).symlink_to(victim)
        code, _, err = self.hook()
        self.assertEqual(code, 2)
        self.assertEqual(victim.read_text(encoding="utf-8"), "giu-nguyen\n")  # không ghi theo symlink
        self.assertFalse((self.gitdir / LOG).is_symlink())
        self.assertIn("AssertionError: SYM", err)
        (self.gitdir / LOG).unlink()
        (self.gitdir / LOG).mkdir()
        code, _, err = self.hook()
        self.assertEqual(code, 2)
        left = self.leftovers()
        self.assertEqual(len(left), 1, left)  # không đổi tên được → trỏ tới tệp tạm (vẫn đọc được)
        self.assertIn(str(self.gitdir.resolve() / left[0]), err)

    def test_concurrent_commits_do_not_mix_logs(self) -> None:
        self.xt("sh -c 'echo AssertionError: M-$XT_MARK; sleep 1; echo DUOI-$XT_MARK; exit 1'")
        with concurrent.futures.ThreadPoolExecutor(2) as ex:
            res = list(ex.map(lambda m: (m, self.hook({"XT_MARK": m})), ("A", "B")))
        for mark, (code, _, err) in res:
            other = "B" if mark == "A" else "A"
            self.assertEqual(code, 2, err)
            self.assertIn(f"M-{mark}", err)
            self.assertIn(f"DUOI-{mark}", err)
            self.assertNotIn(f"M-{other}", err)
        self.assertEqual(self.leftovers(), [])
        self.assertRegex((self.gitdir / LOG).read_text(encoding="utf-8"), r"DUOI-[AB]")


if __name__ == "__main__":
    unittest.main()
