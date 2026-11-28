"""AUD-SEC-999: kiểm theo thuộc tính cho lớp "tải giấu trong biến" của `gh release` — oracle độc lập với mã guard.

Sinh lệnh `gh …` từ khuôn có `$X`/glob KHÔNG nháy ở mọi vị trí (vùng cờ trước tên lệnh, giữa `release` và lệnh con,
giá trị cờ — tách, dính, `=`, cụm ngắn —, sau cờ bool, đối số vị trí, sau tag, sau `--`). Oracle mô phỏng bash (thay
`$X` bằng tải rồi tách theo khoảng trắng; glob coi như bung ra đúng các từ của tải — kẻ tấn công đặt tên tệp), rồi đọc
argv như cobra (`stripFlags`/`argsMinusFirstX`) + pflag với bảng cờ của gh 2.95 (`gh release create|edit --help`).
NGUY HIỂM = lệnh thật là `release create|new <vX.Y.Z…>`, hay `release edit` có `--tag <vX.Y.Z…>` hoặc phát hành bản
nháp (`--draft` false) của release `<vX.Y.Z…>`. Thuộc tính: khuôn nào có một tải làm nó NGUY HIỂM thì guard chặn (deny
thô ⇒ deny ở mọi chính sách); lệnh chữ (đã thay tải, không còn `$`/glob) AN TOÀN thì guard không chặn vì tag phiên bản,
NGUY HIỂM thì guard chặn."""

from __future__ import annotations

import os
import re
import sys
import tempfile
import unittest
import unittest.mock as mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nonet import HOOKS, isolate_network

sys.path.insert(0, str(HOOKS))
import guard

VERSION = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.+-]*)?")  # F-144: vX.Y.Z kèm hậu tố SemVer
PFLAG_FALSE = {"0", "f", "F", "false", "FALSE", "False"}  # strconv.ParseBool
REPO = {"-R", "--repo"}  # cờ bền của nhóm `release`/`pr`… (ăn giá trị)
# gh 2.95 `gh release create --help` / `gh release edit --help`
CREATE_VALUED = {"-t", "--title", "-n", "--notes", "-F", "--notes-file", "--target", "--discussion-category"}
CREATE_VALUED |= {"--notes-start-tag"} | REPO
CREATE_BOOL = {
    "-d",
    "--draft",
    "-p",
    "--prerelease",
    "--generate-notes",
    "--latest",
    "--verify-tag",
    "--notes-from-tag",
}
CREATE_BOOL |= {"--fail-on-no-commits", "-h", "--help"}
EDIT_VALUED = {
    "-t",
    "--title",
    "-n",
    "--notes",
    "-F",
    "--notes-file",
    "--target",
    "--discussion-category",
    "--tag",
} | REPO
EDIT_BOOL = {"--draft", "--latest", "--prerelease", "--verify-tag", "-h", "--help"}
ALIAS = {"-t": "--title", "-n": "--notes", "-F": "--notes-file", "-R": "--repo", "-d": "--draft", "-p": "--prerelease"}
SUBS = {"create", "new", "edit", "upload", "view", "list", "delete", "download"}
TREE: dict[str, set[str] | None] = {"release": SUBS, "pr": {"list", "merge", "view"}, "api": None, "status": None}

