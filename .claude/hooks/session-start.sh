#!/usr/bin/env bash
# session-start.sh — SessionStart hook (startup|resume|clear|compact).
# Nạp NGẮN GỌN trạng thái để phiên tiếp tục đúng chỗ: 4 mục của PROGRESS.md (tối đa 8 KB),
# verdict autopilot (từ bằng chứng trên đĩa), git branch/dirty/3 commit, và nhắc đọc AGENTS.md.
# Tổng additionalContext ≤ 9 800 ký tự: vượt 10 000 thì Claude Code thay cả chuỗi bằng đường dẫn tệp + 2 000 ký tự đầu
# (AUD-HAR-461), nên khối Autopilot (≤ 2 400)/Git (tên nhánh, repo ≤ 200; log ≤ 1 200)/luật dựng trước, PROGRESS lấy
# phần ngân sách còn lại. Cần python3 (như `utf8_head`, `context_output`); thiếu thì hook không in gì.
# Chỉ đọc, không đổi gì. Fail-open.
set -uo pipefail
. "$(dirname "$0")/_lib.sh"

# Chỉ lấy các mục "Đang làm / Tiếp theo / Quyết định / Bàn giao" (và tiêu đề). Cắt 8 KB và cắt theo ngân sách tổng làm
# ở bước ghép cuối (một dấu cắt duy nhất); ở đây chỉ chặn trên 64 KB để đối số python không quá lớn.
# Chuẩn hoá NFC trước awk: PROGRESS.md dạng NFD (soạn trên macOS) không khớp tên mục → mất cả 4 mục.
PROGRESS_LIMIT=8192  # khớp PROGRESS_MAX_BYTES của `xt.py progress-check` (test ghim hai số bằng nhau)
progress_block() {
  [ -f "$XT_ROOT/PROGRESS.md" ] || return 0
  local prog
  prog="$(python3 -I -c 'import sys, unicodedata; sys.stdout.write(unicodedata.normalize("NFC", sys.stdin.read()))' \
    < "$XT_ROOT/PROGRESS.md" 2>/dev/null | awk '
    /^## /{keep = ($0 ~ /Đang làm|Tiếp theo|Quyết định|Bàn giao/)}
    NR==1 || keep {print}
  ' | utf8_head 65536)"
  [ -n "$prog" ] || prog="$(utf8_head 65536 < "$XT_ROOT/PROGRESS.md")"
  printf '%s' "$prog"
}

rest=""
XT="$(xt_py)" || true
if [ -n "${XT:-}" ] && [ -f "$XT_ROOT/.autopilot/state.json" ]; then
  status="$(py_run "$XT" loop status 2>/dev/null)" || status='không đọc được trạng thái'
  # Quá 2 400 ký tự: giữ dòng verdict đầu (chặn ở 1 200 ký tự kèm "…"), bỏ các dòng giữa, giữ nguyên các dòng cuối còn
  # vừa (dòng checkpoint); dòng cuối dài hơn phần còn lại thì giữ phần đầu của nó kèm "…"; chỉ một dòng thì cắt cụt kèm "…".
  status="$(printf '%s' "$status" | python3 -I -c '
