# Audit delta X-Templates — 2026-11-27

Mốc `60681783` trên `main`. Audit plan yêu cầu quét lại 11 nhóm. Dải nền `78ad81dd..60681783`, riêng UI và hiệu năng `008b03b0..60681783`. Kết quả dưới đây ghi phạm vi đã kiểm trong từng nhóm. Sổ ghi các phát hiện mới và kế hoạch xử lý được duyệt ở D-638.

## Kết luận ở mốc audit

Một phát hiện 🔴, bảy 🟠 và một 🟢 về trải nghiệm tải lại ghi chú. Blueprint có 65 MUST đạt, 5 miễn và 0 mở. Audit nghiêm ngặt đã đỏ trước đợt này vì 9 mục 🟠 mở và một nợ review 🟢. Cần xử lý các phát hiện đang mở và xác nhận điều kiện phát hành trước 3.37.0.

## Phạm vi và bằng chứng

| Kiểm | Mã thoát | Kết quả |
|---|---|---|
| `xt.py audit plan --blueprint BLUEPRINT.md --status docs/ops/AUDIT-STATUS.md --json` | 0 | 13 nhóm áp dụng, 11 nhóm cần quét lại, 68 bằng chứng hoặc miễn trừ cần đối chiếu do tệp đổi |
| `xt.py blueprint-status BLUEPRINT.md --strict --json` | 0 | 65 đạt, 5 miễn, 0 MUST mở, kiểm tĩnh |
| `xt.py doctor --json` trên Python 3.15.2 | 0 | Công cụ cổng đã cài, detector sandbox của khung còn một cảnh báo |
| `quality` và `coverage` trên `60681783` | 0 | GitHub CI đạt cổng 100% dòng và nhánh. Lint và typecheck cũng đạt cục bộ. [CI](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/46038052884) |
| `gitleaks git --redact` với bản 8.30.1 ghim SHA-256 và tham số CI | 0 | 2.333 commit được quét, 0 phát hiện |
| `npm audit --package-lock-only --ignore-scripts --audit-level=moderate --prefix tests_e2e/verify-render-deps` | 0 | 4 gói, 0 advisory tại thời điểm quét |
| `python3 tests_e2e/pack_ui.py` trên Chromium | 0 | 15 ô ma trận Notes UI, 25 cặp tương phản, hai đối chứng đỏ đúng kỳ vọng |
| `audit check docs/ops/AUDIT-STATUS.md --strict` trước khi thêm phát hiện | 1 | 9 mục 🟠 mở và AUD-HAR-568 là nợ review 🟢 còn mở |
| `release-check --json` ở mốc liền trước `6adbd4ad` | 1 | `NO-GO` ở `audit`, `verify` và `review_debt`; 69 lệnh kiểm Blueprint đạt |

Các cụm reviewer rà luồng cài và nâng, CPU, i18n, đóng gói, kiểm phát hành, CI, tài liệu và tài sản Notes UI. CI đã chạy [CodeQL](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/46038052919), [Gitleaks](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/46038052953) và [quét phụ thuộc](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/46038052835) trên mốc audit. Trong 68 mục Blueprint/backlog cần đối chiếu, 43 lệnh ghi kèm đạt; ba lệnh guard chưa chạy ở lượt này, 22 mục được đọc theo tham chiếu vì thiếu lệnh ghi kèm. Chưa kiểm đủ bằng chứng, chưa rà từng thay đổi trong các nhóm quét rút gọn. Chưa đo Core Web Vitals ở đích hoặc workload thật trên WSL2. Giữ SHA nhóm cũ cho tới khi các phần còn lại được kiểm.

## Phát hiện và ca tái hiện

