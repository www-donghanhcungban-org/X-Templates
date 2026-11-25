# ADR-0099: Lệnh `static-check` theo loại và gói `xt_checks`

- **Trạng thái:** Đã chấp nhận ngày 2026-11-24 (D-564)
- **Làm rõ:** ADR-0097 (hợp đồng công khai và artefact), ADR-0043 (trần byte), tiền lệ `license-check`, `contrast`, `prompt-assets-scan`
- **Căn cứ:** bốn báo cáo rà PLAYBOOK §5–§7 của catalog stored (đọc 2026-11-24, loại mảng kiểm định công nghiệp): khung đã có ID cho khoảng hai phần ba ý; chỗ hở chính là **máy kiểm cho yêu cầu đã có** (MUST/SHOULD không có công cụ), và nhiều ý trùng nhau (chuẩn hoá NFC, rò trace OTLP, SBOM/VEX)

## Bối cảnh

Khung đòi nhiều quy tắc kiểm được bằng máy mà dự án đích phải tự viết kiểm tra (NFC cho chuỗi tiếng Việt, sổ bản quyền asset, token thiết kế, `prefers-reduced-motion`, SBOM/VEX hợp lệ, span trace mồ côi, truy vết `AC-xx` tới test…). Thêm mỗi máy kiểm một lệnh `xt.py` riêng sẽ làm `xt.py` phình thêm, đổi bề mặt hợp đồng (ADR-0097) nhiều lần và khó gỡ từng cái.

## Quyết định

- Một lệnh `python3 scripts/xt.py static-check <loại> [ĐƯỜNG…] [--opt khoá=giá-trị] [--json]` và một gói `scripts/xt_checks/`, mỗi loại một module `kind_<tên>.py`. Hợp đồng đổi **một lần** (thêm lệnh); thêm loại sau đó không đổi hợp đồng.
- Giao diện một loại: `HELP` (một dòng), `SUFFIXES` (đuôi tệp khi quét thư mục), `OPTS` (tên các khoá `--opt` loại nhận; khoá lạ hoặc mã `ignore` sai dạng → mã thoát 2), tuỳ chọn `SNIFF` (khi quét thư mục chỉ giữ tệp mang dấu hiệu đúng định dạng, để `sbom`/`vex`/`trace` không báo mọi `.json`; dạng `sniff(text, opts)` khi dấu hiệu phụ thuộc `--opt`), tuỳ chọn `NAMES` (khi quét thư mục chỉ nhận tệp đúng tên); tệp nêu đích danh luôn được kiểm, `check(files, opts) -> list[Finding]`. `Finding` gồm `path`, `line`, `code` (`<LOẠI>NNN`), `message`. Bộ duyệt tệp dùng chung: không theo liên kết, bỏ `.git`/`node_modules`/`.venv`, trần 2 MiB mỗi tệp; tệp được nêu đích danh được đọc bất kể đuôi.
- Mã thoát: 0 sạch; 1 có phát hiện; 2 dùng sai (loại lạ, đường dẫn không có, `--opt` sai). `--json` in `{"schema": 1, "kind", "findings": [...]}`. Chỉ stdlib, tất định, chỉ đọc (không sửa tệp).
- Chọn loại theo bốn tiêu chí: (1) có yêu cầu MUST/SHOULD đã đòi mà chưa có máy kiểm; (2) stdlib, tất định; (3) ít báo nhầm (có ngoại lệ khai được); (4) nhỏ (≲ 150 dòng kèm test đủ nhánh). Ý cần chạy model, trình duyệt, ffmpeg hay công cụ Java/Go ngoài **không** vào gói này.
- Gói vào artefact `.pyz` (như `xt_app`) và được `install.py` chép như module khung.

## Loại hiện có (đợt 1, 2026-11-24)

| Loại | Yêu cầu được máy kiểm | Mã | Giả định cần biết |
|---|---|---|---|
| `nfc` | `UX-CONTENT-002`, `FE-FORM-013`, `BASE-DATA-*` | `NFC000`–`003` | Chỉ báo chuỗi chưa NFC, U+FFFD, ký tự ẩn, tệp không phải UTF-8 |
| `credits` | `UX-VISUAL-007`, `CMP-LIC-026` | `CRD000`–`004` | Bảng `assets/CREDITS.md`; ô chứa nhiều tệp hay liên kết Markdown chưa hỗ trợ |
| `tokens` | `UX-DS-002`, `UX-DS-010`, `UX-DS-019` | `TOK000`–`002` | Heuristic bằng regex; `#abc` trong `href` có thể báo nhầm; ngoại lệ bằng `xt-allow: TOK002` |
| `motion` | `UX-VISUAL-001`…`003`, `UX-A11Y-015` | `MOT001`–`004` | Heuristic CSS/SCSS; khối SCSS lồng có thể xác định sai |
| `trace` | `AI-OBS-001`, `AI-OBS-008`, `AI-OBS-013`, `OPS-OBS-002` | `TRC000`–`004` | OTLP JSON hoặc JSON Lines; span có cha ở trace khác báo cả `TRC001` và `TRC003` |
| `ac-trace` | `WF-SDD-002`, `WF-SDD-003`, `WF-SDD-008` | `ACT000`–`003` | Mã tiêu chí dạng `AC-<số>` ở đầu dòng spec; tiêu chí dạng `AC-LOGIN-1` chưa nhận |
| `sbom` | `SEC-SUPPLY-012`, `SEC-SUPPLY-028`, `CMP-LIC-003` | `SBM000`–`007` | CycloneDX JSON; tỷ lệ license mặc định 0,99 |
| `vex` | `SEC-SUPPLY-030`, `SEC-SUPPLY-031` | `VEX000`–`005` | OpenVEX JSON |
| `pii-vn` | `CMP-PRIV-010`, `PM-METRIC-005`, `AI-GUARD-004`, `PRF-DATA-009` | `PII001`–`004` | CCCD: mã tỉnh 001–096 và chữ số thứ 4 trong 0–3 là heuristic, chưa đối chiếu danh sách chính thức; không quét `INSERT … VALUES` |

