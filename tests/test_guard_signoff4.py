"""D-503 (T-3937): phát hiện cổng ký lần 4 — `cd`/`pushd` vào thay lệnh chưa tính được rồi lệnh có luật với đích tương
đối (🔴), hồi quy chặn oan (thân commit ở cụm cờ `-am`, `${TMPDIR:-/tmp}`, `cd` vào giá trị mờ không kèm lệnh có luật,
lệnh chỉ đọc `find`/`gh api` GET).

DENY: mẫu tái hiện mà guard ở `61375e6a` cho chạy (hay ca gần nhất phải vẫn chặn). ALLOW: dạng lành guard cũ chặn oan."""

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
ATTR = "Claude-Session: x"  # dòng ghi công AI (`AI_ATTRIBUTION_RE`)
HEREDOC_BODY = "\"$(cat <<'EOF'\nfix: x\nEOF\n)\""


def decide(cmd: str, root: Path = ROOT) -> dict:
    with (
        mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(root), "XT_GUARD_POLICY": ""}),
        mock.patch.object(guard, "_current_branch", return_value="feat"),
    ):
        return guard.apply_policy(guard.bash_decision(cmd.replace("@H", H), str(root)))


BUDGET_CASES = (
    # 1. `cd` vào thay lệnh chưa tính được, rồi lệnh có luật với đích tương đối
    'cd "$(echo @H)" && rm -rf zz',
    'cd "$(dirname "$PWD")" && rm -rf zz',
    'cd "$(cd ..; pwd)" && rm -rf zz',
    'cd "$(git rev-parse --show-toplevel)/.." && rm -rf zz',
    'pushd "$(echo @H)" && rm -rf zz',
    'cd "$(echo @H)"; ls; rm -rf zz',
    'cd "${HOME%/*}" && rm -rf zz',
    'cd "$OLDPWD" && rm -rf zz',
    'cd "$(git -C /x rev-parse --show-toplevel)" && rm -rf zz',
    'X=abc; cd "${X@E}" && rm -rf zz',
)

