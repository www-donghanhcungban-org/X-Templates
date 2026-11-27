"""T-5041 (D-612, AUD-HAR-541): mọi glob không nháy ở vị trí tên tag của lệnh DẠNG TẠO là tag phiên bản.

Oracle: với mỗi lệnh xấu, test dựng thư mục tạm chỉ có tệp `v1.2.0` (và `v1.2.0+b`), cho CHÍNH bash bung từ glob
(`shopt` kèm theo nếu có) rồi khẳng định (1) bash bung ra tên tag phiên bản — bằng chứng lệnh thật tạo được tag —
và (2) guard chặn lệnh ở chính sách mặc định lẫn `strict`. Ca tốt: dạng liệt kê chỉ đọc, tên không phải phiên bản,
refspec không có glob — guard không chặn."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
import unittest.mock as mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

os.environ.setdefault("XT_GUARD_PHASE", "harden")
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
import guard

VERSION = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.+-]*)?")
GLOB_WORDS = (  # từ ở vị trí tên tag; `PRE` là tiền tố lệnh (shopt) của ca
    "*",
    "??????",
    "*.*",
    "?*",
    "??????+b",
    "v1.2.[]0]",
    "[[=v=]]1.2.0",
    "[[:alpha:]][[:digit:]].[[:digit:]].[[:digit:]]",
    "[!x]1.2.0",
)
BAD = (
    *(f"git tag {w}" for w in GLOB_WORDS),
    *(f"git tag -a {w} -m x" for w in ("*", "?*")),
    "git tag -f *",
    "git tag * HEAD",
    "shopt -s nocaseglob; git tag V1.2.?",
    "shopt -s nocaseglob; git tag V*",
    *(f"git update-ref refs/tags/{w} HEAD" for w in ("*", "??????", "?*", "*.*")),
    *(f"git push origin HEAD:refs/tags/{w}" for w in ("*", "??????", "?*", "*.*")),
    "git push origin ??????",
    "git push origin ?*",
)
GOOD = (
    "git tag",
    "git tag -l",
    "git tag --list 'v*'",
    "git tag -l v*",
    "git tag -n5 v*",
    "git tag --contains HEAD v*",
    "git tag --merged HEAD v*",
    "git tag --points-at HEAD v*",
    "git tag -d old",
    "git tag nightly",
    "git tag 'rc*'",  # glob không thể bung ra `v…` (đầu `r`), tên ref không hợp lệ: luật cũ cho qua
    "git tag 'r?'",
    "git tag '?.?.?'",  # 5 ký tự: ngắn hơn tag phiên bản ngắn nhất `v1.2.3`
    "git tag v1",
    "git tag v1.2",
    "git tag -a keep-this -m x",
    "git update-ref refs/heads/topic HEAD",
    "git push origin topic",
    "git push origin HEAD:refs/heads/topic",
)


def decide(cmd: str, policy: str = "") -> dict:
    with (
        mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(ROOT), "XT_GUARD_POLICY": policy}),
        mock.patch.object(guard, "_current_branch", return_value="feat"),
        mock.patch.object(guard, "_origin_repo", return_value="me/repo"),
    ):
        raw = guard.bash_decision(cmd, str(ROOT), str(ROOT))
        return {**raw, "code": guard.decide(raw).code} if policy else guard.apply_policy(raw)


def blocked(cmd: str, policy: str = "") -> bool:
    return bool(decide(cmd, policy).get("decision"))


def bash_expansion(cmd: str) -> list[str]:
    """Từ bash bung ra cho đối số của lệnh trong thư mục chỉ có `v1.2.0`, `v1.2.0+b`: thay `git …` bằng `printf`."""
    pre, _, tail = cmd.rpartition("; ")
    argv = re.sub(r"^git (tag|update-ref|push origin)\s+", "", tail)
    with tempfile.TemporaryDirectory() as tmp:
        for name in ("v1.2.0", "v1.2.0+b"):
            Path(tmp, name).touch()
        script = f"{pre + '; ' if pre else ''}printf '%s\\n' {argv}"
        out = subprocess.run(["bash", "-c", script], cwd=tmp, capture_output=True, text=True, check=True).stdout
    return out.split()


class TagGlobOracle(unittest.TestCase):
    def test_bad_commands_expand_to_version_tag_and_are_blocked(self) -> None:
        for cmd in BAD:
            for policy in ("", "strict"):
                with self.subTest(cmd=cmd, policy=policy):
                    self.assertTrue(blocked(cmd, policy), "guard để lọt lệnh tạo tag viết bằng glob")

    def test_bad_glob_really_expands_to_release_tag(self) -> None:
        # bằng chứng bash (không áp cho `push origin ??????`/refspec: đích nằm sau `HEAD:refs/tags/`)
        for cmd in BAD:
            if "refs/tags" in cmd or "push origin" in cmd:
                continue
            with self.subTest(cmd=cmd):
                words = bash_expansion(cmd)
                self.assertTrue(any(VERSION.fullmatch(w) for w in words), words)

    def test_good_commands_pass(self) -> None:
        for cmd in GOOD:
            for policy in ("", "strict"):
                with self.subTest(cmd=cmd, policy=policy):
                    self.assertFalse(blocked(cmd, policy), "guard chặn oan lệnh lành")

    def test_literal_release_tag_still_blocked(self) -> None:
        for cmd in ("git tag v1.2.0", "git tag -a v1.2.0-rc.1 -m x", "git push origin HEAD:refs/tags/v1.2.0"):
            with self.subTest(cmd=cmd):
                self.assertTrue(blocked(cmd))

    def test_sort_and_format_with_name_create_tag(self) -> None:
        # AUD-HAR-571: git 2.53 TẠO tag `zz` khi `--sort`/`--format` đi với tên — không phải liệt kê, guard chặn đúng
        for cmd in ("git tag --sort=-v:refname v1.2.0", "git tag --format='%(refname)' v1.2.0"):
            with self.subTest(cmd=cmd):
                self.assertTrue(blocked(cmd))


if __name__ == "__main__":
    unittest.main()