import sys
t = sys.stdin.buffer.read().decode("utf-8", "replace")
n = int(sys.argv[1])
if len(t) > n:
    mark = "\n[… đã cắt giữa …]\n"
    lines = t.split("\n")
    if len(lines) == 1:
        t = t[: n - 1] + "…"
    else:
        first = lines[0]
        if len(first) > n // 2:  # dòng verdict có thể rất dài (lý do dán nguyên văn, nhiều việc chờ người): chặn nửa trần
            first = first[: n // 2 - 1] + "…"
        keep = n - len(first) - len(mark)
        tail, size = [], 0
        for line in reversed(lines[1:]):
            if size + len(line) + 1 > keep:
                break
            tail.insert(0, line)
            size += len(line) + 1
        if not tail:
            tail = [lines[-1][: keep - 1] + "…"]
        t = first + mark + "\n".join(tail)
sys.stdout.buffer.write(t.encode("utf-8", "replace"))
' 2400 2>/dev/null)" || status='không đọc được trạng thái'
  rest+="===== Autopilot =====
$status

"
fi

if git -C "$XT_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  branch="$(git -C "$XT_ROOT" branch --show-current 2>/dev/null)"
  # Tên repo: đuôi URL remote origin (bỏ .git), không có remote thì tên thư mục gốc (LOOP-HARNESS-028).
  repo="$(git -C "$XT_ROOT" remote get-url origin 2>/dev/null | sed -e 's#/*$##' -e 's#\.git$##' -e 's#.*[/:]##')"
  [ -n "$repo" ] || repo="$(basename "$XT_ROOT")"
  # Tên nhánh/repo dài bất thường không được ăn ngân sách PROGRESS: cắt 200 byte và thêm "…"; nhánh đã cắt thì không gợi ý
  # tên phiên (tên cắt sẽ sai).
  branch_cut=""
  short="$(printf '%s' "$branch" | utf8_head 200)"
  if [ "$short" != "$branch" ]; then branch="${short}…"; branch_cut=1; fi
  short="$(printf '%s' "$repo" | utf8_head 200)"
  if [ "$short" != "$repo" ]; then repo="${short}…"; branch_cut=1; fi
  if [ -n "$branch_cut" ]; then
    name_hint="Tên phiên: \"<Tên repo> — <tên nhánh>\" (tên repo hoặc nhánh quá dài nên đã cắt khi hiển thị; lấy tên thật bằng git)."
  elif [ -n "$branch" ] && [ "$branch" != "main" ] && [ "$branch" != "master" ]; then
    name_hint="Tên phiên: \"$repo — $branch\" — đặt ngay nếu phiên chưa mang tên này (Claude Code: /rename; phiên cloud: tool set_session_title)."
  else
    name_hint="Tên phiên: \"$repo — <nhánh>\" — tạo nhánh làm việc (<type>/<mô-tả-ngắn>) rồi đặt tên phiên (Claude Code: /rename; phiên cloud: tool set_session_title)."
  fi
  rest+="===== Git =====
Branch: $branch
$name_hint
Chưa commit: $(git -C "$XT_ROOT" status --short 2>/dev/null | wc -l | tr -d ' ') file
$(git -C "$XT_ROOT" log --oneline -3 2>/dev/null | utf8_head 1200)

"
fi

fw="framework"; [ -d "$XT_ROOT/.xtemplates/framework" ] && fw=".xtemplates/framework"
rest+="Luật vận hành: AGENTS.md ở gốc dự án (Claude Code đã nạp qua CLAUDE.md; agent khác tự đọc); chạy autopilot thì đọc thêm $fw/11-autonomous-loop/README.md. Khi người dùng nhắn \"tiếp tục\": nối tiếp mục Đang làm/Bàn giao ở trên, không hỏi lại điều đã có trong file."

ctx="$rest"
prog="$(progress_block)"
if [ -n "$prog" ]; then
  # Ngân sách PROGRESS = 9 800 trừ phần còn lại, đo bằng ký tự trong Python (đọc UTF-8 tường minh, không phụ thuộc
  # LANG: `${#rest}` đếm byte khi locale trống). Cắt thì nối dấu để phiên sau biết còn phần chưa đọc.
  ctx="$(python3 -I -c '
import sys
prog, rest, limit = sys.argv[1], sys.argv[2], int(sys.argv[3])
head = "===== PROGRESS.md (trạng thái phiên trước) =====\n"
note = "\n[đã cắt phần cuối PROGRESS.md — đọc cả tệp]"
budget = 9800 - len(rest) - len(head) - 2
raw = prog.encode("utf-8", "replace")
cut = len(raw) > limit  # trần byte của PROGRESS (một con số với `progress-check`)
if cut:
    prog = raw[:limit].decode("utf-8", "ignore")
if len(prog) + (len(note) if cut else 0) > budget:  # trần tổng ký tự của additionalContext
    cut = True
    prog = prog[: max(budget - len(note), 0)]
if cut:
    prog += note
sys.stdout.buffer.write((head + prog + "\n\n" + rest).encode("utf-8", "replace"))
' "$prog" "$rest" "$PROGRESS_LIMIT" 2>/dev/null)" || ctx="$rest"
fi

context_output SessionStart "$ctx"
exit 0
