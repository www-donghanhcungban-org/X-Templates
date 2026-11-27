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

## Rà bổ sung ở `feb86abd`

Reviewer kiến trúc chạy nạp 14 bộ kiểm tĩnh và bốn module đã chọn khi chưa nạp `xt`. Kiểm AST 19 module và đối chiếu danh sách mô-đun đi kèm của installer/pack đều qua. Bộ test cost, sổ lát, toolcfg, JSON shape qua 55 kiểm. Bộ API PR và kiểm liên kết qua 56 kiểm. Phạm vi ARCH, CODE và XFEAT còn rút gọn ở hook, nhánh ghi của steward, phê duyệt thiết kế, installer, CPU, deploy, release và thuật toán từng bộ kiểm tĩnh.

Reviewer SEC, CI và DEP kiểm bốn workflow đổi, ruleset, cấu hình release/review và lock verify-render. `ci-check`, `license-check`, Zizmor ở ngưỡng cao và 17 kiểm tập trung đều đạt. Actionlint kèm ShellCheck báo `SC2129` trên cả mốc cũ và mốc mới. Zizmor ở ngưỡng trung bình báo hai checkout phát hành giữ credential để chạy Git. Hai job này chỉ xuất artifact đã chọn. GitHub trả 404 với environment `pr-review` và `xt-release`. Chưa diễn tập quyền của App hoặc phát hành thật. [Dependency audit](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/46049830349)

| Phát hiện | Xác minh đối kháng |
|---|---|
| AUD-CODE-069 🟠 | `loop record --task T-0010 --cost '' -- true` trả 0 và ghi bằng chứng. Reviewer khác dùng Gate tạo marker kiểm được lần chạy. `pr reviewed --no-publish` cũng ghi dấu cục bộ với cost rỗng. Cost sai có nội dung trả 2 trước khi ghi. |
| AUD-XFEAT-061 🟠 | Trong hai Git scratch riêng với REST GET giả, `GH_REPO` khác origin làm API danh sách từ chối và API thống kê lấy số từ repo khác. Đối chứng cùng repo cho kết quả thống nhất. |

D-640 duyệt hai lát riêng T-5092 và T-5093, giữ nguyên trạng thái mở đến khi qua Gate và vào `main`. SHA quét theo nhóm giữ ở mốc trước cho tới khi các đường dẫn còn lại được rà.

## Kiểm lại `main` sau #873

Ở `75eb07cd`, kết quả `loop verify --all` đạt 1 Gate Chromium và 69 lệnh Blueprint. `release-check` trả `NO-GO` với 17 lỗi audit strict và 147 tệp ngoài tài liệu còn nợ review. `audit plan` yêu cầu quét lại 11 nhóm và báo 68 bằng chứng cũ. Gitleaks quét 901 commit tổ tiên của SHA này và không phát hiện bí mật. `npm audit` trên lock của verify-render trả 0 cảnh báo. [CI của commit đã kiểm](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/46057710185)

## Truy vết tiêu chí trong Markdown ở `75eb07cd`

Hai lượt độc lập xác nhận `ac-trace` báo đạt với code span ở đầu dòng chứa mã AC thiếu test. Dạng mã trực tiếp báo `ACT001`. Thêm đúng mã vào test thì dạng code span lại báo `ACT002`. Mẫu SPEC gốc có ba tiêu đề S-NNN và thiếu bảng mã AC, nên cùng cổng này trả 0 với thư mục test chưa có test tham chiếu. D-641 đăng ký AUD-XFEAT-062 mức 🔴 và giao T-5094 sửa parser, nối hai bộ mã trong mẫu. [WF-SDD-002/003](../../framework/10-workflow/spec-driven-development.md) · [PM-SPEC-002/004](../../framework/17-product-project/specification.md)

## Delta A11Y và PERF trên Notes UI

Đã rà hai tệp UI của delta nhóm 5/6 từ `008b03b` và đối chiếu thêm mã JS với danh sách cặp tương phản. `xt.py contrast` đạt 25/25 cặp. Mức thấp nhất là 6,22:1 cho chữ và 3,69:1 cho thành phần phi văn bản. Reflow và ma trận Notes UI 15 ô đạt ở #872, các tệp liên quan khớp byte với `75eb07cd`. Chromium ở 320×800 cho thấy focus về thân trang khi GET chờ và trở lại nút Tải lại khi nhận 503. AUD-A11Y-005 còn mở vì phản hồi nằm xa nút khi có 100 ghi chú. [CI #872](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/46055219138)

Ba tài sản Notes UI tăng từ 11.387 lên 12.980 byte. Gzip ngoại tuyến tăng từ 4.219 lên 4.600 byte. Trang dùng ba request cùng origin. PERF giữ mức rút gọn tới khi có số Core Web Vitals, Lighthouse và độ trễ đích.

## Delta DEP và CI trên `75eb07cd`

DEP rà hai tệp của verify-render. Bốn bản ghi registry khớp version, license, URL và SHA-512 trong lock, npm audit trả 0 advisory. Hai lượt kiểm độc lập xác định `@axe-core/playwright` và `axe-core` 4.13.0 thuộc MPL-2.0. D-133 áp cho nguồn axe vendored riêng. D-642 ghi phạm vi dev/CI và giao T-5095 bổ sung inventory. AUD-DEP-040 vẫn mở vì required audit và Dependabot chưa bao phủ lock này.

CI rà bốn workflow đổi từ `78ad81dd`. `ci-check`, 68 test và zizmor ngưỡng high đạt. CI chính thức có đủ năm context bắt buộc. Run pack cùng byte workflow và lock đạt nghiệm thu Chromium. AUD-CI-049 giữ mở do bộ lọc còn nhận sai tên asset. `pr-review` dispatch và `tag-app` sau #868 còn chờ diễn tập live, giữ nhóm CI ở mức rút gọn. [CI exact](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/46057710185) · [Pack](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/46056231988)

Đối chiếu chứng cứ Blueprint ở cùng SHA cho thấy 46 trong 68 mục bị đánh dấu cũ có lệnh `loop verify --all` đã chạy xanh. 22 mục còn lại gồm 19 tham chiếu và ba miễn trừ hoặc mục không áp dụng. Cập nhật mốc chứng cứ theo kết quả khi rà từng mục.

Sau mốc trên, #874 đóng AUD-XFEAT-057 ở `fc18c250`. Cổng cục bộ của bản sửa và CI trên head đã đạt. [PR #874](https://github.com/www-donghanhcungban-org/X-Templates/pull/874)
