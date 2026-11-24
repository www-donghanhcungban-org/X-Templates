# ADR-0102: Ghim đích và head từ quyết định merge tới lệnh ghi

- **Trạng thái:** Đã chấp nhận ngày 2026-11-24 (D-579, T-5008).
- **Liên quan:** [ADR-0096](0096-merge-verdict-enforcement.md), AUD-HAR-492.

## Bối cảnh

Guard từng kiểm PR của checkout nhưng lệnh `gh` có thể chọn repository hoặc host khác bằng môi trường.
Ở chính sách mặc định, PR đủ điều kiện còn có thể đi qua bằng lệnh thiếu pin. Hai PR cùng số, thậm chí cùng
head, có thể thuộc hai repository khác nhau. Khoảng thời gian giữa đọc và ghi cũng đủ để PR nhận commit mới.

## Quyết định

Lựa chọn giữ một lệnh mẫu chỉ ghim SHA đòi mỗi executor tự suy lại đích. Khung chọn lưu bốn trường dưới
`merge_intent` trong kết quả JSON của `pr next` khi dữ liệu live cho hành động `merge`.

| Trường | Nguồn và kiểm tra |
|---|---|
| `host` | Host trong `html_url` HTTPS của pull request, trùng host đã chọn tường minh. |
| `repo` | Owner/name trong URL phải trùng `base.repo.full_name` và repository tường minh của lần đọc. |
| `pr` | Số nguyên dương trong kết quả REST phải trùng URL và số PR đã yêu cầu. |
| `expected_head` | Đủ 40 ký tự hex của `head.sha`, trùng head dùng để quyết định. |

`pr next` vẫn xét CI, review, làn và ngoại lệ theo chính sách dự án. Bằng chứng CI và review được đọc trên host
và repository đã xác minh. Nhánh có nhiều PR mở cần chỉ định số PR. Bản JSON PR offline dùng để xem trước và
không sinh lệnh ghi. Ngay trước khi ghi, steward đọc lại đúng PR trên đúng host, so cả bốn trường và trạng thái mở.
Nếu đích đổi, head đổi, PR đóng hoặc
lần đọc lỗi, lượt đó bỏ qua lệnh ghi. Executor gửi `PUT repos/OWNER/REPO/pulls/N/merge` với `--hostname HOST`
và `sha=EXPECTED_HEAD`. GitHub kiểm SHA tại thời điểm ghi. Thay đổi trạng thái CI ở cùng SHA vẫn do ruleset
và các cổng CI hiện có bảo vệ.

Guard đọc `merge-check` của checkout độc lập với `GH_REPO` và `GH_HOST` của lệnh yêu cầu. Guard xét repo/host
tường minh qua `--repo`/`-R` và `gh api --hostname`, biến môi trường tiến trình, phép gán đầu lệnh, `env` và
`export`. Đích có dạng `HOST/OWNER/REPO` mang host riêng. Với REST chuẩn, host và đường dẫn owner/repo tường
minh của lệnh quyết định nơi ghi. Sai đích hoặc không đọc được đích bị chặn bằng `UNVERIFIED`.

| Đường ghi | Pin phía máy chủ |
|---|---|
| `gh pr merge` | `--match-head-commit` |
| `gh api` REST | Trường `sha` |
| MCP GitHub tại github.com | `expectedHeadSha` cùng `owner`, `repo`, `pullNumber` |

Trên GitHub Enterprise, executor dùng REST với host tường minh. Guard so đích và pin với kết quả live khi nhận
sự kiện MCP GitHub. Các server MCP khác giữ mã `UNVERIFIED`. Guard giữ thứ tự xét ngoại lệ cứng, repo tường minh,
review và verdict rồi kiểm host, repo, số PR và SHA của phản hồi live. Nếu thiếu trường hoặc thiếu đúng một pin đầy đủ, mã `UNVERIFIED`
chặn ở mặc định và yêu cầu xác nhận ở `strict`. Dạng REST với đích tường minh đúng giữ yêu cầu xác nhận ở
`strict`. Điều kiện review và chặn bật auto-merge tiếp tục áp dụng.

## Kiểm chứng và đường lùi

`tests/test_merge_verdict_corpus.py` kiểm hai chính sách, host Enterprise, API trả PR khác, các nguồn chọn đích,
MCP chưa xác minh và dữ liệu đổi trước ghi. `tests/test_merge.py` kiểm đường steward với GitHub CLI giả trong
repository tạm. Corpus autonomy có ca tái hiện AUD-HAR-492 và đối chứng cùng host/repo/head. Revert PR triển
khai sẽ khôi phục hợp đồng cũ và cần mở lại AUD-HAR-492.

## Tài liệu nguồn

- [GitHub CLI environment](https://cli.github.com/manual/gh_help_environment)
- [gh pr merge](https://cli.github.com/manual/gh_pr_merge)
- [gh api](https://cli.github.com/manual/gh_api)
- [GitHub CLI — xử lý host và placeholder cho gh api](https://github.com/cli/cli/blob/trunk/pkg/cmd/api/api.go)
- [GitHub REST — Merge a pull request](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request)
