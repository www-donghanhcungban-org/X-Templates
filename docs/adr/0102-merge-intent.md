# ADR-0102: Ghim đích và head từ quyết định merge tới lệnh ghi

- **Trạng thái:** Đã chấp nhận ngày 2026-11-24 (D-579, D-588, T-5008).
- **Liên quan:** [ADR-0096](0096-merge-verdict-enforcement.md), AUD-HAR-492.

## Bối cảnh

Guard từng kiểm PR của checkout nhưng lệnh `gh` có thể chọn repository hoặc host khác bằng môi trường.
Ở chính sách mặc định, PR đủ điều kiện còn có thể đi qua bằng lệnh thiếu pin. Hai PR cùng số, thậm chí cùng
head, có thể thuộc hai repository khác nhau. Khoảng thời gian giữa đọc và ghi cũng đủ để PR nhận commit mới.

## Quyết định

Lựa chọn giữ một lệnh mẫu chỉ ghim SHA đòi mỗi executor tự suy lại đích. Khung chọn lưu bốn trường dưới
`merge_intent` trong kết quả JSON của `pr next` khi dữ liệu live cho hành động `merge`. Trước lần đọc GitHub đầu,
khung đọc đúng một `remote.origin.url` từ cấu hình Git cục bộ của checkout cung cấp policy. Hỗ trợ HTTPS, SSH
và SCP với host và owner/repo xác định. `--repo`, URL PR, `GH_REPO` và `GH_HOST` phải đồng ý với origin.
Không xác minh được origin hoặc đích lệch thì dừng trước khi đọc policy của checkout cho PR đó (D-588).

| Trường | Nguồn và kiểm tra |
|---|---|
| `host` | Host từ origin, truyền tường minh ngay từ lần đọc đầu và đối chiếu với `html_url` HTTPS chuẩn. |
| `repo` | Owner/name từ origin, viết tường minh trong đường REST và đối chiếu với URL cùng `base.repo.full_name`. |
| `pr` | Số nguyên dương trong kết quả REST phải trùng URL và số PR đã yêu cầu. |
| `expected_head` | Đủ 40 ký tự hex của `head.sha`, trùng head dùng để quyết định. |

`pr next` vẫn xét CI, review, làn và ngoại lệ theo chính sách dự án. Bằng chứng CI và review được đọc trên host
và repository đã xác minh. Nhánh có nhiều PR mở cần chỉ định số PR. URL người dùng ở tab PR được chuẩn hóa về
cùng số PR. `html_url` của API vẫn phải ở dạng chuẩn. Bản JSON PR offline dùng để xem trước và bỏ hướng dẫn ghi.
`merge-watch` giữ URL chuẩn suốt lượt theo dõi và chuyển tiếp tới `pr next`. Ngay trước khi ghi, steward đọc lại
PR trên đúng host, so cả bốn trường và trạng thái mở. Nếu đích đổi, head đổi, PR đóng hoặc lần đọc lỗi, lượt đó bỏ qua
lệnh ghi. Executor gửi `PUT repos/OWNER/REPO/pulls/N/merge` với `--hostname HOST`
và `sha=EXPECTED_HEAD`. GitHub kiểm SHA tại thời điểm ghi. Thay đổi trạng thái CI ở cùng SHA vẫn do ruleset
và các cổng CI hiện có bảo vệ. Quét PR, nhãn, cập nhật nhánh, CI, đọc commit merge và dispatch release dùng cùng
đích. Lệnh ghi review và nợ review cũng kiểm origin trước khi đọc phạm vi và gửi dấu. Cache quyền cộng tác
viên và cache chuỗi cập nhật nhánh giữ host trong khóa.

Guard đọc `merge-check` của checkout độc lập với `GH_REPO` và `GH_HOST` của lệnh yêu cầu. Khi tự merge, số PR
phải tường minh. Guard xét repo/host
tường minh qua `--repo`/`-R` và `gh api --hostname`, biến môi trường tiến trình, phép gán đầu lệnh, `env` và
`export`. Đích có dạng `HOST/OWNER/REPO` mang host riêng. Với REST chuẩn, host và đường dẫn owner/repo tường
minh của lệnh quyết định nơi ghi. Dạng dựa vào `GH_REPO` của checkout chỉ được xét từ cùng Git worktree, kể cả
thư mục con. Repo lồng là worktree riêng. Sai đích hoặc không đọc được đích bị chặn bằng `UNVERIFIED`.

| Đường ghi | Pin phía máy chủ |
|---|---|
| `gh pr merge` | `--match-head-commit` |
| `gh api` REST | Trường `sha` |
| MCP thiếu metadata endpoint tin cậy | `UNVERIFIED`. Dùng lệnh REST đã có host, repo, số PR và pin. |

Trên GitHub Enterprise, executor dùng REST với host tường minh. Tên server MCP và `GH_HOST` không chứng minh
endpoint của connector. Guard giữ ngoại lệ cứng, review và verdict. Nếu thiếu đích hoặc thiếu đúng một pin đầy
đủ, mã `UNVERIFIED` chặn ở mặc định và yêu cầu xác nhận ở `strict`. Dạng REST với đích tường minh đúng giữ yêu
cầu xác nhận ở `strict`. Điều kiện review và chặn bật auto-merge tiếp tục áp dụng.

## Kiểm chứng và đường lùi

`tests/test_merge_verdict_corpus.py` kiểm hai chính sách, host Enterprise, API trả PR khác, các nguồn chọn đích,
MCP chưa xác minh và dữ liệu đổi trước ghi. `tests/test_merge_target_binding.py` kiểm CLI với checkout Git thật
và GitHub CLI giả, gồm lần đọc đầu, từ chối checkout khác, watch, tác vụ phụ, cache và đường đọc ở thư mục con.
Corpus autonomy có ca tái hiện AUD-HAR-492 và đối chứng cùng host/repo/head. Revert PR triển
khai sẽ khôi phục hợp đồng cũ và cần mở lại AUD-HAR-492.

## Tài liệu nguồn

- [GitHub CLI environment](https://cli.github.com/manual/gh_help_environment)
- [gh pr merge](https://cli.github.com/manual/gh_pr_merge)
- [gh api](https://cli.github.com/manual/gh_api)
- [GitHub CLI — xử lý host và placeholder cho gh api](https://github.com/cli/cli/blob/trunk/pkg/cmd/api/api.go)
- [GitHub REST — Merge a pull request](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request)
