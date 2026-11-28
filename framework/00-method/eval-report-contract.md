---
title: Hợp đồng báo cáo eval và cổng theo chính sách
kind: method
updated: 2026-11-28
---

# Hợp đồng báo cáo eval và cổng theo chính sách

**Schema 1 · 28/11/2026.** `static-check eval-report` kiểm báo cáo eval có cấu trúc và đối chiếu một chính sách do bên nghiệm thu cấp. Quy tắc chất lượng nằm tại [evaluation.md](../13-ai-engineering/evaluation.md). Bộ kiểm chỉ đọc, dùng stdlib, không gọi dịch vụ ngoài và không chạy model.

## 1. Hai chế độ có ý nghĩa khác nhau

| Chế độ | Kiểm gì | Ý nghĩa khi không có finding |
|---|---|---|
| `validate` — mặc định | Định dạng, trường bắt buộc, kiểu, ID/lượt duy nhất, bằng chứng được khai và tổng đếm | Báo cáo hợp lệ về hợp đồng. `checked.quality_gates=0`, `schema_only=1`. Báo cáo có ca thất bại vẫn có thể hợp lệ. |
| `gate` | Toàn bộ `validate`, rồi so identity, phạm vi, lượt, provenance được khai, thời hạn và ngưỡng với policy ngoài report | Các kết quả được khai đáp ứng policy đã cấp. `quality_gates=1` chỉ khi mọi kiểm tra đạt; đây chưa phải chứng thực tính xác thực của người chạy hoặc artefact. |

Các lệnh dưới đây dùng checkout nguồn; trong dự án đã cài, dùng `.xtemplates/scripts/xt.py` thay `scripts/xt.py`. Fixture và test dành cho người phát triển nằm trong checkout nguồn, không thuộc bản cài.

Cả hai chế độ từ chối đầu vào không có report. `gate` nhận đúng một report; nhiều lượt thử phải được khai trong cùng report theo policy, không gộp âm thầm nhiều report. Các tuỳ chọn không biết và `ignore` bị từ chối.

```bash
python3 scripts/xt.py static-check eval-report EVAL-REPORT.json --json
python3 scripts/xt.py static-check eval-report EVAL-REPORT.json --json \
  --opt mode=gate --opt policy=EVAL-POLICY.json \
  --opt revision=<SHA-40-hoặc-64-ký-tự-hex-thường> \
  --opt at=2026-11-28T15:00:00Z
```

`revision`, policy và thời điểm `at` phải đến từ người/cổng nghiệm thu độc lập với report. `at` là thời điểm xét bằng chứng, có múi giờ; người chạy truyền nó tường minh để phép kiểm tất định và chạy lại được. Không chép các giá trị kỳ vọng từ chính report rồi gọi đó là xác minh độc lập. Trong một pipeline, ghim policy vào bản đã được duyệt, SHA vào ứng viên và `at` vào thời điểm của job.

Mã thoát theo `static-check`: 0 không có finding; 1 có finding; 2 dùng sai. `EVR000` là lỗi hợp đồng; `EVR001` là không đáp ứng policy. Việc hết hạn bằng chứng, thiếu case hay ca critical thất bại không được biến thành N/A.

## 2. Báo cáo schema 1

Các mảng `cases` và các danh sách trong policy vượt 100.000 phần tử bị từ chối trước khi duyệt phần tử; report vượt hạn không được tính vào `checked.case_records`. Giới hạn bytes vẫn áp dụng.

Mọi object dùng đúng bộ khoá đã nêu; khoá thừa cũng bị từ chối để tránh người đọc và máy hiểu hai hợp đồng khác nhau. JSON lặp khoá, số `NaN`/`Infinity`, boolean thay số, chuỗi rỗng/đệm khoảng trắng, hash sai dạng đều không hợp lệ. Tệp phải là UTF-8 thường, tối đa theo giới hạn 2 MiB của `static-check`; không đi theo symlink tại tệp đích.

