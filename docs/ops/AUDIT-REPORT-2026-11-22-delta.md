# Audit delta ngày 22/11/2026

Dải `98770bc7..ce08f914` (#730–#737, 25 tệp). Mốc rà là `main` tại `ce08f914099c6ecf34e41b68799bf06a5e2c39cc`. [Sổ audit](AUDIT-STATUS.md).

## Phạm vi

`xt.py audit plan` (Python 3.15.0b4) báo bảy nhóm cần quét lại: ARCH, SEC, CODE, TEST, DOC, XFEAT, HAR. Nhóm còn lại không có tệp đổi nên giữ SHA cũ. Người viết dải này là phiên chính; mọi reviewer là `reviewer-alt` chạy `claude-opus-5-5`, effort `max`, cao hơn người viết (`LOOP-ORCH-005`).

| Cụm | Phạm vi | Kết quả |
|---|---|---|
| Mã/test | `session-start.sh`, `install.py`, `xt_distribution.py`, `xt_ops_setup.py`, bốn tệp test | 0 🔴, 1 🟠, 5 🟢. 858 test của bốn module xanh (exit 0). |
| Tài liệu/harness, lượt 1 | 17 tệp tài liệu | INCONCLUSIVE: hết lượt, 2 🟠, 8 🟢. |
| Tài liệu/harness, lượt 2 | phần lượt 1 chưa đọc (DECISIONS, hunk sổ, GO-NO-GO, SPEC, README, CHANGELOG) | Đủ 7 mục, 0 🔴, 0 🟠, 4 🟢. |
| Xác minh đối kháng | ba 🟠, reviewer khác người tìm, không nhận lý luận của người tìm | Cả ba tái hiện được. |

## 🟠 (đã tái hiện độc lập)

- **AUD-HAR-473.** `session-start.sh:41-50` không cắt dòng đầu của `loop status`. Dòng đầu ≥ 2 382 ký tự làm khối Autopilot vượt 2 400 và mất checkpoint. Đo với `xt.py` thật: `loop block --reason` 12 000 ký tự cho tổng 12 853 (> 10 000), mất `## Đang làm` lẫn checkpoint; 16 việc defer × 146 ký tự cho khối 2 624, mất checkpoint. Hook cũ luôn giữ khối 2 399. Hồi quy do #737; test hiện có không có ca dòng đầu dài.
- **AUD-DOC-325.** `LOOP-CTX-001` (`context-and-token-budget.md:68`) còn ghi "lần cắt 8 KB đầu tiên chưa có dấu". PROGRESS 11 920 B: hook cũ không dấu, hook mới có dấu.
- **AUD-DOC-326.** `WF-SDD-018` → Kiểm đòi `AGENTS.md` dự án nêu Plan Mode; #736 chuyển dòng đó sang `templates/CLAUDE.md`. Reviewer xác minh cho rằng 🟢 cũng có lý (SHOULD, ý vẫn đạt); giữ 🟠 theo tiêu chí "cách hiểu chặt hơn" (AGENTS §4).

## 🟢 mới

AUD-TEST-146, AUD-XFEAT-053, AUD-CODE-067, AUD-DOC-327/328/329, AUD-HAR-474. Chi tiết ở sổ.

## Không có lỗi

Luật bất biến AGENTS §3 không bị làm yếu; khối D-520/D-521 của `DECISIONS.md` giống hệt `3e0fff6d`; SPEC-factory-setup khớp 14 id; README "mọi workflow `ubuntu-latest`" đúng (25/25 dòng `runs-on`); `keep_mode` của `install.py` đúng (đột biến làm 2/6 test đỏ); không `eval`/nội suy shell mới, không bí mật; `changelog-check`, `validate`, `doctor --json` exit 0.

## Chưa biết

- Coverage dòng/nhánh và CI của dải: chưa chạy cục bộ (CI là cổng).
- Claude Code đếm giới hạn 10 000 theo đơn vị nào (AUD-HAR-474).
- Danh sách CodeQL ở `scripts/AGENTS.md` và URL ngoài: chưa xác minh từ nguồn sống.
- `progress-check` và `audit check --strict` cục bộ báo SHA chưa trên `origin/main` vì `origin/main` cục bộ cũ; với `XT_PROGRESS_BASE=ce08f914…` thì `audit check` exit 0.
- Guard chặn `git archive … | tar -x` vào scratch và `git update-ref`; các reviewer không đi đường khác (`LOOP-STOP-025`).

## Kế hoạch sửa

Một PR, tách commit: (1) test đỏ cho AUD-HAR-473 và AUD-TEST-146, rồi sửa hook (cắt dòng đầu ở n//2 kèm "…"); (2) AUD-DOC-325/326 kèm nâng `updated` và CHANGELOG; (3) các 🟢 rẻ (`updated`, newline cuối `AGENTS.md`, số PR ở sổ). PR cần review sạch trước merge; sau đó nâng SHA nhóm HAR/DOC/CODE/TEST.
