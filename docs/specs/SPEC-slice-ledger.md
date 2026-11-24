# SPEC-slice-ledger — Sổ lát: một định danh nối yêu cầu tới sự cố, số đo đọc từ sổ

| Trường | Giá trị |
|---|---|
| ID tính năng | Mục 12 của đề xuất 2026-11-23 — `T-4008` (SPEC này), `T-4009` (ghi và đọc), `T-4010` (baseline) |
| Trạng thái | Approved for implementation (phiên chính tự duyệt, ADR-0008; PLAN đã duyệt ở D-544) |
| Phiên bản | 1 |
| Luật sẵn có (không chép lại) | `LOOP-ORCH-020` (chỉ tăng agent khi có số), sổ triển khai `docs/ops/DEPLOYS.json`, `xt_flow.report()` |
| Kế hoạch | [`PLAN-improve-2026-11-23.md`](../autopilot/PLAN-improve-2026-11-23.md) lát 1E |

## 1. User story
Là chủ dự án, tôi muốn biết một lát nghiệp vụ tốn bao nhiêu tiền, bao lâu từ yêu cầu tới production, PR có hay bị xung
đột không và có lỗi nào lọt sau merge không, để quyết tăng agent, đổi cách điều phối hay dừng một hướng **bằng số**, không
bằng cảm giác. Hôm nay `xt_flow.report()` trả `null` cho cả ba số `cost_usd_per_slice`, `ever_conflicted_pr_rate`,
`escaped_after_merge` vì không có nguồn.

## 2. Giao ước

### 2.1 Định danh lát
- `slice` = `<tên PLAN không đuôi>/<ID task đầu của lát>`, ví dụ `PLAN-improve-2026-11-23/T-4003`. Task đầu lấy theo thứ tự
  trong PLAN của tiêu đề lát (`### Lát …`); PLAN không chia lát thì mỗi task là một lát.
- Định danh không đổi khi tick, đổi tên lát hay thêm task sau; task thêm vào lát mang `slice` của lát đó.
- Yêu cầu gốc (`requirement`) là chuỗi tự do do PLAN khai (mục, issue, câu của chủ dự án) — sổ không diễn giải nó.

### 2.2 Nơi lưu
- **Mỗi lát một tệp** `.autopilot/slices/<slice với "/" thay bằng "__">.jsonl`, chỉ nối thêm, một sự kiện một dòng. Không
  có tệp chung nên hai lát song song không ghi đè nhau.
- Sổ là **trạng thái máy theo checkout**, như `.autopilot/runs.jsonl` (D-549): không theo git, nên không làm bẩn cây,
  không sinh nợ review và không đổi vân tay gói ký; guard chặn ghi tay; ghi không xuyên liên kết. Hệ quả: số đo chỉ phản
  ánh các lệnh đã chạy trên checkout đó — `coverage.slices` của báo cáo nói rõ. Sổ không ghi bí mật; giá trị đi qua
  `redact()`.

### 2.3 Sự kiện
Mỗi dòng: `{"schema": 1, "slice", "kind", "at" (UTC ISO 8601, độ lệch `+00:00` hoặc `Z`), "source" (lệnh sinh ra), "ref", "data"}`. Chỉ
ghi từ lệnh đã có — không thêm bước tay cho agent:

| `kind` | Lệnh ghi | `ref` | `data` bắt buộc |
|---|---|---|---|
| `requirement` | `loop init` (mỗi lát của PLAN) | ID lát | `text` |
| `task_green` | `loop record` exit 0 | ID task | `head`, `cmd_sha256` |
| `pr` | `pr next` lần đầu thấy PR, rồi mỗi lần verdict đổi | số PR | `verdict`, `head`, `mergeable` |
| `review` | `pr reviewed` | số PR | `why` (lý do gọi: `required`, `immediate`, `suspect`), `confirmed`, `rejected` |
| `merged` | `pr next` thấy PR đã merge | số PR | `merge_sha` |
| `artefact` | receipt `deploy` | digest | `name` |
| `deployed` | receipt `deploy` thành công | môi trường | `digest`, `receipt` |
| `incident` | `incident check` | tệp post-mortem | `severity` (`sev1`…`sev4`), `introduced_by` (số PR hoặc `null`) |
| `cost` | `loop record --cost`, `pr reviewed --cost` | `cost_id` duy nhất | `usd` hoặc `tokens` + `price` |

