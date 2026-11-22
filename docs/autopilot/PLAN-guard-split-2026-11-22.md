# PLAN tách guard.py 2026-11-22 — lát đo trước, rồi hạ tầng nạp module

> Duyệt: D-540 (phiên chính tự duyệt) · Blueprint: BLUEPRINT.md · Căn cứ: [ADR-0090](../adr/0090-split-guard-and-xt-monoliths.md) (ranh giới), [ADR-0091](../adr/0091-progress-hook-cap-and-split-constraints.md) (bất biến nạp, "đo trước khi quyết tách") · Việc gốc: D-142

## Tóm tắt
- Mục tiêu: có số đo chi phí compile và quyết định của `.claude/hooks/guard.py` theo họ hàm (ADR-0091: lát đầu phải có số đo, đóng AUD-ARCH-007), rồi dựng hạ tầng nạp module anh em và tách cụm đầu tiên mà không đổi hành vi hàng rào.
- Dữ kiện đã đo ngày 2026-11-22 (CPython 3.15.0b4, container phiên, chưa phải máy chuẩn): `guard.py` 24 423 dòng, 1 379 538 B; hook `pre-bash-guard.sh` mất 0,51–0,59 s mỗi lệnh Bash, kể cả lệnh bị chặn (`git push --force`: 0,59 s). `AUD-PERF-013` từng đo 0,21–0,28 s ở 510 KB. Bộ nạp compile từ nguồn mỗi lần, không pyc (AUD-SEC-074).
- Hệ quả thiết kế: không có pyc nên tách module chỉ giảm chi phí mỗi lệnh khi module được nạp lười (chỉ lệnh nhắc `git`/`gh` mới nạp luật git/gh). Tách mà nạp hết thì tổng compile không đổi, lợi ích chỉ còn bảo trì (ADR-0090). Số đo ở lát 0 quyết cụm nào nạp lười.
- Ngoài phạm vi: tách `scripts/xt.py` (ADR-0090 mục 1, `perf trial` chạy một blob — ADR-0091); đổi hành vi bất kỳ luật nào của guard; thêm cache bytecode (bị loại ở AUD-SEC-074).
- Mỗi lát một PR; guard là hàng rào duy nhất nên mỗi PR đổi `guard.py` hoặc module guard cần review độc lập ở head (reviewer cao hơn người viết) và chỉ merge sau review sạch (bài học #738).
- Rủi ro đã biết: guard chặn script thông dịch tự do đọc/ghi `guard.py` (D-105); phân tích phải đi qua lệnh `xt.py` có test, không qua script ad-hoc.

## Ngân sách
- Số vòng: mặc định `--single-session` · Chi phí ngoài phiên: 0 · Timeout Gate: 1200 giây · Hạn: không (không có hạn thật; hạn xét lại hàng rào 2027-01-21 ở PROGRESS).

## Task
### Lát 0 — đo (không đổi hành vi, không đổi guard)
- [ ] `T-3984` Lệnh chỉ đọc `xt.py guard-profile` (hoặc module `scripts/xt_guard_profile.py`): đo thời gian compile `guard.py` và thời gian quyết định, lập họ hàm theo tiền tố (git, gh, xargs, sed, …) với số dòng, hằng dùng chung và cạnh gọi giữa họ; có test, mypy strict, chỉ stdlib — Gate: `python3 -m unittest tests.test_guard_profile`
- [ ] `T-3985` Chạy `guard-profile` ở repo khung, ghi `research/2026-11-22-guard-compile-cost.md` (số đo kèm ngày, máy, phiên bản Python; mỗi con số kèm lệnh) và đóng phần đo của AUD-ARCH-007 — Gate: `python3 scripts/xt.py validate` (sau: T-3984)
- [ ] `T-3986` Quyết định theo số đo: cụm tách đầu tiên và cụm nạp lười, ghi `loop decide` (D-NNN) và ADR mới về cách nạp module anh em (đổi cấu trúc cần ADR, AGENTS §7); đóng AUD-ARCH-010 (ràng buộc `perf trial` ghi cho kế hoạch tách) — Gate: `python3 scripts/xt.py validate` (sau: T-3985)
### Lát 1 — hạ tầng nạp và cụm đầu tiên (chi tiết task chốt sau T-3986)
- [ ] `T-3987` Bộ nạp: `py_run` (`.claude/hooks/_lib.sh`), `PY_LOADER` của guard và `xt_adapter.load_guard` nạp module anh em từ nguồn (compile mỗi lần, không pyc), một cách duy nhất; thiếu module sau cài dở thì guard lỗi nạp và Bash bị chặn (ADR-0054); test so ba bộ nạp giống nhau — Gate: `python3 -m unittest tests.test_hooks tests.test_codex_harness` (sau: T-3986)
- [ ] `T-3988` Tự bảo vệ: module guard mới nằm trong tập tệp hàng rào (guard chặn sửa/ghi qua Bash, `pre-edit-guard`, baseline `guard_fence_baseline.json`), `install.py` đồng bộ tệp companion dưới `.claude/hooks/`, `.coveragerc`/`typecheck` trong `xt.yaml` phủ module — Gate: `python3 -m unittest tests.test_install tests.test_guard_git_metadata` (sau: T-3987)
- [ ] `T-3989` Tách cụm đầu tiên (do T-3986 chọn) sang `guard_<cụm>.py`, `guard.py` vẫn là điểm nạp tương thích ngược; không đổi hành vi — Gate: `python3 scripts/xt.py autonomy-bench` (sau: T-3988)
- [ ] `T-3990` Parity: so quyết định thô base ↔ nhánh ở cả hai chính sách (mặc định và `XT_GUARD_POLICY=strict`) là tập cha không lọt; chạy `test_guard_fuzz`, `test_green_shell`, `test_green_gh`, `test_signoff2_scripts`, `test_audit_dot4_har` (tests/AGENTS.md) — Gate: `python3 -m unittest tests.test_guard_fuzz tests.test_green_shell tests.test_green_gh tests.test_signoff2_scripts tests.test_audit_dot4_har` (sau: T-3989)