| Trường | Hợp đồng |
|---|---|
| `schema`, `kind` | Số nguyên `1`, chuỗi `eval-report`. |
| `identity` | Object `{suite, eval_version, dataset_sha256, scorer_sha256, config_sha256, environment_sha256}`. `suite` khác rỗng; `eval_version` theo `N-X` (AI-EVAL-023): N là số nguyên dương không có số 0 đầu, X gồm một hoặc nhiều chữ A–Z, ví dụ `1-A`, `2-B`, `10-AA`. Bốn digest là SHA-256 hex thường. |
| `run_id` | ID lần chạy khác rỗng. Chọn ID không chứa thông tin riêng tư. |
| `timestamp` | RFC 3339 có giây và múi giờ. Nếu có phần lẻ giây, chấp nhận 1–6 chữ số và từ chối độ chính xác cao hơn để tránh làm tròn im lặng ở biên freshness. Offset có giờ 00–23/phút 00–59 và xác định rõ. Cùng quy tắc áp dụng cho `at`. |
| `revision` | SHA Git đầy đủ, 40 hoặc 64 ký tự hex thường. |
| `dirty` | Boolean. Báo cáo cây bẩn được `validate`; `gate` luôn yêu cầu `false`. |
| `content_sha256` | Digest nội dung triển khai được đánh giá, so với policy ngoài report. |
| `runtime` | Object `{implementation, version, platform}` bằng chuỗi khác rỗng, so chính xác với policy. |
| `claim` | Một trong bốn loại ở bảng dưới. |
| `execution` | Object `{mode, cache, attempts_per_case}`. `mode=fresh|replay`; `cache=off|provider|replay`; `attempts_per_case` là số nguyên 1–1000. `mode=replay` khi và chỉ khi `cache=replay`. |
| `cases` | Mảng 1–100.000 bản ghi, mỗi cặp `id`/`attempt` duy nhất. Giới hạn bytes vẫn áp dụng trước giới hạn số ca. |
| `counts` | Object gồm `total`, `eligible` và đủ sáu trạng thái. Các giá trị là số nguyên không âm, khớp hoàn toàn với `cases`. |

| Claim | Phạm vi được khẳng định |
|---|---|
| `real-path` | Báo cáo khai đã đi qua đường thực; chỉ nhận `execution.mode=fresh`. Checker chưa chứng thực lời khai này. |
| `faithful-fixture` | Replay từ lần chạy thật có provenance truy lại được; chỉ nhận `execution.mode=replay`, kết luận giới hạn ở dữ liệu nguồn và fixture đã giữ. |
| `asserted-not-measured` | Chỉ là lời khai/chưa đo. Có thể lưu qua `validate`; không được policy cho qua `gate`. |
| `synthetic-fixture` | Dữ liệu viết tay để thử chính checker, có thể mô tả fresh hoặc replay. Chỉ được gate khi policy cho phép rõ; không tính là số đo chất lượng sản phẩm hay model. |

Quan hệ claim/mode là hợp đồng schema: policy có cho phép cũng không hợp thức hoá `real-path` đi với replay hoặc `faithful-fixture` đi với fresh. Nhãn `asserted-not-measured` vẫn lưu được ở chế độ validate để thể hiện khoảng trống, nhưng gate luôn từ chối.

Mỗi bản ghi case có đúng `{id, attempt, cluster, status, evidence_sha256}`. `attempt` bắt đầu từ 1. `cluster` là đơn vị gom các ca/lượt có phụ thuộc; policy ghim nó theo từng ID. `evidence_sha256` là digest bằng chứng được khai cho bản ghi, không được bỏ ngay cả khi kết quả không đạt.

`status` nhận `pass`, `fail`, `infra_failure`, `error`, `unscored`, `skipped`. Chỉ `infra_failure` có thêm `infra_confirmation={confirmed, reason, evidence_sha256}`: boolean xác nhận, lý do khác rỗng và digest bằng chứng hạ tầng. Thiếu trường này là lỗi hợp đồng; `confirmed=false` là báo cáo hợp lệ nhưng không qua gate.

`counts.total` bằng số bản ghi; mỗi bộ đếm trạng thái bằng đúng số hàng tương ứng. `counts.eligible = total - infra_failure`. Chế độ validate chỉ đối soát phép đếm này; gate xác nhận độc lập mọi hàng bị loại trước khi chấp nhận mẫu số.

## 3. Policy được cấp từ ngoài report

Policy dùng `schema=1`, `kind=eval-policy`, `policy_id` khác rỗng và các trường sau:

