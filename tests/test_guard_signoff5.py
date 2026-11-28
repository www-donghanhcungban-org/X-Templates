"""D-503 (T-3940): phát hiện cổng ký lần 5 — hồi quy #648 (biến `for` duyệt glob cắt `${f%…}` coi như chữ đã tính, 🔴),
thân `sh -c "…"` nháy kép có `\\"`/`\\$` (🔴), thư mục làm việc không xác định (`CDPATH`, `~-`, `env -C "$X"`, `pushd -n`,
🔴), xargs miễn theo nguồn (🟠), mảng còn gán vô hướng; chặn oan: kịch bản sed, `$(date +FMT)` ở đích ghi, cờ bool
của trình chạy gói, `cd "$HOME/<dự án>"`.

DENY: mẫu tái hiện mà guard ở `702e006d` cho chạy. ALLOW: dạng lành (đối chứng) phải vẫn chạy."""

from __future__ import annotations

import os
import sys
import unittest
import unittest.mock as mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("XT_GUARD_PHASE", "harden")
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
sys.path.insert(0, str(ROOT / "tests"))
import guard
from test_guard_default_deny import assert_cache_cleanup_layouts

H = chr(126)  # `~` dựng bằng chr: chữ xoá home không nằm nguyên văn trong tệp test
CL = "." + "claude"  # thư mục hàng rào


def decide(cmd: str, root: Path = ROOT, env: dict | None = None) -> dict:
    with (
        mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(root), "XT_GUARD_POLICY": "", **(env or {})}),
        mock.patch.object(guard, "_current_branch", return_value="feat"),
    ):
        return guard.apply_policy(guard.bash_decision(cmd.replace("@H", H).replace("@C", CL), str(root), str(root)))


