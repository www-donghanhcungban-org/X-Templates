---
title: Đánh giá đề xuất cải tiến 2026-11-23 (18 thay đổi, 6 nhóm) so với mã thật
kind: research
updated: 2026-11-23
---

# Đánh giá đề xuất cải tiến ngày 2026-11-23

> Mục đích: đối chiếu đề xuất "Đề xuất cải tiến X Templates — Ưu tiên triển khai và tiêu chí hoàn thành" (chủ dự án gửi
> 2026-11-23, 18 thay đổi trong 6 nhóm, 5 đợt) với mã và tài liệu thật, làm căn cứ cho
> [PLAN-improve-2026-11-23](../docs/autopilot/PLAN-improve-2026-11-23.md). Mốc đối chiếu: `main` `9c014bb2`.
> Cách làm: ba lượt dò chỉ đọc theo nhóm mục, phiên chính đọc lại các dòng đánh dấu ✓. Số dòng đúng ở mốc này và sẽ trôi.
> Mục nào không đọc được nguồn ghi **chưa xác minh**. Một lượt rà độc lập ở head `4fda705c` đã sửa hàng 04, 05 và điểm
> chéo 2–4 của bản đầu (bản đầu nói quá "mọi verdict khác `merge` đi qua" và ghi ruleset live là chưa xác minh).

## Kết luận

- Hướng của đề xuất đúng và phần lớn dữ kiện khớp mã; không mục nào sai hướng. Ba mục đã có sẵn một phần: mục 03 (phần
  CI), mục 02 (ghim head, ADR-0057) và mục 13 (phần đo). Hai mục (04, phần máy của 01) là đổi chính sách đã ghi trong
  ADR, không phải sửa lỗi.
- Đề xuất **chưa thực thi được như đang viết**: không có ID task, Gate máy kiểm hay phạm vi file; tiêu chí hoàn thành là
  văn xuôi. Bản PLAN chỉnh lại chuyển đợt 1 và đợt 2 thành task có Gate, giữ đợt 3–5 ở dạng khung có điều kiện vào.
- Bảy điểm cần chỉnh nêu ở mục "Phát hiện chéo": mốc đã cũ một commit, trùng việc với `PLAN-factory-e2e`, mục 04 rộng
  hơn mô tả, bẫy `bypass_actors` rỗng đã nằm sẵn trong repo, mục 07 trỏ sai tệp và là thay đổi phá tương thích, việc cần
  người chưa tách riêng, và một hạn cứng (2026-12-02) bị bỏ sót.

## Đối chiếu từng mục

