"""Trần kích thước file hướng dẫn nạp đầu phiên (PLAN-3.12-lean Lát 1, D-111): giữ lâu dài sau khi PLAN đóng — review #190
chỉ ra Gate của PLAN không còn chạy khi task đã tick. Vượt trần → cắt chữ, chuyển nội dung về "nhà", không nới trần."""

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAPS = {  # byte; nhà của từng trần: PLAN-3.12-lean T-1701…T-1704; ADR-0089 nâng 5×, ADR-0092 đặt lại theo giới hạn kênh
    # AGENTS.md + CLAUDE.md ≤ 32 768 (XC-DOCAI-006, giới hạn Codex): 28 672 + 4 096; skill ≤ 12 288 (~5 000 token sau compaction).
    "AGENTS.md": 28672,
    "framework/templates/AGENTS.md": 28672,
    "CLAUDE.md": 4096,
    "framework/templates/CLAUDE.md": 4096,
    ".claude/skills/autopilot/SKILL.md": 12288,
    ".claude/skills/complete/SKILL.md": 12288,  # ADR-0046: skill pha harden, cùng trần với /autopilot
    ".claude/skills/optimize/SKILL.md": 12288,  # ADR-0048: skill tối ưu, cùng trần
    "framework/11-autonomous-loop/README.md": 12288 * 50,
}
# Trần TỔNG byte theo thư mục (ADR-0043, T-2407; ADR-0050/ADR-0088: +1 MiB; ADR-0089: ×5 trần hiện tại).
# Chỉ đếm file git theo dõi (bỏ cache/sinh ra).
DIR_CAPS = {  # nhóm → (pathspec git, trần byte); đo: `git ls-files -z -- <spec> | xargs -0 cat | wc -c`
    "scripts (xt.py, install.py, xt_app)": (("scripts/*.py", "scripts/xt_app/"), (711855 + 1048576) * 50),
    ".claude/hooks": ((".claude/hooks/",), (369393 + 1048576) * 50),
    "framework/11-autonomous-loop": (("framework/11-autonomous-loop/",), (232307 + 1048576) * 50),
    # Sổ sách đang dùng (T-3651, AUD-DOC-180, D-314; ADR-0088 +1 MiB; nâng 5× theo ADR-0089, ×10 theo ADR-0092).
    # File lưu trữ (`*-ARCHIVE.md`, `DECISIONS-YYYY-MM.md`) đóng băng, không tính: lưu trữ thêm phải làm trần còn chỗ.
    "docs/ops": (("docs/ops/", ":(exclude)docs/ops/*-ARCHIVE.md"), (810114 + 1048576) * 50),
    "docs/autopilot": (("docs/autopilot/", ":(exclude)docs/autopilot/DECISIONS-*.md"), (352345 + 1048576) * 50),
}
MARK_FACTOR = 50  # ADR-0092: mỗi nhóm ≤ 50× mốc mới nhất (5× theo ADR-0089, trước đó 2× theo ADR-0050/ADR-0072).
# Mốc kích thước (ADR-0050 §Hệ quả, ADR-0072, ADR-0083, ADR-0089): mỗi nhóm ≤ MARK_FACTOR × mốc mới nhất.
SIZE_MARKS = {
    "scripts (xt.py, install.py, xt_app)": (
        ("2026-10-26", 711824, "ADR-0072"),
        ("2026-11-20", 1414300, "ADR-0083"),
        ("2026-11-21", 1639253, "ADR-0089"),
    ),
    ".claude/hooks": (
        ("2026-10-26", 369274, "ADR-0072"),
        ("2026-11-05", 843817, "ADR-0072"),
        ("2026-11-21", 1417480, "ADR-0089"),
    ),
    "framework/11-autonomous-loop": (
        ("2026-10-26", 232297, "ADR-0072"),
        ("2026-11-21", 336675, "ADR-0089"),
    ),
    "docs/ops": (
        ("2026-11-02", 771538, "ADR-0072"),
        ("2026-11-21", 798004, "ADR-0089"),
    ),
    "docs/autopilot": (
        ("2026-11-02", 335567, "ADR-0072"),
        ("2026-11-21", 352327, "ADR-0089"),
    ),
}


def double_mark_breach(size: int, marks: "tuple[tuple[str, int, str], ...]") -> "tuple[str, int, str] | None":
    """Mốc mới nhất (theo ngày, không theo thứ tự khai) khi `size` > MARK_FACTOR × mốc đó; None khi còn trong ngưỡng."""
    latest = max(marks)
    return latest if size > MARK_FACTOR * latest[1] else None