**Đợt 2 (2026-11-24):**

| Loại | Yêu cầu được máy kiểm | Mã | Giả định cần biết |
|---|---|---|---|
| `i18n` | `XC-I18N-009` | `LOC000`–`007` | Catalog JSON, bắt buộc `--opt source=<tệp nguồn>`; ICU chỉ kiểm cân ngoặc và quote `'{`; khoá lồng làm phẳng bằng dấu chấm; `--opt min=<0-100>` cho completeness |
| `dedup-leak` | `AI-DATA-007`, `PRF-DATA-007` | `DDL000`–`005` | JSONL/CSV; bắt buộc `--opt train=` và `--opt eval=` (tên tập = tên tệp bỏ đuôi); CSV hàng đầu là tiêu đề; near-duplicate (MinHash/LSH) chỉ chạy khi có `--opt near=`, bucket chặn 64 mục nên có thể bỏ sót |
| `srm` | `PM-METRIC-018`, `PM-METRIC-011` | `SRM000`–`006` | CSV/JSON/JSONL bản ghi gán biến thể (bỏ BOM đầu tệp); quét thư mục giữ tệp có bản ghi mang trường `--opt variant=`; chi-bình-phương Pearson (p tự cài, stdlib) ở ngưỡng `--opt alpha=` (mặc định 0,001); `--opt ratio=a:b` gán theo tên biến thể sắp tăng dần; kỳ vọng nhỏ nhất theo ratio < 5 → "chưa đủ bằng chứng" (SRM006); SRM005 là kiểm định đồng nhất bảng exposed/không exposed × biến thể (bậc k−1), bỏ qua khi không ai hay ai cũng exposed, ô kỳ vọng < 5 → SRM006; không có `--opt ratio` thì biến thể 0 bản ghi không thấy được, có ratio (vd `1:1:1`) cũng chỉ ra SRM006 |
| `llms-txt` | `XC-DOCAI-010` | `LLM000`–`009` | Định dạng llms.txt v2 (H1, blockquote, H2 có link, `## Optional` cuối); quét thư mục chỉ nhận `llms.txt`/`llms-full.txt`, tệp nêu đích danh luôn được kiểm; `--opt root=` kiểm link tương đối (đích > 4096 ký tự → LLM008), `--opt md=1` kiểm bản `.md` kề |

Tệp không đọc được hoặc không phải UTF-8: `i18n`, `dedup-leak`, `srm`, `llms-txt` báo (`…000`); `nfc`, `credits`, `trace`, `sbom`, `vex`, `pii-vn` báo (`…000`; `pii-vn` bắt buộc vì cổng quyền riêng tư không được lọt dữ liệu ở tệp log lớn); `tokens`, `motion`, `ac-trace` bỏ qua im lặng — loại nào cần thì thêm mã `…000` khi có ca thực tế.

**Giới hạn đã biết của `motion`:** `/*` nằm trong chuỗi (`content: "/*"`), trong `//` của SCSS hay trong glob sass bị coi là bắt đầu bình luận và làm trắng phần còn lại của tệp (có thể bỏ sót `MOT001`); chấp nhận vì CSS/SCSS không có bộ phân tích trong stdlib, dùng `/* xt-allow: … */` hoặc `--opt ignore=` khi gặp.

**An toàn khi đọc:** mọi loại đọc qua `read_text` — không theo liên kết tượng trưng, chỉ nhận tệp thường (FIFO/thiết bị bị bỏ), trần 2 MiB; regex dùng neo lookbehind và lượng từ chiếm hữu hoặc đoạn quét có trần để thời gian tuyến tính theo độ dài dòng (test `assert_not_quadratic`, rà #776 🔴).

## Hệ quả

- Dự án đích gọi một lệnh cho nhiều quy tắc và gắn vào `checks`/CI của mình; khung không bắt buộc (opt-in).
- Mỗi loại có test riêng với fixture tốt/xấu và coverage đủ; gỡ một loại là xoá một module và một dòng ở danh sách `KINDS`.
- Phải bảo trì danh sách loại và ngoại lệ; loại nào báo nhầm nhiều thì chuyển SHOULD → MAY ở yêu cầu tương ứng thay vì nới máy kiểm.

## Phương án đã loại

- Mỗi máy kiểm một lệnh `xt.py` riêng: đổi hợp đồng nhiều lần, `xt.py` phình, gỡ từng cái khó.
- Tự động nạp mọi module `kind_*` bằng `pkgutil`: ngầm, khó đoán trong zipapp; danh sách tường minh dễ kiểm bằng test.
