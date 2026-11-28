# Audit ngày 28/11/2026 — chi phí ngữ cảnh và thời gian

Mốc kiểm là `main` ở `719eb8b0`. Ba lỗi tái hiện được ảnh hưởng đến lượng log agent phải đọc hoặc khả năng nhận biết việc phải rà. Số byte dưới đây đo bằng UTF-8. Chi phí hóa đơn và token của phiên người dùng chưa được đo.

| Phát hiện | Tái hiện trên mã gốc | Quyết định D-645 |
|---|---|---|
| AUD-CI-050 🟠 | Chạy `loop ci-triage --run 501 --log ci.log --json` trong thư mục tạm. File gồm 10 dòng khác nhau dạng `FAIL: test_demo_{i} AssertionError: `, theo sau là 16.384 chữ q và ` EXPECTED_alpha`. Log 164.340 B, JSON 164.905 B, xuất lại dạng văn bản 164.593 B, state 165.083 B. Chỉ đổi hậu tố thành beta đã đổi chữ ký. Reviewer tái hiện qua CLI. | Giữ đầu và cuối dòng sau khi che dữ liệu, tính chữ ký trên dòng đầy đủ. Áp dụng khi ghi và khi phát lại bằng chứng cũ. |
| AUD-HAR-585 🟠 | Trong repo hai commit, ghi cùng SHA đã quét cho 13 nhóm rồi sửa `app.py`. Bình thường CLI trả bốn nhóm 1, 2, 3, 12. Khi riêng `git diff` trả 128 và stdout rỗng, CLI trả tập rỗng, exit 0. Hai lượt độc lập tái hiện cả lỗi 128 và timeout 124. Trên chính sổ khung, 13 nhóm dùng ba SHA, mỗi lượt thực hiện 26 lệnh Git tra tổ tiên và diff. | Báo rõ cần quét lại khi diff lỗi. Dùng chung kết quả Git và phân nhóm theo SHA trong một lượt. |
| AUD-HAR-586 🟠 | Với từng commit riêng, thay `.codex/hooks.json` hoặc `.codex/agents/executor.toml` cho tập rỗng, thay `.agents/skills/audit/SKILL.md` chỉ trả DOC. Cả ba là tệp Git theo dõi, là harness theo ADR-0082. | Đưa cả ba bề mặt vào HAR, giữ các nhóm đã áp dụng cho cùng đường dẫn. |

## Phạm vi và cổng

- `audit plan --json` đếm 1.053 tệp, 215 tệp test, 13 workflow và chỉ ra 11 nhóm cần rà lại. Đợt này rà CLI, cổng, harness và đường đi của log, chưa phủ mọi thay đổi ở 11 nhóm. Giữ SHA kiểm nhóm trước đó cho các phần còn mở.
- `blueprint-status BLUEPRINT.md --strict --run` exit 0, 65 MUST đạt, năm miễn, không có MUST mở. `audit plan` đánh dấu 68 tham chiếu có tệp đã đổi, gồm một miễn trừ. `doctor --json` exit 0 với một cảnh báo môi trường thiếu sandbox.
- Trên cùng SHA, CI đạt cả quality và coverage. Job verify-render và sáu ca nghiệm thu gói hoàn thành. Quét dependency, CodeQL và secret scan đều đạt. Bằng chứng này dành cho mốc trước sửa. [CI](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/46154269522) · [Nghiệm thu UI và dữ liệu](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/46154269519) · [Secret scan](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/46154269534) · [Dependency audit](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/46154269521) · [CodeQL](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/46154269524).
- Với log coverage thật của PR #904, công cụ chọn một dòng dài 57 ký tự trên log 94.688 byte. Lợi ích về ngữ cảnh tập trung ở ca dòng dài. [Job đã đo](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/46154912933/job/141011847296).
- `audit check` exit 0 trên mốc gốc. `audit check --strict` exit 1 với sáu mục 🟠 đang mở trước đợt này. Sổ hiện hành nêu chủ và phạm vi của từng khoản.

## Hai cơ hội ưu tiên thấp

`xt.py checks` dựng parser sáu lần để chạy năm kiểm. cProfile ghi 0,157 giây cộng dồn trong parser. Chưa đo thời gian sau tối ưu. Workflow dependency audit gọi pip-audit hai lần để xuất bảng và SBOM. Trên 12 run xanh, mỗi bước có trung vị một giây. Bảng chẩn đoán hiện có thông tin giúp sửa CVE. Hai cơ hội được ghi để đối chiếu khi có profile mới.

## Kết quả sửa ci-triage

| Cùng fixture, cùng ID | Trước | Sau |
|---|---:|---:|
| JSON gửi agent | 164.905 B | 6.595 B |
| Token trong cùng JSON, bộ mã hóa `o200k_base` | 82.271 | 3.091 |
| Văn bản khi gọi lại | 164.593 B | 6.283 B |
| State sau một run | 165.083 B | 6.773 B |
| State sau hai run | 329.893 B | 13.283 B |

Mỗi dòng dài giữ đầu, cuối và dấu cắt trong 600 ký tự. Hai chữ ký của biến thể alpha và beta vẫn khớp kết quả gốc. Hai ca hồi quy đỏ trước sửa. Sau sửa, 50 test triage CI/cục bộ, ghi state và trần kích thước đạt, exit 0. Đếm toàn bộ JSON bằng `len(tiktoken.get_encoding("o200k_base").encode(text))`, tiktoken 0.12.0 chạy riêng ngoài dự án ngày 28/11/2026. Fixture giảm 96,2% token với bộ mã hóa này. [tiktoken](https://github.com/openai/tiktoken)

Đối chứng trên năm lượt CI đỏ gần nhất tại thời điểm đo, dùng `gh run view ID --log-failed`. Log từ 9.770 B đến 1.488.610 B, dòng bằng chứng dài nhất từng lượt lần lượt là 57, 57, 57, 190 và 55 ký tự. Cả năm giữ nguyên toàn bộ bằng chứng và tiết kiệm 0 token từ phần này. Mẫu hiện tại cho thấy giới hạn có tác dụng ở ca log bất thường. [Lượt 1](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/46154912933) · [Lượt 2](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/46145557879) · [Lượt 3](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/46113766233) · [Lượt 4](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/46112995241) · [Lượt 5](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/45990523804).
