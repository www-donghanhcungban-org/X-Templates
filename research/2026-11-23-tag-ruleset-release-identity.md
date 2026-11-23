---
title: Ruleset tag và danh tính phát hành — quyền tạo tách khỏi quyền sửa, xoá
kind: research
updated: 2026-11-23
---

# Ruleset tag và danh tính phát hành

> T-4005, T-4006 của [PLAN cải tiến](../docs/autopilot/PLAN-improve-2026-11-23.md). Nguồn chính thức được đọc
> ngày **2026-11-23**. Phần cấu hình trong repo chuẩn bị cho chủ repo; chưa phải bằng chứng đã áp ruleset live.

## Kết luận và phạm vi

Bypass áp dụng cho **cả ruleset**, không theo từng luật. Tách quyền tạo tag khỏi quyền sửa/xoá bằng hai ruleset cùng
phạm vi `refs/tags/v*`: `tags-create.json` chỉ có `creation`; `tags.json` chỉ có `update` và `deletion`.
Ruleset tạo cần đúng một GitHub App chuyên phát hành, actor type `Integration`, App ID dương do chủ repo xác minh,
`bypass_mode: always`. Ruleset sửa/xoá không có bypass, kể cả cho App phát hành. Đây là cách dùng cơ chế ruleset
của GitHub để giới hạn quyền; chưa thay cho diễn tập với danh tính thật. [1][2]

Mẫu tạo để `bypass_actors: []` vì không có App ID dùng chung cho các dự án. `admin-plan` nhận trạng thái này là thiếu,
không coi một ruleset chặn mọi actor là thiết lập hoàn chỉnh. Script cho chủ repo từ chối POST mẫu tạo còn trống;
chủ repo điền ID thật, commit cấu hình rồi mới áp. Không tự chọn role `write` hay `admin` làm đường tắt.
Installer giữ file đã được dự án chỉnh theo manifest; bản mẫu mới không ghi đè App ID đã khai.

## Những gì tài liệu GitHub xác nhận

| Câu hỏi | Bằng chứng và hệ quả |
|---|---|
| Actor nào được khai? | Schema REST hiện liệt kê `Integration`, `OrganizationAdmin`, `RepositoryRole`, `Team`, `DeployKey`, `User`. `OrganizationAdmin` không áp dụng repo cá nhân. Khung chọn App riêng, không cần cấp tất cả các loại. [1] |
| Bypass ở cấp nào? | `bypass_actors` là thuộc tính của ruleset, ngang hàng với danh sách `rules`; không có bypass riêng cho một rule. Bypass tạo trên ruleset chung sẽ đồng thời cho qua update/deletion trong ruleset đó. [1] |
| Dùng chế độ nào? | `always`, `pull_request`, `exempt` có trong API; `pull_request` chỉ áp dụng ruleset branch. Dùng `always` cho App tạo tag, giữ audit bypass thay vì `exempt`. [1] |
| `creation` tác động ra sao? | Chỉ actor có bypass tạo được ref khớp phạm vi. Danh sách trống chặn cả workflow nếu không có quyền bypass thích hợp. [2] |
| Ai áp được ruleset? | Quyền admin hoặc quyền riêng sửa repository rules. Quyền push không tự có quyền sửa ruleset. [2] |

`GITHUB_TOKEN` là installation access token của GitHub Actions App được cấp cho job, không phải một actor độc lập
theo tên biến môi trường. [3] Tài liệu đã đọc **chưa xác nhận** native Actions App có thể được thêm vào danh sách bypass
của repo này; chưa có phép thử live. Vì vậy không khẳng định tuyệt đối nó được hay không được thêm, và không xem fallback
`github.token` trong workflow là bằng chứng đã cấp quyền tạo tag. Cần App phát hành riêng và phép thử T-4007.
Quyền theo App cũng không phân biệt từng workflow; chủ repo phải giữ quyền sử dụng danh tính phát hành đúng phạm vi.

Installation token của App hết hạn sau **một giờ**; không lưu một token như vậy vào `XT_RELEASE_TOKEN` rồi coi đó là
cấu hình phát hành lâu dài. [6] Luồng bền cần tạo token mới trong từng run từ App đã cài và khoá riêng được chủ tài khoản
cấp, giới hạn repo/quyền cần dùng. GitHub hướng dẫn `actions/create-github-app-token` cho bước này. [7] Workflow hiện còn
đọc secret tĩnh `XT_RELEASE_TOKEN` hoặc `github.token`; kết nối danh tính App và quản lý vòng đời token là điều kiện phải
hoàn thành trước diễn tập T-4007, không phải kết quả của việc sửa hai tệp JSON.

## Trạng thái live và việc của chủ repo