Cú pháp `--cost` (một chuỗi, khoá cách nhau dấu phẩy): `id=<cost_id>,usd=<số>` hoặc
`id=<cost_id>,in=<token vào>,out=<token ra>[,price_in=<USD/MTok>,price_out=<USD/MTok>,source=<nguồn giá>,as_of=<YYYY-MM-DD>]`.
Đối số sai (khoá lạ/lặp, số âm hay không hữu hạn, `usd` đi cùng token, ngày sai dạng) → mã thoát 2 trước khi chạy gì; thiếu
một phần giá vẫn ghi (số đo báo `unpriced`, không đoán giá). `loop record` chỉ ghi khi Gate xanh, vào lát của task; `pr reviewed`
ghi vào lát của `--slice` (mặc định lát của task có bằng chứng mới nhất). Không có lát hay lỗi ghi → cảnh báo stderr, không chặn.

### 2.4 Số đo (`xt_flow.report()` đọc từ sổ)
Mỗi số là giá trị **hoặc** `null` kèm mã lý do máy đọc trong `coverage.<số>`: `no_source` (chưa có lệnh nào ghi kind cần),
`no_events` (có nguồn, lát chưa có sự kiện), `window_open` (cửa sổ quan sát chưa đóng), `unpriced` (có token, thiếu giá).
- **`cost_usd_per_slice`** = tổng `usd` của các sự kiện `cost` trong lát, mỗi `cost_id` tính **một lần** (ghi lặp không
  đếm trùng). Sự kiện chỉ có `tokens` thì quy đổi bằng `price` = `{usd_per_mtok_in, usd_per_mtok_out, source, as_of}`;
  thiếu `source` hoặc `as_of` → cả số là `null` + `unpriced`, không đoán giá.
- **Lead time** = `deployed` production đầu tiên − `requirement`, theo đồng hồ. Thời gian các task chạy song song **không
  cộng** thành lead time; tổng thời gian máy (nếu cần) là số riêng.
- **`ever_conflicted_pr_rate`** = số PR của các lát từng có sự kiện `pr` với `mergeable` = `CONFLICTING` / số PR có ít
  nhất một sự kiện `pr`. Không PR nào → `null` + `no_events`.
- **`escaped_after_merge`** = số `incident` có `introduced_by` trỏ PR của lát, trong **14 ngày** sau `merged`, nhóm theo
  `severity`. Còn PR chưa đủ 14 ngày → giá trị phần đã đóng kèm `window_open` cho phần còn mở; chưa PR nào đóng cửa sổ →
  `null` + `window_open`.

## 3. Ca biên (Given/When/Then)
- Given hai lát chạy song song, When cả hai ghi sự kiện, Then mỗi lát một tệp, không merge conflict ở sổ.
- Given cùng `cost_id` ghi hai lần (thử lại), Then `cost_usd_per_slice` tính một lần.
- Given sự kiện `cost` chỉ có `tokens` và `price` thiếu `as_of`, Then số là `null` và `coverage.cost_usd_per_slice` =
  `unpriced`.
- Given hai task song song, mỗi task 3 giờ, lát xong sau 3 giờ, Then lead time là 3 giờ, không phải 6.
- Given sự cố `sev2` 20 ngày sau merge, Then không tính vào `escaped_after_merge` của lát đó.
- Given PR merge 3 ngày trước, chưa có sự cố, Then `escaped_after_merge` là `null` + `window_open`, không phải 0.
- Given dòng sổ hỏng (JSON sai, thiếu khoá, `at` không có múi giờ), Then bỏ dòng đó, đếm vào `coverage.invalid_lines`,
  không làm hỏng các số khác.

## 4. Không làm
- Không đo năng suất từng agent hay xếp hạng người; không gửi số ra ngoài repo.
- Không thêm bước ghi tay cho agent; không đọc lại API GitHub để dựng lịch sử cũ (baseline là việc của `T-4010`).
- Không dùng số trong sổ làm cổng merge hay cổng ký ở bản này.

## 5. Kiểm
- `T-4009`: `python3 -m unittest tests.test_slice_ledger tests.test_factory_metrics` phủ mọi ca ở §3 và mỗi mã `null`.
- `T-4010`: baseline 20 PR theo cùng định nghĩa §2.4, mỗi số kèm lệnh và ngày.
