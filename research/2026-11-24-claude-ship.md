---
title: Claude Ship (ra mắt 2026-11-23) — dữ kiện, đối chiếu với khung và cách chung sống
kind: research
updated: 2026-11-24
---

# Claude Ship: dữ kiện, đối chiếu với khung, khuyến nghị

Đọc ngày 2026-11-24 từ tài liệu chính thức của Anthropic (`code.claude.com/docs/en/…`). Hai lượt đọc: một agent tra tổng quát, rồi một lượt riêng trích **nguyên văn** tám điểm then chốt ở bốn trang (`claude-ship`, `ship-command`, `pr-steward-security`, `approvals`) và `approvals-github-rules`. Mức bằng chứng ở cột cuối: **(a)** tài liệu chính thức đọc trực tiếp; **(b)** thứ cấp. Không có mục nào ở mức (c) trong bảng dữ kiện; điều chưa xác minh ở §5.

## 1. Kết luận

- Claude Ship là bộ agent cho pull request trên GitHub: **Code Review** (GA), **PR Steward** và **Claude Approvals** (public beta), cùng hai lệnh CLI `/ship` và `/steward`.
- Khung X-Templates **không dùng** PR Steward và Approvals làm đường merge; Code Review chỉ là tín hiệu rà phụ (ADR-0100). Lý do chính: hai điều tài liệu tự nêu — hook của dự án không áp dụng cho `gh`/`git` do `/ship` tự chạy, và `/ship` không có bước xác nhận thật — làm lệch với hàng rào của khung (ADR-0018).
- Con số hiệu quả của Anthropic (PR merged gấp đôi, PR bị revert giảm hơn 40 %) là số nội bộ không có đối chứng; khung không dựa vào nó.

## 2. Dữ kiện (trích nguyên văn khi dùng ngoặc kép)

| Dữ kiện | Nguồn | Mức |
|---|---|---|
| Ra mắt 2026-11-23, "available today in beta"; Code Review GA, PR Steward và Claude Approvals public beta | `claude-ship`; bài ra mắt `claude.com/resources/articles/introducing-claude-ship` | (a) |
| "Claude Ship is for organizations on Team and Enterprise plans." Không dùng được với Zero Data Retention, cấu hình HIPAA hay khoá mã hoá do khách quản lý (CMEK) | `claude-ship`, `approvals` | (a) |
| "`/ship` proceeds with no confirmation prompt." Trước commit và trước push chỉ có dòng `Esc to cancel`, "If you do nothing, `/ship` continues after a few seconds." | `ship-command` | (a) |
| "`/ship` can commit all your uncommitted changes, new files included." "`/ship` looks for secrets by file name, such as `.env`, so look inside your files yourself." Deny rule `Read(./notes.txt)` không ngăn tệp vào commit | `ship-command` | (a) |
| Lệnh commit/push của `/ship` do Claude Code chạy "outside the sandbox"; tool hooks như `PreToolUse`: "They don't run" (với `/ship`) và "They don't apply to the `gh` and `git` commands that Claude Code runs itself, outside the sandbox" (trong watch); git hooks của repo cũng không chạy ở các lượt đó | `ship-command` (bảng quy tắc) | (a) |
| Trong watch, lệnh git viết dạng `git -c core.hooksPath=/dev/null push` | `ship-command` | (a) |
| Tắt `/ship` và `/steward` toàn tổ chức: khoá `skillOverrides` ở managed settings, `ship-local` và `steward` đặt `off`; deny `Bash(git push *)` thì "No watch starts" | `ship-command` | (a) |
| `/ship` chỉ chạy bằng CLI trong bản clone cục bộ: "Cloud sessions don't have them." (thay thế cho cloud: auto-fix hoặc `/autofix-pr`) | `ship-command` | (a) |
| PR Steward bị dịch vụ từ chối: approve PR; đổi branch protection/ruleset/status hay ghi check run; xoá nhánh; push tag. Merge, bật auto-merge, force-push, push sang nhánh khác, dismiss review: **để GitHub branch rules quyết định** | `pr-steward-security` | (a) |
| "The rules match a command's text and the check is a model's judgment, so a command that's written another way can pass both." | `pr-steward-security` | (a) |
| Khuyến nghị: bắt buộc review bằng branch rules và "keep the Claude GitHub App off each ruleset's bypass list" | `pr-steward-security` | (a) |
| "Claude's approving review can meet a GitHub branch rule that requires one approval." Check Approvals chỉ chặn merge khi đặt là required check; `seats: 0` hoặc `seats: 1` (tác giả điền được) và danh sách `from` cho phép bot đều cho merge không người duyệt | `approvals-github-rules` | (a) |
| "If you use GitHub auto-merge or a merge queue with a policy that doesn't require a person's approval, a change can merge without anyone acting." | `approvals-github-rules` | (a) |
| "`claude: approves` … Claude can approve a change that nothing has reviewed." Push thẳng vào nhánh mặc định không có check | `approvals`, `approvals-github-rules` | (a) |
| Giá: theo token qua usage credits, tách khỏi hạn mức gói; "Observe mode is billed."; "PR Steward has no spend limit of its own until you set one."; tắt usage credits: "an agent that's on keeps running and billing your organization." | `claude-ship` | (a) |
| Yêu cầu `/ship`: Claude Code ≥ v2.1.330, GitHub CLI ≥ 2.63, git ≥ 2.38 | `ship-command` | (a) |
| Tin cùng ngày: TechCrunch và một số trang khác | báo | (b) |