DENY = (
    # 1. hồi quy #648: cắt trên biến `for` duyệt glob
    'for d in @H/*/; do rm -rf "${d%/}"; done',
    'for d in /*; do rm -rf "${d%/}"; done',
    'for d in ../*; do rm -rf "${d%/}"; done',
    'for d in @H/.*; do rm -rf "${d%/}"; done',
    'for d in /home/u/*; do rm -rf "${d%/}"; done',
    'for d in @H/X*; do rm -rf "${d%/}"; done',
    'for f in @H/.ssh/*; do rm -f "${f%.pub}"; done',
    'for f in *; do rm -rf "${f%x}"; done',
    'for f in .git/*; do rm -rf "${f%x}"; done',
    'for d in /*; do rm -rf "${d#x}"; done',
    'for f in @C/*.json; do cp /dev/null "${f%x}"; done',
    "for d in @H/*/; do rm -rf ${d%/}; done",
    'for d in @H/a*; do rm -rf "${d%%a}"; done',
    'rm -rf "${d%/}"; for d in a*; do :; done',
    'for d in @H/*/; do rm -rf "${X:-${d%/}}"; done',
    'for d in "a b"*; do rm -rf "${d%/}"; done',
    # 2. kịch bản sed có mở rộng ngoài vế thay/giá trị không tính chắc
    'sed -i "s/x/$(cat f)/e" f',
    'sed -i "s/x/$(date +%F)/w out" f',
    'sed -i "s:x:$(date +%T):" f',
    'sed -i "s/$(date +%F)/x/" f',
    'sed -i "s/x/$FOO/" f',
    'sed -i "s/x/$(date +%D)/" f',
    'NEW=/w; sed -i "s/x/$NEW/" f',
    'false || NEW=1; sed -i "s/x/$NEW/" f',
    'sed -i "s/x/$NEW/" f; NEW=1',
    'read NEW; sed -i "s/x/$NEW/" f',
    'rm -f x; sed "s/__V__/$(cat VERSION)/" tpl > out',
    'sed "s/x/$(cat ../VERSION)/" tpl > out',
    'sed "s/x/$(cat nosuchfile)/" tpl > out',
    'sed -e "s/x/$(date +%F)/" -e "1r $(cat f)" f',
    'sed -i "1s/x/$(date +%F)/;2r f" f',
    'sed -n "${n},${e}p" f',
    'sed -n "$n p" f',
    'sed -n "$((n-1))s/x/$(cat f)/p" f',
    'sed --expr "s/x/$(cat f)/e" f',
    'sed -i "s/x/${NEW%a}/" f',
    'sed -i "s/x/$1/" f',
    # 3. `$(date …)` ngoài dạng tính được
    'cp X "$(date +/etc/%F)"',
    'cp X "$(date +%F/..)"',
    'cp X "$(date +.)"',
    'cp X "$(date +%F) $(date +%n)"',
    # fuzz 1: thân `sh -c "…"` nháy kép
    'sh -c "X=-rf; rm \\"\\$X\\" @H"',
    'sh -c "export X=@H; rm -rf \\"\\$X\\""',
    'sh -c "X=-rf; uv run rm \\"\\$X\\" @H"',
    'bash -c "for X in -rf; do rm \\"\\$X\\" @H; done"',
    # fuzz 2: thư mục làm việc không xác định
    "CDPATH=/ cd etc ; rm -rf ssl",
    "CDPATH= cd .. && rm -rf proj",
    "export CDPATH=/; cd etc ; command rm -rf ssl",
    "cd @H+/.. && rm -rf proj",
    "cd @H- && rm -rf zz",
    'cd "$(builtin pwd)/.." && rm -rf proj',
    'cd "$(command pwd)/.." && nice rm -rf proj',
    "CDPATH=/home; cd u && rm -rf zz",
    'env -C "$HOME" rm -rf zz',
    'env -C "$PWD/.." rm -rf proj',
    'env --chdir="$HOME" rm -rf zz',
    'env -C"$HOME" rm -rf zz',
    "pushd -n @H; pushd; rm -rf zz",
    "pushd +1 && rm -rf zz",
    "shopt -s cdable_vars; X=/etc; cd X && rm -rf ssl",
    "cd - && rm -rf zz",
    "cd && rm -rf zz",
    # fuzz 3: xargs miễn theo nguồn
    'echo "@C/settings.json" | xargs mv x.json',
    "echo '@C/settings.json' | xargs -I{} nice mv x.json {}",
    "echo -n @C/settings.json | xargs -I{} mv x.json {}",
    "echo @C/settings.json | xargs env mv x.json",
    "echo @C/settings.json | xargs -I@ env mv x.json @",
    "cd @C && ls | xargs rm",
    "cd .autopilot && ls | xargs cp /dev/null",
    "find @C -name settings.json | xargs rm",
    "find @C/settings.json -maxdepth 0 | xargs mv x.json",
    "ls -d @C/* | xargs sed -i s/a/b/",
    "ls -A | xargs cp /dev/null",
    "echo @C/settings | xargs -I{} mv x.json {}.json",
    "echo settings.json | xargs -I{} nice mv x.json @C/{}",
    "echo @C/settings.json | xargs -t env mv x.json 2>/dev/null",
    "find . -name '*.json' | xargs mv x.json",
    "find . -name '*.json' | xargs -I{} cp x.json {}",
    "printf '%s\\n' git | xargs -I{} nice {} push --force origin main",
    "printf '%s\\n' rm | xargs -I{} env {} -rf @H",
    "echo $X | xargs rm",
    # mảng còn gán vô hướng
    'X=1; X=(-h); dropdb "${X[0]}" db.prod.example.com app',
    'X=1; X=(/etc); cd "${X[0]}" && rm -rf ssl',
    # cd "$HOME/…" ra ngoài dự án / HOME gán lại vẫn chặn
    'cd "$HOME" && git pull',
    'HOME=/ ; cd "$HOME/proj" && git pull',
)

