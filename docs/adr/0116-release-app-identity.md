# ADR-0116: Danh tính GitHub App cho phát hành tag

- **Trạng thái:** Đã chấp nhận (D-637); T-4007 còn mở cho cấu hình và kiểm chứng live.
- **Tiếp nối:** [ADR-0095](0095-immediate-effect-early-review.md), nghiên cứu `research/2026-11-23-tag-ruleset-release-identity.md`.

## Quyết định

Sau khi ứng viên qua job duyệt, job phát hành dùng installation token của GitHub App khi repository variable `XT_RELEASE_APP_CLIENT_ID` được khai. Token giới hạn repo hiện tại, Contents và Workflows write; private key lấy từ environment secret trong Actions Environment `xt-release`, được giới hạn bằng rule Branch chính xác `main`, không cho tag; không để bản cùng tên ở cấp repository. Job dùng `deployment: false` và vẫn chịu quy tắc environment. Mint lỗi hoặc token rỗng dừng job. Khi chưa khai Client ID, giữ đường checkout PAT/GITHUB_TOKEN và release GITHUB_TOKEN hiện có. Giữ kiểm SHA, attestation và quy trình release nháp.

Action xác thực bằng Client ID. Ruleset xác định ngoại lệ bằng App ID dạng số. Diễn tập CI dùng App và khoá riêng cho repo thử. Chủ repo kiểm phạm vi cài App production trước khi áp ruleset live. Chi tiết và đường lùi ở [runbook](../ops/RUNBOOK-PR-STEWARD.md#4-đẩy-tag-phát-hành-release-tagyml).