DENY = (
    # 2. cụm cờ chỉ nhận khi các chữ trước `m` là cờ bool của `git commit` (`-C m` lấy giá trị `m`); `-m` chỉ là cờ chữ ở
    # lệnh con nhận thông điệp (`checkout -m`/`branch -m` là cờ bool — từ sau là đích)
    'git commit -Cm "$(cat f)"',
    'git commit -um "$(cat f)"',
    'git push -m "$(cat f)" origin feat',
    'git checkout -m "$(cat f)"',
    'git branch -m "$(cat f)" main',
    # 3. mặc định của TMPDIR phải là chữ tuyệt đối dưới /tmp, /var/tmp
    'rm -rf "${TMPDIR:-/tmp/../home}"',
    'rm -rf "${TMPDIR:-$HOME}/x"',
    'rm -rf "${TMPDIR:-/etc}/x"',
    'rm -rf "${TMPDIR:-tmp}/x"',
    'rm -rf "${TMPDIR:=/tmp}/x"',
    'rm -rf "${HOME:-/tmp}/x"',
    'rm -rf "${PWD:?}/x"',
    # 4a. `$_` ghép biến cho phép chỉ khi lệnh trước không gán
    'HOME=/tmp/h : "$HOME/zz"; rm -rf "$_"',
    'mkdir -p "$X/y" && cd "$_" && rm -rf zz',
    # 4c. find có hành động, gh api ghi
    'find "$(cat f)" -delete',
    'find "$(cat f)" -exec rm {} +',
    'find "$(cat f)" -fprint out',
    'find . -execdir rm "$(cat f)" ;',
    'gh api -X DELETE "repos/o/r/$(cat f)"',
    'gh api -XPUT "repos/o/r/$(cat f)"',
    'gh api --method=PATCH "repos/o/r/$(cat f)"',
    'gh api --method "$M" "repos/o/r/$(cat f)"',
    'gh api "repos/o/r/$(cat f)" -f x=1',
    'gh api "repos/o/r/$(cat f)" --raw-field x=1',
    'gh api --input f "repos/o/r/$(cat f)"',
    'gh api -iXPOST "repos/o/r/$(cat f)"',
    # 4c. từ có mở rộng không neo chữ ở lệnh chỉ đọc có thể thành vị từ/cờ ghi
    'find "$(cat f)" -name x -print',
    'find . "$(echo -delete)"',
    "find $(cat f)/docs -name x",
    'gh api "$(echo -XDELETE)" repos/o/r',
    # bổ sung fuzz bất biến: biến gán ngoài mô hình, tham số vị trí, trình chạy, xargs, lệnh ghi
    'eval X=@H; rm -rf "$X"',
    'eval "$(cat f)"; rm -rf "$X"',
    'source f.env; rm -rf "$DIR"',
    ': ${X:=@H}; rm -rf "$X"',
    'X=build; : "${X:=@H}"; rm -rf "$X"',
    'X=(-rf); rm "$X" zz',
    'X[0]=@H; rm -rf "$X"',
    'Z=${HOME%/}; rm -rf "$Z"',
    'X=zq-rf; Z=${X: -3}; rm "$Z" zz',
    'X=@H :; rm -rf "$X"',
    'unset HOME; rm -rf "$HOME/x"',
    'set -- @H; rm -rf "$1"',
    'set -- @H; rm -rf "$@"',
    "bash -c 'rm -rf \"$1\"' _ @H",
    "bash -c 'rm \"$1\" @H' _ -rf",
    "bash -c 'rm -rf \"${1%x}\"' _ ax",
    "bash -c 'shift; rm -rf \"$1\"' _ a @H",
    "bash -c 'rm -rf $1' _ \"$(cat f)\"",
    'read T; bash -c \'rm -rf "$1"\' _ "$T"',
    "timeout 5 sh -c 'rm -rf \"$0\"' @H",
    'uv run rm "$(echo -rf)" @H',
    'uv run --with zq "$(echo git)" push --force origin main',
    'direnv exec . "$(echo gh)" pr merge 5 --admin --squash',
    'nix develop -c "$(echo rm)" -rf @H',
    'uv run "$@"',
    "printf '%s\\n' -rf | xargs -I{} rm {} @H",
    "echo -rf | xargs rm @H",
    "printf '%s\\n' .claude/settings.json | xargs mv x.json",
    "cat list | xargs sed -i s/a/b/",
    "printf '%s\\n' .claude/settings.json | xargs rm",
    "printf '%s\\n' .claude/settings.json | xargs -I{} rm {}",
    'tee "$(echo .claude/settings.json)" < /dev/null',
    'timeout 5 cp /dev/null "$(echo .autopilot/state.json)"',
    'uv run tee "$(echo .claude/settings.json)" < /dev/null',
    'cp /tmp/x "$(echo)"notes.txt',
)