| Mục | Khẳng định của đề xuất | Đối chiếu ở `9c014bb2` | Chỉnh trong PLAN |
|---|---|---|---|
| 01 | Phiên tự gọi reviewer khi `pr next` không đòi; hướng dẫn chưa thống nhất | Đúng. ADR-0080 cấm rà giữa nhịp vét, nhưng `PLAN-guard-split-2026-11-22` ("mỗi PR đổi `guard.py` cần review độc lập ở head"), `PLAN-harden-2026-11-22-b` ("lát mã chỉ merge sau review sạch ở head") và PROGRESS §Bàn giao ("Merge sau review ở head") lại đòi ✓ | ADR mới định nghĩa một lớp ngoại lệ hẹp; đồng bộ skill, PLAN, bảng điều phối; máy cưỡng chế sau mục 04. Phần máy thu hẹp ADR-0079 và là phương án D-533 từng loại — ADR phải ghi rõ |
| 02 | Kết quả review cần mốc nội dung, base, phạm vi, chính sách | Một phần đã có: bản ghi `pr reviewed` giữ `head`, kết luận, model, effort, thời điểm (`xt.py:17645` ✓); dấu đăng `xt-review v1 head=… verdict=…`; ADR-0057 phủ nợ theo PR đã merge có review sạch ở head. Chưa có: base, danh sách tệp, chính sách | Thêm ba trường, dấu v2 đọc được v1 |
| 03 | Loại kiểm trùng; `test-select` sót kế thừa | Phần CI **đã có**: `concurrency` + `cancel-in-progress` cho PR (`ci.yml:20-22` ✓), cache pip theo `requirements-dev.txt`, job `quality` chặn "skipped tính là đạt". Phần `test-select` đúng: bắc cầu kế thừa chỉ trong cùng tệp (`xt.py:2580-2586` ✓); `AUD-TEST-131` (38 lớp, 🟢 mở), `AUD-HAR-443` (tệp chưa track kéo 449/702 lớp, 🟢 mở) | Chỉ làm phần còn thiếu; bỏ "evidence cache" khỏi đợt gần |
| 04 | `wait`/`human` bị hạ thành `ask` rồi `OTHER_ASK`, guard không phản đối | Đúng và **rộng hơn** `AUD-HAR-454`, nhưng là hành vi có chủ ý: `_merge_verdict` trả `ask` không mã cho `wait`, `fix`, `update`, `human` không cứng, `closed` và ca lệch head (`guard.py:12490-12493` ✓), bảng `POLICY` cho `OTHER_ASK` đi qua (`guard.py:24196` ✓). Đã bị chặn sẵn: verdict `review` (`REVIEW_MISSING`, `guard.py:12455-12462` ✓), ngoại lệ cứng và `merge-check` lỗi (`_hard_gate`, `guard.py:12433-12451` ✓). `LOOP-STOP-002` ghi phần còn lại "mặc định cho chạy, lớp đỡ là CI, ruleset nhánh, review" (ADR-0018/0019) ✓ — nên đây là **đổi chính sách**, không phải văn bản lệch mã. Lượt rà độc lập đã chạy thử từng ca qua `apply_policy` | ADR sửa ADR-0018/0019 và D-534 trước; mã quyết định riêng đặt ở nơi sinh; đóng `AUD-HAR-454` trước hạn 2027-01-21 |
| 05 | Thiếu ruleset `v*` ở API live; đừng áp `bypass_actors` rỗng | Trạng thái live đúng như đề xuất: `xt.py admin-plan --json` ngày 2026-11-23 (HEAD `4fda705c`) trả hàng `ruleset`: thiếu; lượt rà độc lập đọc API thấy đúng một ruleset `main`. Khớp với `PLAN-factory-e2e` ("T-3858 chờ xác nhận danh tính được phép tạo tag `v*`"). Bẫy đề xuất cảnh báo **đã nằm trong repo**: `.github/rulesets/tags.json` có `bypass_actors: []` cùng `creation`/`update`/`deletion` ✓, `install.py --with-github` phát nó cho dự án đích, `admin-plan` so khớp nguyên văn với live (`xt_ops_setup.py:168-196` ✓) trong khi script cho chủ repo lại đòi đúng một actor `Integration` trong tệp (`xt_ops_setup.py:469` ✓) — hai chỗ mâu thuẫn nhau, và bypass cả ruleset thì actor đó sửa, xoá được tag; `release-tag.yml:118` đẩy tag bằng `XT_RELEASE_TOKEN` hoặc `github.token` ✓. `AUD-HAR-452/453` được chấp nhận với lý do "hàng rào thật là ruleset tag" — hàng rào đó hiện chưa có ở live | Tra nguồn sống trước; tách ruleset tạo và ruleset sửa/xoá; áp live là việc của chủ repo |
| 06 | `BLUEPRINT.md` bị tính là tài liệu dù lệnh của nó chạy ở CI | Đúng: `is_doc_path` coi mọi `.md` ngoài thư mục runtime là tài liệu (`xt.py:6194-6209` ✓), nợ review bỏ tài liệu (`xt.py:13969` ✓). `docs/**/PLAN*.md` cũng vậy (dòng Gate do harness chạy). Skill dưới `.claude/skills/` đã tính là mã. Sổ đã có hàng này: `AUD-HAR-460` (🟠 chấp nhận, D-535, hạn 2027-01-21) | Phân loại theo **dòng đổi** (dòng `Kiểm:`, Gate, `- grant:`), không theo tệp |
| 07 | Adapter kế thừa môi trường rộng, `BASH_ENV` lọt | Đúng về hành vi, **sai tệp**: `xt_adapter.py` là adapter hook của host, không phải adapter triển khai. Lệnh deploy/smoke/rollback/digest chạy ở `xt.py:15431` ✓ với `os.environ` nguyên, chỉ bỏ `XT_DEPLOY_*`. Mẫu allowlist có sẵn: `PERF_TRIAL_ENV_KEEP` (`xt.py:20816` ✓) | Hai bước: bỏ biến khởi động trình thông dịch ngay, allowlist khai tên sau canary |
| 08 | Consumer tái dựng `tar.gz` rồi kỳ vọng cùng bytes | Đúng: workflow `git archive`, attest, tạo receipt rồi chỉ đẩy tag — archive và receipt không lưu ở đâu (`release-tag.yml:153-185`); consumer dựng lại với tiền tố cố định `X-Templates-` (`xt_distribution.py:137-138` ✓) trong khi workflow lấy theo tên repo (`AUD-CI-036`, đang chấp nhận) | Lưu đúng bytes theo bản phát hành; đóng luôn `AUD-CI-036` |
| 09 | `release-check` trả GO khi promotion còn chờ; `pending_human` gây nhầm; README lệch | Đúng cả ba: verdict chỉ có `NO-GO`/`GO (chờ người)`/`GO` (`xt.py:15030` ✓); `promotion.state = pending_human` kể cả khi `release_signoff: agent`, và là giao diện thật vì `xt_release_ops.py:109` so chuỗi ✓ (workflow dự án đích gọi); `README.md:9` ghi `v3.34.0` trong khi tag `v3.35.0` đã có ✓ | Tên trạng thái mới có đường tương thích; README do máy kiểm |
| 10 | Pilot production có nghiệp vụ mới, ưu tiên Hotel Manager | Căn cứ đúng (pilot hiện có chưa tới production). Bằng chứng triển khai nghiêng về sản phẩm khác: pilot lọc tầng "chưa có bằng chứng triển khai lên VPS"; quyền SSH và health của VPS DHCB đã xác minh (`PLAN-factory-e2e` §Bằng chứng) | Chọn sản phẩm theo đích triển khai đã xác minh, quyết ở cửa đợt 3 |
| 11 | Hoàn thiện starter `web-api-ts` | Đúng: README của gói tự ghi thiếu vai trò migration, thu hồi phiên, giới hạn tần suất, MFA, đích staging/production (`README.md:90-98` của gói ✓). Cô lập tenant (RLS) và backup/restore đã có test | Chỉ làm rủi ro mà nghiệp vụ pilot chạm tới |
| 12 | Ba chỉ số còn `None`; cần định danh nối toàn tuyến | Đúng: đặt cứng `None` (`xt_flow.py:335-339` ✓), test khẳng định `None`; không có sổ sự kiện hay mã lát. Đã ghi rời: `runs.jsonl`, receipt `DEPLOYS.json`, `STAGE.json`. Gần với `T-3854` còn mở, nhưng `T-3854` chờ `T-3851` | Bản ghi tối thiểu ở đợt 1 bằng task mới; `T-3854` giữ phần so song song với tuần tự, theo sau `T-3851` |
| 13 | Đo trước khi tách lõi | **Đã làm** sau mốc của đề xuất (#746): `xt_guard_profile.py`, báo cáo đo, ADR-0093, D-542 — compile trung vị 398,5 ms trong ≈ 0,55 s mỗi lệnh Bash; tách theo họ lệnh giảm tối đa ≈ 18 % | Không lặp lại; tách sâu xếp theo đúng điều kiện đề xuất nêu |
| 14 | Giảm tệp dùng chung, mảnh changelog | Trùng `T-3851` (diff thật nằm trong `files:`) và `T-3852` (`changelog.d/`), cả hai còn mở. Hiện `files:` chỉ dùng xếp đợt và digest, chưa cưỡng chế ghi; CHANGELOG một tệp, PR nào cũng sửa | Dùng ID cũ, không mở việc song song |
| 15 | Registry thiếu dữ liệu vận hành | Đúng: 7 sản phẩm đều `release: null`, `slo: ""`, `environments: []` ✓. Lược đồ đã có `environments`, `slo`, `release`; `registry pull` đọc receipt. Chưa có: giai đoạn, thời điểm quan sát, nguồn từng trường | Lược đồ 2 ở đợt 3 |
| 16 | Nâng khung trên một repo canary | Trùng `T-3865` (mô hình kéo, canary do dự án khai). Cần `XT_STEWARD_TOKEN` (việc của người) | Dùng ID cũ |
| 17 | Bootstrap và kiểm host thật | Đúng: không có `.devcontainer` hay script bootstrap; sáu host ngoài Claude Code ghi "thử nghiệm, chưa có payload thật". Bằng chứng thêm từ chính phiên này: container có Python 3.13, `uv` chỉ cấp 3.15.0b4 (CI dùng 3.15.2), `shellcheck` cài vào venv không nằm trên `PATH` — phải dựng tay | Bootstrap tối thiểu kéo lên đợt 1 |
| 18 | Một màn trạng thái dùng `xt_flow` | Đúng một phần: `xt_app` chưa dùng `xt_flow` ✓; frontend không tự tính quyết định, nên chưa có "bộ quyết định song song" | Giữ đợt 4 |

## Phát hiện chéo

1. **Mốc đã cũ.** Đề xuất ghim `b47cdf08`; `main` đã ở `9c014bb2` (#746) và phần "đo nền" của mục 13 đã xong.
2. **Trùng việc với PLAN đang mở.** Mục 05, 14, 16 trùng `T-3858`, `T-3851`, `T-3852`, `T-3865` của `PLAN-factory-e2e`;
   mục 12 và 10 gần với `T-3854`, `T-3863` nhưng hai task đó có cạnh `sau:` riêng (chờ `T-3851`, `T-3862`). Mở việc mới
   song song cho phần trùng trái luật "một chủ đề một nhà"; phần gần thì giữ task cũ nguyên chỗ.
3. **Mục 04 rộng hơn mô tả và là đổi chính sách.** Ngoài làn `derived` và PR fork, các verdict `wait`, `fix`, `update`,
   `human` không cứng, `closed` và ca lệch head đều đi qua ở chính sách mặc định — theo đúng `LOOP-STOP-002`, lớp đỡ là
   CI, ruleset và review. Dự án đích chưa áp ruleset thì không có lớp đỡ đó.
4. **Bẫy ở mục 05 đã có sẵn, và hàng rào tag chưa có ở live.** Mẫu `tags.json` hiện hành áp vào là chặn luôn workflow
   phát hành. Có thể cần hai ruleset nếu bypass đặt theo ruleset, không theo từng luật (**chưa xác minh** từ tài liệu
   GitHub hiện hành — việc đầu của lát).
5. **Mục 07 phá tương thích.** Script triển khai của dự án đích có thể đang dựa vào biến kế thừa (khoá đám mây,
   `SSH_AUTH_SOCK`, `KUBECONFIG`). Chuyển thẳng sang allowlist làm hỏng chúng; cần bước chuyển và ghi chú nâng bản.
6. **Việc cần người chưa tách.** Áp ruleset và cấp danh tính phát hành (quyền admin), `XT_STEWARD_TOKEN`, đích và khoá
   production, tài khoản host khác, chọn yêu cầu từ backlog thật. Đề xuất xếp chúng như việc của agent.
7. **Hạn cứng bị sót.** PROGRESS ghi hạn 2026-12-02 bỏ `pull_request_target` khỏi `pr-review.yml` (`T-3555`); đề xuất
   không nhắc. Ngày và căn cứ phía GitHub của hạn này **chưa xác minh** lại trong phiên.

## Chưa xác minh

- Loại actor được vào `bypass_actors` của ruleset tag và việc `GITHUB_TOKEN` có vào được không.
- Con số "4.417 test trong 752 nhóm" của đề xuất: phiên này không chạy cổng đầy đủ.
- Nguồn số liệu token hoặc chi phí theo phiên cho chỉ số `cost_usd_per_slice`.