| ID | Bằng chứng trên luồng thật | Xác minh |
|---|---|---|
| AUD-XFEAT-057 🟠 | Trong repo tạm, cài `--harness codex --codex-models`, lấy argv từ `install_options(manifest)` rồi cài lại. Mã thoát 0 nhưng bốn agent mất trường `model`; executor mất cả `model_reasoning_effort`. Đối chứng truyền lại cờ giữ được pin. | Reviewer thứ hai tái hiện ở commit đầu có opt-in và ở `6adbd4ad`. Bản cài kế thừa vẫn kế thừa. |
| AUD-CODE-068 🟠 | Với `XT_RESOURCE_WAIT_TIMEOUT=1`, giữ khoá khay tạm. Sau 1,251 giây kể từ lúc gọi thử, nhả khoá. CLI trả 0 và chạy lệnh con. Đồng hồ giả cũng cho cấp lease đúng lúc hết hạn. | Reviewer thứ hai tái hiện cả hai ca, ca đối chứng giữ khay đầy trả 2. |
| AUD-XFEAT-058 🟠 | `static-check i18n` trả 0 khi bản dịch bỏ `{name}` trong plural hoặc đổi tên trong select. Cùng sai khác ở cấp đầu trả `LOC004`. Khoá `invoice.total` và object `invoice.total` trùng nhau bị hợp nhất im lặng. | Reviewer thứ hai tái hiện hai dạng ICU và kiểm đối chứng đổi selector hợp lệ. Ca khoá trùng do reviewer phát hiện. |
| AUD-HAR-582 🟠 | Repo tạm đổi riêng `notes-ui/app.js` hoặc `contrast-pairs.txt` bỏ sót nhóm PERF/A11Y. Đổi `tests_e2e/verify_render.test.mjs` hoặc `tests_e2e/pack_ui.py` bỏ sót TEST. | Phiên chính đối chiếu `_path_groups` trên cả bốn đường dẫn. Ca `tests/test_pack_ui.py` vào TEST. |
| AUD-A11Y-004 🔴 | Chromium ở 320 px, khung `overflow:hidden` viền 30 px. Chữ vượt mép cắt x=194 tới x=210,55 nhưng chưa tới mép ngoài x=224. Reflow strict trả 0. Ca đối chứng vượt mép ngoài trả 1. | Hai reviewer độc lập đo trên HTTP loopback, xác nhận cả `overflow:hidden` và `clip`. Bỏ viền để chữ vượt mép cho exit 1; mở đủ rộng cho exit 0. |
| AUD-CI-049 🟠 | Thử cả hai bộ lọc `jq` của `release-tag.yml` với release công bố có `other.tar.gz` và `other.promotion.json`. Cả hai trả `released`; bên tải yêu cầu đúng stem của repo và tag. Kiểm `VERSION` tại tag cũng khác hợp đồng downstream. | Phiên chính tái hiện kết quả hai bộ lọc với cùng fixture. |
| AUD-DEP-040 🟠 | CI cài verify-render bằng `--no-audit`, required dependency audit chỉ bao phủ Python và starter. Dependabot thiếu thư mục verify-render. | Reviewer kiểm tệp ghim và advisory, phiên chính chạy lại npm audit độc lập. |
| AUD-XFEAT-059 🟠 | Fixture mã nguồn chạy `rollout-drill --require-ready` với adapter prod thiếu `deploy_env_pass`. Báo `ready_for_pipeline_review`; preflight non-dev đòi khoá này. | Hai reviewer chạy fixture loopback và GitHub giả. Thiếu khóa hoặc giá trị `null` cùng báo ready nhưng preflight từ chối. Danh sách rỗng được khai rõ đạt đối chứng. |
| AUD-A11Y-005 🟢 | Với 100 ghi chú ở 320×800, đang tải lại thì focus về `BODY`. Sau GET 503, thông báo ở y=9.441 px và nút tải lại ở y=547 px. Axe không báo vi phạm trong ca này. | Đo trên fixture loopback. Chủ xử lý: người duy trì starter web-api-ts. Xét lại 2026-12-31. |

AUD-HAR-567 được kiểm riêng: shadow mở và shadow đóng cho kết quả như #856 mô tả. Pseudo có `content: ""` và nền rộng hơn khung vẫn xanh. Ca cuộn lồng hiện được mô tả là advisory. Khoản nợ này giữ nguyên cho tới khi xác định và kiểm được phạm vi cần chặn.

## Kế hoạch sau audit

[PLAN-harden đã duyệt theo D-638](../autopilot/PLAN-harden-2026-11-27-audit.md) chứa một Gate cho mỗi lát sửa. Sau khi merge, chạy lại audit theo nhóm, trả nợ review và kiểm G7. Cài đặt GitHub App, ruleset tag, release immutability và diễn tập T-4007/T-5020 vẫn cần quyền quản trị. Payload `PreSkillShellCommand` và số đo WSL2 vẫn cần các môi trường tương ứng.
