# PLAN — Nâng trần eval của X-Templates

Các tệp người dùng gửi chốt hợp đồng cấu trúc, danh tính và cách đánh giá bằng chứng. Khôi phục ba lát P0 từ `main` sau #913. Ghi kết quả model, pilot và host theo số đo có thật. Chạy đối chứng bằng fixture theo đúng hợp đồng, trên các runtime mà cổng repo hỗ trợ.

### Cổng eval P0

- [x] `T-5210` Bắt buộc tập danh tính testcase khớp khóa nghiệm thu và kiểm JUnit trên release (files: scripts/xt_acceptance.py, tests/test_acceptance_lock.py; topo: parallel) — Gate: `python3 -m unittest tests.test_acceptance_lock tests.test_reviewed_acceptance_scope`
- [x] `T-5211` Kiểm chính sách outcome từ trial đã ghi nhận (files: scripts/xt_checks/kind_design_outcome.py, tests/test_check_design_outcome.py; topo: parallel) — Gate: `python3 -m unittest tests.test_check_design_outcome`
- [x] `T-5212` Đối chiếu report eval với manifest, policy và bằng chứng (files: scripts/xt_checks/, tests/test_check_eval_report.py, tests/test_check_eval_evidence.py; topo: parallel) — Gate: `python3 -m unittest tests.test_check_eval_report tests.test_check_eval_evidence`
- [ ] `T-5213` Xác minh các lớp kiểm ở checkout, bản cài và gói; quyết định cắt 3.37.0 bằng cổng G7 (sau: T-5210, T-5211, T-5212; topo: review) — Gate: `scripts/dev-task.sh gate`