| Trường | Ý nghĩa |
|---|---|
| `identity`, `content_sha256`, `runtime` | Bộ giá trị kỳ vọng độc lập, cùng hợp đồng với report. Thay corpus, scorer, cấu hình hoặc môi trường đòi policy tương ứng. |
| `case_ids` | Tập ID dự kiến khác rỗng, không trùng, không lấy lại từ kết quả đã lọc. |
| `critical_ids` | Tập con không trùng của `case_ids`; có thể rỗng khi bên nghiệm thu xác nhận không có ca critical trong suite này. |
| `clusters` | Object có đúng khoá là `case_ids`, giá trị là cluster đã chốt. Không dùng cluster mới để giả số đơn vị độc lập. |
| `attempts_per_case` | Số lượt 1–1000, áp dụng mọi case. Tổng ID × lượt không vượt 100.000. |
| `min_success_rate` | Ngưỡng hữu hạn trong [0, 1] trên mẫu số eligible. |
| `max_infra_rate` | Trần hữu hạn trong [0, 1] trên mẫu số total. |
| `max_age_seconds` | Tuổi bằng chứng tối đa, số nguyên 1–31.536.000 giây tính tại `at`. Report ở tương lai bị từ chối. |
| `allowed_claims` | Danh sách không rỗng, không trùng; không được chứa `asserted-not-measured`. |
| `allowed_execution_modes`, `cache` | Các mode được chấp nhận và cache kỳ vọng; replay không tự được coi là lần chạy mới. |
| `infra_exclusions` | Danh sách xác nhận độc lập `{id, attempt, reason, evidence_sha256}`. Mỗi cặp duy nhất, ID/lượt nằm trong phạm vi. |

Gate đòi tập cặp `id`/`attempt` đúng bằng `case_ids × [1..attempts_per_case]`. Không được loại ca thất bại, thêm ca dễ, bỏ lượt, nhân đôi kết quả hoặc đổi cluster rồi giữ nguyên kết luận. Summary từ report chỉ được sử dụng sau khi đã kiểm lại từ toàn bộ case.

Mọi lượt của ca critical phải `pass`, bất kể điểm trung bình. `error`, `unscored` và `skipped` luôn làm gate đỏ. Ca không critical có thể `fail` nếu vẫn đạt ngưỡng bên nghiệm thu đã chốt trước; report không được tự mang theo ngưỡng thay thế.

## 4. Phân loại lỗi hạ tầng và tỷ lệ

Một ca chỉ được loại khỏi eligible khi cả bốn điều kiện cùng đúng: status là `infra_failure`; `confirmed=true`; ID/lượt/lý do/digest xác nhận khớp chính xác với `infra_exclusions` của policy; tỷ lệ hạ tầng không vượt trần. Policy có xác nhận không được dùng trong report cũng bị từ chối để hồ sơ của run không nhập nhằng.

```text
total = tất cả các ca/lượt đã chốt
eligible = total - số lỗi hạ tầng được xác nhận độc lập
success_rate = pass / eligible
infra_rate = infra_failure / total
```

Gate không chấp nhận eligible bằng 0. Lỗi của scorer, output không parse được hoặc chưa chấm không tự động là lỗi hạ tầng. Nếu ca critical không có kết quả vì hạ tầng, gate vẫn đỏ: phải chạy lại theo chính sách và lưu lịch sử trước khi kết luận đạt. Người nghiệm thu phải kiểm nguồn xác nhận; đổi nhãn `fail` thành `infra_failure` trong report không đủ để thay mẫu số.

## 5. Fixture và kiểm tra checker

`tests/fixtures/evaluation/policy.json` và `tests/fixtures/evaluation/report.json` trong checkout nguồn là **dữ liệu tổng hợp viết tay**. Các SHA lặp ký tự, runtime và thời điểm trong đó phục vụ test, không mô tả một lần chạy sản phẩm. Policy chỉ cho `synthetic-fixture`.

```bash
python3 scripts/xt.py static-check eval-report tests/fixtures/evaluation/report.json --json \
  --opt mode=gate --opt policy=tests/fixtures/evaluation/policy.json \
  --opt revision=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --opt at=2026-11-28T15:00:00Z
python3 -m unittest tests.test_check_eval_report
```

Bộ test `tests/test_check_eval_report.py` trong checkout nguồn có ca đối chứng cùng ca đối kháng: schema-only với kết quả fail; critical fail dù ngưỡng bằng 0; thay revision/corpus/scorer/content/runtime; bằng chứng cũ/tương lai; thay case/attempt/cluster; replay/cache; tự nhận lỗi hạ tầng; mẫu số rỗng; skip/unscored/error; đếm sai; thiếu evidence; boolean thay số; số không hữu hạn; khoá JSON trùng; quét rỗng và `ignore`. Các phép kiểm này chứng minh hành vi checker trong những ca đã thử.

## 6. Ranh giới bằng chứng và phần chưa triển khai

