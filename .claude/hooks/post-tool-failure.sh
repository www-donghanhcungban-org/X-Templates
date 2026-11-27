#!/usr/bin/env bash
# post-tool-failure.sh — hook PostToolUseFailure (TD-5, T-1822). Lệnh Bash là cổng/Gate (`dev-task.sh`, `xt.py loop
# record`, `unittest`, `pytest`, `npm test`, …) vừa đỏ → `xt.py loop triage-local` phân loại output bằng bộ của
# `ci-triage` và trả ≤ 20 dòng lỗi đã che bí mật làm `additionalContext` — agent khỏi đọc lại log dài (LOOP-CTX-004).
# Chỉ gợi ý, không quyết. Toàn bộ logic ở xt.py (có test); hook chỉ chuyển stdin. Lệnh khác, payload rác, thiếu
# python3/xt.py, xt.py lỗi → không in gì (fail-open). Luôn exit 0.
# Tiền lọc (T-5042): payload không chứa dấu hiệu lệnh cổng thì thoát TRƯỚC khi nạp python (mỗi lần Bash đỏ).
# `PREFILTER_RE` là TẬP CHA của `TRIAGE_LOCAL_GATE_RE` (scripts/xt.py): cùng các nhánh, bỏ `\b`, khoảng trắng `\s` →
# ký tự không phải chữ/số/`_` hoặc dạng đã mã hoá JSON (`\n` `\t` `\uXXXX`); khớp thừa thì xt.py lọc lại, bỏ sót thì
# mất gợi ý. Test `tests/test_post_tool_failure_prefilter.py` ghim quan hệ tập cha.
set -uo pipefail
. "$(dirname "$0")/_lib.sh"

payload="$(cat)"
PREFILTER_RE='dev-task\.sh|xt\.py(\\u[0-9a-fA-F]{4}|\\[nrtfv]|[^[:alnum:]_])+loop(\\u[0-9a-fA-F]{4}|\\[nrtfv]|[^[:alnum:]_])+(record|verify)|unittest|pytest|(npm|pnpm|yarn|bun)(\\u[0-9a-fA-F]{4}|\\[nrtfv]|[^[:alnum:]_])+(run(\\u[0-9a-fA-F]{4}|\\[nrtfv]|[^[:alnum:]_])+)?test|(go|cargo|make)(\\u[0-9a-fA-F]{4}|\\[nrtfv]|[^[:alnum:]_])+test|ruff|mypy|shellcheck|tsc|eslint'
[[ $payload =~ $PREFILTER_RE ]] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0
XT="$(xt_py)" || exit 0
printf '%s' "$payload" | py_run "$XT" loop triage-local 2>/dev/null || exit 0
exit 0