ALLOW = (
    'cd "$(git rev-parse --show-toplevel)" && rm -rf build',
    "cd $(git rev-parse --show-toplevel) && git clean -n",
    "git commit -am " + HEREDOC_BODY,
    'git commit -qm "$(cat msg.txt)"',
    'git commit -sm "$(cat msg.txt)"',
    'git commit -asm "$(cat msg.txt)"',
    'git add -A && git commit -am "$(cat msg.txt)"',
    'git tag -m "$(cat msg.txt)" v1',
    'git merge --message "$(cat msg.txt)" feat',
    'rm -rf "${TMPDIR:-/tmp}/xt-build"',
    'rm -rf "${TMPDIR-/tmp}/x"',
    'rm -rf "${TMPDIR:?}/xt-build"',
    'rm -rf "${TMPDIR:-/tmp}"/xt-*',
    'rm -rf "${TMPDIR:-/var/tmp/xt}/a"',
    'rm -rf "${TMPDIR:?TMPDIR chưa đặt}/xt"',
    'cd "$OLDPWD" && ls',
    'pushd "$OLDPWD"',
    'cd "$(dirname "$0")" && ls',
    'DIR="$(cd "$(dirname "$0")" && pwd)"; echo "$DIR"',
    'cd "$(echo @H)" && git status',
    'mkdir -p "$TMPDIR/xt" && cd "$_" && ls',
    'mkdir -p "$TMPDIR/xt" && cd "$_" && rm -rf build',
    'mkdir -p "${TMPDIR}/xt" && rm -rf "$_"',
    "find \"$(git rev-parse --show-toplevel)/docs\" -name '*.md'",
    'gh api "repos/{owner}/{repo}/commits/$(git rev-parse HEAD)/check-runs"',
    'gh api -X GET "repos/o/r/$(cat f)" --paginate',
    'gh api --method=get "repos/o/r/$(cat f)"',
    # bổ sung: dạng lành gần nhất của các gốc fuzz
    "bash -c 'echo \"$1\"' _ hello",
    'bash -c \'printf "%s\\n" "$@"\' _ a b',
    'TMP=$(mktemp -d); bash -c \'cd "$1"\' _ "$TMP"',
    'uv run --frozen pytest -k "$K"',
    "uv run -- python3 -c 'print(1)'",
    "find docs -name '*.md' | xargs sed -i s/a/b/",
    "ls | xargs -I{} rm -f {}",
    "XT=1 git ls-files -z src | xargs -0 rm -f",  # T-3942: `git ls-files` trần liệt kê tệp hàng rào → BUDGET
    'a=(status); git "${a[*]}"',
    'X=build; rm -rf "$X"',
    "d=build; d=$(cat f) true; rm -rf $d",
    'git log --oneline "$(git merge-base HEAD origin/main)"..HEAD',
)


class SignOff4DenyTest(unittest.TestCase):
    def test_budget(self):
        for cmd in BUDGET_CASES:
            with self.subTest(cmd=cmd):
                d = decide(cmd)
                self.assertEqual((d["decision"], d.get("code")), ("deny", guard.BUDGET), d.get("reason"))

    def test_deny(self):
        for cmd in DENY:
            with self.subTest(cmd=cmd):
                self.assertEqual(decide(cmd)["decision"], "deny")

    def test_attribution_still_applies_to_cluster_body(self):
        for flag in ("-am", "-sm", "-m"):
            with self.subTest(flag=flag):
                body = "\"$(cat <<'EOF'\nfix: x\n\n" + ATTR + '\nEOF\n)"'
                self.assertEqual(decide(f"git commit {flag} {body}")["decision"], "deny")


class SignOff4AllowTest(unittest.TestCase):
    def test_allow(self):
        for cmd in ALLOW:
            with self.subTest(cmd=cmd):
                d = decide(cmd)
                self.assertEqual(d["decision"], "", d.get("reason"))

    def test_cache_cleanup(self):
        assert_cache_cleanup_layouts(self, decide, ("find . -name '*.pyc' | xargs rm -f",))

    def test_xargs_hint_lists_targets(self):
        reason = str(decide("echo a | xargs sh -c 'echo \"$1\"' _")["reason"])
        self.assertIn("liệt kê đích nguyên văn", reason)
        self.assertNotIn("while", reason)


