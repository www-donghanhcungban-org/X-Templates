# ADR-0097: Phân phối công cụ bằng artefact có phiên bản; dự án đích tự đặt tên

- **Trạng thái:** Đã chấp nhận ngày 2026-11-24 (D-557); triển khai theo pha P0–P6, mỗi pha một PR đảo ngược được.
- **Làm rõ:** ADR-0007 (tên kỹ thuật `xtemplates`: giữ làm mặc định, thêm khả năng đặt tên), ADR-0054 (guard fail-closed: artefact hỏng hoặc lệch digest là hỏng), ADR-0082 (harness host khác: lệnh adapter đổi theo layout), ADR-0090/0093 (tách module, bộ nạp anh em: áp được trong zip), ADR-0095 (lớp tác động tức thì thêm thư mục công cụ).
- **Đính chính:** `PROGRESS.md` và ADR-0038 ghi "`xt.pyz` (ADR-0010)" nhưng ADR-0010 là «Phản hồi từ dự án đích» và không nói về `pyz`; ADR này là quyết định đầu tiên về `.pyz`.
- **Căn cứ:** [báo cáo tách khung](../../research/2026-11-24-framework-target-independence.md) và [khảo sát 26 dự án](../../research/2026-11-24-similar-projects-survey.md).

## Bối cảnh

`install.py` sao chép vào mỗi dự án đích khoảng 2,9 MB mã khung dạng nguồn (`xt.py`, 9 module `xt_*.py`, `dev-task.sh`, `.claude/hooks/guard.py` và 12 hook, 17 skill, 6 subagent). Tên `xt`/`.xtemplates`/`xt.yaml`/`XT_*` cứng ở ít nhất 20 chỗ chạy được. Đích sửa được harness chép nên nâng bản có thể phải gộp tay; ở `docs/ops/registry.json` đích đã lệch ba thế hệ (3.29, 3.34, 2.0.0). Chủ dự án yêu cầu khung hoạt động độc lập với đích: đích viết code của đích, không dùng chung hay lấy mã của khung, tự đặt tên công cụ.

## Phương án

1. **A. Giữ nguyên, vá nhỏ** (bộ phân giải tên, launcher, render `<XT>`). Chi phí thấp nhưng đích vẫn giữ mã khung.
2. **B. Một artefact `.pyz` ghim digest, launcher mang tên đích, hợp đồng có schema** (chọn). Đích không giữ mã khung; digest kiểm được khi cài, khi nâng và qua `doctor`, attestation ở `release-verify` (không phải mỗi lượt hook; kiểm digest trên đường hook là mục xét ở P5).
3. **C. Gói PyPI + `uvx`**: đòi `uv` và mạng ở mọi máy, CI và phiên cloud; guard fail-closed chặn mọi lệnh khi tải lỗi; cần tài khoản registry của chủ dự án.
4. **D. Plugin host**: marketplace do repo khai không được thêm trong phiên cloud (tài liệu Claude Code, đọc 2026-11-24), nên guard vắng đúng nơi autopilot chạy; tên skill đổi thành `<plugin>:…`.
5. **E. Reusable workflow ghim SHA**: một pha của B (P6), không thay được B.

Số đo P0 (2026-11-24; script và kết quả thô ở [`research/evidence/2026-11-24-zip-load-bench.py`](../../research/evidence/2026-11-24-zip-load-bench.py) và `…-bench.txt`; 30 lượt 3.15.2 và 20 lượt 3.13.18, `guard.py` 1,38 MB, nạp rồi biên dịch từ nguồn như `py_run`): trung vị tệp rời 428 ms (3.15) và 325 ms (3.13); zip `ZIP_STORED` 431 ms và 318 ms; zip `ZIP_DEFLATED` 445 ms và 336 ms (một lượt đo trước đó trên cùng máy cho 463/459/482 ms và 361/370/373 ms: số tuyệt đối dao động theo tải máy; chênh lệch tương đối của zip stored nằm trong ±3 % ở cả hai lượt, không đồng dấu). Chi phí chủ yếu là biên dịch (khoảng 0,40 s/hook, AUD-SEC-074) nên zip stored không đổi độ trễ đáng kể (trong ±3 %, deflate +4 %).

## Quyết định

**Chọn B kèm các bổ sung B1–B7, mặc định giữ tên `xt`/`.xtemplates`/`xt.yaml`/`XT_`**, nên dự án đã cài không đổi gì cho tới khi tự chọn.