## 3. Đối chiếu với khung

| Việc | Khung hiện có | Claude Ship | Nhận định |
|---|---|---|---|
| Theo dõi PR sau khi mở | `pr next`, `merge-watch`, `pr-steward` (RUNBOOK-PR-STEWARD) | PR Steward, `/steward` | Trùng chức năng; khung ghim head và có điều kiện merge máy đọc |
| Rà độc lập | reviewer năng lực cao hơn người viết (`LOOP-ORCH-005`), dấu `pr reviewed` ghim head | Code Review | Có thể bổ sung như tín hiệu, không thay dấu |
| Cổng merge | CI xanh + `merge-check`, không auto-merge (ADR-0036) | Approvals, policy `.claude/approvals.yml` | Approvals thêm một đường tạo approval mà `pr next` không biết; ngược nguyên tắc "bằng chứng, không lời khai" (P1) |
| Hàng rào hành động | guard `PreToolUse`, "bị chặn là kết luận" (ADR-0018, `LOOP-STOP-025`) | giới hạn riêng của Anthropic, hook không áp dụng | `/ship` đi vòng qua guard của dự án |

## 4. Rủi ro cho dự án đích dùng khung

1. Dev chạy `/ship` ở máy: commit toàn bộ tệp chưa commit và push **không qua guard và git hooks của dự án**, chỉ dò bí mật theo tên tệp.
2. Bật Approvals cùng auto-merge hoặc merge queue và policy không đòi người: có thể merge không ai hành động.
3. PR Steward ghi `contents`, `pull requests`, có thể cả `workflows`; hai lớp chặn merge của nó là luật khớp văn bản và phán đoán của model — tài liệu thừa nhận lệnh viết khác có thể qua cả hai. Lớp chặn thật là GitHub branch rules.
4. Chi phí không trần mặc định (PR Steward), tắt usage credits không dừng agent đang bật, observe mode vẫn tính tiền.
5. Code và PR đi qua hạ tầng Anthropic; tổ chức bật ZDR/HIPAA/CMEK không dùng được.

## 5. Chưa xác minh

- Hiệu quả thật trên dự án này: chưa có số đo (cần chạy thử ở observe mode trên repo thật).
- Giá cụ thể theo token của từng agent; khuyến mãi credits cho Enterprise (hạn claim 2027-01-15, theo trang hỗ trợ) chưa đọc từng chữ.
- Bản Claude Code đầu tiên có `/ship` (chỉ biết ≥ v2.1.330); việc `/ship` ra desktop app; chi tiết `code-review-setup`, `pr-steward-setup`, `approvals-setup` chưa đọc.
- Tài liệu không nói rõ `PreToolUse` có áp dụng cho lệnh git/gh do model tự đề xuất trong watch hay không (chỉ nói không áp dụng cho lệnh Claude Code tự chạy).
- Nhiều skill cộng đồng tên `/ship` (không phải của Anthropic) — đừng nhầm.
