#!/usr/bin/env bash
# pre-compact.sh — PreCompact hook (manual|auto). Trước khi Claude Code nén context, ghi vị trí làm việc
# (task đang làm, lệnh kiểm cuối + exit code, file chưa commit, lỗi lặp) vào .autopilot/state.json để
# SessionStart(compact) nạp lại qua `xt.py loop status` — chế độ một phiên (ADR-0009, LOOP-CTX-017).
# Rồi in checkpoint vừa ghi ra stdout bằng chữ thường: Claude Code dùng stdout của PreCompact (exit 0) làm chỉ dẫn cho bản
# tóm tắt nén, cắt ở 10 000 ký tự (docs hooks §PreCompact output, đọc 2026-11-26; LOOP-CTX-009). Dòng đầu không phải `{`.
# LUÔN exit 0 và không in quyết định: PreCompact exit 2 / "decision":"block" sẽ CHẶN compaction — phiên kẹt
# vì context đầy. Ghi ở `xt.py loop checkpoint` (có test); phần in: `tests/test_hook_precompact_output.py`. Chưa
# `loop init` → không làm gì, không in gì.
set -uo pipefail
. "$(dirname "$0")/_lib.sh"

payload="$(cat)"
# Chưa `loop init` (không có state.json): `loop checkpoint` là no-op → không khởi động python (T-1711).
[ -f "$XT_ROOT/.autopilot/state.json" ] || exit 0
XT="$(xt_py)" || exit 0
since="$(date -u +%Y-%m-%dT%H:%M:%S+00:00)"
printf '%s' "$payload" | py_run "$XT" loop checkpoint >/dev/null 2>&1 || true
# Chỉ in checkpoint ghi ở lần chạy này (`at` ≥ lúc bắt đầu): ghi hỏng (khoá bận…) thì checkpoint cũ sẽ dẫn sai chỗ.
python3 -I -S -c '
import json, re, sys
root, since = sys.argv[1], sys.argv[2]
try:
    cp = json.load(open(root + "/.autopilot/state.json", encoding="utf-8")).get("checkpoint")
except (OSError, ValueError, AttributeError):
    sys.exit(0)
if not isinstance(cp, dict) or str(cp.get("at") or "") < since:
    sys.exit(0)
ev = cp.get("last_evidence") if isinstance(cp.get("last_evidence"), dict) else {}
code = "—" if ev.get("exit_code") is None else str(ev.get("exit_code"))
cmd = str(ev.get("cmd") or "")
cmd = cmd if len(cmd) <= 500 else cmd[:500] + " […]"  # lệnh dài không đẩy các dòng sau ra khỏi trần 9 000 ký tự
gate = str(ev.get("task") or "—") + " `" + cmd + "` exit " + code if ev else "chưa có bằng chứng"
try:
    ids = re.findall(r"^### (D-\d+)", open(root + "/docs/autopilot/DECISIONS.md", encoding="utf-8").read(), re.M)
except (OSError, ValueError):
    ids = []
dirty = cp.get("dirty") if isinstance(cp.get("dirty"), list) else []
lines = [
    "Chỉ dẫn tóm tắt (X-Templates, checkpoint trước nén " + str(cp.get("at")) + "): giữ nguyên văn các mục sau.",
    "- Task đang làm: " + str(cp.get("task") or "—") + " (verdict " + str(cp.get("verdict") or "—") + ").",
    "- Gate cuối: " + gate + ".",
    "- Tệp chưa commit: " + (", ".join(map(str, dirty)) or "không") + ".",
    "- D-NNN: giữ mọi D-NNN ghi trong phiên; mới nhất trong sổ: " + (ids[-1] if ids else "—") + ".",
    "- PR đang mở: giữ số PR, nhánh và bước `xt.py pr next` cuối cùng.",
    "Sau nén chạy `xt.py loop status` để nạp lại vị trí.",
]
sys.stdout.write("\n".join(lines)[:9000] + "\n")
' "$XT_ROOT" "$since" 2>/dev/null || true
exit 0