`eval-report` không chạy eval, không mở nội dung artefact theo digest, không xác minh chữ ký và không chứng minh report do runner hoặc model thật tạo. Muốn kiểm bytes, dùng `eval-evidence` tại §7. Digest đúng định dạng hoặc khớp một policy chưa được duyệt không phải bằng chứng độc lập. Muốn dùng cho quyết định phát hành, bên nghiệm thu vẫn cần nguồn policy được ghim, log/artefact giữ được, người/cổng tạo report độc lập với tác nhân được chấm và phép xác minh nguồn tương ứng. Với `faithful-fixture`, artefact nguồn phải truy lại được run/revision/môi trường thật đã sinh dữ liệu; dữ liệu viết tay giữ nhãn `synthetic-fixture`. Hash bytes không tự chứng minh các mối liên hệ về nguồn đó đúng.

Schema 1 ghi số lượt và cluster, không tính khoảng tin cậy, paired significance, pass@k, mức suy giảm thống kê, chi phí hay độ trễ. Không được suy các kết luận đó từ `counts` hoặc cộng các lượt cùng cluster như mẫu độc lập. `scorer_sha256` ghi danh tính scorer, chưa chứng minh scorer được calibration; scorer dựa trên model vẫn cần đối chiếu nhãn độc lập và lưu bằng chứng calibration riêng. Các phần này là bước mở rộng có version và ca nghiệm thu riêng, không được tự khai đã đạt nhờ `mode=gate`.

## 7. Cổng mở và kiểm bytes artefact

```bash
python3 scripts/xt.py static-check eval-evidence EVAL-REPORT.json --json \
  --opt policy=EVAL-POLICY.json --opt revision=<SHA-Git-đầy-đủ> \
  --opt at=2026-11-28T15:00:00Z --opt artifacts=/duong-dan-tuyet-doi/kho-bang-chung
```

`eval-evidence` nhận đúng một report và bốn tuỳ chọn trên, luôn chạy đầy đủ cổng policy. Report và policy mỗi tệp đọc một lần; dùng cùng snapshot cho schema, policy và danh sách bytes cần kiểm. Cổng không nhận `mode=validate` hoặc `ignore`.

Kho có cấu trúc phẳng: tên mỗi tệp là SHA-256 hex thường của chính bytes tệp. Bắt buộc có blob cho `content_sha256`, bốn digest trong `identity`, mọi `cases[].evidence_sha256`, và digest xác nhận hạ tầng khi có. Cùng digest được đọc một lần. Extra file không được dùng để thay blob thiếu; không suy chất lượng từ số file trong kho.

Mỗi blob phải là file thường; cổng chấp nhận tối đa 16 MiB mỗi blob, tổng tối đa 128 MiB và tối đa 4.096 digest khác nhau. Khi đọc, checker có thể lấy thêm tối đa một byte để phát hiện vượt giới hạn từng tệp hoặc tổng, rồi dừng với lỗi. Report/policy vẫn chịu giới hạn 2 MiB. Dữ liệu lớn hơn dùng manifest được chuẩn hoá và ghim độc lập; cổng chỉ bảo đảm bytes của manifest đã cấp, không tự truy cây phụ thuộc bên trong nó.

Đường dẫn kho không qua symlink hoặc `..`. Checker ghim directory descriptor và mở từng digest tương đối, không theo symlink và không chờ FIFO. Nền tảng thiếu directory-relative open/no-follow trả lỗi dùng sai, chưa được coi là hỗ trợ. Không đi theo thư mục thay thế giữa lúc kiểm và lúc đọc. Các blob vẫn cần được quản lý bất biến trong lúc xét; hash bảo đảm bytes đã đọc, không chứng nhận file sẽ không bị đổi sau khi cổng kết thúc.

`EVA000`: blob thiếu/không đọc được/không phải file thường; `EVA001`: bytes lệch digest; `EVA002`: vượt giới hạn. `EVR000`/`EVR001` giữ nguyên ý nghĩa từ cổng report. `checked.report_policy_gates` có thể bằng 1 trong khi `quality_gates=0` nếu bytes thất bại. Chỉ `quality_gates=1` sau cả policy và tất cả bytes; bộ đếm `artifacts_expected`, `artifacts_verified`, `artifact_bytes_read` nêu phạm vi thực đã xét.

Lệnh kiểm ở checkout nguồn: `python3 -m unittest tests.test_check_eval_evidence tests.test_eval_surface_parity`. Có controls artefact đủ, chia sẻ cùng digest, thiếu/sửa nội dung/đổi symlink, bằng chứng hạ tầng, sai SHA, policy sai và giới hạn đầu vào. Fixture thử bytes không chứng thực runner hay phép đo sản phẩm.