ALLOW = (
    'for f in *.txt; do mv "$f" "${f%.txt}.md"; done',
    'for f in docs/*.md; do echo "${f#docs/}"; done',
    'for f in build/*.o; do rm -f "${f%.o}.d"; done',
    'for f in a b; do rm -rf "${f%x}"; done',
    'for f in src/*.ts; do cp "$f" "${f##src/}.bak"; done',
    'sed -i "s/^updated: .*/updated: $(date +%F)/" f',
    'NEW=$(date +%F); sed -i "s/x/$NEW/" f',
    'NEW="$(date +%F)"; sed -i "s/x/$NEW/g" f',
    'NEW=v1.2; sed -i "s/x/${NEW}/" f',
    'sed "s/__VERSION__/$(cat VERSION)/" tpl > out',
    'V=$(cat VERSION); sed "s/__V__/$V/" tpl > out',
    "sed -i -e \"s/a/$(date +%s)/g\" -e 's/b/c/' f",
    'sed -n --expression "s|a|$(date -u +%FT%T)|p" f',
    'sed -E -i.bak "1,/x/ s#a#$(date +%Y)#2" f',
    'sed -i "s/x/$(date +%F)/" -- f',
    'sed -i "s/x/y/" f',
    'sed -i "1s/x/$(date +%F)/;2d" f',
    'n="$(grep -n foo f | cut -d: -f1)"; sed -n "$((n-25)),$((n+5))p" f',
    "sed --quiet '$p' f; sed 's/[.]py$//' f",
    'N=3; sed -n "${N}q;$((N+1)),20d" f',
    'sed --expr "s/x/$(date +%F)/" f',
    'mv report.html "report-$(date +%Y%m%d).html"',
    'cp X "/tmp/x-$(date +%F).md"',
    'make test | tee "/tmp/test-$(date +%s).log"',
    'npx -y prettier --write "$FILE"',
    'npx --yes prettier --write "$FILE"',
    'npx --no-install prettier --write "$FILE"',
    'pnpm dlx --silent prettier --write "$FILE"',
    # đối chứng của fuzz
    "ls *.md | xargs -I{} cp {} /tmp/",
    "find docs -name '*.md' | xargs sed -i s/a/b/",
    "echo docs/a.md | xargs -I{} cp {} /tmp/",
    "echo a.md b.md | xargs -t cp -t /tmp/",
    "cd build && rm -rf out",
    'd=build; cd "$d" && rm -rf out',
    'sh -c "echo \\"hi\\""',
    "pushd build && rm -rf out",
    "cd build out; rm -rf zz",  # `cd` hai toán hạng: bash báo lỗi, thư mục không đổi
    "cd @H+/docs && echo x > out.md; cd @H- && echo x > out.md",
    "cd @H+/docs && rm -rf out",
    "cd src && cd - && git status",
    "cd @H- && git fetch origin",  # git/gh: luật riêng xét mọi thư mục ứng viên (D-347)
    'X=(a b); echo "${X[0]}"',
)


class SignOff5DenyTest(unittest.TestCase):
    def test_deny(self):
        for cmd in DENY:
            with self.subTest(cmd=cmd):
                self.assertEqual(decide(cmd)["decision"], "deny")

    def test_cdpath_from_environment(self):
        self.assertEqual(decide("cd etc && rm -rf ssl", env={"CDPATH": "/"})["decision"], "deny")


class SignOff5AllowTest(unittest.TestCase):
    def test_allow(self):
        for cmd in ALLOW:
            with self.subTest(cmd=cmd):
                d = decide(cmd)
                self.assertEqual(d["decision"], "", d.get("reason"))

    def test_cache_cleanup(self):
        assert_cache_cleanup_layouts(self, decide, ("find . -name '*.pyc' | xargs rm -f",))

    def test_cd_home_inside_project(self):
        """4b: `cd "$HOME/<dự án>"` (HOME không gán lại) — bộ theo dõi thư mục giải được, không dời mờ."""
        home = str(ROOT.parent)
        rel = ROOT.name
        with mock.patch.dict(os.environ, {"HOME": home}):
            for cmd in (f'cd "$HOME/{rel}" && git pull', f'cd "${{HOME}}/{rel}/docs" && git status && git pull'):
                with self.subTest(cmd=cmd):
                    self.assertEqual(decide(cmd)["decision"], "", decide(cmd).get("reason"))
            self.assertEqual(decide(f'cd "$HOME/{rel}/.." && git pull')["decision"], "deny")
            self.assertEqual(decide(f'HOME=/tmp; cd "$HOME/{rel}" && git pull')["decision"], "deny")


