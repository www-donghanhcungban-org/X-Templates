# Universal Adaptive Context Manager

Ngày 28/11/2026. Khảo sát nền và thứ tự triển khai cho X-Templates. Hồ sơ phát hành 3.37.0 tiếp tục theo PLAN harden hiện hành. UACM đi theo các lát riêng, bắt đầu bằng hợp đồng và chế độ quan sát.

## Nền hiện có

- `.claude/hooks/pre-compact.sh` gọi `xt.py loop checkpoint`. SessionStart sau compaction nạp trạng thái từ vòng lặp. Tái sử dụng đường này và giữ hành vi compaction gốc của runtime.
- Checkpoint hiện tại thuộc worktree/vòng lặp. Chưa xác minh cơ chế lưu bền xuyên máy, dedupe sau merge và đối chiếu trạng thái giữa nhiều phiên.
- Phiên bản cài tại máy khảo sát là Codex CLI 0.172.0 và Claude Code 2.1.332. Chưa chạy tích hợp compaction trên phiên thật.

| Môi trường | Căn cứ và phạm vi xác minh |
| --- | --- |
| Codex Local và worker tự quản | [App Server](https://developers.openai.com/codex/app-server/) công bố `thread/compact/start` và sự kiện `contextCompaction`. ACK chỉ xác nhận đã tiếp nhận. Kiểm tra schema của bản cài và chạy thử trong phiên riêng trước khi bật. |
| Codex Desktop, IDE, Cloud managed | Chưa xác minh quyền gọi trực tiếp cho phiên hiện hành. Dùng checkpoint theo quyền và compaction do runtime quản lý. |
| Claude Code Local và worker tự quản | [Hooks](https://code.claude.com/docs/en/hooks) công bố PreCompact và PostCompact. Chỉ ghi metadata cần thiết. Bỏ qua nội dung `compact_summary` khi lưu. |
| Claude Code Cloud managed | [Tài liệu Cloud](https://code.claude.com/docs/en/claude-code-on-the-web) công bố `/compact` cho phiên ngoài thread của Projects. Điều khiển từ adapter và quyền lưu checkpoint vẫn cần kiểm chứng theo loại phiên. |
| Hybrid | Dùng capability của từng worker. Khôi phục khác máy chỉ khi checkpoint thực sự có trong kho được cấp quyền. |
| API trực tiếp | Lát riêng sau pilot. Capability và quota được đo theo từng API. |

## Thứ tự và cổng nghiệm thu

1. Foundation. Định nghĩa sự kiện merge đã xác minh, capability ba trạng thái, phiên bản checkpoint và chính sách quan sát. Dùng fixture vô hại cho checkpoint lặp, chưa lưu thành công, thiếu telemetry, busy/conflict/approval và recovery từ snapshot cũ. Dữ liệu động nằm ngoài Git.
2. Adapter local. Xác minh protocol Codex và vòng đời hook Claude trên phiên test. ACK, sai phiên, timeout và lỗi đều cần kiểm thử trước khi công nhận compaction hoàn tất.
3. Cloud và hybrid. Kiểm tra từng loại phiên và kho trạng thái. Dùng fallback provider-managed nếu thiếu quyền hoặc tín hiệu xác nhận. Kiểm thử worker mất phiên và khôi phục trên worker khác.
4. Merge integration. Chỉ quan sát merge đã xác nhận và checkpoint theo repo, phiên, PR và SHA merge. Hai lần nhận cùng sự kiện chỉ tạo một checkpoint. Recovery đối chiếu nguồn thật và không phát sinh merge, push hoặc CI.
5. Pilot. So sánh native mặc định, nén ở mỗi safe point sau merge và chính sách thích ứng trên workload tương đương. Đo context, cache, thời gian, công việc làm lại và chất lượng. Tách số theo runtime.
6. Canary và rollout. Chỉ sau khi có số đo và kiểm tra rollback, với flag mặc định tắt. Adapter Agent Desktop/X-Working cần đối chiếu trong repo của thành phần đó.

Giữ FIFO và CI bắt buộc. Mỗi lát có Gate riêng và mở PR nháp khi đến lượt. Giữ D-610 cho các dự án đích.
