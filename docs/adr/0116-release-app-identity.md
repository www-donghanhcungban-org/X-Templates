# ADR-0116: Danh tính GitHub App cho phát hành tag

- **Trạng thái:** Đã chấp nhận (D-637); T-4007 còn mở cho cấu hình và kiểm chứng live.
- **Tiếp nối:** [ADR-0095](0095-immediate-effect-early-review.md), nghiên cứu `research/2026-11-23-tag-ruleset-release-identity.md`.

## Quyết định

Sau khi ứng viên qua job duyệt, workflow chọn `tag-app` khi repository variable `XT_RELEASE_APP_CLIENT_ID` được khai. Installation token giới hạn repo hiện tại với quyền Contents và Workflows write. Private key lấy từ environment secret trong Actions Environment `xt-release`, giới hạn bằng rule Branch chính xác `main` và chỉ lưu ở cấp environment. Job dùng `deployment: false` và vẫn chịu quy tắc environment. Mint lỗi hoặc token rỗng dừng job.

Khi chưa khai Client ID, job `tag` dùng checkout PAT/GITHUB_TOKEN hiện có và chạy độc lập với action tạo token App và environment. Hai job dùng chung nhóm concurrency theo phiên bản và dùng YAML anchors để chia sẻ các bước kiểm SHA, attestation và công bố release nháp bằng GITHUB_TOKEN. GitHub xác nhận anchors và aliases trên GitHub.com và Enterprise Cloud (đối chiếu 2026-11-27). [Tài liệu GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations#yaml-anchors-and-aliases)

Action xác thực bằng Client ID. Ruleset xác định ngoại lệ bằng App ID dạng số. Diễn tập CI dùng App và khoá riêng cho repo thử. Chủ repo kiểm phạm vi cài App production trước khi áp ruleset live. Chi tiết và đường lùi ở [runbook](../ops/RUNBOOK-PR-STEWARD.md#4-đẩy-tag-phát-hành-release-tagyml).
