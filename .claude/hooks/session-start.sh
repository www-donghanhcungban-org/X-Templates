#!/usr/bin/env bash
# session-start.sh — SessionStart hook (startup|resume|clear|compact).
# Nạp NGẮN GỌN trạng thái để phiên tiếp tục đúng chỗ: 4 mục của PROGRESS.md (tối đa 8 KB),
# verdict autopilot (từ bằng chứng trên đĩa), git branch/dirty/3 commit, và nhắc đọc AGENTS.md.
# Tổng additionalContext ≤ 9 800 ký tự: vượt 10 000 thì Claude Code thay cả chuỗi bằng đường dẫn tệp + 2 000 ký tự đầu
# (AUD-HAR-461), nên khối Autopilot/Git/luật dựng trước, PROGRESS lấy phần ngân sách còn lại.
# Chỉ đọc, không đổi gì. Fail-open.
set -uo pipefail
. "$(dirname "$0")/_lib.sh"

# Chỉ lấy các mục "Đang làm / Tiếp theo / Quyết định / Bàn giao" (và tiêu đề), cắt 8 KB.
# Chuẩn hoá NFC trước awk: PROGRESS.md dạng NFD (soạn trên macOS) không khớp tên mục → mất cả 4 mục.
progress_block() {
  [ -f "$XT_ROOT/PROGRESS.md" ] || return 0
  local prog
  prog="$(python3 -I -c 'import sys, unicodedata; sys.stdout.write(unicodedata.normalize("NFC", sys.stdin.read()))' \
    < "$XT_ROOT/PROGRESS.md" 2>/dev/null | awk '
    /^## /{keep = ($0 ~ /Đang làm|Tiếp theo|Quyết định|Bàn giao/)}
    NR==1 || keep {print}
  ' | utf8_head 8192)"
  [ -n "$prog" ] || prog="$(utf8_head 8192 < "$XT_ROOT/PROGRESS.md")"
  printf '%s' "$prog"
}

rest=""
XT="$(xt_py)" || true
if [ -n "${XT:-}" ] && [ -f "$XT_ROOT/.autopilot/state.json" ]; then
  status="$(py_run "$XT" loop status 2>/dev/null)" || status='không đọc được trạng thái'
  status="$(printf '%s' "$status" | utf8_head 2400)"
  rest+="===== Autopilot =====
$status

"
fi

if git -C "$XT_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  branch="$(git -C "$XT_ROOT" branch --show-current 2>/dev/null)"
  # Tên repo: đuôi URL remote origin (bỏ .git), không có remote thì tên thư mục gốc (LOOP-HARNESS-028).
  repo="$(git -C "$XT_ROOT" remote get-url origin 2>/dev/null | sed -e 's#/*$##' -e 's#\.git$##' -e 's#.*[/:]##')"
  [ -n "$repo" ] || repo="$(basename "$XT_ROOT")"
  if [ -n "$branch" ] && [ "$branch" != "main" ] && [ "$branch" != "master" ]; then
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
  # Ngân sách PROGRESS tính bằng ký tự (chừa 60 cho tiêu đề và xuống dòng); thiếu python3 thì cắt theo byte (chặt hơn).
  budget=$(( 9800 - ${#rest} - 60 ))
  [ "$budget" -gt 0 ] || budget=0
  cut="$(printf '%s' "$prog" | python3 -I -c 'import sys; sys.stdout.write(sys.stdin.read()[: int(sys.argv[1])])' "$budget" 2>/dev/null)" \
    || cut="$(printf '%s' "$prog" | utf8_head "$budget")"
  ctx="===== PROGRESS.md (trạng thái phiên trước) =====
$cut

$rest"
fi

context_output SessionStart "$ctx"
exit 0