class SignOff4HelperTest(unittest.TestCase):
    """Nhánh của bộ đọc gọi thẳng."""

    def test_text_values(self):
        self.assertEqual(guard._dd_args("git", ["commit", "-asm", '"$(x)"', "-m$(y)"]), ["commit"])
        self.assertEqual(guard._dd_args("git", ["merge", "--message=$(x)", "-m$(y)", "feat"]), ["merge", "feat"])
        self.assertEqual(guard._dd_args("git", ["commit", "-Cm", '"$(x)"']), ["commit", "-Cm", '"$(x)"'])
        self.assertEqual(guard._dd_args("git", ["tag", "-am", '"$(x)"']), ["tag", "-am", '"$(x)"'])
        self.assertEqual(guard._dd_args("git", ["-am"]), ["-am"])
        self.assertEqual(guard._dd_args("gh", ["pr", "create", "-b", '"$(x)"']), ["pr", "create"])

    def test_tmpdir_default(self):
        self.assertTrue(guard._dd_op_ok("TMPDIR", ":-/tmp", set()))
        self.assertTrue(guard._dd_op_ok("TMPDIR", "-/var/tmp/a.b", set()))
        self.assertTrue(guard._dd_op_ok("TMPDIR", "?", set()))
        self.assertFalse(guard._dd_op_ok("TMPDIR", ":-/tmpx", set()))
        self.assertFalse(guard._dd_op_ok("TMPDIR", ":-/tmp/./..", set()))
        self.assertFalse(guard._dd_op_ok("TMPDIR", "%/*", set()))

    def test_cd_moves(self):
        self.assertFalse(guard._cd_moved('"$(git rev-parse --show-toplevel)"', set(), set()))
        self.assertFalse(guard._cd_moved("build", set(), set()))
        self.assertTrue(guard._cd_moved('"$(git rev-parse --show-toplevel)/.."', set(), set()))
        self.assertTrue(guard._cd_moved('"$d"', {"d"}, set()))
        self.assertTrue(guard._cd_moved('"${HOME%/*}"', set(), set()))

    def test_cd_home_pwd_resolved(self):
        """Quyết định phiên chính (T-3937): `cd "$HOME"`/`"$PWD/.."`/`"$(pwd)/.."` giải như `cd ~`/`cd ..`."""
        for cmd in ('cd "$HOME" && rm -rf zz', 'cd "$PWD/.." && rm -rf zz', 'cd "$(pwd)/.." && rm -rf zz'):
            with self.subTest(cmd=cmd):
                self.assertEqual(decide(cmd)["decision"], "deny")
        for cmd in ('d=build; cd "$d" && rm -rf out', 'cd "$PWD/build" && rm -rf out', 'cd "$HOME" && ls'):
            with self.subTest(cmd=cmd):
                self.assertEqual(decide(cmd)["decision"], "")
        flags = guard._CwdFlags()
        self.assertEqual(guard._cd_vars(["cd", "$PWD/x"], None, flags), ["cd", "$PWD/x"])
        flags.see(["PWD=/"])
        self.assertEqual(guard._cd_vars(["cd", "$PWD"], "/a", flags), ["cd", "$PWD"])
        self.assertEqual(guard._cd_vars(["cd", "${HOME}/x"], "/a", flags), ["cd", "~/x"])
        self.assertEqual(guard._cd_vars([], "/a", flags), [])

    def test_wrapped_forms_denied(self):
        """Dạng bọc của `tests.test_guard_fuzz` (`X && …`, `…;`, `bash -c`, `$(…)`, `env`/`command`)."""
        for core in ('cd "$PWD/.." && rm -rf zz', 'cd "$(pwd)/.." && rm -rf zz', 'cd "$HOME" && rm -rf zz'):
            for wrap in ("true && {}", "true; {}", "bash -c '{}'", 'echo "$({}\n)"'):
                with self.subTest(cmd=wrap.format(core)):
                    self.assertEqual(decide(wrap.format(core))["decision"], "deny")
        feed = "echo .claude/settings.json | xargs mv x.json"
        for wrap in ("true && {}", "true; {}", "XT_FUZZ=1 {}", "command {}", "nice -n 5 {}", "timeout 60 {}"):
            with self.subTest(cmd=wrap.format(feed)):
                self.assertEqual(decide(wrap.format(feed))["decision"], "deny")
        self.assertEqual(guard._xargs_fed_all("true && echo a | xargs rm; echo b | xargs mv x"), ["rm a", "mv x b"])
        self.assertTrue(guard._cd_leaves_project('"${HOME}/x"'))
        self.assertTrue(guard._cd_leaves_project('"$(pwd)/.."'))
        self.assertFalse(guard._cd_leaves_project('"$PWD/build"'))
        self.assertFalse(guard._cd_leaves_project("build"))

    def test_xargs_literal_feed_rescanned(self):
        """Quyết định phiên chính (T-3937): nguồn chữ trơn của xargs nối vào argv rồi quét như lệnh trơn."""
        for cmd in ("echo .claude/settings.json | xargs mv x.json", "ls .claude/settings.json | xargs sed -i s/a/b/"):
            with self.subTest(cmd=cmd):
                self.assertEqual(decide(cmd)["decision"], "deny")
        for cmd in ("echo docs/autopilot/PLAN-a.md | xargs -I{} cp {} /tmp/", "ls docs/a.md | xargs sed -i s/a/b/"):
            with self.subTest(cmd=cmd):
                self.assertEqual(decide(cmd)["decision"], "")
        self.assertEqual(guard._xargs_fed("printf '%s\\n' a b | xargs -I{} cp {} d/"), "cp a d/; cp b d/")
        self.assertIsNone(guard._xargs_fed("echo a | xargs"))
        self.assertIsNone(guard._xargs_fed("echo origin/main | xargs git tag"))  # git: luật riêng giữ nguyên
        self.assertIsNone(guard._xargs_fed("echo $X | xargs rm"))

    def test_runner_name(self):
        self.assertFalse(guard._runner_name_dyn("uv", ["run", "--frozen"]))
        self.assertTrue(guard._runner_name_dyn("direnv", ["exec", ".", '"$C"']))
        self.assertFalse(guard._runner_name_dyn("nix", ["develop", "-c", "pytest", '"$K"']))
        self.assertTrue(guard._dd_op_ok("f", "%.txt", {guard.GLOB_MARK + "f"}))
        self.assertFalse(guard._dd_op_ok("f", "/.txt/.bak", {guard.GLOB_MARK + "f"}))

    def test_read_only_levels(self):
        self.assertEqual(guard._dd_level("find", ["d", "-name", "x"]), guard.DD_BASIC)
        self.assertEqual(guard._dd_level("find", ["d", "-okdir", "x"]), guard.DD_FULL)
        self.assertEqual(guard._dd_level("gh", ["api", "x", "-Fa=1"]), guard.DD_FULL)
        self.assertEqual(guard._dd_level("gh", ["api", "x", "-X", "get"]), guard.DD_BASIC)
        self.assertEqual(guard._dd_level("gh", ["api", "x", "-X"]), guard.DD_FULL)
        self.assertEqual(guard._dd_level("gh", ["pr", "close"]), guard.DD_FULL)
        self.assertEqual(guard._dd_level("git", ["log"]), guard.DD_BASIC)
        self.assertEqual(guard._dd_level("make", []), guard.DD_BASIC)
        self.assertIsNone(guard._dd_level("ls", []))

    def test_last_arg_allowed_vars(self):
        self.assertEqual(
            guard._last_arg_splice('mkdir -p "$TMPDIR/xt" && cd "$_"'), 'mkdir -p "$TMPDIR/xt" && cd "$TMPDIR/xt"'
        )
        for cmd in (
            'mkdir "$X/y"; cd "$_"',
            'X=1 mkdir "$TMPDIR/y"; cd "$_"',
            'export "$TMPDIR/y"; cd "$_"',
            'mkdir "$TMPDIR/y"; cd $_/z',
            'mkdir "${TMPDIR%/}/y"; cd "$_"',
        ):
            with self.subTest(cmd=cmd):
                self.assertIsNone(guard._last_arg_splice(cmd))


if __name__ == "__main__":
    unittest.main()