- **Artefact:** `<tên>.pyz` dựng tất định (`ZIP_STORED`, thứ tự tên, `mtime` cố định, quyền cố định) chứa (P1) `xt.py`, các module `xt_*.py`, `xt_app` và `VERSION`; guard, hook và `dev-task.sh` vào ở P5; phát hành cùng archive và biên nhận trong Release bất biến, có attestation (T-4017/T-4018 đã có phần tải đúng bytes).
- **Hợp đồng công khai** (số `contract: N` trong `tool.json`, SemVer riêng): (1) CLI mà hook/CI/skill gọi và mã thoát; (2) bộ khoá `xt.yaml`; (3) định dạng có `schema` (manifest/lock, STAGE, `release-check --json`, sổ lát, DEPLOYS, biên nhận promotion); (4) giao thức hook (stdin JSON → quyết định); (5) ID yêu cầu và dấu `xt-review vN`. Mọi thứ khác là riêng của khung.
- **B1 tên suy từ launcher:** launcher của đích mang `version` + `sha256`; `tool.json` chỉ giữ `config`, `env_prefix`, `contract`.
- **B2 launcher đóng băng:** nâng bản chỉ đổi dòng ghim; có test.
- **B3 hai mặt nâng bản:** "nâng artefact" và "sinh lại tệp render" riêng, mỗi cái một mã thoát, kèm lệnh `status`.
- **B4 tệp sinh ra thuộc khung, tuỳ biến ở overlay:** skill/agent render có dấu phiên bản và đè vô điều kiện; đích tuỳ biến ở thư mục overlay được khai; thay `kept-own`/`.xtemplates-new` của layout artefact.
- **B5 lệnh soi nguồn:** `which`/`explain` cho skill, cấu hình, luật guard.
- **B6 migration có phiên bản, hai bước:** bảng migration nằm trong artefact đã attest; `upgrade` sinh kế hoạch đọc được trước khi chạy; mỗi migration một commit trong PR nâng bản.
- **B7 sàn hợp đồng:** `tool.json: min_contract`, artefact thấp hơn thì fail-closed có thông báo; overlay chỉ được thêm luật guard, không nới.
- **Giữ nguyên:** ID `LOOP-*`/`WF-*`/`XC-*`, dấu `xt-review vN`, `.autopilot/`, tài liệu yêu cầu `framework/**` ở đích dưới dạng dữ liệu chỉ đọc (agent đọc bằng Read nên không bỏ được; ranh giới là «không chứa mã khung»).

## Lộ trình

| Pha | Nội dung | Đảo ngược |
|---|---|---|
| P0 | ADR này, số đo độ trễ, test đóng băng bề mặt hợp đồng | xoá test |
| P1 | `xt_pack.py` dựng `.pyz` tất định, test tái lập và sửa-một-byte; `xt.py` nhận ra module anh em trong zip (`sibling_exists`) để zip có đủ lệnh con của hợp đồng | xoá module |
| P2 | `tool.json` và bộ phân giải (gốc, thư mục, tên tệp cấu hình, tiền tố biến) thay chỗ cứng; mặc định y nguyên | giữ mặc định |
| P3 | `install.py --tool-name`, launcher, render `<XT>` (layout cây) | `--tool-name` bỏ trống |
| P4 | `release-tag.yml` dựng và attest `.pyz`; `release-verify` kiểm thêm | bỏ bước |
| P5 | `install.py --layout artifact`; guard, hook, `dev-task.sh` và git hook thành lệnh con của artefact (`hook <event>`, `gate-*`); kiểm digest khi khởi động phiên; canary một đích | `--layout tree` |
| P6 | Reusable workflow ghim SHA; bản MAJOR kế đặt artefact làm mặc định, layout cây giữ thêm một MAJOR | `--layout tree` |

## Tiêu chí nghiệm thu (đo được)

- Layout artefact: đếm tệp `*.py` và `*.sh` của khung trong đích, trừ launcher và thư mục `framework/` (dữ liệu chỉ đọc), bằng 0.
- Cài với `--tool-name acme`: grep `xtemplates|xt\.py|xt\.yaml` trong đích, trừ thư mục `framework/`, chỉ còn một dòng ghi chú nguồn.
- Zip chứa đủ lệnh con của hợp đồng (`tests/fixtures/contract-surface.json`); lệnh con duy nhất vắng là `derived` (chỉ repo khung).
- `release-check --json`, `doctor`, `ci-check`, `pr next` cho cùng JSON và mã thoát với tên mặc định và tên `acme` trên cùng fixture.
- Sửa một byte artefact: `doctor` và kiểm digest lúc khởi động phiên (P5) báo lỗi; mọi lệnh đọc mục hỏng thất bại rõ ràng (`OSError`), không rơi về đọc đĩa. Digest không được kiểm ở từng lượt hook PreToolUse (chi phí và đồng bộ với guard xét ở P5).
- Nâng bản: diff PR ở đích chỉ gồm artefact, dòng ghim ở launcher, tệp render có dấu phiên bản (skill, agent), tài liệu yêu cầu, manifest và các commit migration của B6 (mỗi migration một commit); launcher không đổi ngoài dòng ghim.
- Bản dựng `.pyz` hai lần cho cùng `sha256`.

## Hệ quả

- Đích không sửa tay guard; điểm mở rộng là khoá cấu hình và overlay (B4, B7).
- Review PR nâng bản không đọc được diff của artefact nhị phân: dựa vào digest, attestation và `release-verify` (nguồn: T-4018).
- Nếu sau này cần cache ngoài repo thì phải kiểm digest mỗi lần (shiv cho thấy cache sửa tay được); Yarn đã bỏ khuyến nghị để binary trong repo, nhưng với khung (phiên cloud mạng hạn chế, guard fail-closed) artefact trong repo vẫn hợp lý. Đây là đánh đổi có chủ ý.
- Xét lại khi: host agent hỗ trợ nạp plugin có hook trong phiên cloud; hoặc số đo thật ở đích cho thấy độ trễ vượt ngưỡng.
