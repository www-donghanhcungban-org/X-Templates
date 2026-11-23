# Audit delta 2026-11-23 — `27d70c0c..fae1ca30` (#746–#755)

> Phạm vi: diff tích luỹ #746–#755 chia hai lô, mỗi lô một lượt `reviewer-alt` chỉ đọc (effort cao nhất, độc lập với người viết); phần #756 đã có ba lô rà ở head cũ và hai lượt rà hẹp ở các head sau (xem hàng AUD-HAR-484…487, AUD-CI-041/042 trong sổ). Kết quả: **0 🔴**; 🟠 và 🟢 ghi vào [sổ](AUDIT-STATUS.md). Chưa chạy: bốn lớp `GuardFuzzMutation`, `mutate-guard`, hành vi GitHub thật (ruleset, bypass của App), integrity 10 gói nền tảng Biome.

## Lô A — guard, hồ sơ guard, quyết định merge (#746, #754)
Không có đường lọt hay `allow` sai verdict; mã chặn được giữ qua mọi lớp bọc đã thử; tài liệu khớp mã.

| Mức | Chỗ | Điều tìm thấy (đường tái hiện) |
|---|---|---|
| 🟠 | `guard.py:10532-10552`, `12536` | `gh pr merge 7 --disable-auto -R o/r` (verdict `wait`) ra `deny MERGE_INELIGIBLE`; dạng trần `--disable-auto` vẫn qua, dù chú thích ghi "máy phải tắt được" |
| 🟢 | `guard.py:12549-12567` | pin không phải 40 hex nguyên văn (`$H`, `$(git rev-parse HEAD)`, `expectedHeadSha` viết hoa) ra `MERGE_HEAD_MISMATCH`, lý do gây hiểu lầm |
| 🟢 | `xt_guard_profile.py:99-105` | `--closure` không theo phụ thuộc trong biểu thức khởi tạo hằng (`POLICY`), số hàng kèm theo thấp |
| 🟢 | `tests/test_merge_verdict_codes.py:78-85` | nhánh `strict` của ma trận chỉ mô phỏng, thiếu test qua `main()` (nghi, chưa chạy đột biến) |
| 🟠 (có từ trước) | `guard.py` | `GH_REPO`/`GH_HOST` (đầu lệnh, `env`, `export`) vượt cổng "repo khác"; gần AUD-SEC-030 |
| 🟢 (có từ trước) | `guard.py:10525-10527` | docstring ghi `--admin` "luôn hỏi", mã deny `MERGE_ADMIN` |

## Lô B — ops, CI, release, sàn Python (#751, #752, #755)
Sàn runtime nhất quán (`MIN_PYTHON`, `install.py`, `dev-task.sh`); ruleset tag đúng hợp đồng; 9/9 hash Playwright 1.65.2 khớp PyPI.

| Mức | Chỗ | Điều tìm thấy (đường tái hiện) |
|---|---|---|
| 🟠 | `BLUEPRINT.md:62` | `BASE-DEP-003` đòi đúng `(3, 15)`; #751 hạ sàn xuống 3.13 mà sót mục này (đỏ trên 3.13; xanh ở CI 3.15.2) |
| 🟠 | `ruff.toml:3` | `target-version = "py315"` trái ADR-0094; `ruff format --diff` đề xuất lại cú pháp `except A, B:` của 3.14 |
| 🟠 (có từ trước) | `RUNBOOK-PR-STEWARD.md:93-97`, `release-tag.yml:118` | runbook dạy `XT_RELEASE_TOKEN` là PAT, workflow nhận `secrets.XT_RELEASE_TOKEN \|\| github.token`, mà `release_actor()` chỉ nhận một actor `Integration`: sau khi áp `tags-create.json` live, PAT và đẩy tay không có bypass (hỏng theo hướng đóng) |
| 🟢 | `requirements-e2e.txt` (và bản starter) | khoá chỉ có wheel cp315, không cài được trên 3.13; ghi chú "xác minh 2026-11-14", "8 wheel" (thực 9 hash); `DEPENDENCIES.md:41` còn Playwright 1.64.1 |
| 🟢 | `xt_ops_setup.py:602-608` | script chủ repo `PUT` theo ID không `GET` đối chiếu `name`/`target` ruleset |
| 🟢 | `xt_ops_setup.py:618-634` | `admin-plan --only X --out FILE` đè bản kế hoạch đầy đủ bằng bản một hàng |
| 🟢 | ADR-0094 | ghi chi phí CI "~ một shard", thực là ma trận 8 shard |

Nghi ngờ, chưa tái hiện: dự án nằm trong thư mục con của repo git làm script chủ repo thoát 2; luật `update` kèm `parameters` làm `tag_rules_configured` báo thiếu mãi (đỏ oan).

## Xử lý
Mọi 🟠/🟢 ở trên là nợ theo ADR-0062 (không có 🔴): sửa hoặc `chấp nhận` có chủ và hạn trong sổ, kèm D-NNN. Ghi chú vận hành: guard chặn một lệnh `git grep` chỉ đọc có pathspec `DECISIONS.md` (AUD-SEC-641), nghi chặn oan.