class SignOff5HelperTest(unittest.TestCase):
    """Nhánh của bộ đọc gọi thẳng."""

    def test_glob_word_cut(self):
        cut = guard._glob_word_cut
        self.assertEqual(cut("*.txt", "%", ".txt"), "*")
        self.assertEqual(cut("*.txt", "%", ".md"), "*.txt")
        self.assertEqual(cut("docs/*.md", "#", "docs/"), "*.md")
        self.assertEqual(cut("docs/*.md", "##", "src/"), "docs/*.md")
        self.assertEqual(cut("ab", "%", "abc"), "ab")
        self.assertEqual(cut("abc", "%", ""), "abc")
        self.assertIsNone(cut("*", "%", "x"))
        self.assertIsNone(cut("~/x", "#", "~"))
        self.assertIsNone(cut("a b", "%", "x"))
        self.assertIsNone(cut("*.txt", "%", "*"))

    def test_glob_loop_splices(self):
        cmd = 'for f in *.txt b.txt; do mv "$f" "${f%.txt}.md" ${f%.txt}; done'
        names, variants = guard._glob_loop_splices(cmd, guard._simple_cmds(cmd) or [])
        self.assertEqual(names, {"f"})
        self.assertEqual(
            variants,
            [
                'for f in *.txt b.txt; do mv "$f" ""*".md" *; done',
                'for f in *.txt b.txt; do mv "$f" ""b".md" b; done',
            ],
        )
        self.assertEqual(guard._glob_loop_splices("echo ${f%x}", []), (set(), []))
        bad = "for f in a; do echo 'x"
        self.assertEqual(guard._glob_loop_splices(bad + "${f%x}", [([], ["for", "f", "in", "a"])]), (set(), []))
        many = "for a in 1 2 3 4 5 6 7 8 9; do for b in 1 2 3 4 5 6 7 8; do rm -rf ${a%x}${b%x}; done; done"
        self.assertEqual(guard._glob_loop_splices(many, guard._simple_cmds(many) or []), (set(), []))
        self.assertEqual(decide(many.replace("rm -rf", "echo"))["decision"], "")
        self.assertEqual(decide("for f in a; do echo ${f%x}; done; for f in b; do :; done")["decision"], "")

    def test_sed_slots(self):
        slots = guard._sed_script_slots
        self.assertEqual(slots(["-i", "s/a/b/", "f"]), {1})
        self.assertEqual(slots(["-n", "-e", "x", "--expression", "y", "f"]), {2, 4})
        self.assertEqual(slots(["-f", "s.sed", "f"]), set())
        self.assertEqual(slots(["--file=s.sed", "f"]), set())
        self.assertEqual(slots(["-es/a/b/", "f"]), set())
        self.assertEqual(slots(["-l", "5", "x", "f"]), {2})
        self.assertEqual(slots(["-l5", "x", "f"]), {1})
        self.assertEqual(slots(["--line-length", "5", "--in-place=.b", "x"]), {3})
        self.assertEqual(slots(["--", "-x", "f"]), {1})
        self.assertEqual(slots([">", "out", "s/a/b/"]), {2})
        self.assertEqual(slots(["-", "f"]), {0})
        self.assertEqual(guard._sed_option_value("-ni"), "")
        self.assertEqual(guard._sed_option_value("-nE"), "")

    def test_sed_skeleton(self):
        ok = guard._sed_skeleton_ok
        self.assertTrue(ok("s/a/\x00/g; s|b|c|", "0-"))
        self.assertTrue(ok("$s/a/\x00/\n", "0"))
        self.assertFalse(ok("s/a/\x00/e", "0"))
        self.assertFalse(ok("s/a/\x00/ x", "0"))
        self.assertFalse(ok("s/a/\\\x00/", "0"))
        self.assertFalse(ok("s/a/\x00", "0"))
        self.assertFalse(ok("s/a\nb/\x00/", "0"))
        self.assertFalse(ok("y/a/b/", "0"))

    def test_sed_ctx(self):
        cmd = 'sed "s/x/$(cat VERSION)/" f'
        ctx = guard._SedCtx(cmd, guard._simple_cmds(cmd) or [], str(ROOT), "")
        self.assertIsNone(ctx.value("$(cat VERSION)", 1))
        ctx = guard._SedCtx(cmd, guard._simple_cmds(cmd) or [], str(ROOT), str(ROOT))
        self.assertIsNotNone(ctx.value("$(cat VERSION)", 0))  # T-3942: chỉ số của chính lệnh sed (lệnh trước nó: không)
        self.assertIsNone(ctx.value("$(cat .git)", 1))  # thư mục: lỗi đọc
        self.assertIsNone(ctx.value("$(cat BLUEPRINT.md)", 1))  # nội dung không phải giá trị gọn
        self.assertIsNone(ctx.value("$(echo a)", 1))
        self.assertTrue(ctx.script_ok("s/a/b/", 1))
        self.assertFalse(ctx.script_ok("'s/a/b/'`x`", 1))
        self.assertFalse(ctx.script_ok("\"s/a/${X}/\"'$s/a/b/'", 1))
        self.assertIsNone(ctx._assigned("'a b'", 1))
        self.assertIsNone(ctx._assigned('"$(date +%F)x"', 1))
        cmd = "X[0]=1; sed s/a/$X/ f"
        cmds = guard._simple_cmds(cmd) or []
        self.assertIsNone(guard._SedCtx(cmd, cmds, str(ROOT), str(ROOT))._var("X", 1))
        checked = [("s/a/b/", guard.DD_FULL)]
        ctx = guard._SedCtx("sed", [], str(ROOT), str(ROOT))
        self.assertEqual(ctx.checked(["sed", "s/a/b/", "f"], checked), checked)  # không khớp số từ
        self.assertEqual(ctx.checked(["sed", "x"], [("y", guard.DD_FULL)]), [("y", guard.DD_FULL)])

    def test_date_fmt(self):
        for fmt in ("+%F", "+%Y%m%d", "+%FT%T", "+%s.%N", "+%Y-%m-%d_%H:%M:%S", "+%z"):
            with self.subTest(fmt=fmt):
                self.assertTrue(guard._date_fmt_ok(["date", fmt]))
        for n in (
            ["date", "+%D"],
            ["date", "+.."],
            ["date", "+state%F"],
            ["date", "+12"],
            ["date"],
            ["date", "-d", "x"],
        ):
            with self.subTest(n=n):
                self.assertFalse(guard._date_fmt_ok(n))
        self.assertTrue(guard._date_fmt_ok(["date", "-u", "+%F"]))

    def test_xargs_helpers(self):
        self.assertEqual(guard._xargs_token(["xargs", "-I", "@"]), "@")
        self.assertEqual(guard._xargs_token(["xargs", "-I"]), "{}")
        self.assertEqual(guard._xargs_token(["xargs", "-i"]), "{}")
        self.assertEqual(guard._xargs_token(["xargs", "--replace=%"]), "%")
        self.assertEqual(guard._xargs_token(["xargs", "--replace"]), "{}")
        self.assertIsNone(guard._xargs_token(["xargs", "-n1"]))
        self.assertEqual(guard._xargs_wraps_end(["nice", "-n", "5", "timeout", "5", "mv"]), 5)
        self.assertTrue(guard._xargs_dest("mv", ["x.json"], False))
        self.assertTrue(guard._xargs_dest("cp", [], True))
        self.assertFalse(guard._xargs_dest("cp", ["-t", "d"], False))
        self.assertFalse(guard._xargs_dest("sed", ["-i"], False))
        self.assertEqual(guard._xargs_src_words(" 'a"), [".?"])
        self.assertEqual(guard._xargs_fed("echo 'a b' c | xargs -I@ mv @ d/"), "mv 'a b c' d/")
        self.assertEqual(guard._xargs_fed("printf '%s\\n' \"a b\" c | xargs -I@ mv @ d/"), "mv 'a b' d/; mv c d/")

    def test_cd_scope(self):
        cmd = "cd x"
        scope = guard._CdScope(cmd, guard._simple_cmds(cmd) or [], set(), set(), "")
        self.assertFalse(scope.moves([]))
        self.assertFalse(scope.moves(["ls"]))
        self.assertFalse(scope._home_inside('"$HOME/x"'))  # không biết gốc dự án
        self.assertFalse(scope._home_inside('"$PWD/x"'))
        self.assertFalse(guard._env_dir_moved(["env", "-C", "/tmp", "rm"], ["rm"]))
        self.assertTrue(guard._env_dir_moved(["env", "-C"], []) is False)

    def test_dq_unescaped(self):
        self.assertEqual(guard._dq_unescaped(["rm \\$X", "ls"]), ["rm \\$X", "rm $X", "ls"])

    def test_heredoc_shell_why_branches(self):
        """AUD-SEC-310/392: `_heredoc_shell_why` là lớp phòng thủ cuối của heredoc không nháy vào shell. Các bước quét sớm
        hơn (D-503) nay chặn phần lớn dạng này trước khi tới đây, nên ghim thẳng hàm: thân có mở rộng → lý do; thân
        không mở rộng, heredoc có nháy hay không có shell đọc stdin → rỗng."""
        self.assertIn("AUD-SEC-310", guard._heredoc_shell_why("bash <<EOF\necho $(cat f)\nEOF"))
        self.assertIn("AUD-SEC-310", guard._heredoc_shell_why("sh <<EOF\nrm -rf $X\nEOF"))
        self.assertEqual(guard._heredoc_shell_why("bash <<EOF\necho ok\nEOF"), "")
        self.assertEqual(guard._heredoc_shell_why("bash <<'EOF'\necho $(cat f)\nEOF"), "")
        self.assertEqual(guard._heredoc_shell_why("cat <<EOF\necho $(cat f)\nEOF"), "")


if __name__ == "__main__":
    unittest.main()