def mentions_size(text: str, size: int) -> bool:
    """`text` ghi `size` dạng liền ("843817") hoặc tách nghìn bằng khoảng trắng ("843 817"), không dính chữ số bên cạnh."""
    groups = f"{size:,}".split(",")
    body = "[   ]?".join(groups)
    return re.search(rf"(?<![\d.,])(?<!\d[   ]){body}(?![   ]?\d)", text) is not None


def group_token(specs: "tuple[str, ...]") -> str:
    """Đường nhóm ADR ghi: pathspec đầu cắt tới `/` cuối trước ký tự glob ("scripts/*.py" → "scripts/")."""
    head = re.split(r"[*?\[]", specs[0], maxsplit=1)[0]
    return head[: head.rfind("/") + 1] or head


def declares_mark(text: str, token: str, day: str, size: int) -> bool:
    """Một dòng của `text` chứa đường nhóm, và ngày cùng số byte của mốc nằm chung MỘT ô bảng (review #448: rải rác
    trong file không tính; review #449: hàng bảng còn số 2×/trần/số đo khác — ngày và byte phải cùng ô)."""
    return any(
        token in ln and any(day in cell and mentions_size(cell, size) for cell in ln.split("|"))
        for ln in text.splitlines()
    )


def tracked_bytes(specs: "tuple[str, ...]") -> int:
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "--", *specs], capture_output=True, check=True)
    return sum((ROOT / rel.decode()).stat().st_size for rel in out.stdout.split(b"\0") if rel)


