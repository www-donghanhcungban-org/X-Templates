# Đối chiếu báo cáo đánh giá ngoài ngày 24/11/2026 (UI/UX và bằng chứng)

Báo cáo "Đánh giá sâu X-Templates và năng lực thiết kế UI/UX" chấm repo ở `f670c50` (#782). Bản này kiểm lại từng nhận định ở `b82e369` (hai commit sau, #783 và #784 không chạm các điểm bị nêu) ngày 2026-11-24, rồi nêu chỗ đồng ý, chỗ chỉnh mức ưu tiên và chỗ báo cáo chưa nói tới. Kế hoạch đi kèm: [PLAN-ceiling-2026-11-24](../docs/autopilot/PLAN-ceiling-2026-11-24.md) (D-573; cấp lại số khi tiếp quản PR #786 vì D-571 đã được dùng trên `main`). Các đối chiếu ban đầu giữ mốc `b82e369`; phần bổ sung cuối ghi rõ mốc rà sau.

## Kết luận

Báo cáo đúng ở phần lớn dữ kiện và đúng ở nhận định trung tâm: khung mạnh về luật và máy kiểm, yếu ở chỗ nối chúng thành kết quả sản phẩm có số đo. Sáu phát hiện kỹ thuật kiểm lại được đều tái hiện. Ba chỗ cần chỉnh: mức ưu tiên của SBOM/VEX và của merge thiếu pin thấp hơn báo cáo xếp; hai nguyên nhân gốc chung (oracle của test và Gate của task) quan trọng hơn từng lỗi lẻ; trần của mảng UI/UX nằm ở việc cần người, máy không tự vượt được.

## Kiểm lại từng nhận định

| Nhận định của báo cáo | Kết quả kiểm ở `b82e369` | Đánh giá lại |
|---|---|---|
| SBOM/VEX báo sạch khi `components`/`statements` là chuỗi | Tái hiện: `xt.py static-check sbom` (kèm `--opt hashes=require`) và `static-check vex` trả `findings: []`, exit 0. `_flatten` trong `scripts/xt_checks/kind_sbom.py` bỏ qua mọi thứ không phải list | Đúng. Mức thực tế hiện là P2: `static-check` vào `main` sau tag `v3.36.0`, chưa nằm trong `release-check`. Lên P1 ngay khi dùng làm bằng chứng phát hành. Sửa rẻ nên làm đầu tiên |
| Sổ lát thiếu nguồn sự kiện, `T-4009` đã tick | Xác nhận: `SLICE_KINDS` có 9 loại, `slice_append` chỉ được gọi ở ba chỗ (`task_green`, `cost`, `review`) trong `scripts/xt.py`. Bảng SPEC-slice-ledger gán `requirement` cho `loop init`, `merged` cho `pr next`, `deployed` cho receipt | Đúng, và là phát hiện nặng nhất về quy trình: task được tick bằng test đưa sự kiện giả vào bộ tính |
| Ruleset tag `v*` chưa có trên GitHub | Khớp PROGRESS (`T-4007` chờ quyền admin). Không gọi lại API rulesets trong phiên này. `immutable=false` của release: chưa xác minh | Đúng. Việc của người; máy chỉ chuẩn bị lệnh và phép thử |
| Merge thiếu pin HEAD đi qua `OTHER_ASK`; `GH_REPO` khác đường `--repo` | Khớp sổ: AUD-HAR-492 chấp nhận tới 2027-01-21; thiếu pin là phạm vi ADR-0096 chủ ý để ngoài. Không chạy lại phép thử | Đúng dữ kiện. Xếp P2: cần đổi HEAD giữa kiểm và merge, và GitHub vẫn chặn check đỏ. Hướng "một intent host/repo/PR/expected_head" đáng làm, cần ADR |
| Adapter còn để `GIT_CONFIG_COUNT` qua; allowlist rỗng bị hiểu là chưa bật | Xác nhận bằng mã: `DEPLOY_ENV_DROP` và `DEPLOY_ENV_DROP_PREFIX` không có `GIT_`; `deploy_env_pass()` trả `None` khi rỗng | Đúng. P1 trước khi adapter chạy với khoá production |
| Bộ dò tài liệu thực thi khác parser chạy lệnh | Khớp sổ: AUD-HAR-478 chấp nhận tới 2027-01-21 | Đúng. Nên kéo sớm vì `release-check` đã dùng nợ review làm điều kiện |
| Build `--strict` không đòi đủ gói | Xác nhận bằng mã: `entries()` trong `scripts/xt_pack.py` chỉ đòi `ARTIFACT_SCRIPTS` và `VERSION`; gói trong `PACKAGES` vắng thì `rglob` trả rỗng, không lỗi | Đúng. P2, sửa rẻ |
| Hai file lõi 48.160 dòng, vẫn tăng | `wc -l`: `xt.py` 23.615, `guard.py` 24.546 | Đúng. Chưa có cơ chế nào ngăn hai file tiếp tục lớn |
| `UX-VISUAL-009` dùng `deviceScaleFactor: 4` làm zoom 400 % | Xác nhận ở `framework/06-design-ux/motion-and-visual-quality.md:59` | Đúng. DPR không gây reflow; phải tách ba phép kiểm |
| Starter chưa nối cổng UI | Xác nhận: trong `framework/templates/packs/web-api-ts/starter` không có axe, ma trận viewport hay kiểm bàn phím ngoài `index.html` | Đúng. Đây là khoảng hở đáng giá nhất của mảng UI |
| `verify-render` chỉ chạy axe ở 1280 px, `UNMEASURED` không đỏ | Chưa đọc lại mã `framework/templates/ui-gates/verify-render.mjs` trong phiên này | Tạm nhận theo báo cáo; kiểm lại khi làm task tương ứng |
| Dự án đích còn ở 3.34.0 | Khớp PROGRESS | Đúng. Cần `XT_STEWARD_TOKEN` |
| Release-check cục bộ NO-GO vì AUD-HAR-514, 61 tệp nợ | AUD-HAR-514 là 🟢 đang mở trong sổ. Số 61 do báo cáo tự nêu là chưa đối soát được dấu review | Không phải khoảng hở: NO-GO trên `main` giữa hai bản là trạng thái bình thường, đóng ở lượt `/complete` kế |

### Bổ sung khi tiếp quản PR #786 tại `7a1cf1d`

- Đã đọc `framework/templates/ui-gates/verify-render.mjs` và README: axe chạy ở 1280 px; viewport hẹp mới kiểm tràn ngang. **`--strict` đã tồn tại và làm `UNMEASURED` thoát mã 1**; mặc định không strict thoát 0 khi không có vi phạm khác. Đây là đối chiếu mã, chưa chạy trình duyệt. `T-5013` vì thế dùng lại strict, bổ sung axe hẹp, báo cáo và test thực thi; không coi strict là tính năng còn thiếu.
- [SPEC-slice-ledger](../docs/specs/SPEC-slice-ledger.md) phân biệt nguồn chưa nối, không có sự kiện và cửa sổ quan sát chưa đóng. Diễn tập tích hợp phải phủ đủ chín đường ghi; pilot không cần tạo incident khi thực tế không có. Gate pilot phải đối chiếu bằng chứng và receipt, không chỉ tìm cụm chữ trong báo cáo.
- Kế hoạch đã sửa điều kiện chờ admin của `T-5020`, phụ thuộc của lần phát hành và Gate cho UI, diễn tập tag, pilot, nâng dự án đích. Các sửa này hoàn thiện kế hoạch; chưa đóng phát hiện kỹ thuật hoặc tick task triển khai.

## Hai nguyên nhân gốc chung

1. **Oracle của test.** Test SBOM/VEX khẳng định chính hành vi sai (đầu vào sai kiểu trả danh sách rỗng), nên coverage 100 % và kiểm đột biến đều không bắt được. Cùng mẫu có thể nằm ở các loại `static-check` khác. Cần một test tính chất cho mọi loại: container sai kiểu không bao giờ cho kết quả sạch, và kết quả luôn kèm số mục đã thực sự kiểm.
2. **Gate của task.** `T-4009` xanh vì Gate chạy bộ tính trên dữ liệu giả. Task "nối luồng" phải có Gate đi qua lệnh thật trong repo tạm. Hai lỗi này cùng loại với thứ khung sinh ra để chống (P1: bằng chứng, không lời khai), nên phải sửa ở mức quy ước, không chỉ ở hai chỗ bị bắt.

## Chỗ báo cáo chưa nói hoặc nói nhẹ

- Chưa có trần kích thước cho `xt.py` và `guard.py`. Kế hoạch tách guard không có tác dụng nếu logic mới vẫn tiếp tục vào hai file đó.
- Hạn 2026-12-02 bỏ `pull_request_target` khỏi `pr-review.yml` nằm ngoài phạm vi báo cáo nhưng đến trước mọi mốc khác.
- Báo cáo không chạy được trình duyệt và không có ảnh, nên không chấm được thẩm mỹ. Nhận định "chưa chứng minh" vì vậy là thiếu bằng chứng, không phải bằng chứng là kém.

## Trần của dự án nằm ở đâu

Máy tự làm được: sửa bộ kiểm, nối sổ lát, đóng môi trường adapter, nối cổng UI vào starter, viết đường thiết kế (brief, phương án, lý do chọn), tách lõi theo lát. Máy không tự làm được và đang giữ trần: ruleset tag và danh tính phát hành (`T-4007`), `XT_STEWARD_TOKEN` để lan bản mới sang dự án đích, người dùng thật cho thử tác vụ, môi trường production và khoá cho pilot. Kế hoạch tách hai nhóm để việc của người không chặn việc của máy.