Ngày **2026-11-23**, đọc
[`GET /repos/www-donghanhcungban-org/X-Templates/rulesets`](https://api.github.com/repos/www-donghanhcungban-org/X-Templates/rulesets)
trả đúng một ruleset: `main`, ID `25128933`, target `branch`, enforcement `active`. **Chưa có ruleset tag.**
Phiên có quyền push nhưng không có quyền admin. Đây là bằng chứng đọc tại thời điểm kiểm; không là cam kết trạng thái tương lai.

Chủ repo cần hoàn thành T-4007: cấp danh tính phát hành thật, áp hai ruleset, diễn tập cô lập actor thường bị từ chối tạo,
sửa, xoá `v*`; workflow chuẩn tạo được tag nhưng không được sửa/xoá. Giữ tag `v3.35.0` nguyên vẹn. Sau khi cấu hình đã commit
và áp live, `admin-plan --only ruleset` kiểm đúng hàng ruleset; thiếu secret triển khai hay ledger dev khác không làm hàng này
đỏ. Kết quả đạt của CLI vẫn cần đi cùng bằng chứng diễn tập danh tính; không tự tick T-3858 từ mẫu đã sửa.

### Di trú dự án đã áp mẫu gộp creation/update/deletion

Quy trình dưới đây dành cho chủ repo, chưa chạy trên GitHub trong phiên nghiên cứu. Bypass giữa các ruleset không thay thế
nhau: thêm ruleset mới không xoá luật `creation` của ruleset cũ. Không POST thêm một ruleset cùng tên rồi coi việc di trú đã xong.

1. Đọc danh sách ruleset và nội dung từng ID trên đúng repo; ghi ID của ruleset tag cũ cùng payload để có đường lùi.
   Điền App ID vào `tags-create.json`, giữ tên ruleset cũ trong `tags.json`, commit cả hai cấu hình đã rà.
2. **Tạo ruleset tạo tag trước**: chọn `XT_NEW_RULESET_FILE=.github/rulesets/tags-create.json`. Chỉ để trống
   `XT_EXISTING_RULESET_ID` khi đã kiểm ruleset này chưa tồn tại; script sẽ POST. Nếu đã có, dùng ID của chính ruleset đó
   để PUT, không tạo bản trùng. App có thể vẫn bị luật `creation` cũ chặn ở thời điểm này.
3. **Cập nhật ruleset cũ theo đúng ID**: chọn `XT_NEW_RULESET_FILE=.github/rulesets/tags.json` và đặt
   `XT_EXISTING_RULESET_ID` bằng ID tag cũ đã xác minh ở bước 1. Script kiểm file rồi PUT
   `/repos/{owner}/{repo}/rulesets/{ruleset_id}`; payload mới bỏ `creation`, chỉ giữ update/deletion và không bypass. [1]
4. GET lại cả hai ID: creation chỉ có trong ruleset mới và đúng một App, update/deletion trong ruleset cũ không bypass.
   Chạy `admin-plan --only ruleset` rồi diễn tập T-4007. Chỉ kết luận hoàn tất khi cấu hình và phép thử actor đều đạt;
   không xoá hay di chuyển tag đã phát hành để thử.

Script chỉ hỗ trợ tạo mới hoặc cập nhật theo ID do chủ repo đã kiểm; nó không tự chọn ID hay tự áp cấu hình. Cả ba file
`main.json`, `tags.json`, `tags-create.json` đi qua cùng bộ kiểm Python với CLI trước POST/PUT. File thiếu, JSON lỗi,
`main.json` có target tag, hoặc App ID dạng số thực đều bị từ chối.

## Archive và receipt bất biến cho T-4017

Workflow hiện tạo archive, attest archive, tạo và attest promotion receipt rồi push tag; chưa upload hai tệp để nơi dùng
tải đúng bytes. GitHub có immutable releases: khi publish, assets bị khoá và tag gắn với commit được bảo vệ. Quy trình chính
thức là tạo **draft release**, đính kèm đủ archive và receipt, sau đó publish. Release tự có attestation liên kết tag, commit,
assets; vẫn giữ việc xác minh danh tính workflow và digest theo hợp đồng của khung. [4][5]

Bật release immutability là việc quản trị cần xác minh, không tự suy từ tên tệp có phiên bản. Immutable release đã publish
không cho thêm, thay hay xoá asset; việc xoá cả release có hệ quả riêng và không phải đường cập nhật bản cũ. Dự án cần kiểm
cài đặt này trước khi coi assets là bất biến, giữ tên phiên bản không tái sử dụng, và phát hành bản mới khi cần sửa. [4]
Phần upload/download và phép thử bytes thuộc T-4017/T-4018, chưa hoàn thành bởi việc tách ruleset.

## Nguồn

1. [GitHub REST — Repository rules](https://docs.github.com/en/rest/repos/rules), đọc 2026-11-23: schema actor,
   cấp bypass và quyền API.
2. [GitHub — Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets),
   đọc 2026-11-23: creation/update/deletion và quyền quản trị.
3. [GitHub — GITHUB_TOKEN](https://docs.github.com/en/actions/concepts/security/github_token), đọc 2026-11-23:
   danh tính installation của token từng job.
4. [GitHub — Immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases),
   đọc 2026-11-23: phạm vi khoá, attestation và thứ tự draft/asset/publish.
5. [GitHub — Managing releases](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository),
   đọc 2026-11-23: tạo draft, gắn asset và phát hành.
6. [GitHub — Generating an installation access token](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app),
   đọc 2026-11-23: thời hạn một giờ và phạm vi repo/quyền của token App.
7. [GitHub — Authenticating an App in an Actions workflow](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/making-authenticated-api-requests-with-a-github-app-in-a-github-actions-workflow),
   đọc 2026-11-23: tạo token mới trong workflow từ App đã được chủ tài khoản cài và cấp khoá.
