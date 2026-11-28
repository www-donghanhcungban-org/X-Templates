"""D-503 (T-3934): mặc định chặn theo CẤU TRÚC ở lệnh có luật — giá trị guard không tính chắc ở vị trí đích/cờ/lệnh con,
tên lệnh có luật sau trình chạy gói/tên lạ, xargs đưa chữ stdin vào shell/trình bọc thiếu lệnh/lệnh xoá/git → BUDGET.

DENY: mẫu tái hiện bằng bash thật mà guard ở `8fd09a30` cho chạy. ALLOW: dạng lành gần nhất (hồi quy). Bộ sinh có hướng:
lệnh có luật bị chặn ở dạng trơn, thay một từ ở vị trí đích/cờ/lệnh con bằng dạng mở rộng guard không tính chắc → không
bao giờ cho qua."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
import unittest.mock as mock
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
import cpu_budget

os.environ.setdefault("XT_GUARD_PHASE", "harden")
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
import guard

H = chr(126)  # `~` dựng bằng chr: chữ xoá home không nằm nguyên văn trong tệp test
ATTR = "Claude-Session: x"  # dòng ghi công AI (`AI_ATTRIBUTION_RE`)
ATTR_GLUED = "Claude-\"'Session: x'"  # bash ghép "Claude-" và "Session: x" qua hai kiểu nháy


def decide(cmd: str, root: Path = ROOT, cwd: Path | None = None) -> dict:
    with (
        mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(root), "XT_GUARD_POLICY": ""}),
        mock.patch.object(guard, "_current_branch", return_value="feat"),
    ):
        return guard.apply_policy(guard.bash_decision(cmd.replace("@H", H), str(root), str(cwd) if cwd else None))


def cache_cleanup_projects(top: Path) -> tuple[Path, Path]:
    frame, app = top / "frame", top / "app"
    for root, rel in (
        (frame, "framework/00-method/README.md"),
        (frame, "scripts/xt.py"),
        (frame, "scripts/__pycache__/sample.pyc"),
        (app, ".xtemplates/scripts/xt.py"),
        (app, "scripts/__pycache__/sample.pyc"),
    ):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    return frame, app


def assert_cache_cleanup_layouts(
    test: unittest.TestCase, classify: Callable[[str, Path], dict], commands: tuple[str, ...]
) -> None:
    """Giữ ca dọn cache trên app có CLI cài riêng và đối chứng với cache do khung sở hữu."""
    frame, app = cache_cleanup_projects(Path(test.enterContext(tempfile.TemporaryDirectory())))
    for command in commands:
        with test.subTest(command=command):
            allowed, denied = classify(command, app), classify(command, frame)
            test.assertEqual(allowed["decision"], "", allowed)
            test.assertEqual((denied["decision"], denied["code"]), ("deny", guard.BUDGET), denied)


DENY = {
    "a-value": (
        'echo HOME=1; rm -rf "${HOME%/*}"',
        'rm -rf "${HOME%/*}" HOME=1',
        'X=$HOME/x; rm -rf "${X%/x}"',
        'for X in "$HOME"; do rm -rf "${X%/*}"; done',
        "git -c zz.zz=--hard reset ${BASH_COMMAND:13:6}",
        'cd @H; rm -rf "$DIRSTACK"',
        'BASH_ARGV0=@H; rm -rf "$0"',
        'select x in @H; do rm -rf "$x"; break; done <<< 1',
        "printf -v 'd[0]' %s @H; rm -rf \"$d\"",
        ': @H; x[0]=$_; rm -rf "$x"',
        ': @H; cd "$_"; rm -rf zz',
        "f() { d=@H; }; trap 'f;' DEBUG; d=/tmp/x; rm -rf \"$d\"",
        'rm -rf "$(dirname "$PWD")"',
        'rm -rf "$(cd ..; pwd)"',
        'IFS= read -r x < <(echo @H); rm -rf "$x"',
        'read -r X < f.txt; git reset "$X"',
        'read -r X < f.txt; kubectl --insecure-skip-tls-verify "$X" ns prod',
        'X=$(cat f); rm -rf "$X"',
        "X=abc; git reset ${X@E}",
        'true && : @H; rm -rf "$_"',  # lệnh trước `$_` đứng sau `&&`: có thể không chạy
        'true && : @H; cd "$_"; rm -rf zz',  # `cd` vào `$_` không tính được
        'read d; cd "$d"; rm -rf zz',  # `cd` vào biến mờ rồi lệnh có luật (đích tương đối)
        'read -r d < f.txt; cd "$d" && rm -rf build',
        'D=$(cat f); pushd "$D"; rm -rf build',
        'select d in a; do break; done; cd "$d"; git clean -fdx',
        'false && HOME=/x; rm -rf "${HOME%/x}"',  # gán sau `&&`/`||` có thể không chạy: không phải gán chắc
        'false && HOME=/tmp/h; rm -rf "${HOME%/h}/x"',
        '[ -n "$Z" ] && HOME=/tmp/h; rm -rf "${HOME%/h}"',
        'false || X=/tmp/a/x; rm -rf "${X%/x}"',
    ),
    "b-runner": (
        "uv run --with rm git push --force",
        "direnv exec rm git push --force",
        'G=$(echo Z2l0 | base64 -d); uv run "$G" push --force',
        "uvx git-filter-repo --force",
        "uv run python3 -m git_filter_repo --force",
        "uv run dropdb -h db.prod.example.com app",
        "uv run git commit -F - <<'E'\nfix: x\n\n" + ATTR + "\nE",
        "dropdb --ho db.prod.example.com app",
        "dropdb --maintenance-db=postgresql://db.prod.example.com/postgres app",
        "psql --ho db.prod.example.com -c 'DROP TABLE t'",
    ),
    "c-xargs": (
        "printf '@H fr- \\x6dr\\n' | rev | sh",
        "echo @H | xargs --rep=Z rm -rf Z",
        "echo @H | xargs -I{} sh -c 'rm -rf \"$1\"' _ {}",
        "echo rm -rf @H | xargs env",
        "echo rm -rf @H | xargs nice",
        "echo rm -rf @H | xargs timeout 5",
        "echo x | xargs sh",
        "echo --hard | xargs git reset",
        "echo x | xargs shred",
        "git commit -F - <<< $'fix: x\\n\\n'\"" + ATTR_GLUED,
    ),
}

ALLOW = (
    'mkdir -p build/out && cp README.md "$_"',
    'mkdir -p build/out; cp README.md "$_/x"',
    'true && mkdir -p build/out && chmod 755 "$_"',
    'mkdir -p d && cd "$_"',
    'cd "$d" && ls',
    'read d; cd "$d" && ls',
    'mkdir -p x && cd "$_" && rm -rf build',
    "cd build && rm -rf out",
    'X=build/x && rm -rf "${X%/x}"',  # gán ở lệnh đơn đầu: chắc chạy
    'true && X=build/x; rm -rf "${X%/x}"',  # sau `true &&`: chắc chạy
    'cd "${CLAUDE_PROJECT_DIR:-.}" && git status',
    'git -C "${CLAUDE_PROJECT_DIR:-.}" status --short',
    'while IFS= read -r; do git add -- "$REPLY"; done < files.txt',
    'for f in *.txt; do rm "$f"; done',
    'X=build; rm -rf "$X"',
    'X=build/x; rm -rf "${X%/x}"',
    'for X in a/x b/x; do rm -rf "${X%/x}"; done',
    'rm -rf "${BUILD_DIR:?}/out"',
    'rm -rf "${OUT:-build}"',
    'rm -f "$1" "$@"',
    "rm -f build/$((1+2)).txt",
    "git commit -m \"$(cat <<'EOF'\nfix: x\nEOF\n)\"",
    "gh pr create --title 'fix: x' --body \"$(cat <<'EOF'\nbody\nEOF\n)\"",
    'gh pr view "$(git branch --show-current)"',
    "ls | xargs -I{} echo {}",
    "git ls-files | xargs git add",
    'tmp=$(mktemp); echo x > "$tmp"',
    'git push -u origin "$(git branch --show-current)"',
    'rm -rf "$(pwd)"/build',
    'git diff --stat "$(git merge-base HEAD origin/main)" HEAD',
    "d=build; d=$(cat f) true; rm -rf $d",
    "echo a | xargs -n1 sh -c 'echo hi'",
    "uv run pytest",
    'npm test -- -t "git reset --hard"',
    'flock /tmp/l git commit -m "rm -rf @H is bad"',
    "timeout 30 make",
    "git commit -F - <<< 'fix: x'",
    "dropdb app",
    "dropdb --host=localhost app",
)


class DefaultDenyTest(unittest.TestCase):
    def test_deny(self):
        for group, cmds in DENY.items():
            for cmd in cmds:
                with self.subTest(group=group, cmd=cmd):
                    self.assertEqual(decide(cmd)["decision"], "deny")

    def test_allow(self):
        for cmd in ALLOW:
            with self.subTest(cmd=cmd):
                d = decide(cmd)
                self.assertEqual(d["decision"], "", d.get("reason"))

    def test_find_xargs_respects_cache_ownership(self):
        top = Path(self.enterContext(tempfile.TemporaryDirectory()))
        frame, app = cache_cleanup_projects(top)
        installed_cache = app / ".xtemplates/scripts/__pycache__"
        installed_cache.mkdir()
        (installed_cache / "sample.pyc").touch()
        cleanup = "find . -name '*.pyc' | xargs rm -f"
        (app / "scripts/installed-cache").symlink_to(installed_cache, target_is_directory=True)
        self.assertEqual(decide(cleanup, app, app / "scripts")["decision"], "")
        follows_links = cleanup.replace("find .", "find -L .", 1)
        self.assertEqual(decide(follows_links, app, app / "scripts")["code"], guard.BUDGET)
        for root in (frame, app):
            with self.subTest(root=root):
                decision = decide(cleanup, root)
                self.assertEqual((decision["decision"], decision["code"]), ("deny", guard.BUDGET))

    def test_find_cache_options_and_explicit_startpoints(self):
        frame, app = cache_cleanup_projects(Path(self.enterContext(tempfile.TemporaryDirectory())))
        installed_cache = app / ".xtemplates/scripts/__pycache__"
        installed_cache.mkdir()
        (installed_cache / "sample.pyc").touch()
        (app / "scripts/installed-cache").symlink_to(installed_cache, target_is_directory=True)
        for option in ("-P", "-H", "-O2", "-D search", "-D search -O2 -P", "-L -P", "--"):
            with self.subTest(option=option):
                find = f"find {option} scripts -name '*.pyc'"
                self.assertEqual(decide(f"{find} | xargs rm -f", app)["decision"], "")
                self.assertEqual(decide(f"{find} | xargs rm -f", frame)["code"], guard.BUDGET)
        for root, start in ((app, app / "scripts"), (app, installed_cache.parent), (frame, frame / "scripts")):
            with self.subTest(start=start):
                find = f"find -P {start} -path '{start}/*' -name '*.pyc'"
                result = decide(f"{find} | xargs rm -f", root, root / "scripts")
                self.assertEqual(result["decision"], "" if start == app / "scripts" else "deny", result)
        for start in ("-L scripts", "-H scripts/installed-cache"):
            with self.subTest(start=start):
                find = f"find {start} -name '*.pyc'"
                self.assertEqual(decide(f"{find} | xargs rm -f", app)["code"], guard.BUDGET)
                self.assertEqual(decide(f"{find} -delete", app)["code"], "HOOK_BYPASS")

    def test_value_class_is_budget_with_rewrite_hint(self):
        for cmd in (*DENY["a-value"][:10], DENY["b-runner"][2], *DENY["c-xargs"][2:5]):
            with self.subTest(cmd=cmd):
                d = decide(cmd)
                self.assertEqual(d.get("code"), guard.BUDGET, d.get("reason"))
                self.assertIn("viết lại", str(d["reason"]))


# Lệnh có luật bị chặn ở dạng trơn; `W` là từ ở vị trí đích/cờ/lệnh con được thay bằng dạng mở rộng.
FUZZ_SEEDS = (
    "rm -rf W",
    "rm W @H",
    "shred -u W",
    "rmdir W",
    "find W -delete",
    "rsync -a W src/ dst/",
    "git reset W",
    "git W --hard",
    "git push W origin feat",
    "git clean W",
    "git checkout W .",
    "git branch W feat",
    "gh repo delete W --yes",
    "gh pr merge W",
    "gh W delete o/r --yes",
    "dropdb W app",
    "kubectl W ns prod",
    "mkfs.ext4 W",
    "echo x > W",
)
# Dạng mở rộng guard không tính chắc: toán tử trên biến môi trường có luật/biến không gán chữ, biến bash tự gán, gián
# tiếp, thay lệnh/tiến trình, biến gán từ `read`/`select`/`for` không chữ/thay lệnh, toán tử `@E` trên biến chữ.
FUZZ_FORMS = (
    ("", '"${HOME%/*}"'),
    ("", '"${PWD#/}"'),
    ("", '"${HOME:0:5}"'),
    ("", '"${TMPDIR/x/y}"'),
    ("", "${BASH_COMMAND:0:4}"),
    ("", '"$DIRSTACK"'),
    ("", '"$0"'),
    ("", '"$OLDPWD"'),
    ("", '"$-"'),
    ("", '"$_"'),
    ("", '"${!v}"'),
    ("", '"$(echo x)"'),
    ("", "$(cat f)"),
    ("", "<(echo x)"),
    ("", '"$REPLY"'),
    ("read -r X < f; ", '"$X"'),
    ("IFS= read -r X <<< x; ", '"${X%x}"'),
    ("X=$(cat f); ", '"$X"'),
    ("select X in a; do break; done; ", '"$X"'),
    ("for X in $(cat f); do :; done; ", '"$X"'),
    ("X=abc; ", '"${X@E}"'),
    ("Y=$HOME/x; ", '"${Y%/x}"'),
    ("mapfile -t A < f; ", '"$A"'),
)


class DirectedFuzzTest(unittest.TestCase):
    """Bất biến D-503: mọi tổ hợp (lệnh có luật × dạng mở rộng ở vị trí đích/cờ/lệnh con) đều bị chặn."""

    def test_every_form_in_ruled_position_is_denied(self):
        allowed = []
        for seed in FUZZ_SEEDS:
            for prefix, form in FUZZ_FORMS:
                if seed.startswith("echo x >") and form.startswith("<("):
                    continue  # chuyển hướng vào thay tiến trình ghi vào tiến trình, không phải tệp (`exec > >(tee log)`)
                cmd = prefix + seed.replace("W", form)
                if decide(cmd)["decision"] != "deny":
                    allowed.append(cmd)
        self.assertEqual(allowed, [])

    def test_text_flag_values_stay_open(self):
        for _, form in FUZZ_FORMS[11:13]:
            with self.subTest(form=form):
                self.assertEqual(decide(f"git commit -m {form}")["decision"], "")


class DefaultDenyHelperTest(unittest.TestCase):
    """Nhánh của bộ đọc D-503 gọi thẳng."""

    def test_params(self):
        self.assertEqual(guard._dd_params("${#X} ${!v} ${X:-a} '${Y%b}'"), [("X", ""), ("!", ""), ("X", ":-a")])
        self.assertEqual(guard._dd_params("${X"), [("", "")])
        self.assertFalse(guard._dd_op_ok("", "", set()))
        self.assertTrue(guard._dd_op_ok("X", "@U", {"X"}))
        self.assertFalse(guard._dd_op_ok("X", "@Q", {"X"}))
        self.assertTrue(guard._dd_op_ok("OUT", ":?", set()))
        self.assertFalse(guard._dd_op_ok("HOME", ":?", set()))
        self.assertFalse(guard._dd_op_ok("OUT", ":-$Y", set()))

    def test_subst(self):
        self.assertTrue(guard._dd_subst(guard.PROCSUB_WORD))
        self.assertFalse(guard._dd_subst("plain"))
        self.assertFalse(guard._dd_subst("$((1+2))"))
        self.assertFalse(guard._dd_subst("'$(x)'"))
        self.assertTrue(guard._dd_subst('"$(x)"'))
        self.assertTrue(guard._dd_subst("`x`"))

    def test_args(self):
        self.assertEqual(guard._dd_args("git", ["-c", '"$X"', "status"]), ['"$X"'])
        self.assertEqual(guard._dd_args("git", ["-C", '"$X"', "add", '"$Y"']), [])
        self.assertEqual(guard._dd_args("git", ["commit", "-m", '"$(x)"', "--message=$(y)"]), ["commit"])
        self.assertEqual(guard._dd_args("gh", ["pr", "view", '"$(x)"']), [])
        self.assertEqual(guard._dd_args("rm", ["-f", '"$X"']), ["-f", '"$X"'])
        self.assertEqual(guard._git_sub_at(["-C", "d", "--no-pager", "push"]), 3)

    def test_weak_and_lit(self):
        self.assertEqual(guard._weak_seeds(["for", "f", "in", '"$@"']), set())
        self.assertEqual(guard._weak_seeds(["for", "f", "in", '"$x"']), {"f"})
        self.assertEqual(guard._weak_seeds(["select", "f", "in", "a"]), {"f"})
        self.assertEqual(guard._weak_seeds(["IFS=", "read", "-r", "x[1]"]), {"x"})
        self.assertEqual(guard._weak_seeds(["x=$(cat f)", "y=1"]), {"x"})
        self.assertEqual(guard._weak_seeds(["k=$(echo core.hooksPath)"]), set())  # gán chữ được nâng, quét lại
        self.assertEqual(guard._weak_seeds(["k=$(printf '\\x2d')"]), {"k"})
        self.assertEqual(guard._weak_seeds([]), set())
        cmds = guard._simple_cmds("X=a; then Y=b; echo $Z; Z=c; for W in a b; do :; done; V=$X")
        assert cmds is not None
        self.assertEqual(guard._lit_names(cmds, "X=a"), {"X", "W"})
        self.assertEqual(guard._lit_names(cmds, "f() { :; }"), set())
        self.assertEqual(guard._lit_assigns(["for", "W", "in", "*.txt"], ["for", "W", "in", "*.txt"]), set())

    def test_last_arg_splice(self):
        self.assertEqual(guard._last_arg_splice('mkdir -p d && cp f "$_"'), "mkdir -p d && cp f d")
        self.assertEqual(guard._last_arg_splice(': @H; rm "$_"'.replace("@H", H)), ": " + H + "; rm " + H)
        self.assertEqual(guard._last_arg_splice('mkdir d; cp f "${_}/x"'), 'mkdir d; cp f "d/x"')
        self.assertEqual(guard._last_arg_splice("touch 'a b'; rm \"$_\""), "touch 'a b'; rm 'a b'")
        for cmd in (
            'rm "$_"',
            'echo a | cat; rm "$_"',
            'echo $(x); rm "$_"',
            'echo *.txt; rm "$_"',
            'touch "a b"; rm "$_/x"',
            "X=1; rm $_",
            'for x in a; do rm "$_"; done',
            "echo a",
            "touch 'a'; rm x$_",
            "echo a &",
        ):
            with self.subTest(cmd=cmd):
                self.assertIsNone(guard._last_arg_splice(cmd))

    def test_xargs_and_runner(self):
        self.assertIsNone(guard._xargs_rest(["env"], ["env", "rm"]))
        self.assertEqual(
            guard._xargs_rest(["xargs"], ["xargs", "-n", "1", "-I", "{}", "--rep=Z", "rm", "Z"]), ["rm", "Z"]
        )
        self.assertFalse(guard._xargs_bad([]))
        self.assertTrue(guard._xargs_bad(["env", "-i", "X=1"]))
        self.assertTrue(guard._xargs_bad(["bash", "-c"]))
        self.assertTrue(guard._xargs_bad(["git"]))
        self.assertTrue(guard._xargs_bad(['"$C"']))
        self.assertFalse(guard._xargs_bad(["rm", "-f"], listed=True))
        self.assertTrue(guard._xargs_bad(["rm", "-f"]))  # T-3937: stdin không từ lệnh liệt kê (`printf … | xargs rm`)
        self.assertFalse(guard._xargs_bad(["gh", "pr", "view"]))
        self.assertTrue(guard._xargs_bad(["gh", "pr", "close"]))
        self.assertEqual(guard._runner_dyn_why("uv run pytest"), "")
        self.assertEqual(guard._runner_dyn_why("uv run --"), "")
        self.assertIn("D-503", guard._runner_dyn_why('nix develop -c "$G" push'))
        self.assertEqual(guard._runner_tails(["mytool", "rm", "git", "push"]), [["rm", "git", "push"], ["git", "push"]])
        self.assertEqual(guard._runner_tails(["git", "push"]), [])

    def test_cond_segs(self):
        def cond(cmd: str) -> set:
            return guard._cond_segs(cmd, guard._simple_cmds(cmd) or [])

        self.assertEqual(cond("a; b"), set())
        self.assertEqual(cond("true && X=1; false || Y=2; c && Z=3; d"), {3, 5})
        self.assertEqual(cond("a | b && X=1"), {1, 2})
        self.assertEqual(cond("true && X=a; git push origin ${X/a}"), set())
        self.assertEqual(cond("echo `x` && X=1"), {1})

    def test_func_names(self):
        self.assertEqual(guard._func_names("function g { :; }; f() { :; }; ( ) x"), {"g", "f"})
        self.assertEqual(
            guard._dd_args("gh", ["pr", "merge", "7", "--match-head-commit", '"$(x)"']), ["pr", "merge", "7"]
        )

    def test_destroy_hosts(self):
        self.assertEqual(
            guard._long_abbrevs(["--ho=h", "--", "--x", "-h"], ("-h", "--host")), ["--host=h", "--", "--x", "-h"]
        )
        self.assertEqual(guard._destroy_hosts(("-h", "--host"), ["--ho", "h1", "host=h2"]), ["h1", "h2"])


class DefaultDenyTimeTest(unittest.TestCase):
    """Phần mới tuyến tính theo số lệnh đơn/số `$_`/số từ."""

    def test_value_gate_not_quadratic(self):
        def work(n: int) -> None:
            guard._opaque_value_why("; ".join(f'X{i}=a; read Y{i}; rm -rf "${{X{i}%a}}" "$Y{i}"' for i in range(n)))

        cpu_budget.assert_not_quadratic(self, work, 40)

    def test_last_arg_not_quadratic(self):
        def work(n: int) -> None:
            guard._last_arg_splice("; ".join(f'mkdir d{i} && cp f "$_"' for i in range(n)))

        cpu_budget.assert_not_quadratic(self, work, 40)

    def test_xargs_runner_not_quadratic(self):
        def work(n: int) -> None:
            cmd = "; ".join(f"echo x | xargs -n 1 nice rm -f a{i} && uv run --with rm a{i} pytest" for i in range(n))
            guard._xargs_why(cmd)
            guard._runner_dyn_why(cmd)

        cpu_budget.assert_not_quadratic(self, work, 40)


if __name__ == "__main__":
    unittest.main()
