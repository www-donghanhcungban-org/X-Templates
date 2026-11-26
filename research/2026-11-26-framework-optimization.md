---
title: Tối ưu khung — số đo 10 hướng, kế hoạch 31 lát, phương án nâng dự án đích để dành
kind: research
updated: 2026-11-26
---

# Tối ưu khung: số đo 10 hướng và kế hoạch 31 lát (đo 2026-11-26)

> Căn cứ của [PLAN-optimize-2026-11-26](../docs/autopilot/PLAN-optimize-2026-11-26.md) (D-608, D-609, D-610 ở [sổ quyết định](../docs/autopilot/DECISIONS.md)). Pha nghiên cứu chỉ đọc, không sửa tệp nào. Đo ở `main` `5b471ea7` (v3.36.0 cộng 55 commit); khi viết `origin/main` ở `5deb88e3` (#822–#824), nên số dòng và trọng số phải đo lại trước khi giao lát. Máy đo: WSL2, 10 nhân, CPython 3.15.2 (đối chứng 3.14.4), Claude Code 2.1.332. Dữ liệu thô và script đo nằm ở vùng tạm của phiên, không bền và không vào repo; tệp này là bản lưu duy nhất.

## 1. Kết luận

1. **Ba đòn bẩy lớn nhất đã được phản biện xác nhận.** (a) Nén sớm phiên chính ở 400K token: mô phỏng giảm 55,5 % cache-read của phiên chính, khoảng 13 % tổng chi phí (cận trên). (b) Chặn trần thông báo cổng commit đỏ: trung vị 68 500 ký tự xuống ≤ 8 000, loại ca 14–42 MB làm chết phiên. (c) `check-links` bỏ `.claude/worktrees`: lint ở checkout chính từ 24 s xuống dưới 1 s, hết đỏ giả.
2. **Tiền nằm ở ngữ cảnh tích luỹ, không ở phần cố định.** Phần harness nạp cố định là 31 415 byte, khoảng 2 % khối lượng đầu vào. Vì vậy không rút mô tả skill, không cắt PROGRESS ở SessionStart, không hạ trần output Bash.
3. **Hook tốn khoảng 0,37 s mỗi lần guard chạy, bằng khoảng 2,6 % thời gian phiên** lúc máy rảnh (con số 9 % trong bản đo đầu dùng trung vị 4 s giữa hai lần gọi; trung bình thật là 14,7 s). 75–80 % là compile `guard.py` từ nguồn. Tách cụm edit đưa hook Edit/Write từ 376 xuống 54 ms. Đường nhanh cho Bash chỉ phủ 1,1 % lệnh thật.
4. **CI: đường găng là một lớp test và hàng đợi runner.** Tách `GuardFuzzTest` đưa job chậm nhất từ 376–549 s về khoảng 370–390 s (trần 600 s). Trần 20 job đồng thời cộng trung vị 152,5 s vào thời gian tới-xanh 687,5 s.
5. **Hai tệp nóng kẹt trần dòng** (`guard.py` 24 689/24 689, `xt.py` 23 643/23 644). Mọi việc thêm dòng phải đi sau lát tách module (C14, C15) hoặc viết với 0 dòng ròng.
6. **Dự án đích: hoãn nâng** theo chủ dự án 2026-11-26 (D-610). Đợt này chỉ sửa trong repo khung, cả mã khung lẫn mẫu cài cho đích; đích nhận khi cắt bản kế. Phương án nâng 5 repo ở §7 giữ làm tài liệu cho lần nâng sau. X-Scanner giữ 3.29.0, ghi ngoại lệ có hạn 2027-01-21 (D-609). X-Agents loại khỏi danh sách đích (D-610).
7. **Chín phát hiện chưa có nhà** đã vào [sổ audit](../docs/ops/AUDIT-STATUS.md) (§9.2), trong đó ba đường lọt hàng rào mức 🟠.

## 2. Phương pháp

- **10 hướng đo**, mỗi hướng một lượt đo chỉ đọc, rồi **một lượt phản biện** chạy lại lệnh đo và tìm quyết định cũ (D-NNN, ADR) đã bác đề xuất hay chưa, cuối cùng **một lượt tổng hợp** xếp lát. Tổng: 169 số đo, 55 đề xuất, 50 điểm phản biện bổ sung.
- **Kết quả phản biện:** 28 xác nhận · 23 yếu đi (lợi ích nhỏ hơn hoặc rủi ro lớn hơn đã khai) · 4 bác bỏ. Đề xuất yếu đi chỉ vào kế hoạch ở dạng đã hiệu chỉnh.
- **Mức bằng chứng:** (a) nguồn sống đọc trực tiếp trong ngày có URL, hoặc số đo tại chỗ mà phản biện chạy lại ra cùng kết quả; (b) đo một phía hoặc mô phỏng trên dữ liệu thật, ghi "mô phỏng" hay "ước"; (c) suy luận, ghi "(chưa xác minh)" hay "chưa đo". Bảng §3 chỉ giữ số mức (a) và (b); số mức (c) nằm ở §9.
- **Xếp thứ tự lát:** an toàn trước, rồi lợi ích đã kiểm chia cho công. 7 lát song song không chạm tệp nóng (L00–L06), 24 lát nối tiếp theo một chuỗi `CHANGELOG` (C01–C24).

| Hướng | Câu hỏi | Số đo | Đề xuất | Xác nhận / yếu đi / bác |
|---|---|---|---|---|
| Token và harness | Ngữ cảnh nào tốn tiền thật | 16 | 3 | 2 / 1 / 0 |
| Độ trễ hook | Mỗi lần guard tốn bao nhiêu, ở pha nào | 18 | 5 | 3 / 2 / 0 |
| CLI `xt.py` | Khởi động, doctor, lint cục bộ | 14 | 6 | 4 / 2 / 0 |
| Test và cổng | Lớp nào quyết định thời gian, `test-select` chọn gì | 20 | 6 | 2 / 4 / 0 |
| CI | Tới-xanh, hàng đợi, phút-máy | 19 | 5 | 4 / 1 / 0 |
| Luồng PR | Vòng đời, PR sửa nối, tệp nóng | 16 | 7 | 2 / 4 / 1 |
| Tài liệu khung | Byte, sổ, blueprint, nhiễu tìm kiếm | 24 | 7 | 3 / 3 / 1 |
| Claude Code (nguồn sống) | Khoá, hook, biến môi trường mới | 17 | 5 | 1 / 2 / 2 |
| Thực hành ngoài | Dự án tương tự đã thêm gì trong 30 ngày | 6 | 1 | 0 / 1 / 0 |
| Dự án đích | Trạng thái 7 repo, đường nâng | 19 | 10 | 7 / 3 / 0 |

## 3. Số đo chính theo hướng

Số ở dạng min/trung vị khi có hai giá trị. "Phiên chính" là phiên điều phối; tên agent theo `.claude/agents/`.

### 3.1 Token và harness

Mẫu: transcript cục bộ từ 2026-11-15 (11 ngày), 4 phiên chính, 142 lượt subagent; không có phiên cloud.

| Số đo | Giá trị |
|---|---|
| Ngữ cảnh cố định phiên chính | 31 415 B (ước 9 800 token): CLAUDE.md 2 060 · AGENTS.md 8 145 · SessionStart 9 547 · mô tả 17 skill 7 993 · mô tả 8 agent 3 670 |
| Mỗi subagent nạp lại | CLAUDE.md + AGENTS.md 10 205 B, cộng thân agent 570–2 540 B; không nhận SessionStart |
| Mẫu ở đích sau cài | CLAUDE.md + AGENTS.md 11 036 B |
| Ngữ cảnh mỗi lượt gọi | Phiên chính p50 442K · p90 843K · max 967K token; executor-deep p50 218K; reviewer-alt p50 133K |
| Cache-read 11 ngày | Phiên chính 1 945,5M · executor-deep 1 629,3M · reviewer-alt 543,4M token |
| Chi phí quy theo giá (§4) | Tổng ≈ 397M token-input-tương-đương: executor-deep ≈ 141M · phiên chính ≈ 137M · reviewer-alt ≈ 92M (riêng output 8,09M token ≈ 10 % tổng) |
| Thông báo cổng commit đỏ | 20 lần: trung vị 68 500 · p90 109 380 · max 626 781 ký tự; thêm trực tiếp 686 891 token. Từ 2026-10-29: 45 lần, 7 lần 14–42 MB |
| Chi phí kéo dài của cổng đỏ | Đọc lại 179,7M token = 9,2 % cache-read phiên chính (cận trên); theo giá ≤ 2,6 % tổng, ≤ 7,6 % phiên chính |
| Hình dạng thông báo | 60 dòng cuối của ca trung vị chỉ có `OK` của shard cuối: phải trích khối lỗi, không chỉ cắt đuôi |
| Nén tự động hiện tại | 6 lần, 5 lần ở 861K–968K token; ngay sau nén còn 62,7K–78K |
| Mô phỏng nén sớm | Ở 400K: cache-read phiên chính 1 958,6M → 871,5M (−55,5 %, thêm khoảng 14 lần nén); 300K −64,4 %; 500K −46,1 % |
| Subagent ghi lại cả cache | 22,5M token (≈ 7 % tổng chi phí): TTL 5 phút hết sau tool chạy > 300 s; executor-deep 39 lần |
| Guard chặn (không tính cổng đỏ) | 931 lần, lượt kế đọc lại 170,9M token (≈ 2,2 % tổng); một lý do "tự ghi tệp rồi đọc lại trong cùng lệnh" chiếm 406 lần |
| Output Bash | 22 487 kết quả; 23 lần > 31 000 ký tự, tất cả là thông báo hook cổng commit. P95 output cổng 3 463 ký tự, mọi Bash 7 979 |

### 3.2 Độ trễ hook

| Số đo | Giá trị |
|---|---|
| Mẫu lời gọi tool | 76 595 **dòng** tool_use trong 323 transcript; **id duy nhất 40 067** (phiên nối tiếp chép lại lịch sử). Bash 74,2 % · Edit 12,6 % · Read 6,5 % · Write 5,0 %; 91,8 % có guard |
| Mỗi lần guard, máy rảnh | Bash đơn 356/366 ms · Bash phức tạp 437/443 · Edit 362/375 · Write 358/367 (CPython 3.15.2, load ≈ 3) |
| Máy bận (load 12–19) | 0,7–1,9 s mỗi lần; độ trễ là CPU thuần |
| Tách pha | Khởi động 9 ms · compile nguồn 1 390 800 B 265–300 ms (75–80 %) · thân module 52–58 ms (636 lần `re.compile` 36–38 ms) · quyết định 2,8 ms |
| 3.14.4 so với 3.15.2 | `guard.py` compile 234 so với 266 ms (3.15 chậm hơn ≈ 14 %); `xt.py` thì ngược lại (hook lỗi-tool 450 so với 366 ms) |
| Số lần guard mỗi phiên | Trung vị 2 974 (8 phiên) đến 3 264 (42 066 quyết định trong 21,5 ngày); lớn nhất 14 693 trong 89,7 giờ. Sổ cũ dùng 1 500 |
| Tỉ trọng thời gian phiên | ≈ 2,6 % lúc máy rảnh (khoảng cách trung bình 14,7 s giữa hai lần guard); máy bão hoà gấp 2–5 lần. Phiên 300 lời gọi ≈ 114 s hook |
| Bao đóng theo chế độ | edit 61 định nghĩa, 629 dòng = 3,9 % · MCP 2,0 % · commit-msg 0,3 % · Bash 94,1 % |
| Nháp module riêng cho edit | Hook Edit 376 → 54 ms (3.14.4: 324 → 43); parity 13 735 payload ở hai chính sách, 0 lệch |
| Hook lỗi-tool | 6,8 % lệnh Bash lỗi; 18,0 % trong đó là lệnh cổng. Tiền lọc chặt cho lọt 21,0 %, 0 lệnh cổng bị sót trên 29 716 lệnh; 360 → 5 ms |
| Đường nhanh Bash | Vị từ thận trọng phủ 1,1 % lệnh; cận trên lạc quan 26,2 %; 83,7 % lệnh có toán tử hoặc mở rộng |
| Regex lười | ≈ −30 ms với lệnh đơn, ≈ 0 với lệnh phức tạp; chạm ≥ 518 dòng tệp hàng rào |
| Thiếu pyc stdlib | Import 130–180 ms thay vì 25–31 ms; ở mọi môi trường đã đo: 0 |
| Compile song song (nháp, chưa thành lát) | Fork + ống, không cache đĩa: K=4 −52 %, K=8 −61 % (3.14.4, load 3,5); parity 3 000 lệnh |
| `site` trong tiến trình hook | `python3 -I -B` vẫn nạp `site`: site-packages ghi được có trong `sys.path`, tệp `.pth` có dòng `import` chạy trước guard; thêm `-S` thì hết (57 → 21 module nạp sẵn) |

### 3.3 CLI `xt.py` và cổng cục bộ

| Số đo | Giá trị |
|---|---|
| Khởi động `xt.py` | `--version` 345/349 ms · `commit-gate` 329/342 · `validate` 469/475 · `checks` 560/581; compile 1 268 478 B mất 212/222 ms |
| `check-links` ở checkout chính | 23,1–24,3 s. Duyệt 24 258 tệp `.md`, 23 690 thuộc `.claude/worktrees` (51 worktree, 1,3 GB, cả 51 sạch); tệp theo dõi 568. Sau tỉa: 0,45–0,95 s, 0 lỗi |
| Chuỗi `lint` | 24,8/24,9 s; `gate-fast` cây sạch 26,7/27,1 s |
| `doctor` | 1,42–1,47 s; `--fix` 2,49–2,61 s. `guard.py` bị compile 3 lần mỗi lượt (864 ms trên 1 207 ms), 6 lần ở `--fix` |
| `harness-check` | 3,7–3,9 s: `guard.py` bị compile 10 lần (2 784 ms trên 3 203 ms) |
| `format-file` | 2,04–2,06 s ở checkout chính: chụp 792 tệp qua 42 434 tệp; tỉa worktree còn 18 tệp |
| `typecheck` qua `dev-task.sh` | 0,80–0,85 s so với mypy trần 0,1 s; khoảng 0,7 s là `guard-check` |
| Bytecode trong phiên agent | Phiên mang `PYTHONDONTWRITEBYTECODE=1`. Bỏ biến cho lệnh test: −15 đến −21 % CPU trên mẫu 20–30 lớp |
| Nạp `xt` qua pyc ấm | 102–127 ms so với 338–419 ms từ nguồn (≈ −250 ms mỗi lời gọi); chính sách pyc chưa chốt (L05) |
| Bytecode ghim digest (nguyên mẫu) | `guard.py` 351 → 92 ms; bytecode tất định giữa các tiến trình cùng bản CPython. Chưa có layout artefact nên lợi ích hiện tại 0 |
| Phần độc quyền theo miền của `xt.py` | perf/trial 2 244 dòng · loop 2 068 · pr/merge 1 699 · release 1 608 · quét 1 038 (chỉ 1 chỗ test vá) |
| `audit plan` | 4,5 s, trong đó 3,66 s là 3 464 lời gọi stat vì `PATH` của máy có 47 mục `/mnt/` (cấu hình máy, không phải mã) |

### 3.4 Test và cổng

| Số đo | Giá trị |
|---|---|
| Quy mô | 877 lớp · 5 194 phương thức · 166 module |
| Trọng số shard | 756 mục, tổng 3 420,9 s; 30 lớp nặng nhất chiếm 51,6 %. `GuardFuzzTest` 225,0 · `GuardLayersNoNetworkTest` 161,9 · `TrialFlowTest` 114,0 |
| Lớp thiếu trọng số | 121/877 = 13,8 %; trần của test là 131 lớp, còn dư 10 lớp |
| Job `test 1/8` trên CI | 376–549 s ở 5 run `main` (trần 600 s); lớp fuzz chạy 350–523 s, gấp khoảng 2,3 lần trọng số đo cục bộ |
| Tách lưới fuzz thành 4 phần | 29 134 biến thể, 0 trùng, 0 quyết định lệch; tổng 4 phần bằng 83 % cả lưới (187–193 so với 223–231 s) |
| Độ chọn của `test-select` | `xt.py` kéo 666 lớp (75,9 %) · `guard.py` 493 · `README.md` bất kỳ 243 · mỗi `SKILL.md` 78. Trên 60 commit: trung vị 298 lớp, 6 commit chạy cả bộ |
| Tệp không ánh xạ được | 8/1 007 tệp; hai tệp verify-render gây 10 lần chạy cả bộ trên 300 commit (3,3 %) |
| Thời gian do tiến trình con | 36,7 % wall của test; 67 693 lần spawn (18,8 mỗi test); riêng `xt.py` 682 lần |
| Đỏ giả cục bộ | `DocCommandDriftTest` báo 895 mục vì quét `.claude/worktrees` |
| Thứ tự nặng-trước (mô phỏng) | `test_fast` −6,8 % ở 5 tiến trình; bộ đầy đủ −21,8 % ở 10 tiến trình |

### 3.5 CI

20 PR #800–#821, head lúc merge. Năm số N8–N12 nối tiếp N1–N7 của [baseline T-4010](2026-11-26-delivery-baseline.md) và là mốc so trước/sau cho L01, C08, C21.

| Mã | Số đo | Giá trị |
|---|---|---|
| N8 | Hàng đợi runner (job tạo → job bắt đầu) | Mọi job: trung vị 24 s · p90 231 · max 488. Cộng vào đường găng: trung vị **152,5 s** (24–419) |
| N9 | Tới-xanh (push → 5 check bắt buộc xanh) | min 528 · trung vị **687,5 s** · max 938. Không xếp hàng thì trung vị 533,5 s |
| N10 | CI chạy lại trên push `main` | Cây squash trùng cây head PR 20/20; trung vị **114,1 phút-máy** mỗi merge (101,3–132,1). `test-main` lặp nguyên job `test`: 30,6 phút-máy |
| N11 | Biên timeout 10 phút | Ít nhất 5 lần hết giờ từ 11-16 đến 11-24; `test 1/8` max 572 s, 21/44 job ≥ 540 s |
| N12 | PR chạy trùng run push `main` | 4/20 PR: tới-xanh trung vị 870 so với 650 s; hàng đợi 242 so với 11 s |

| Số đo khác | Giá trị |
|---|---|
| Phút-máy mỗi push | 101,4/116,5/142,7 (min/trung vị/max): `test` 38,39 · `test-main` 31,13 · `compat-py313` 29,49 (ba nhóm 84 %) |
| Job mỗi push | 38–46; đỉnh đồng thời chạm 20 ở 15/20 PR |
| Run ở head cũ | 15,8 % phút-máy (baseline T-4010 ghi 27,8 % theo định nghĩa rộng hơn) |
| 300 run CI của PR | 227 xanh · 44 huỷ · 29 đỏ |
| Tách fuzz, cận dưới đo được | Tới-xanh trung vị 686 → 583 s; 4/20 PR lợi 0 |
| Mô phỏng trần 20 job | Hiện tại 611 s (lệch đo thật 76 s) · tách fuzz 525 · bỏ `test-main` 534 · cả hai 416 |
| Tỉ trọng runner | Repo khung ≈ 89 % phút-job 7 ngày của 8 repo (ước thô); hàng đợi ở xboss trung vị 608 s |

### 3.6 Luồng PR

| Số đo | Giá trị |
|---|---|
| Vòng đời 60 PR (#760–#821) | Trung vị 14,2 phút · p90 70,2 · max 605,9; CI wall trung vị 11,5 phút |
| Mức tuần tự | 44/60 PR không chồng PR khác; 40/60 đến từ hai nhánh phiên dùng lại, 0 cặp chồng cùng nhánh |
| PR sửa theo rà | 17/60 = 28 %; "sửa của bản sửa" 4/60 = 6,7 %; PR chỉ sổ 8/60 = 13 % |
| Chi phí chuỗi | verify-render 5 PR: 603 runner-phút. Tag glob 2 PR: 466 phút vòng đời, 2 ADR cho 44 dòng guard |
| Luật tag glob | 70/1 500 lệnh sinh theo thuộc tính (4,7 %) không bị chặn, đều ở `git tag` và `update-ref` (đã có AUD-HAR-541) |
| Tệp nóng | CHANGELOG 47/60 PR (445 406 B) · DECISIONS 25 · `xt.py` 17 · sổ audit 15 (710 188 B) |
| Cổng ký | 3.36.0 cần 7 PR sổ (145 phút); 3.35.0 cần 6 PR |
| Tăng trưởng `guard.py` | +35,5 % byte từ 11-17 đến 11-26; từ khi có trần dòng (#798) chỉ +44 dòng |

### 3.7 Tài liệu khung

| Số đo | Giá trị |
|---|---|
| Kho | 1 007 tệp, 21 167 020 B; 2 879 mục checklist trong 202 tệp (MUST 716 · MUST@M 80 · MUST@L 750 · SHOULD 955 · MAY 379) |
| Cài vào đích | 350 tệp, 6 903 360 B |
| BLUEPRINT web-app theo quy mô | S 40 710 B/70 mục · M 247 290 B/473 · L 544 404 B/1 154. Công cụ Read trả tối đa 25 000 token mỗi lần và từ chối tệp > 256 KB (§4) |
| Sổ audit | 710 188 B, 1 178 hàng: đã sửa 663 (396 694 B) · mở 362 · chấp nhận 146. Dời 567 hàng có PR trong tag v3.36.0 (328 274 B) thì còn khoảng 380 KB |
| Ứng viên lưu kho | 20 PLAN đã đóng; 11 PLAN cũ còn 37 task mở; 8 GO-NO-GO và 6 báo cáo cũ |
| BLUEPRINT của chính khung | Ghép 2026-10-29, lệch chữ 23 mục, trong đó 17 MUST đang được CI chấm theo chữ cũ |
| Tìm kiếm của agent | 14 transcript: 4 048 lệnh grep qua Bash so với 4 lệnh rg. Grep của shell agent không theo `.ignore`, có quét thư mục ẩn: cùng từ khoá ở bản cài thử cho 79 479 B so với 1 220 B của rg |
| Hành vi đọc | 0 lần Read `BLUEPRINT.md` trong 22 transcript; 34 lần Read sổ audit đều có offset/limit |
| Gói `context` | `_tree_bytes` cộng cả `__pycache__`: một task báo 41 MB trong khi tệp theo dõi 1,43 MB |

### 3.8 Claude Code, thực hành ngoài và dự án đích

| Số đo | Giá trị |
|---|---|
| Hiện trạng harness | `settings.json` chưa có khối `env`, chưa có hook `PreSkillShellCommand`; 8 agent chưa dùng `omitClaudeMd`; 0 skill của khung dùng lệnh chèn |
| Hook cho lệnh chèn của skill | +0,6–0,85 s mỗi lệnh chèn, 0 byte ngữ cảnh |
| Auto memory | Chỉ mục nạp đầu phiên 1 055 B (không phải 25 KB) |
| Cài bị ngắt giữa chừng | Tiêm lỗi 21 kịch bản: 15 hội tụ sau một lần chạy lại, 6 kịch bản cắt tệp để lại trạng thái lệch. `guard.py` cụt 1 300 000 B; cài lại exit 0 vẫn giữ bản cụt |
| Hook 0 byte | `pre-bash-guard.sh` rỗng: hook exit 0 không quyết định (lệnh nguy hiểm đi qua). `doctor` exit 0 ở cả ba ca cắt tệp |
| Chuẩn ngoài | MCP hiện hành 2026-07-28, khung đã khớp. PEP 810 (`lazy import`) có ở CPython 3.15 nhưng là lỗi cú pháp trên 3.13/3.14 nên không dùng được |
| Bản khung ở đích | 5 repo `3.34.0 (3a1cd54)`; X-Scanner 3.29.0; X-Agents 2.0.0 không manifest. 0/7 có `xt-upgrade.yml` |
| Tag v3.36.0 | Gắn 2026-11-24 00:57:02 UTC; đủ soak 3 ngày lúc 2026-11-27 00:57 UTC. `release-verify` exit 0, 18,6–22,8 s |
| Cài thử v3.36.0 (tệp đổi / `.xtemplates-new` / `doctor --offline`) | X-Company 74/6/0 · hotel-manager 75/8/0 · xboss 73/4/0 (không kèm `--with-github`: 62 tệp, gộp 3) · dhcb 60/7/1 (2 hook chưa gộp) · x-shop 75/7/0 · X-Scanner 250/10/1 · X-Agents 283/11/1 |
| Trần tệp của X-Scanner | 1 048 576 B; `xt.py` 1 259 177 B và `guard.py` 1 384 897 B ở 3.36.0. `.pyz` nén DEFLATE đo được 541 430 B |
| Ngoại lệ cứng khi merge | `merge_hard_reasons` trả rỗng cho X-Company, x-shop, xboss, dhcb; chỉ hotel-manager dính vì `xt.yaml` nằm trong `merge_risk_paths` |
| Steward ở đích | Cron khai 10 phút nhưng 8 lượt `schedule` gần nhất của X-Company cách nhau 6,6–11,4 giờ |
| Chặn nhầm còn lại trên guard 3.36.0 | Ống `curl` sang `python3 -c` (đã có AUD-SEC-025); chèn chuỗi `cert.pem` vào tệp `.sh` (mới, §9.2) |
| Registry | 7 sản phẩm, lệch 7; `--strict` vẫn exit 1 sau đợt nâng vì ngoại lệ không miễn lệch |

## 4. Dữ kiện nguồn sống mức (a), đọc 2026-11-26

| Dữ kiện | Nguồn |
|---|---|
| Claude Code mới nhất là 2.1.332 | <https://registry.npmjs.org/> (dist-tag `latest` của gói CLI) |
| `PreSkillShellCommand` cần ≥ 2.1.332; hook PreToolUse không chạy cho lệnh chèn của skill; sự kiện này chỉ chặn được, chạy cả ở chế độ bỏ qua quyền | <https://code.claude.com/docs/en/hooks> |
| stdout của hook PreCompact (exit 0) được dùng làm chỉ dẫn tóm tắt, tối đa 10 000 ký tự; `onFailure: "block"` cần ≥ 2.1.295 | <https://code.claude.com/docs/en/hooks> |
| `autoCompactWindow` là khoá settings ở mọi phạm vi, tối thiểu 100000, cần ≥ 2.1.296; biến môi trường cùng tên thắng cả cờ dòng lệnh và khoá settings | <https://code.claude.com/docs/en/settings-reference> · <https://code.claude.com/docs/en/model-config> |
| Giá trị sai kiểu trong settings làm cả tệp không nạp, kể cả hook và luật quyền; `requiredMinimumVersion` chỉ có hiệu lực ở managed | <https://code.claude.com/docs/en/settings> · <https://code.claude.com/docs/en/settings-reference> |
| `disableSkillShellExecution` có ở mọi phạm vi; `bashOutputMaxChars` kẹp 4 000–128 000, mặc định 30 000; `idleCompaction` mặc định bật cho hội thoại ≥ 200 000 token sau khoảng một giờ nghỉ | <https://code.claude.com/docs/en/settings-reference> |
| `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` mặc định 3, đặt `1` để tắt lồng (≥ 2.1.217); `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` mặc định 20; chạm trần thì công cụ Agent báo lỗi và không thử lại | <https://code.claude.com/docs/en/env-vars> · <https://code.claude.com/docs/en/sub-agents> |
| `omitClaudeMd` cần ≥ 2.1.271; CLAUDE.md thư mục con vẫn nạp; subagent không nạp auto memory của phiên chính | <https://code.claude.com/docs/en/sub-agents> |
| Ngân sách bảng skill bằng 1 % cửa sổ ngữ cảnh | <https://code.claude.com/docs/en/skills> |
| Read trả tối đa 25 000 token mỗi lần và từ chối tệp > 256 KB; ở macOS, Linux, WSL agent tìm kiếm bằng `find`/`grep` qua Bash | <https://code.claude.com/docs/en/tools-reference.md> |
| Hệ số giá so với input: đọc cache 0,05 · ghi cache 5 phút 1,25 · ghi cache 1 giờ 2 · output 5 | <https://platform.claude.com/docs/en/about-claude/pricing> |
| Trần job đồng thời trên runner chuẩn: Free 20 · Pro 40 · Team 60 · Enterprise 500 | <https://docs.github.com/en/actions/reference/limits> |
| Image Python chính thức xoá pyc của stdlib khi dựng | <https://raw.githubusercontent.com/docker-library/python/master/3.13/bookworm/Dockerfile> |
| spec-kit v1.4.3 (2026-11-19) hoàn tác khi nâng cấp lỗi trước lúc ghi manifest | <https://github.com/github/spec-kit/releases> |
| Bản đặc tả MCP hiện hành là 2026-07-28 | <https://modelcontextprotocol.io/specification/versioning> |
| PEP 810 (nhập lười tường minh) ở trạng thái Final | <https://peps.python.org/pep-0810> |

Chưa xác minh từ nguồn sống: gói GitHub thật của tài khoản (API cần quyền quản trị tổ chức); biến độ sâu subagent có thuộc nhóm áp dụng ngay lúc khởi động không; mặc định của biến tắt tóm tắt tiến độ subagent.

## 5. Kế hoạch 31 lát

Công: S dưới nửa ngày phiên, M một phiên, L nhiều phiên. Cột "ADR / cổng": có cần ADR mới và có chạm cấu hình cổng, CI, hook hay settings không. Cột "Đợt 1" ghi task trong PLAN-optimize-2026-11-26 (`T-5032`…`T-5037`); lát ghi "—" thuộc mục "Đợt sau". `T-5038` (canary X-Company) đã bỏ theo D-610.

| Lát | Đợt 1 | Mục tiêu một dòng | Lợi ích đã hiệu chỉnh | Công | Phụ thuộc | ADR / cổng |
|---|---|---|---|---|---|---|
| L00 sổ đo và sổ audit | `T-5032` | Ghi số đo 10 hướng vào `research/`, mở hàng sổ cho phát hiện chưa có nhà | Giữ mốc so trước/sau; 9 phát hiện vào sổ | S | — | không / không |
| L01 tách guard fuzz | `T-5033` | Tách lưới fuzz thường thành 4 phần và lớp no-network theo từng lớp mạng, giữ tên `GuardFuzzTest` | Job chậm nhất 376–549 → 370–390 s; biên tới trần 28–51 → khoảng 210 s; tới-xanh 686 → 583 s (cận dưới) | M | — | không / không |
| L02 trọng số và tripwire | — | Đo 121 lớp thiếu trọng số; tripwire lớp đơn quá dài trong `test_ci_shard` | Mở lại dư địa 131 lớp; bắt lớp dài trước khi hết giờ | M | L01 | không / không |
| L03 ánh xạ verify-render | `T-5034` | Test nêu đích danh hai tệp verify-render để `test-select` không rơi về cả bộ | 877 → 126–285 lớp cho commit chỉ đụng `.mjs`; khoảng 3 % commit được lợi | S | — | không / không |
| L04 kiểm kiểu settings | `T-5035` | Test kiểm kiểu các khoá đã biết của `settings.json` | Chặn lớp lỗi sai kiểu làm cả tệp settings không nạp (mất hook) | S | — | không / không |
| L05 ADR tách `xt.py` và chính sách pyc | — | ADR bổ sung ADR-0090, PLAN tách theo số đo; chốt pyc có được tin cho công cụ `xt` | Mở đường cho lát thêm dòng vào `xt.py`; đóng câu hỏi bảo mật về pyc | S | — | có / không |
| L06 registry ngoại lệ đích | `T-5036` | Ghi ngoại lệ có hạn 2027-01-21 cho X-Scanner kèm ba điều kiện mở; loại X-Agents khỏi registry và TARGETS (D-610) | Lý do giữ bản có nhà; tránh PR nâng chắc chắn đỏ; danh sách đích khớp chỉ đạo | S | — | không / không |
| C01 `check-links` bỏ worktrees | `T-5037` | `os.walk` có tỉa, bỏ đúng tiền tố `.claude/worktrees`; test dò lệnh tài liệu loại cùng đường | Lint checkout chính 23,3–24,9 → 0,5–1 s; hết 895 phát hiện đỏ giả | S | — | không / không |
| C02 trần thông báo cổng đỏ | — | Gom output cổng vào log trong thư mục git; stderr chỉ còn khối lỗi và đuôi, ≤ 8 000 ký tự | −75 đến −90 % ký tự; ≈ 2,6 % tổng chi phí; loại ca đuôi làm chết phiên | M | C01 | không / có |
| C03 rào skill và độ sâu subagent | — | Hook `PreSkillShellCommand` dùng lại guard Bash; độ sâu subagent 1; nâng `claude_min_version` lên 2.1.332 | Đóng một đường lọt thật của guard và đường lồng 3 tầng | S | C02, L04 | không / có |
| C04 nén sớm phiên chính | — | Khoá `autoCompactWindow: 400000`; `pre-compact.sh` in chỉ dẫn tóm tắt ra stdout | Mô phỏng −55,5 % cache-read phiên chính; ≈ 13 % tổng (cận trên) | S | C03 | không / có |
| C05 install ghi nguyên tử | — | Ghi tệp tạm rồi `os.replace` cho 7 điểm ghi; git hook 0 byte được cài lại; bắt OSError | Tiêm lỗi hội tụ 15/21 → 21/21; hook không còn ở trạng thái cụt | S | C04 | không / có |
| C06 tag glob danh sách đóng | — | Test oracle trước; mọi glob không nháy ở vị trí tên tag của dạng tạo thì chặn; 0 dòng ròng | 70/1 500 lệnh lọt về 0; đóng AUD-HAR-541 | M | C05 | không / có |
| C07 ghép lại BLUEPRINT khung | — | `compose` lại, kiểm lại đủ 17 MUST trong một PR | Cổng G7 của khung chấm đúng chữ hiện hành | M | C06 | không / không |
| C08 `test-main` thoát sớm khi push | — | Thoát ở cấp bước khi sự kiện không phải `pull_request` | −30,6 phút-máy và 8 job dài mỗi merge | S | C07 | không / có |
| C09 lọc trước hook lỗi-tool | — | Tiền lọc bash là tập cha của regex lệnh cổng, thoát trước khi khởi động python | ≈ 79 % lệnh Bash lỗi bỏ qua python; −4,2 s mỗi 300 lời gọi | S | C08 | không / có |
| C10 `xt.py` sửa không tăng dòng | — | `doctor --fix` chỉ kiểm lại khi có sửa; `harness-check` nạp guard một lần | `doctor --fix` 2,61 → 1,47 s; `harness-check` 3,7 → 1,0 s | S | C09 | không / không |
| C11 thân agent hai dòng phòng ngừa | — | Ghi log và đọc log là hai lệnh riêng; lệnh chờ chia lượt ≤ 4 phút | Chưa đo; trần lợi ích ≈ 7 % tổng chi phí (ghi lại cache) | S | C10 | không / không |
| C12 quy trình rà bản sửa | — | Rà bản sửa ở head trước merge; dòng sổ đi cùng PR sửa; bản sửa xanh giả kèm bộ sinh biến thể | Bớt khoảng 229 runner-phút mỗi chuỗi sửa nối; bớt khoảng 3/60 PR chỉ sổ | S | C11 | không / không |
| C13 mẫu AGENTS không đọc trọn BLUEPRINT | — | Thay "đọc BLUEPRINT.md" bằng `blueprint-status` và tra theo ID | Hướng dẫn khớp giới hạn công cụ ở quy mô M và L | S | C12 | không / không |
| C14 guard tách cụm edit | — | Bao đóng edit sang module anh em, hook edit nạp riêng; hạ trần dòng đúng số dòng rút | Hook Edit/Write 376 → 54 ms; gỡ 950–1 650 dòng `guard.py` | L | C13 | có / có |
| C15 `xt.py` tách nhóm quét | — | Ba lệnh quét sang `xt_scan.py`, hạ trần dòng theo bánh cóc | `xt.py` bớt khoảng 1 000 dòng; lợi ích là bảo trì | M | C14, L05 | không / có |
| C16 công cụ test sau tách | — | `test-select` in tên tệp không ánh xạ được; `test-weights` chỉ đo lớp thiếu và đọc thời gian CI | Bỏ lượt đo tay 57 phút; giảm lệch giữa shard | M | C15 | không / không |
| C17 doctor và context sau tách | — | Compile guard một lần mỗi lượt doctor; doctor báo hook rỗng và worktree quá ngưỡng; `_tree_bytes` chỉ cộng tệp theo dõi | doctor −0,55 s; có lưới đỡ cho hook rỗng | M | C16 | không / có |
| C18 install không hồi sinh tệp đã gỡ | — | Tệp `.github/` có hash trong manifest nhưng vắng thì bỏ qua và báo; thêm `.claude/worktrees/` vào gitignore của đích | PR nâng nhỏ đi 10–11 tệp ở xboss, dhcb | M | C17 | có / không |
| C19 bot nâng giữ sửa tay | — | `publish_upgrade` không dựng lại cây khi tag không đổi và nhánh có commit ngoài bot | Giữ 3–9 tệp gộp tay mỗi repo mỗi bản | M | C18 | không / không |
| C20 install gộp khoá settings | — | Gộp danh sách trắng khoá cấp cao kiểu thiếu-thì-thêm; chỉ sau khi C04 đo đạt | Đích đã cài nhận nén sớm và trần độ sâu | M | C19, C04 | không / có |
| C21 gộp chiều nhánh `main` vào compat | — | Xoá ma trận `test-main`, thêm khẳng định tên nhánh vào `compat-py313`; chỉ khi số N8–N12 sau L01, C08 chưa đủ | 46 → 38 job; −31,1 phút-máy mỗi push PR | S | C20, C08, L00 | có / có |
| C22 test cục bộ dùng lại bytecode | — | Bỏ `PYTHONDONTWRITEBYTECODE` ở đầu lệnh test của `xt.yaml` nếu hợp chính sách L05 | −15 đến −21 % CPU test cục bộ | S | C21, L05 | không / có |
| C23 lưu kho sổ audit | — | Dời khoảng 567 hàng `đã sửa` sang sổ lưu trữ; `git mv` PLAN và báo cáo đã đóng | Sổ sống 710 → khoảng 380 KB | M | C22 | không / không |
| C24 đóng T-1834 merge-gate | — | Xoá stub `merge-gate.yml` và tham chiếu, giữ tên trong danh sách check ngoài CI thêm một bản | Đóng task treo từ 3.13 | M | C23 | không / có |

### Đợt sau

Các lát chưa thuộc đợt 1, theo thứ tự chuỗi. Mỗi nhóm mở PLAN riêng khi nhóm trước merge.

1. Song song, không chạm tệp nóng: **L02** (sau L01) · **L05** (ADR và D-NNN về pyc, điều kiện của C15 và C22).
2. Chuỗi hàng rào và ngữ cảnh: **C02 → C03 → C04 → C05 → C06**. C03 cần L04; C04 phải đo `preTokens` ≈ 400K và tỉ lệ Gate xanh lần đầu trước khi sang đích.
3. Chuỗi tài liệu và công cụ nhẹ: **C07 → C08 → C09 → C10 → C11 → C12 → C13**.
4. Chuỗi tách tệp nóng: **C14 → C15 → C16 → C17**. C14 cần ADR nói thẳng là sửa ADR-0090 mục 2, ADR-0093 mục 1–2 và D-542.
5. Chuỗi cài đặt và đích: **C18 → C19 → C20**. C03 và C18 buộc đích làm gì đó, nên cần mệnh đề "Dự án đích" và cắt bản sớm.
6. Chuỗi dọn: **C21 → C22 → C23 → C24**. C21 có thể không làm nếu số đo sau L01 và C08 đã đủ.

## 6. Đề xuất bị bác hoặc hoãn

| Đề xuất | Kết luận | Lý do |
|---|---|---|
| Cài `.ignore` ở đích để che nội dung khung | Bác | Grep của shell agent chỉ theo `.gitignore`; 4 048 lệnh grep so với 4 lệnh rg. Thay bằng câu hướng dẫn phạm vi tìm (C13) |
| Tắt auto memory trong settings dự án | Bác | Lợi ích đo được 1 055 B mỗi phiên chính; mất ghi nhớ vận hành chủ dự án đã lưu |
| `bashOutputMaxChars` thấp thay cho hook cắt output | Bác | P95 output cổng 3 463 ký tự, thấp hơn điều kiện 12 000; vượt trần là mất phần đuôi có tổng kết |
| Kéo `changelog.d` lên trước | Bác | PR tuần tự do một phiên một nhánh (40/60 PR, 0 cặp chồng cùng nhánh), không do tệp nóng |
| Journal và hoàn tác cho `install.py` | Bác phần journal | 15/15 kịch bản lỗi giữa các tệp đã hội tụ sau một lần chạy lại; luồng `upgrade open-pr` đã là giao dịch. Lỗ thật là ghi không nguyên tử (C05) |
| Bot nâng không ép `--with-github` theo manifest | Bác phần tiêu chí | Manifest của xboss, dhcb vẫn ghi tệp `.github/` nên tiêu chí không cứu được; gốc là installer hồi sinh tệp đã xoá (C18). Cờ chỉ cài bot nâng: hoãn |
| Bỏ CLAUDE.md/AGENTS.md cho hai agent nhẹ | Hoãn | Hai agent có 0 lượt chạy trong mẫu; lợi ích khoảng 0,002 USD mỗi lượt. Không áp cho agent có quyền sửa |
| Regex cấp tệp của guard biên dịch lười | Hoãn sau tách guard | Lợi khoảng 30 ms với lệnh đơn; chạm ≥ 518 dòng tệp đang đúng trần; đổi fail-closed lúc nạp thành fail-open lúc dùng |
| doctor cảnh báo stdlib thiếu pyc | Hoãn | Lợi ích 0 ở mọi môi trường đã đo |
| Viết lại shell lớp chụp GO-NO-GO của `format-file` | Hoãn | Dọn 51 worktree sạch cho cùng −1,0 s mà không sửa hàng rào; chỉ giữ cảnh báo doctor (C17) |
| Nạp bytecode trong artefact có ghim digest | Hoãn | Chưa có layout artefact; D-307 còn hiệu lực |
| Chạy lớp nặng trước ở test cục bộ | Hoãn | Lợi ≤ 7 % theo mô phỏng, thêm 0,35 s cố định mỗi `gate-fast` |
| Giữ tệp vào `xt.py` nhỏ để bớt compile | Chuyển thành dữ kiện cho L05 | Lợi 0 ms nếu chính sách bytecode không đổi |
| Cảnh báo máy khi CI đích lệch ADR-0039 | Hoãn | Hàng đợi ở đích nhiều khả năng do repo khung chiếm khoảng 89 % phút-job |
| Cổng ký gói còn 2 PR | Hoãn | Mốc quét phải trỏ SHA merge nên khả thi 3–4 PR; chạy thử có đếm ở lần cắt bản kế |
| `pr next` nhắc dòng sổ | Hoãn phần công cụ | `xt.py` kẹt trần; phần câu chữ đã nhận ở C12 |
| Chọn họ tag/ref làm cụm tách đầu của guard | Thay bằng C14 | Lệch thứ tự D-542; tốc độ tăng `guard.py` đã dừng từ khi có trần |
| Trần độ dài mục checklist | Hoãn | Không gắn giới hạn kênh nào, ngược ADR-0092; phần phình là văn xuôi |
| Chỉ cài tệp research được trỏ trực tiếp | Hoãn | Chỉ bớt 244 KB trên đĩa, đảo quyết định T-3660 |
| Chữ yêu cầu trong gói `context` | Hoãn phần này | 0 lần Read BLUEPRINT trong 22 transcript; phần câu AGENTS mẫu và `_tree_bytes` đã nhận (C13, C17) |
| Trần 5 subagent đồng thời | Hoãn | Trùng thói quen 5 lô reviewer song song; cần đo đỉnh đồng thời. Độ sâu 1 đã nhận (C03) |
| Thân PR của bot theo mẫu đích | Hoãn | Chỉ chắc qua cổng ở 1/7 đích; phần giữ sửa tay đã nhận (C19) |
| Nén sớm bằng biến môi trường và mục trong CLAUDE.md | Thay chi tiết | Dùng khoá settings và stdout của `pre-compact.sh`; cửa sổ riêng cho executor-deep hoãn tới C20 |
| Đường nhanh cho Bash (ADR-0093 mục 5) | Chưa mở ADR | Phủ 1,1 % lệnh thật; compile song song cho lợi ích lớn hơn mà không cần chứng minh tập con an toàn |

## 7. Phương án nâng dự án đích (hoãn, D-610)

**Hoãn theo chủ dự án 2026-11-26, giữ làm tài liệu cho lần nâng sau.** Đợt này không mở PR nào ở repo đích; canary `T-5038` đã bỏ và dừng trước khi đẩy nhánh. Số đo trong bảng là trạng thái ngày 2026-11-26 với tag v3.36.0; lần nâng sau phải đo lại trên bản cắt mới, vì các tối ưu của kế hoạch chưa có trong v3.36.0. X-Agents đã loại khỏi danh sách đích (D-610); hàng của nó chỉ còn là dữ kiện đo.

Quy trình chung: clone tag v3.36.0 và `release-verify` exit 0; clone đích, tạo nhánh riêng, **cài phụ thuộc của đích trước mọi cổng** (AUD-CI-038); `install.py --plan` rồi chạy thật; gộp các tệp `.xtemplates-new`; `doctor --offline`; kiểm không có hook 0 byte; `gate-fast`; commit; PR; `pr next`. Phiên repo khung không merge được PR ở repo khác.

| Repo | Bản đích | Điểm riêng | Đường merge | Rủi ro chính |
|---|---|---|---|---|
| X-Company (canary khi nâng lại) | 3.36.0 | `--with-github`; 74 tệp, gộp 6; thêm `upgrade_wave: canary`; sau merge chạy tay bot nâng một lần | L3, làn chuẩn: một dấu review sạch ở head rồi steward hoặc phiên tại repo merge | PR Dependabot đang đỏ pr-policy; PR của bot ở bản kế đỏ pr-policy cho tới khi có cách điền thân |
| xboss | 3.36.0 | Sau canary và mốc soak; không `--with-github` (sẽ tạo lại 10 tệp đã gỡ); 62 tệp, gộp 3 | L1: chủ repo merge khi 4 check bắt buộc xanh | Merge xếp hàng pipeline VPS, cần duyệt môi trường Production |
| hotel-manager | 3.36.0 | Sau canary và soak; `--with-github`; 75 tệp, gộp 8, ưu tiên `pr-steward.yml` | Người merge: `xt.yaml` nằm trong `merge_risk_paths` nên thành ngoại lệ cứng | 28 check bắt buộc, strict: nhánh tụt là chạy lại 17 phút CI |
| dhcb | 3.36.0 | Sau canary và soak; 60 tệp, gộp 7, trong đó 2 hook lệch khoảng 200 dòng (công mức L) | L1: chủ repo merge; merge là deploy production | Gộp hook sai làm hàng rào không chạy; sửa hook ở clone đích có thể bị guard chặn, khi đó cần phiên mở tại dhcb |
| x-shop (`master`) | 3.36.0 | Làm sau cùng (job `gate` 55 phút); 75 tệp, gộp 7; bỏ `xt-upgrade.yml` khỏi PR khi chưa có token | L3, làn chuẩn; người merge tự chờ `gate` xanh | Ruleset đang tắt: merge không bị chặn khi CI đỏ |
| X-Scanner | Giữ 3.29.0 | Không mở PR: cổng của repo trần 1 048 576 B mỗi tệp. Ghi ngoại lệ có hạn (L06). Điều kiện mở, một trong ba: đích miễn hai đường dẫn; khung tách hai tệp dưới 1 MiB; `.pyz` nén | Không có PR ở đích | Thiếu sửa guard của 7 bản minor |
| X-Agents | Loại khỏi danh sách đích (D-610) | Dữ kiện lúc đo: lõi 2.0.0, đổi 283 tệp, 3 hook tự sửa, không manifest. D-610 thay phần X-Agents của D-609 | Không có | Không áp dụng |

## 8. Việc cần người

Mục 1, 2, 3, 6, 7 chỉ cần khi mở lại đợt nâng đích (D-610); mục 4, 5, 8 áp dụng ngay cho repo khung.

1. Merge PR nâng khung ở xboss, dhcb (L1) và hotel-manager (ngoại lệ cứng). dhcb merge là deploy VPS; xboss cần duyệt môi trường Production.
2. x-shop: bật lại ruleset đang tắt và đặt `XT_STEWARD_TOKEN`, hoặc chấp nhận nâng tay và không cài bot nâng.
3. Kiểm quyền ghi và quyền workflows của `XT_STEWARD_TOKEN` ở X-Company, hotel-manager, xboss, dhcb. Thiếu thì bot nâng hỏng ở bước đẩy tệp workflow.
4. Trần 20 job đồng thời: nâng gói GitHub hoặc xin hỗ trợ là việc tiền và tài khoản. Nếu nâng, phần xếp hàng 152,5 s gần như hết mà không cần đổi CI.
5. 115 worktree đăng ký ngoài repo, 10 cái bẩn: chủ repo xem trước khi dọn.
6. X-Scanner: có miễn hai tệp công cụ của khung khỏi trần 1 MiB không (quyết định ở X-Scanner).
7. xboss, dhcb: ý định với `XT_STEWARD_TOKEN` đã đặt 2026-11-14. hotel-manager, X-Company: có giữ `pr-title.yml`, `merge-gate.yml` mà installer tạo lại không.
8. Cấu hình máy, không phải mã khung: wrapper `python3` ép 3.15; `PATH` của WSL có 47 mục `/mnt/` làm `audit plan` mất 4,5 s.

## 9. Chỗ chưa đo, chưa xác minh

### 9.1 Khoảng trống

1. Số đo lấy ở `5b471ea7`; #822 đã đụng `guard.py`. Số dòng, số lớp test và trọng số phải đo lại trên `main` mới trước khi giao lát.
2. Giả định L00–L06 không cần dòng `CHANGELOG`: xác nhận bằng `pr next` ở PR đầu; sai thì các lát này nhập chuỗi.
3. C04: chưa xác minh khoá `autoCompactWindow` có hiệu lực ở settings dự án, bản tối thiểu của hành vi stdout PreCompact, và chất lượng sau khi nén nhiều gấp 3. Mẫu token chỉ có 4 phiên chính cục bộ.
4. Đòn bẩy lớn nhất cho đường Bash (compile song song) chưa nằm trong lát nào: chưa đo ở load ≥ 12, máy 2 nhân, macOS; cần ADR và rà bảo mật.
5. Hai lỗ cần quyết ở L05 chưa có lát sửa: guard không rào `scripts/__pycache__/`; tiến trình hook còn nạp `site`. Chưa chạy bộ test với `-S`.
6. C06 chỉ làm được với 0 dòng ròng; C14 khai công M nhưng thực tế L (110 chỗ `patch.object`, parity qua 5 bộ nạp, chưa đo parity MCP).
7. CI: gói GitHub thật chưa xác minh; chưa có quyết định về việc chạy lại nguyên cây trên push `main`; chưa lần hết bên tiêu thụ check-runs của commit `main`.
8. Chưa đo: `gate-fast` cả chuỗi và bộ đầy đủ có coverage ở máy này; nguồn của `PYTHONDONTWRITEBYTECODE=1`; đỉnh subagent đồng thời; hiệu quả hai dòng nhắc ở C11; thời lượng một lượt reviewer.
9. reviewer-alt chiếm khoảng 10 % tổng chi phí riêng phần output nhưng chưa có số chất lượng, nên không đề xuất hạ. `idleCompaction` hầu như không chạy (1/6 lần nén), chưa rõ vì sao.
10. Mức của 70/1 500 lệnh tag glob lọt chưa phân loại lại (sổ để 🟠; theo D-507/D-508 có thể là 🟢).
11. `test-select` so theo basename (README kéo 243 lớp, 9/60 PR bị ảnh hưởng): cần thiết kế tránh âm tính giả, chưa có lát. 6 tệp không ánh xạ còn lại chưa có test thật.
12. Chưa có máy phát hiện blueprint lệch chữ so với khung, nên C07 sẽ lại trôi; cần dòng trong `xt.py` sau C15.
13. Đích: chưa đo chữ ký GO-NO-GO có về `pending` sau nâng không; `registry --strict` vẫn exit 1 sau đợt nâng.
14. Các tối ưu này chưa nằm trong v3.36.0: đích chỉ nhận khi cắt bản kế.
15. Dữ liệu đầu vào trích "research 2026-11-25" nhưng repo không có tệp ngày đó: coi là chưa có quyết định trước.
16. Dọn 51 worktree trước thì phép đo sau C01 không còn chứng minh được gì; test của C01 phải tự dựng worktree giả.
17. Cổng ký: cần đếm ở lần cắt bản kế tệp nào sau mốc quét sinh nợ review. 9 run CI đỏ của PR trong cửa sổ đo chưa đọc nguyên nhân. Hiệu quả của LOOP-DESIGN-029 chưa đo được từ dữ liệu GitHub.
18. Tệp lệnh thật dùng để đo độ phủ đường nhanh có thể lẫn bí mật: không vào repo, xoá sau khi dùng.

### 9.2 Phát hiện đã vào sổ audit

AUD-HAR-570, 571, 573 đối chiếu lại bằng `xt.py guard-check` ở `5deb88e3` (chỉ hỏi bộ phân loại, không chạy lệnh); AUD-HAR-572 đọc lại cờ của bộ nạp hook. Các hàng còn lại dựa trên phép đo của lượt phản biện. Ba hàng 🟠 còn `mở` nên `audit check --strict` đỏ cho tới khi sửa hoặc phiên chính ghi chấp nhận có chủ và hạn.

| Hàng sổ | Mức | Phát hiện | Lát xử lý |
|---|---|---|---|
| AUD-HAR-570 | 🟢 | `SECRET_WRITE` chặn nhầm khi nội dung ghi chứa chuỗi `cert.pem` | chưa có lát |
| AUD-HAR-571 | 🟢 | `git tag --sort` và `--format` (chỉ đọc) bị chặn oan | C06 |
| AUD-HAR-572 | 🟠 | Tiến trình hook nạp `site`: `.pth` ở site-packages ghi được chạy trước guard | L05 quyết, chưa có lát sửa |
| AUD-HAR-573 | 🟠 | Guard không rào ghi `scripts/__pycache__/` trong khi module anh em đọc pyc | L05 |
| AUD-HAR-574 | 🟠 | `install.py` ghi không nguyên tử: hook `.sh` 0 byte là fail-open, cài lại không sửa, doctor không báo | C05, C17 |
| AUD-HAR-575 | 🟢 | `.ignore` của khung vô hiệu với grep của agent | cần ADR mới; C13 |
| AUD-TEST-157 | 🟢 | Hai test đo thời gian chập chờn dưới tải CI | chưa có lát |
| AUD-CI-047 | 🟢 | Shard hết giờ 10 phút tái diễn, chưa có tripwire | L01, L02 |
| AUD-PERF-032 | 🟢 | `harness-check` compile `guard.py` 10 lần mỗi lượt | C10 |

Cập nhật hàng cũ: AUD-PERF-013 và AUD-PERF-031 thêm số đo 2026-11-26 (§3.2); AUD-PERF-028 thêm số đo `doctor` (§3.3); AUD-PERF-029 đóng vì mã đã sửa ở #547.
