# ADR-0091: PROGRESS và hook SessionStart giữ 8 KB; ràng buộc bổ sung cho ADR-0089 và ADR-0090

- **Trạng thái:** Đã chấp nhận ngày 2026-11-21 (phiên chính tự duyệt, ADR-0008; D-536). Thay một phần [ADR-0089](0089-raise-file-and-dir-caps-5x.md); bổ sung cho [ADR-0090](0090-split-guard-and-xt-monoliths.md).
- **Trạng thái triển khai:** Đã triển khai — `scripts/xt.py` (`PROGRESS_MAX_BYTES = 8192`), `.claude/hooks/session-start.sh` (`utf8_head 8192`), `tests/test_hooks.py` (`SessionStartUtf8Test`).
- **Liên quan:** [ADR-0043](0043-size-budget.md), [ADR-0050](0050-raise-dir-size-caps.md), [ADR-0072](0072-review-dir-caps-after-2x.md), [ADR-0088](0088-docs-ledger-size-caps.md), AUD-HAR-461.

## Bối cảnh

ADR-0089 nâng 5× trần theo từng file, nhóm thư mục và trần `PROGRESS.md` cùng hook (8 192 → 40 960 byte). Audit delta 3.35.0 (lô B) đo: với `PROGRESS.md` 39 965 byte, hook SessionStart trả `additionalContext` 31 535 ký tự. Tài liệu hook của Claude Code (<https://code.claude.com/docs/en/hooks.md>, đọc 2026-11-21): chuỗi `additionalContext` giới hạn 10 000 ký tự; vượt thì Claude Code lưu cả chuỗi ra tệp trong thư mục phiên và thay bằng đường dẫn kèm xem trước tối đa 2 000 ký tự đầu, không nhắc model đọc tệp. Vượt dù chỉ 1 ký tự là mất mọi thứ sau ký tự 2 000: mục "Tiếp theo", "Bàn giao", verdict autopilot và nhắc luật rơi khỏi ngữ cảnh đầu phiên và sau compaction. Hook vẫn thoát 0 và test xanh, nên lỗi không tự lộ. Trần nhóm thư mục thực dùng 19–20 %, không có áp lực nâng `PROGRESS.md`.

## Quyết định

1. `PROGRESS_MAX_BYTES` và `utf8_head` của hook về 8 192 byte (khớp `LOOP-HARNESS-004`, `LOOP-CTX-001`). Hook dựng khối Autopilot (≤ 2 400 ký tự), Git và luật trước, rồi cắt PROGRESS theo ký tự vào ngân sách còn lại để tổng ≤ 9 800 (review của chính bản sửa này chỉ ra PROGRESS 8 192 B cộng Autopilot đang chạy đã đạt 10 315 ký tự). Test ghim tổng ≤ 10 000 với PROGRESS đúng trần cộng Git dài, và ghim số byte của hook bằng `PROGRESS_MAX_BYTES`. Phần còn lại của ADR-0089 (`CAPS`, `DIR_CAPS`, `MARK_FACTOR`) giữ nguyên hiệu lực, chỉ ở repo khung.
2. Giới hạn của kênh nạp là trần cứng, không phải chỉ số nới theo ý muốn: `AGENTS.md` ≤ 32 768 byte (`XC-DOCAI-006`, Codex), `SKILL.md` đủ ngắn để 5 000 token đầu giữ checklist sau compaction. Trần `CAPS` của các file đó phải ≤ giới hạn kênh; việc hạ trần là nợ AUD-HAR-462.
3. ADR-0089 thay các quyết định "không nới trần" của ADR-0043, 0050, 0072, 0083 và 0088 ở phần `CAPS`/`DIR_CAPS`/hệ số mốc. Lý do: nhóm đo được còn dư chỗ và chủ repo yêu cầu. Đánh đổi: tốn ngữ cảnh mỗi phiên nếu file nạp đầu phiên phình tới trần mới, nên ràng buộc ở mục 2 là cái giữ lại.

## Ràng buộc bổ sung cho ADR-0090

Tách module không được phá các bất biến đã có:

- Bộ nạp guard compile từ nguồn, không dùng `__pycache__` (`.claude/hooks/_lib.sh`, D-307, AUD-SEC-074): bytecode đặt sẵn chạy được dưới `python3 -I -B`. Module guard tách ra phải nạp bằng đường đó. Thiếu module sau cài dở là guard lỗi nạp, nên Bash bị chặn ([ADR-0054](0054-fail-closed-unavailable-state-lock-and-guard-loader.md)).
- `perf trial` (`_trial_exec` trong `scripts/xt.py`, [ADR-0071](0071-perf-trial.md) §5) xuất và chạy một blob `xt.py` duy nhất. Phần nó cần ở lại `xt.py`, hoặc blob phải gồm cả module tách.
- Trình tự: đo chi phí compile (T-3709, [ADR-0072](0072-review-dir-caps-after-2x.md), D-373) trước khi quyết tách guard; AUD-ARCH-007/008/010 đóng khi lát đầu có số đo.

## Hệ quả

- Chưa nâng trần `PROGRESS.md`; muốn nhiều hơn thì giảm khối Autopilot/Git hoặc đổi cách nạp bằng ADR mới. Đưa khối Git/luật lên trước không cứu được: vượt 10 000 thì chỉ 2 000 ký tự đầu còn lại.
- ADR-0090 vẫn là lộ trình; mỗi lát tách phải dẫn mục "Ràng buộc" ở đây trong PR.

## Phương án đã xét

- **Giữ 40 960 và cắt theo ký tự trong hook (chọn một phần):** hook nay đã cắt theo ký tự vào ngân sách còn lại, nhưng không nâng trần PROGRESS vì PROGRESS thật đã sát trần (8 137/8 192 B, bị cắt có dấu khi Autopilot đầy) nên mức hiện tại là giới hạn kênh chứ không phải áp lực dung lượng, và nâng thêm tăng chi phí ngữ cảnh mỗi phiên.
- **Giữ nguyên ADR-0089:** bị loại, đo được additionalContext 41 149 byte với PROGRESS 39 965 byte.
- **Nâng cả PROGRESS lẫn hook ×10:** bị loại, vượt giới hạn kênh.