PAYLOADS = (
    "v1.2.3",
    "x --tag v1.2.3",
    " release create v1.2.3 -n",
    ".2.3 release create -n",
    ".2.3 create -n",
    "--verify-tag=false --tag v1.2.3",
    "--draft=false",
    "o/r release create v1.2.3",
    " --tag v1.2.3",
    "foo",
    "",
)
ZONES = ("-R $X", "-R o$X", "--repo=$X", "--repo $X", "--hostname $X", "--notes-start-tag o$X", "--latest v1$X")
ZONES += ("-p v1$X", "--prerelease $X", "-R *")
TAILS = ("release create nightly", "release edit nightly", "release view v1", "status", "pr list", "api repos/o/r")
SPOTS = (
    "release -R $X create nightly",
    "release --latest v1$X view",
    "release -p v1$X list",
    "release $X",
    "release cre* nightly",
    "release create $X",
    "release create nightly -t $X",
    "release create nightly -t$X",
    "release create nightly --title=$X",
    "release create nightly -pt $X",
    "release create -n -- $X",
    "release create -n --end-of-options $X",
    "release create nightly --latest $X",
    "release create nightly -p $X",
    "release create nightly $X",
    "release create nightly -- $X",
    "release create -t $X nightly",
    "release create --notes-start-tag $X nightly",
    "release create -p $X",
    "release create -t v1.2.? nightly",
    "release create nightly dist/*",
    "release new -n $X",
    "release new nightly -- $X",
    "release edit nightly -t $X",
    "release edit nightly --latest $X",
    "release edit nightly --verify-tag $X",
    "release edit $X",
    "release edit nightly $X",
    "release edit nightly --tag=$X",
    "release edit nightly -n -- $X",
    "release edit nightly --draft $X",
    "release edit nightly dist/*",
    "release edit -t v1.2.? nightly",
    "release upload nightly dist/*",
)


def templates() -> list[str]:
    return [f"gh {z} {t}" for z in ZONES for t in TAILS] + [f"gh {s}" for s in SPOTS]


def expand(template: str, payload: str) -> list[str]:
    """argv sau khi bash mở rộng (khuôn không có nháy): `$X` → tải rồi tách từ; từ có glob → các từ của tải (không
    khớp gì thì giữ nguyên như bash mặc định)."""
    out: list[str] = []
    for tok in template.split():
        if "$X" in tok:
            out += tok.replace("$X", payload).split()
        elif re.search(r"[*?\[]", tok):
            out += payload.split() or [tok]
        else:
            out.append(tok)
    return out


def _flag_eats(s: str) -> bool:
    """cobra `stripFlags`/`argsMinusFirstX`: cờ không `=`, không phải bool đã biết (`--help`, `-h`) nuốt từ kế."""
    if "=" in s or s in ("--help", "-h"):
        return False
    return s[:2] == "--" or s[:1] == "-" and len(s) == 2


def strip_flags(args: list[str]) -> list[str]:
    names, i = [], 0
    while i < len(args):
        s, i = args[i], i + 1
        if s == "--":
            break
        if _flag_eats(s):
            if len(args) - i <= 1:  # cobra: `len(args) <= 1` → dừng
                break
            i += 1
        elif s and s[:1] != "-":
            names.append(s)
    return names


def minus_first(args: list[str], x: str) -> list[str]:
    pos = 0
    while pos < len(args):
        s = args[pos]
        if s == "--":
            break
        if _flag_eats(s):
            pos += 2
            continue
        if s[:1] != "-" and s == x:
            return args[:pos] + args[pos + 1 :]
        pos += 1
    return args


def find(args: list[str]) -> tuple[list[str], list[str]]:
    """(đường lệnh cobra chọn, đối số còn lại); tên lạ → đường dừng ở đó (cobra báo lỗi lệnh lạ)."""
    path: list[str] = []
    node: dict[str, set[str] | None] | set[str] | None = TREE
    while node:
        names = strip_flags(args)
        if not names or names[0] not in node:
            break
        path.append(names[0])
        args = minus_first(args, names[0])
        node = TREE.get(names[0]) if len(path) == 1 else None
    return path, args


def pflag(args: list[str], valued: set[str], bools: set[str]) -> tuple[dict[str, str], list[str]] | None:
    """(cờ → giá trị cuối, đối số vị trí) như pflag; lỗi (cờ lạ, thiếu giá trị) → None."""
    flags: dict[str, str] = {}
    pos: list[str] = []
    i: int | None = 0
    while i is not None and i < len(args):
        a, i = args[i], i + 1
        if a == "--":
            return flags, pos + args[i:]
        if a[:2] == "--" and len(a) > 2:
            i = _long_flag(a, args, i, valued, bools, flags)
        elif a[:1] == "-" and len(a) > 1:
            i = _short_flags(a[1:], args, i, valued, bools, flags)
        else:
            pos.append(a)
    return None if i is None else (flags, pos)


