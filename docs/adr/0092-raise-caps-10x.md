# ADR-0092: Nâng thêm 10× trần kích thước file và nhóm thư mục

- **Trạng thái:** Đã chấp nhận ngày 2026-11-21 (yêu cầu của chủ repo: "nâng trần các giới hạn hiện tại lên x10"; D-537). Nối tiếp [ADR-0089](0089-raise-file-and-dir-caps-5x.md).
- **Trạng thái triển khai:** Đã triển khai — `tests/test_docs_budget.py` (`DIR_CAPS` ×10 so với giá trị sau ADR-0089; `CAPS` theo mục 1–3 và 6 dưới đây, phần lớn thấp hơn ADR-0089; `MARK_FACTOR = 50`).
- **Liên quan:** [ADR-0043](0043-size-budget.md), [ADR-0091](0091-progress-hook-cap-and-split-constraints.md), AUD-HAR-462.

## Quyết định

Nguyên tắc (chủ repo: "chọn mức tối đa hợp lý nhất"): mỗi trần nâng tới mức cao nhất còn nằm trong giới hạn của kênh nạp nó, tối đa 10×.

1. `DIR_CAPS` (nhóm thư mục) và `CAPS` của `framework/11-autonomous-loop/README.md` (không bị kênh nào giới hạn) nhân 10 so với giá trị sau ADR-0089; `MARK_FACTOR` từ 5 lên 50 để trần hiệu lực (min của trần và hệ số × mốc) cũng tăng 10×. Chỉ áp ở repo khung; dự án đích không đổi.
2. `AGENTS.md` và mẫu: 28 672 byte; `CLAUDE.md` và mẫu: 4 096 byte. Tổng 32 768 khớp giới hạn Codex (`XC-DOCAI-006`). Mức 10× giá trị gốc 7 168 (71 680) sẽ vượt kênh nên không dùng.
3. Ba `SKILL.md`: 12 288 byte, xấp xỉ 5 000 token Claude Code gắn lại sau compaction (ước lượng, chưa đo bằng tokenizer). Mức ×10 sẽ làm đuôi checklist rơi sau compaction.
4. **Không đổi** trần `PROGRESS.md` và hook SessionStart (8 192 byte): `additionalContext` vượt 10 000 ký tự thì Claude Code thay cả chuỗi bằng đường dẫn tệp và 2 000 ký tự đầu, và khối Git, autopilot, luật đã chiếm phần còn lại (AUD-HAR-461, ADR-0091). Muốn hơn phải đổi cách nạp (ADR riêng).
5. Nhờ vậy không còn `CAPS` nào lớn hơn giới hạn kênh; AUD-HAR-462 đóng.
6. Chữ "×10" chỉ đúng với `DIR_CAPS`, `MARK_FACTOR` và README vòng lặp. Với file nạp đầu phiên, giá trị mới thấp hơn ADR-0089 ở 7/8 trần (`AGENTS.md` và mẫu 35 840/40 960 → 28 672; `CLAUDE.md` và mẫu → 4 096; `SKILL.md` 30 720 → 12 288) vì giới hạn kênh. Ràng buộc 32 768 tính theo chuỗi `AGENTS.md` (gốc cộng lồng, `XC-DOCAI-006`): `scripts/AGENTS.md` và `tests/AGENTS.md` chưa có trần riêng; nguồn sống của Codex chưa xác minh lại.

## Phương án đã xét

- **×10 mọi trần (chủ repo yêu cầu ban đầu):** bị loại cho `AGENTS.md`, `CLAUDE.md`, `SKILL.md`, PROGRESS và hook vì vượt giới hạn kênh.
- **Giữ trần ADR-0089:** bị loại vì chủ repo muốn nới và nhóm thư mục còn dư nhiều.

## Đánh đổi

- Được: không phải cắt chữ khi viết luật, ADR và sổ trong repo khung.
- Mất: trần nhóm thư mục và README vòng lặp bớt là hàng rào sớm; file nạp đầu phiên phình tới trần mới sẽ tốn ngữ cảnh mọi phiên. Các file đi qua kênh có giới hạn vẫn bị chặn đúng ở giới hạn đó (mục 2–4).
- Đường lùi: đặt lại hằng số về giá trị ADR-0089.