class DocsBudgetTest(unittest.TestCase):
    def test_dir_totals_stay_under_caps(self):
        for group, (specs, cap) in DIR_CAPS.items():
            with self.subTest(group):
                size = tracked_bytes(specs)
                self.assertGreater(size, 0, f"{group}: không thấy file nào — pathspec sai")
                self.assertLessEqual(
                    size, cap, f"{group}: {size} B > {cap} B — cắt chỗ khác (ADR-0043), không nới trần"
                )

    def test_dir_totals_within_double_latest_mark(self):
        for group, (specs, _cap) in DIR_CAPS.items():
            with self.subTest(group):
                self.assertIn(group, SIZE_MARKS, f"{group}: chưa khai mốc kích thước (ADR-0072)")
                size = tracked_bytes(specs)
                hit = double_mark_breach(size, SIZE_MARKS[group])
                self.assertIsNone(
                    hit,
                    f"{group}: {size} B > 2× mốc {hit} — cần ADR xét lại khai mốc mới (ADR-0050 §Hệ quả, ADR-0072)",
                )

    def test_size_marks_are_declared_by_existing_adr(self):
        self.assertEqual(set(SIZE_MARKS), set(DIR_CAPS), "mỗi nhóm DIR_CAPS đúng một bộ mốc")
        for group, marks in SIZE_MARKS.items():
            for day, size, adr in marks:
                with self.subTest(group=group, day=day):
                    self.assertRegex(day, r"^\d{4}-\d{2}-\d{2}$")
                    self.assertGreater(size, 0)
                    self.assertRegex(adr, r"^ADR-\d{4}$")
                    files = list((ROOT / "docs/adr").glob(adr[4:] + "-*.md"))
                    self.assertEqual(len(files), 1, f"{adr}: cần đúng một file ADR")
                    text = files[0].read_text(encoding="utf-8")
                    token = group_token(DIR_CAPS[group][0])
                    self.assertTrue(token, f"{group}: pathspec đầu không có thư mục")
                    self.assertTrue(
                        declares_mark(text, token, day, size),
                        f"{adr}: không dòng nào ghi {token} với {day} và {size} B cùng một ô",
                    )

    def test_declares_mark_needs_one_line(self):
        adr = next((ROOT / "docs/adr").glob("0072-*.md")).read_text(encoding="utf-8")
        self.assertFalse(declares_mark(adr, "scripts/", "2026-11-05", 1164066))  # byte có, ngày ở dòng khác
        self.assertFalse(declares_mark(adr, ".claude/hooks/", "2026-11-05", 1417969))  # trần, không phải mốc
        self.assertFalse(declares_mark(adr, "scripts/", "2026-10-26", 1164066))  # số đo cùng hàng, khác ô (review #449)
        self.assertFalse(declares_mark(adr, "scripts/", "2026-10-26", 1760431))  # trần cùng hàng
        self.assertTrue(declares_mark(adr, ".claude/hooks/", "2026-11-05", 843817))
        self.assertTrue(declares_mark("a `docs/ops/` 771538 (2026-11-02)", "docs/ops/", "2026-11-02", 771538))
        self.assertFalse(declares_mark("`docs/ops/` 2026-11-02\n771 538", "docs/ops/", "2026-11-02", 771538))
        self.assertFalse(declares_mark("`docs/autopilot/` 771 538 (2026-11-02)", "docs/ops/", "2026-11-02", 771538))
        self.assertFalse(declares_mark("", "docs/ops/", "2026-11-02", 771538))

    def test_group_token(self):
        self.assertEqual(group_token(("scripts/*.py", "scripts/xt_app/")), "scripts/")
        self.assertEqual(group_token((".claude/hooks/",)), ".claude/hooks/")
        self.assertEqual(group_token(("docs/ops/", ":(exclude)docs/ops/*-ARCHIVE.md")), "docs/ops/")
        self.assertEqual(group_token(("*.md",)), "")  # không có thư mục: rỗng (khớp mọi dòng — đừng khai nhóm như vậy)

    def test_mentions_size_forms(self):
        self.assertTrue(mentions_size("hooks 843 817 B", 843817))
        self.assertTrue(mentions_size("843817", 843817))
        self.assertTrue(mentions_size("a 843 817.", 843817))
        self.assertTrue(mentions_size("(1 417 969 B)", 1417969))
        self.assertFalse(mentions_size("1 843 817", 843817))  # chữ số dính trước
        self.assertFalse(mentions_size("1843817", 843817))
        self.assertFalse(mentions_size("843 8170", 843817))  # chữ số dính sau
        self.assertFalse(mentions_size("843 817 1", 843817))
        self.assertFalse(mentions_size("843 816", 843817))
        self.assertFalse(mentions_size("", 843817))
        self.assertTrue(mentions_size("x 999 y", 999))  # dưới 1000: một nhóm

    def test_double_mark_breach_boundaries(self):
        marks = (("2026-11-05", 100, "ADR-0072"), ("2026-10-26", 10, "ADR-0050"))  # khai lệch thứ tự: lấy theo ngày
        self.assertIsNone(double_mark_breach(100 * MARK_FACTOR, marks))  # đúng MARK_FACTOR × vẫn đạt
        self.assertEqual(double_mark_breach(100 * MARK_FACTOR + 1, marks), marks[0])
        self.assertIsNone(double_mark_breach(0, marks))
        self.assertEqual(
            double_mark_breach(10 * MARK_FACTOR + 1, (("2026-10-26", 10, "ADR-0050"),)),
            ("2026-10-26", 10, "ADR-0050"),
        )

    def test_guidance_files_stay_under_caps(self):
        for rel, cap in CAPS.items():
            with self.subTest(rel):
                size = (ROOT / rel).stat().st_size
                self.assertLessEqual(size, cap, f"{rel}: {size} B > {cap} B — cắt chữ, không nới trần")

    def test_tracked_text_files_are_clean_utf8(self):
        """Dự án đích (hotel-manager) kiểm mọi file văn bản: UTF-8, không BOM, không U+FFFD — file khung cài sang phải
        qua được (3.11.0 `guard.py` từng chứa ký tự U+FFFD thật trong `clean_text`)."""
        tracked = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, check=True
        ).stdout.split(b"\0")
        bad = []
        for rel in tracked:
            if not rel or rel.endswith((b".png", b".jpg", b".ico", b".pyc", b".zip", b".gz")):
                continue
            if rel.startswith(b"tests_e2e/vendor/"):
                continue  # D-135: tệp bên thứ ba nguyên văn (hash ghim, vendor-check), không cài sang dự án đích
            data = (ROOT / rel.decode()).read_bytes()
            if b"\0" in data:
                continue  # nhị phân
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                bad.append((rel.decode(), "không phải UTF-8"))
                continue
            if data.startswith(b"\xef\xbb\xbf"):
                bad.append((rel.decode(), "BOM"))
            if "\ufffd" in text:
                bad.append((rel.decode(), "U+FFFD"))
        self.assertEqual(bad, [])

    def test_agents_md_keeps_nine_sections(self):
        for rel in ("AGENTS.md", "framework/templates/AGENTS.md"):
            with self.subTest(rel):
                heads = [ln for ln in (ROOT / rel).read_text(encoding="utf-8").splitlines() if ln.startswith("## ")]
                self.assertEqual(len(heads), 9, heads)


if __name__ == "__main__":
    unittest.main()