def _long_flag(a: str, args: list[str], i: int, valued: set[str], bools: set[str], flags: dict[str, str]) -> int | None:
    """`--cờ[=giá trị]`: cờ ăn giá trị không `=` nuốt từ kế (kể cả `-…`); vị trí kế, hay None khi lỗi."""
    key, eq, v = a.partition("=")
    if key not in valued | bools or key in valued and not eq and i >= len(args):
        return None
    if key in valued and not eq:
        v, i = args[i], i + 1
    flags[key] = v if eq or key in valued else "true"
    return i


def _short_flags(
    s: str, args: list[str], i: int, valued: set[str], bools: set[str], flags: dict[str, str]
) -> int | None:
    """Cụm cờ ngắn như `parseSingleShortArg` của pflag: `-f=v`, bool đi tiếp, `-fv`, `-f v`."""
    while s:
        key = "-" + s[0]
        if key not in valued | bools:
            return None
        if len(s) > 2 and s[1] == "=":
            v, s = s[2:], ""
        elif key in bools:
            v, s = "true", s[1:]
        elif len(s) > 1:
            v, s = s[1:], ""
        elif i < len(args):
            v, s, i = args[i], "", i + 1
        else:
            return None
        flags[ALIAS.get(key, key)] = v
    return i


def dangerous(argv: list[str]) -> bool:
    path, rest = find(argv[1:])  # bỏ `gh`
    if path in (["release", "create"], ["release", "new"]):
        parsed = pflag(rest, CREATE_VALUED, CREATE_BOOL)
        return parsed is not None and bool(parsed[1]) and bool(VERSION.fullmatch(parsed[1][0]))
    if path != ["release", "edit"]:
        return False
    parsed = pflag(rest, EDIT_VALUED, EDIT_BOOL)
    if parsed is None or len(parsed[1]) != 1:  # `edit` nhận đúng một đối số
        return False
    flags, pos = parsed
    publish = flags.get("--draft") in PFLAG_FALSE and bool(VERSION.fullmatch(pos[0]))
    return publish or bool(VERSION.fullmatch(flags.get("--tag", "")))


class ReleaseOracleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.guard = guard

    def setUp(self) -> None:
        isolate_network(self, None, self.guard)
        self.root = self.enterContext(tempfile.TemporaryDirectory())
        self.seen: dict[str, dict[str, object]] = {}

    def decide(self, cmd: str) -> dict[str, object]:
        if cmd not in self.seen:
            self.seen[cmd] = self.guard.bash_decision(cmd, self.root)
        return self.seen[cmd]

    def test_oracle_matches_known_cases(self) -> None:
        """Oracle khớp các ca đã chạy thật với gh 2.95 (reviewer) và ca vô hại."""
        self.assertTrue(dangerous("gh --notes-start-tag o release create v1.2.3 -n status".split()))
        self.assertTrue(dangerous("gh -p v1.2.3 release create -n status".split()))
        self.assertTrue(dangerous("gh release --latest v1.2.3 create -n view".split()))
        self.assertTrue(dangerous("gh release edit nightly --latest --tag v1.2.3".split()))
        self.assertTrue(dangerous("gh release edit v1.2.3 --draft=false".split()))
        self.assertTrue(dangerous("gh release create -n -- v1.2.3".split()))
        for safe in ("gh release create nightly v1.2.3", "gh release edit v1.2.3 --draft", "gh -R o/r", "gh status"):
            self.assertFalse(dangerous(safe.split()), safe)
        self.assertTrue(dangerous("gh release create -t=x -pn y v1.2.3-rc.1".split()))
        self.assertTrue(dangerous("gh release edit v1.2.3 --draft=0 --title x".split()))
        for err in ("gh release create v1.2.3 -t", "gh release create v1.2.3 --title", "gh release create -x v1.2.3"):
            self.assertFalse(dangerous(err.split()), err)  # thiếu giá trị / cờ ngắn lạ: gh lỗi
        self.assertFalse(dangerous("gh release create nightly --bogus".split()))  # cờ lạ: gh lỗi
        self.assertFalse(dangerous("gh release edit --tag v1.2.3".split()))  # thiếu đối số: gh lỗi

    def test_dangerous_templates_are_denied(self) -> None:
        """Mọi khuôn có một tải làm lệnh thật NGUY HIỂM → guard deny ở chính sách mặc định (`apply_policy` trên quyết
        định thô); ở `XT_GUARD_POLICY=strict` (quyết định thô dưới biến đó, như `guard.main`) deny, hoặc hỏi người với
        độ tin `unsure` — đúng thiết kế AUD-SEC-587/D-409 cho tên lệnh con động (`gh release $X`)."""
        bad = []
        risky = 0
        tpls = templates()
        for tpl in tpls:
            hits = [p for p in PAYLOADS if dangerous(expand(tpl, p))]
            risky += bool(hits)
            if not hits:
                continue
            with mock.patch.dict(os.environ, {"XT_GUARD_POLICY": "strict"}):
                strict = self.guard.bash_decision(tpl, self.root)
            default = self.guard.apply_policy(self.decide(tpl))
            strict_ok = strict["decision"] == "deny" or self.guard.decide(strict).confidence == "unsure"
            if not strict_ok or default["decision"] != "deny":
                why = str(strict.get("reason"))[:120]
                bad.append(f"{tpl!r} tải {hits[0]!r} → {strict['decision']}/{default['decision']}: {why}")
        self.assertGreaterEqual(len(tpls), 90)
        self.assertGreaterEqual(risky, 40)  # không để thuộc tính rỗng
        self.assertEqual(bad, [], f"{len(bad)}/{risky} khuôn nguy hiểm lọt (trên {len(tpls)} khuôn)")

    def test_literal_commands_follow_oracle(self) -> None:
        """Lệnh chữ (tải đã thay, không còn `$`/glob): NGUY HIỂM → deny; AN TOÀN → luật AUD-SEC-999 không chạy (như base
        — luật cũ #704 vẫn chặn chặt hơn oracle khi một từ bất kỳ của `create` là tag phiên bản, D-424)."""
        cmds = {" ".join(expand(t, p)) for t in templates() for p in PAYLOADS}
        cmds = {c for c in cmds if not re.search(r"[$*?\[]", c)}
        bad, risky = [], 0
        for cmd in sorted(cmds):
            danger = dangerous(cmd.split())
            risky += danger
            out = self.decide(cmd) if danger else {"decision": "deny"}
            if out["decision"] != "deny" or not danger and self.guard._gh_release_split(cmd):
                bad.append(f"{cmd!r} → {out['decision']}: {str(out.get('reason'))[:120]}")
        self.assertGreaterEqual(len(cmds), 90)
        self.assertGreaterEqual(risky, 20)
        self.assertEqual(bad, [], f"{len(bad)}/{len(cmds)} lệnh chữ lệch oracle")


class NamespaceClassificationTest(unittest.TestCase):
    def test_literal_non_tag_namespaces_are_not_tags(self) -> None:
        for namespace in ("heads", "notes", "archive"):
            with self.subTest(namespace=namespace):
                self.assertIs(guard._could_be_tag_namespace(namespace), False)

    def test_tag_and_indeterminate_namespaces_could_be_tags(self) -> None:
        for namespace in ("tags", "", "?", "ta?s"):
            with self.subTest(namespace=namespace):
                self.assertIs(guard._could_be_tag_namespace(namespace), True)


if __name__ == "__main__":
    unittest.main()
