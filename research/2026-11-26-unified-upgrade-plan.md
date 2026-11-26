---
title: Kế hoạch nâng cấp hợp nhất — tách xt.py/guard.py, review high/120, giao hàng theo bằng chứng (đề xuất)
kind: research
updated: 2026-11-26
---

# Kế hoạch nâng cấp hợp nhất (đề xuất, 2026-11-26)

> **Trạng thái: đề xuất, chưa phải PLAN.** Bản chuyển từ PDF "Kế hoạch nâng cấp hợp nhất" (40 trang, đối chiếu mã ở commit `02480424`). Chưa có task ID đăng ký, chưa sửa mã. Khi triển khai phải ánh xạ vào PLAN đang có (không lập kế hoạch cạnh tranh), giữ task đã xong, và ghi rõ ADR bị thay thế. **D-610** (hoãn nâng dự án đích) vẫn hiệu lực.
>
> Bản chuyển này gồm đủ 40 trang PDF (cô đọng; số đo giữ nguyên) và §11: kiểm chứng một bài đăng mạng xã hội về harness ba agent của Anthropic, đối chiếu với khung, kèm các bổ sung đưa vào G01–G12.

## 1. Ba quyết định chính
1. **Tách theo trách nhiệm và phụ thuộc.** Một chương trình thống nhất, chia module có hợp đồng rõ; kế thừa ADR-0090/0091/0093, registry, cơ chế quyết định; bảo toàn loader, CLI, bản cài, bộ kiểm.
2. **Reviewer effort tối đa `high`, `maxTurns` 120.** Cả `reviewer` và `reviewer-alt` khai `effort: high`, tuyệt đối không vượt `high`; `maxTurns` 80 → 120. Agent kết thúc sớm khi xong. Giới hạn vòng agent phân biệt với số lần review lại một PR.
3. **Đo và giao hàng theo bằng chứng.** Sửa lỗi đã tái hiện trước baseline; mỗi lát có parity và kiểm bản đã cài; giữ coverage dòng + nhánh 100 %, `mypy --strict`, C901 ≤ 10. Pilot bắt đầu từ một yêu cầu nghiệp vụ mới và một pack hiện có.

## 2. Hiện trạng đo (commit đối chiếu)
| Chỉ tiêu | `xt.py` | `guard.py` |
|---|---|---|
| Dòng vật lý / trần | 23.643 / 23.644 | 24.689 / 24.689 |
| Kích thước nguồn (byte) | 1.268.478 | 1.390.801 |
| Hàm cấp module | 1.300 | 1.421 |
| Coupling test cần rà | 407 dòng match patch / 55 file | 112 `patch.object` / 36 file |

Dòng vật lý tính bằng `len(read_bytes().splitlines())`, giống test ngân sách. Số patch là thống kê hỗ trợ rà soát, không phải lỗi đã chứng minh. Bộ kiểm chọn lọc đã chạy (CPython 3.13.5): 47 test của `test_docs_budget`, `test_python_floor`, `test_guard_profile`, `test_release_assets` đạt — không thay full CI, parity hay coverage của kiến trúc mới.

## 3. Lỗi đã tái hiện, cần xử lý trước khi tách sâu
| Phát hiện | Đưa vào |
|---|---|
| `executor-mech` chưa được CLI nhận (parser trả `SystemExit 2`; bảng vai chỉ có `executor`/`executor-deep`) | G01 |
| Lượt Gate đỏ bị bỏ chi phí (wrapper chỉ gọi `write_cost` khi rc = 0) | G02 (tiếp T-5010 sau T-5009) |
| Ghi file cài đặt có thể bị cụt (tiêm lỗi sau 4 byte làm mất nội dung cũ; hook rỗng bị phân loại kept-own) | G03 / C05 / C17 |
| Release gặp tag có sẵn thoát sớm (exit 0, `GITHUB_OUTPUT` rỗng, chưa kiểm trạng thái release) | G03 |
| Guard core mất ngữ cảnh khi lỗi (`RuntimeError` trong `_rule_decision` với payload merge: core allow/NONE; bash deny/UNPARSED) | Bugfix riêng trước baseline; chưa gán audit ID |

Phạm vi phát hiện Guard: payload `gh pr merge 17` chỉ vào bộ đánh giá trong bộ nhớ, không chạy lệnh merge. Chưa chứng minh trigger tự nhiên ở production; `xt_adapter.decide` có bước đổi tool về mode Bash. PR sửa lỗi phải làm rõ hành vi mong đợi (kèm ca tốt đối chứng và ngoại lệ từng mode) rồi mới chụp baseline cho parity. Thay đổi tăng bảo vệ pre-edit/loader cần quyết định policy riêng; PR move-only không tự đổi allow/ask/deny.

## 4. Chính sách reviewer: effort tối đa `high`
- Nguồn vai (`.claude/agents/reviewer*.md`) và `/review`: effort `high`, `maxTurns: 120`; bỏ chỉ dẫn "effort cao nhất" không giới hạn; reviewer vẫn chỉ đọc, context độc lập.
- Bản sinh theo host: sửa nguồn rồi sinh lại Codex và bản gương `.agents`; kiểm bản cài sạch và nâng cấp cùng nhận chính sách.
- Định tuyến/launch: kiểm effective effort (session, frontmatter, invocation, biến môi trường) trước launch; chặn nếu không áp được trần theo vai. XHIGH/MAX không được thành yêu cầu thực thi, kể cả qua override. Trần không áp cho tác giả/executor/researcher/phiên chính.
- Hiện trạng cần sửa: `reviewer-alt` khai `effort: max` (và bản Codex `model_reasoning_effort = max`); `reviewer` chưa khai effort; `/review`, mô tả agent và ADR-0098 còn dựa vào giả định "reviewer MAX cao hơn người viết cùng bậc". ADR kế tiếp chỉ thay phần lựa chọn effort và định tuyến; giữ lịch sử ADR-0098. Review MAX hợp lệ theo revision cũ vẫn lưu đúng lịch sử, không cho phép lượt mới dùng MAX.

Định tuyến khi trần là `high` (HIGH là trần effort, không chứng nhận reviewer mạnh hơn):
| Tác giả / reviewer | Quyết định |
|---|---|
| Cùng họ model/tier (tier-only): MEDIUM / HIGH | Hợp lệ về effort; còn kiểm phạm vi, độc lập, bằng chứng |
| Cùng họ: HIGH / HIGH hoặc XHIGH / HIGH | Không đủ điều kiện năng lực cao hơn; không ghi clean; không tự nâng reviewer |
| Tác giả bậc thấp / reviewer bậc cao, HIGH | Có thể hợp lệ nếu bậc reviewer nằm trong phạm vi cho phép |
| Khác nhà cung cấp, reviewer ≤ HIGH | Đường độc lập theo chính sách hiện hành; không diễn giải thành ưu thế năng lực |
| Không có reviewer hợp lệ | INCONCLUSIVE hoặc thiếu reviewer; defer phần cần review, làm tiếp việc độc lập |

Mỗi lượt review ghi repo, head, phạm vi diff, tác giả, reviewer, effort requested/effective, revision chính sách và nguồn setting (mặc định/host/override); không rõ → `unknown`. Kiểm cặp hợp lệ trước khi giao review. Ma trận nghiệm thu: tên model và đường tier-only; default giải quyết tường minh; override XHIGH/MAX bị từ chối trước launch; HIGH/HIGH và HIGH/XHIGH bị từ chối clean; không route nào ghi INCONCLUSIVE được; event noncompliant không mở gate sạch. Đo chất lượng sau thay đổi bằng cùng bộ diff có lỗi gieo + đối chứng (lỗi bỏ sót, chặn oan, thời gian, chi phí, chuyển tuyến); chưa có số thì chưa kết luận tiết kiệm hay chất lượng tương đương.

### 4.1 `maxTurns` 80 → 120: giữ từng loại ngân sách riêng
`maxTurns: 120` là trần lượt agent trong **một lần chạy**, không phải 120 lần review mỗi PR; agent được kết thúc sớm khi xong phạm vi.
| Giới hạn | Thay đổi |
|---|---|
| `maxTurns` hai reviewer | 80 → 120; kiểm giá trị nguồn, cấu hình hiệu lực, hành vi dừng của host |
| `REVIEW_ROUNDS = 1` | Giữ; `review_window`, luồng debt/rethink không đổi |
| `max_rethink` mặc định 1 | Độc lập với lượt agent; không tăng, không bỏ trần |
| Poll, timeout, retry, song song | Không lấy 120 làm số poll/retry/reviewer đồng thời |

Nguồn chung chưa bảo đảm các host giống nhau: `agent_toml` hiện chỉ đưa name, description, effort hợp lệ và thân hướng dẫn sang Codex (thêm model khi bật), **không map `maxTurns`**. Test frontmatter chứa `maxTurns: 120` chỉ chứng minh đọc được nguồn. Xác minh schema từng host trước khi map; không tự thêm khoá TOML chưa xác nhận; chưa có trần tương đương thì báo khoảng trống trong bằng chứng cài. Hết lượt → kết quả có thể chưa đủ; ghi định danh lần chạy, head, phần đã rà/chưa rà, dấu tiếp tục; chưa đủ bằng chứng → INCONCLUSIVE. Nghiệm thu: assertion hai vai `maxTurns = 120`, `effort = high`; giữ trần `executor-mech` riêng; kiểm dừng sớm và biên 119/120/121, hết lượt có partial, resume.

## 4A. Tách lõi an toàn (trang 8–16 của PDF)

**Kiến trúc đích: modular monolith.** XT là CLI điều phối, Guard là lớp đánh giá/bảo vệ; tách miền trong cùng bundle để đổi từng lát và quay lại được. Chưa có bằng chứng cần microservice, plugin tải động, ngôn ngữ policy mới hay vector DB. Bốn khối trách nhiệm: XT entrypoint/đăng ký command → miền XT (loop, PR, doctor, scan, release) → hợp đồng và dữ kiện (kiểu, policy, state, evidence) ↔ ports/adapter (Git, file, clock, process, events) ← miền Guard (Edit, MCP, commit, Bash/SCC) ← Guard đầu vào theo mode (loader nguồn tin cậy). Đây là quan hệ trách nhiệm đích, không phải sơ đồ import đã có. Sáu lớp logic của bản gốc (dữ kiện → năng lực → quyết định → thực thi → kiểm chứng → phát hành/phản hồi) là trách nhiệm, không phải sáu service; module `xt_decision`/`xt_design`/`xt_agent_roles`/`xt_evidence`/`xt_metrics` chỉ tạo khi có lát dùng thật. **Chống chia file hình thức:** không chuyển nguyên khối sang `legacy_core.py`, `guard_core.py`, `common.py`.

**Tách `xt.py` (kế thừa ADR-0090; `build_parser` 641 dòng):**
| Lát ứng viên | Số đo tĩnh và hướng |
|---|---|
| Shard/weights | 7 hàm, 121 dòng, 3 tham chiếu ngoài → `xt_shard` |
| Chọn test | 21 hàm, 241 dòng, 1 phụ thuộc ngoài; giữ fallback chạy toàn suite |
| CSS contrast | 24 hàm, 269 dòng, không gọi ra ngoài cụm; giữ CLI |
| Doctor | tách checker runtime/cấu hình/bản cài/tổng hợp từng lát |
| Loop và PR | PLAN, state, evidence, ledger, runner; PR: dữ liệu, quyết định merge, review ledger, handlers |
| Release/compose | đưa vào module có sẵn; giữ contract phát hành, carry-forward |

Giữ Core(Protocol) làm cầu; bắt đầu từ cụm thấp coupling; `LOOP_HANDLERS` tĩnh đã có, chưa cần plugin discovery; parser register theo miền ở giai đoạn sau, giữ `main(argv)`. Autonomy benchmark và perf trial là miền riêng (blob XT theo ADR-0091). Một chủ sở hữu tích hợp `xt.py`; entrypoint < 150 dòng là đích dài hạn.

**Hợp đồng lõi khi di chuyển:** state/quyền sở hữu (lock, revision/CAS, atomic write, một nơi chuyển trạng thái) · PLAN/evidence (dependency, Gate, task, head, digest liên kết đúng) · ledger/attempt (schema, chống đếm trùng; G02 thêm attempt identity, nối T-5010) · CLI/caller (flags, defaults, JSON, mã thoát, stdout/stderr, import). Patch phải chuyển tới **nơi lookup thật** (407 dòng patch XT/55 file): re-export giữ tên import nhưng thân hàm đã chuyển đọc globals ở module mới → test xanh giả. `SCRIPT_DIR`, cache, dispatch dict, `PR_READ_HOST` ContextVar, `sys.path`, `sys.modules` cần chủ sở hữu. PR extraction không trộn sửa hành vi; characterization test ghi hành vi hiện có nhưng không coi lỗi cũ là đặc tả.

**Tách Guard theo bao đóng phụ thuộc** (Decision, CodedReason, `reason_code`, `policy_action`, `apply_policy`, POLICY đã có; chuyển luật sang YAML chưa đáng chi phí kiểm lại shell parser). Đo tại `02480424`:
| Hạt giống | Định nghĩa | Span dòng |
|---|---|---|
| `edit_decision` | 61 | 629 |
| `mcp_decision` | 34 | 330 |
| `commit_msg_problem` | 5 | 45 |
| `decide` + `apply_policy` | 6 | 58 |
| Nhóm git/gh/push | 534 | 6.061 |
| `bash_decision` | 1.402 | 15.714 |

Các cụm chồng lấn, không cộng thành số dòng xoá được. Công cụ repo cho nhóm từ xa 498 định nghĩa (thấp hơn 36 do chưa lần qua bảng như `GIT_RULES`, `FILE_WRITERS`); 13 nhóm phụ thuộc vòng, lớn nhất 21 định nghĩa quanh `bash_decision` và vòng scan — giữ cụm này trong lượt đầu. Lát ưu tiên: shared helpers + Edit/Write (bao đóng nhỏ; helper dùng chung với Bash một nơi định nghĩa; giữ identity class và ContextVar mỗi bundle), rồi MCP, commit-msg, cuối cùng Bash. T-3995 xong; T-3996, T-3987…3990 tiếp tục. C14 cần ADR bổ sung sửa ADR-0090 §2, ADR-0093 §1-2 và D-542. Mức 376 → 54 ms của C14 là nguyên mẫu lịch sử, chưa benchmark lại.

**Nạp Guard và bảo vệ gói cài.** Companion đọc từ source bytes, tên trong allowlist cố định, đường dẫn tính từ bundle đã chọn; không dò plugin qua cwd/PYTHONPATH; mỗi instance một namespace riêng. Kiểm năm tuyến (`_lib.sh::py_run`, `PY_LOADER`, `xt_adapter.load_guard`, `xt._load_guard`, `BenchEnv.module`) với thiếu file, lỗi cú pháp, nạp dở, pyc đặt sẵn, hai phiên bản cùng tiến trình. Ma trận lỗi hiện hữu:
| Tình huống | Hành vi hiện tại |
|---|---|
| Bash lỗi runtime thường | Fallback rỗng: fail-open (ADR-0002) |
| Bash lỗi runtime khi kiểm merge/gh api | UNPARSED: mặc định deny; strict giữ ask |
| Pre-bash không nạp được Guard | Mặc định deny; strict ask; có ngoại lệ xem/khôi phục |
| Pre-edit không nạp được Guard | Shell thoát 0: fail-open |
| Adapter nạp Guard ném lỗi | Trả BROKEN_GUARD theo giao thức host |

Đổi pre-edit sang chặn khi hỏng là **đề xuất tăng bảo vệ**, cần quyết định và đường khôi phục riêng. Theo CPython: `-B` tắt ghi pyc, `-I` không loại toàn bộ site-packages, `-S` tắt site; hoàn tất AUD-HAR-572/573 bằng chính sách nạp thống nhất, kiểm `-I -S -B` trên runtime hỗ trợ và bộ đo coverage. Companion là một phần hàng rào: manifest khai dependency và phiên bản; doctor phát hiện thiếu/rỗng/cụt/trộn phiên bản.

**Chứng minh tương thích:** so raw decision và kết quả sau policy ở cả mặc định lẫn strict trên bốn nhóm — quyết định (decision, reason, code, confidence, missing, thứ tự ưu tiên), cổng thực thi (`commit`, `no_verify`, `push_no_verify`, `commit_dir`, `commit_alone`), giao thức (thứ tự NUL, JSON, exit code, stdout/stderr), tác động (IO, log, số sự kiện, hành động chỉ một lần). Corpus Guard 4.106 ca là nền so hai phiên bản, không phải bằng chứng phủ mọi hành vi; giữ `autonomy-bench`, `guard_fuzz`, `green_shell`, `green_gh`, `signoff2_scripts`, `audit_dot4_har`. Shadow dùng snapshot filesystem/Git/cấu hình, namespace/cache/ContextVar tách, recorder/replayer IO; không chạy lại action. Rà 112 `patch.object(guard, …)`/36 file; kiểm reset ContextVar trong `finally`. Không hạ coverage về 90 % để dễ tách.

**Hiệu năng gắn đường chạy.** Đo compile nguồn (CPython 3.13.5, Linux x86_64): XT trung vị 358,79 ms (334,11–450,79), Guard 259,00 ms (236,35–282,53) — không gồm khởi động process, đọc file, Git hay quyết định policy; không suy ra p95 hook. Bộ benchmark trước mỗi lát: CLI phổ biến (help, validate, doctor, test-select, loop/pr đọc; cold/warm) · Guard theo mode (Bash đơn/đệ quy, merge/API, Edit/Write, MCP, commit-msg) · tích hợp đã cài (checkout, `.xtemplates`, artifact; số module/byte nạp) · CI và agent (critical path, runner-minutes, time-to-green, token mọi attempt). p50/p95 đủ mẫu, so A/B xen kẽ cùng fixture; ngưỡng regression khoá sau baseline.

**Bản cài và phục hồi là một phần lát tách.** `registered_hooks()` suy companion từ settings và chuỗi shell, không tự tìm mọi dependency Python mới; mỗi lát cập nhật manifest, hash, version, typecheck, coverage, test-select. Ca bắt buộc: checkout/`.xtemplates` (fresh install, upgrade, downgrade, CWD khác, path có dấu/khoảng trắng, thiếu module) · artifact `.pyz`/tarball (chạy entry point thật, không dựa `sys.path` checkout) · perf trial một blob · tệp người dùng đã sửa (owned/customized/deleted, `.xtemplates-new`) · gián đoạn/cạnh tranh (mid-write, thiếu companion, mixed version, hai tiến trình). C05: file tạm cùng filesystem, đủ nội dung và quyền rồi `os.replace`; fsync chỉ khi cần bảo đảm qua mất điện; replace không phải giao dịch cả bundle. Nghiên cứu trước ghi 15/15 gián đoạn hội tụ khi chạy lại nhưng còn ca ghi cụt → atomic từng file + kiểm toàn vẹn + repair; không dựng transaction framework khi chưa có bằng chứng.

**Giảm ngữ cảnh đi cùng độ mới.** Module map và symbol index từ AST (gắn SHA, owner, entry point, callers, tests); BLUEPRINT/SPEC projection phát hiện drift theo dependency; gói giao việc (mục tiêu, constraint, file owner, base/head, decision revision, ca nghiệm thu, unknown); handoff sau compaction (việc xong, diff dở, test đã/chưa chạy, lỗi mở, việc kế, link log); đầu ra lỗi ≤ 8.000 ký tự + full log (C02). C04 cửa sổ 400K là thí nghiệm theo host/model. Nghiệm thu: cùng task/head/fixture, context giảm mà tỷ lệ hoàn thành không giảm, không tăng lượt sửa.

## 4B. Sản phẩm, agent và giao hàng (trang 17–26 của PDF)

**Bối cảnh trước giải pháp.** Mỗi fact có ID, giá trị, phạm vi, nguồn, thời điểm, trạng thái `confirmed`/`observed`/`assumed`/`unknown`; mâu thuẫn lưu thành conflict có tham chiếu. Sáu trục: software profile · kiến trúc và dữ liệu · pack triển khai · design profile · vai agent và model · chính sách thực thi. Sản phẩm đang chạy ưu tiên tận dụng stack/design system; không suy "có AI" thành agentic-system hay "có màn hình điện thoại" thành mobile-app. Chỉ hỏi người khi đáp án đổi lựa chọn đáng kể hoặc dữ kiện chỉ chủ sản phẩm có.

**Chọn phương án có đủ bằng chứng.** Mỗi candidate một hàng cho từng hard constraint: pass/fail/unknown + nguồn + bằng chứng đúng phiên bản; điểm thẩm mỹ/tốc độ/chi phí không bù được vi phạm bắt buộc. Trạng thái: `needs_resolution` · `needs_evidence` · `no_fit` · `selected_provisional` · `validated_for_scope` · `superseded`. Lỗi đọc registry hay danh mục chưa phủ không được gọi là `no_fit`. Đề xuất kiểm độ nhạy trọng số và lưu điều kiện xét lại (phản chứng).

**Bảy hợp đồng dữ liệu logic** (đề xuất, chưa phải bảy file): CONTEXT · PRODUCT-SPEC · CAPABILITY-REGISTRY · DECISION · DECISION.lock · VALIDATION · RUN-EVENTS. JSON Schema kiểm cấu trúc; validator ngữ nghĩa kiểm tham chiếu chéo; giữ DESIGN-EVIDENCE schema 1; VALIDATION nối quyết định với build. Digest trên biểu diễn chuẩn hoá; đổi nghiệp vụ/quyền/candidate làm mất hiệu lực đúng phần phụ thuộc. Schema và policy cho hook đóng gói cùng phiên bản, không tải từ mạng.

**UI/UX theo tác vụ.** Design profile sáu trục (họ trải nghiệm, kiến trúc thông tin, kiểu tương tác, mật độ, ngôn ngữ hình ảnh, chuyển động). Sáu họ trải nghiệm (danh mục để thử, không phải pack có sẵn): vận hành nghiệp vụ · hiện trường · khám phá dữ liệu · nội dung/chuyển đổi · mua hàng/giao dịch · workspace có agent. Quyết định lớn dựng 2–3 phương án trên cùng tác vụ và dữ liệu; review trên UI render với tên dài, số tiền, chữ có dấu, dữ liệu thật. UI sinh động chỉ dựng từ catalog component và action contract đã kiểm.

**Kiểm UI, a11y và outcome** — năm lớp kết luận khác nhau: hồ sơ · candidate · kỹ thuật UI · thử tác vụ · theo dõi tại đích. WCAG 2.2 AA là mục tiêu cho web pilot: reflow 320 CSS px, phóng chữ 200 %, focus không bị che, kéo có cách thay thế, target 24×24 CSS px tối thiểu có ngoại lệ (44×44 không phải yêu cầu AA). DTCG 2025.10 là định dạng của Community Group, không phải W3C Recommendation. Catalog component cần trạng thái empty, loading, lỗi, mất quyền, thành công, gián đoạn, tiếp tục; tôn trọng giảm chuyển động. Web Vitals tham chiếu LCP ≤ 2,5 s, INP ≤ 200 ms, CLS ≤ 0,1 tại p75; báo lab và field riêng; thiếu dữ liệu → `not_measured`. Mọi báo cáo dùng `pass`/`fail`/`not_tested`/`not_applicable` có lý do.

**Điều phối agent.** Registry vai nối tên agent, loại việc, năng lực, quyền, CLI và dữ liệu thực thi; vai công bố phải chạy được qua CLI thực. Sáu trách nhiệm logic (điều phối · phân tích/thiết kế · tác giả nghiệm thu · thực thi · review/kiểm chứng · giao hàng/vận hành) có thể cùng một agent đảm nhiệm, nhưng nghiệm thu và review giữ độc lập. `executor-mech` đỏ một lần phải chuyển cấp đúng quy định. **Bộ đánh giá agent thật:** 24–36 tình huống đã review có đáp án, một phần holdout không dùng để chỉnh prompt (brief mơ hồ, dữ kiện tra được trong repo, pack không hỗ trợ, nguồn mâu thuẫn, SPEC đổi giữa chừng, compaction, nối phiên, hành động vượt quyền); chạy lặp, báo thành công trên tổng trials; phân biệt "ít nhất một lần" với "nhất quán"; code grader cho điều kiện tất định, model grader cho phần mở cần hiệu chuẩn với người.

**Nghiệm thu độc lập và ca sai critical.** Giữ tác giả nghiệm thu độc lập, khoá digest, đỏ trước code ứng viên. Mỗi quy tắc critical nối nguồn yêu cầu → SPEC → test hành vi → ca sai cố ý đã review → kết quả trên artifact; quyền, tenant, gửi lại an toàn, đồng thời, biên thời gian, tiền kiểm khi liên quan. Bộ thử phải bắt toàn bộ tập sai critical đã chốt — không bảo đảm phát hiện mọi lỗi.

**Sổ sự kiện và chi phí.** Producer: requirement, task_green, pr, review, merged, artefact, deployed, incident, cost; gắn ID lát/run/attempt/event. Lần thành công, thất bại, huỷ, review bị bác, retry đều ghi khi có usage; thiếu usage giữ `unknown`, không thành 0. Chỉ số: hoàn thành đúng tác vụ · lead time (tách làm và chờ) · chi phí hoàn thành · sửa lại và lỗi lọt · chất lượng lựa chọn · phục hồi. Ingestion idempotent. OpenTelemetry GenAI conventions còn Development → ghim phiên bản; không capture prompt/output mặc định; ledger cost cần đường ghi đầy đủ riêng vì sampling bỏ dữ liệu.

**Cài đặt và phát hành chịu gián đoạn.** Release có trạng thái rõ (tag đã tạo, asset đã tải và xác minh, đã công bố); chạy lại gặp tag có sẵn phải đối chiếu commit và trạng thái. Chuỗi bằng chứng: source → build (receipt) → release (digest khớp asset; thiếu asset = incomplete) → cài đặt (manifest module, hash, quyền) → phục vụ (receipt tại đích) → chạy lại (tiếp tục đúng bytes hoặc lỗi rõ). Quan sát 26/11: `v3.36.0` có `immutable=false`. Registry đích cần source SHA, phiên bản, pack, môi trường, release, thời điểm, trạng thái `current`/`deferred`/`unknown`/`unsupported`.

**Pilot trọn vòng.** Một yêu cầu nghiệp vụ mới trên Hotel Manager (luồng lọc tầng chỉ là đối chứng): brief, baseline, context, lựa chọn, suite độc lập, triển khai, thử UI, phản hồi, release, kiểm tại đích, theo dõi; không dựng trial người dùng hay receipt production giả; người thử dùng mã ẩn danh. Mức bộ chọn mới: shadow → tự chọn hẹp → canary → mở rộng; không giảm tự hành L3 đang được phép. Diễn tập phục hồi A→B gồm dữ liệu phát sinh khi B chạy; chốt RPO/RTO theo sản phẩm; rollback code không tự phục hồi dữ liệu.

## 5. Backlog hợp nhất G01–G12
| Gói | Đầu ra | Điều kiện nghiệm thu chính |
|---|---|---|
| G01 Điều phối agent | Registry vai thống nhất, `executor-mech` qua CLI + escalation, reviewer high/120, mapping host/route | Parser/dispatch đúng; override/env/fallback không vượt high; host chưa áp được trần → pending/unsupported; hết lượt mà chưa đủ bằng chứng không khai sạch |
| G02 Sự kiện và chi phí | 9 loại sự kiện, attempt ID, cost lượt đỏ, coverage nguồn, export xuyên phiên/worktree | Tiếp T-5009/5010/5011; chống trùng; thiếu nguồn giữ null + lý do |
| G03 Cài và phát hành | Atomic write, doctor hook rỗng, bundle integrity, release retry theo identity, bằng chứng admin tách riêng | Fault cases cài/upgrade phục hồi; tag có sẵn không giả success; T-5020 chỉ xong khi diễn tập thật trong quyền đã giao |
| G04 Pilot và baseline | Một feature nghiệp vụ mới, một sản phẩm/pack hiện có; baseline riêng | Yêu cầu có nguồn; constraints, tiêu chí, phạm vi khoá trước code |
| G05 Quyết định | Context/constraint snapshot, schema, decision/lock, invalidation | Candidate thiếu bằng chứng không bị chọn; đổi input → stale đúng dependency |
| G06 Registry tối thiểu | Tổ hợp pack/host/profile/data đã kiểm phục vụ pilot | Mỗi tuyên bố supported có bằng chứng đúng tổ hợp/version; không tải plugin động từ tên trong cấu hình |
| G07 Thiết kế trải nghiệm | Profile theo tác vụ/vai trò, token ngữ nghĩa, prototype dữ liệu thật, DESIGN-EVIDENCE schema 1 | Phép đo trình duyệt đúng build; T-5012/5013 mở khi đủ bằng chứng |
| G08 Nghiệm thu độc lập | Suite từ SPEC công khai, manifest requirement, ca sai critical | Bắt toàn bộ tập sai đã khoá; ca đúng không bị chặn oan; không sửa tiêu chí để hợp kết quả |
| G09 Tích hợp tại nơi dùng | Factory/compose/stage nối contract; artifact/bản cài sạch | Không dựa source checkout; Python floor, loader matrix đạt; packaging/monkeypatch không làm test xanh giả |
| G10 Agent eval và pilot | Bộ 24–36 tình huống khởi đầu, holdout, trials lặp | Agent/model/tool thật, production receipts thật; thiếu quyền/trial/recovery vẫn pending |
| G11 Mở rộng | Canary theo digest/receipt, registry năng lực | D-610 còn hiệu lực thì chưa nâng repo đích; T-5038 đã bỏ, không đưa lại |
| G12 Lõi và ngữ cảnh | Inventory, compatibility, XT/Guard extraction, bundle, context freshness, retire (G12.0–G12.7) | Mỗi lát hạ cap và giảm coupling có số đo; giữ 100 % line+branch, mypy strict, C901 ≤ 10, Guard source-only |

Thứ tự ưu tiên: sửa tính đúng và khoảng trống cấu hình của G01–G03; G04–G06 triển khai phần contract song song khi owner không trùng. Giữ việc đã có nhà: T-5010 chứa lỗi cost lượt đỏ; T-5016 đã đặt cap dòng — không mở task trùng. Phát hiện Guard core chỉ cấp ID khi đăng ký vào audit thật.

Điểm nối: G07 có thể dựng prototype song song G08 sau khi yêu cầu và hợp đồng công khai ổn định; code nghiệp vụ chỉ triển khai sau khi suite độc lập đã được review và khoá. G12 không là lý do trì hoãn pilot.

### G12 — các lát lõi
- **G12.0 Inventory/baseline:** danh sách symbol, imports, tham chiếu qua hàm, bảng callable/constants/type alias; SCC và caller ngoài cụm; ghi riêng dynamic import, exec, monkeypatch, callback; chốt SHA, công cụ đếm và workload đo.
- **G12.1 Tương thích:** khoá command args/help/exit/stdout/stderr, hook fields/NUL order, schema, import surface; phân biệt API công khai với private helper bị test patch. Quyết định L05 về XT/blob/bytecode + ADR bổ sung cho C14.
- **G12.2 Leaf và port I/O:** cụm nhỏ, ít cạnh ngoài; giữ Core(Protocol) chuyển tiếp rồi thu hẹp; port clock/Git/files/process/events có ngữ nghĩa lỗi, timeout, quyền.
- **G12.3 Miền XT:** tách C15, doctor, state/lock, PLAN/dependency, evidence, ledger/cost, runner, GitHub adapter, quyết định thuần, sổ review, command; parser/register CLI đi sau; facade cũ vẫn hoạt động.
- **G12.4 Guard:** sửa riêng lỗi fallback core; Decision/CodedReason nhỏ; eager-load đủ closure; MCP/commit-msg tiếp theo; vòng scan Bash giữ cùng cụm rồi mới tách theo SCC.
- **G12.5 Loader và ma trận bản cài:** `_lib.sh::py_run`, `guard.PY_LOADER`, `xt_adapter.load_guard`, `xt._load_guard`, `BenchEnv.module`; allowlist cố định, source-only; kiểm thiếu module, pyc giả, hai bản chung process, CWD khác.
- **G12.6 Context đúng miền/revision:** module map, lấy thông tin theo ID và dependency; handoff chứa công việc, constraint, version, phần chưa kiểm; đo token và tỷ lệ hoàn thành trên cùng task.
- **G12.7 Thu hồi đường cũ:** chỉ bỏ shim/stub `merge-gate.yml` khi consumer, bản cài, công cụ đo đã chuyển; hạ ngân sách dòng/byte sau extraction; kiểm SCC, fan-in/out.

Bằng chứng đóng mỗi lát: manifest chuyển symbol; delta trước/sau (LOC/byte, coupling, module nạp, test + benchmark cùng fixture); khả năng đảo (commit độc lập, artifact trước khôi phục được, không lẫn delta policy không tương thích). Mục tiêu facade < 100–150 dòng là đích dài hạn, không phải điều kiện đóng.

Không nhập nhầm chính sách lỗi: pre-edit hiện có đường load lỗi cho qua; Bash thường và merge/API khác nhau — sửa hành vi đó phải là thay đổi policy có nghiệm thu riêng.

## 6. Thứ tự triển khai và Cửa A–E
| Đợt | Đi trước | Song song được |
|---|---|---|
| 0 Tính đúng và cấu hình | G01 high/120, mech; G02 cost; bugfix core; baseline và atomic file | G04 brief/baseline; G05 contract; inventory, fixtures |
| 1 Lát module đầu | G12.1/2, L05; C14 bổ sung ADR; loader/protection/install cùng lát | XT và Guard ở path owner riêng; registry, UX prototype, suite độc lập |
| 2 Tích hợp pilot | G09 từ bản cài; G05–G08 nhất quán; ledger và bằng chứng release | Agent eval, test UI, recovery trên môi trường được phép |
| 3 Outcome và mở rộng | G10 đủ dữ liệu thật; sau đó G11 theo D-610 | G12 tiếp tục ratchet/context/retire; không trì hoãn pilot vì archive |

Dependency kỹ thuật: L01 → L02; L04 → C03; L05 → C15/C22; C04 đo đạt → C20. C14 cần ADR, closure, loader, fence; C15 giải phóng capacity cho C16/C17. C08 cùng L01 đo lại trước xét C21. Mọi module đưa vào artifact đi qua G03 fault cases và G09 installed-copy.

| Cửa | Điều kiện đóng |
|---|---|
| A Máy thực thi và đo | G01–G03 đạt phần máy làm được; giới hạn live/admin ghi đúng, không giả đã hoàn tất |
| B Quyết định có căn cứ | G04–G08 nhất quán; thiếu/mâu thuẫn không bị ép chọn; acceptance đã khoá |
| C Tích hợp | G09 đạt ở bản cài/artifact; checkout xanh chưa đủ |
| D Pilot đầy đủ | G10 đạt toàn scope đăng ký: task người dùng, bản tại đích, diễn tập phục hồi |
| E Mở rộng | G11 canary đúng host đã hỗ trợ và quyền hiện hành; host mới cần chứng nhận riêng |

Đợt bắt đầu có thể giao ngay: PR cấu hình review + route/host contract; PR lỗi core; PR cost đã có task; PR atomic write/doctor; chia quyền sở hữu file rõ (nhiều việc cùng chạm XT/install); sửa quyết định và test trước khi tách sâu, rồi lấy một lát ít coupling để đo chi phí migration thực.

## 7. Đo hiệu quả và rủi ro
Trục đo: tính đúng (parity corpus khoá, bugfix có delta riêng) · cấu trúc (cap XT/Guard giảm từng lát, không thêm chu kỳ import) · chất lượng mã (giữ Gate hiện có) · review (hai role high tối đa + 120 lượt; partial/hết lượt khi thiếu bằng chứng ≠ APPROVE) · hiệu năng (p50/p95 cold/warm theo mode và bản cài; budget khoá trước PR) · CI/phát triển (critical path, time-to-green, runner-minutes) · chi phí agent (cost mọi attempt, token/thời gian trên một thay đổi được nghiệm thu) · outcome sản phẩm (hoàn thành tác vụ, thời gian, lỗi, trợ giúp, accessibility, field performance).

Rủi ro chính và biện pháp: chặn oan (parity gồm cả ca cho phép) · test xanh giả (kiểm nơi lookup của mock) · mixed bundle (manifest/integrity + fault tests) · chi phí điều phối (chỉ song song khi task có owner độc lập, so tổng token/thời gian) · thiếu bằng chứng (để unknown/pending) · rò ngữ cảnh (log tối thiểu, gắn revision) · policy tự biến đổi (lịch sử chỉ đề nghị sửa có version/review) · nợ kiến trúc chuyển chỗ (đo tổng coupling) · `maxTurns` tăng (không tự bảo đảm chất lượng; đo mọi attempt, dừng sớm khi xong). Để sau: dynamic plugin, microservice, DSL luật, vector DB, học xếp hạng tự động, installer journal — chỉ mở lại khi có nhu cầu đo được.

## 8. Ánh xạ 31 lát nghiên cứu hiện có
Dấu task trong PLAN là nguồn trạng thái; số đo trong nghiên cứu [framework-optimization](2026-11-26-framework-optimization.md) là dữ liệu lịch sử/nguyên mẫu, đo lại ở HEAD trước khi áp dụng.
| Lát | Gói | Ghi chú |
|---|---|---|
| L00 / T-5032 | G04, G12.0 | giữ 10 hướng; bổ sung mốc SHA, loại bằng chứng, phép tái hiện |
| L01 / T-5033 | G12, G02 | phân hoạch fuzz; giữ coverage và tên consumer cần |
| L02 | G12 | trọng số/tripwire sau L01; đo job chậm nhất, headroom thật |
| L03 / T-5034 | G09, G12 | ánh xạ verify-render; fallback bảo thủ |
| L04 / T-5035 | G01, G03 | kiểu settings đã biết; mở rộng kiểm high/maxTurns theo schema và host |
| L05 | G12.1/3 | ADR XT split/bytecode; perf trial một blob; Guard source-only |
| L06 / T-5036 | G11 | X-Scanner giữ ngoại lệ đến 21/01/2027; X-Agents rời registry theo D-610 |
| C01 / T-5037 | G12, G04 | check-links đúng worktree; fixture tự dựng |
| C02 | G02, G12.6 | excerpt lỗi ≤ 8.000 ký tự + pointer full log |
| C03 | G01, G03 | `PreSkillShellCommand`/depth theo host đã hỗ trợ; phụ thuộc L04 |
| C04 | G01/2, G12.6 | 400K là trial; kiểm effective config và chất lượng trước C20 |
| C05 | G03 | atomic write bảy điểm và hook rỗng; fault suite |
| C06 | G03, G08 | tag glob: đối chiếu trạng thái HEAD trước; nếu còn khoảng trống, oracle trước code. **Không mở lại mù**: một số phát hiện tag/glob đã có cập nhật sau đó (AUD-HAR-541/542) |
| C07 | G05, G12.6 | compose BLUEPRINT, kiểm 17 MUST; freshness theo dependency |
| C08 | G02, G12 | bỏ bước test-main dư trên push; required checks và nhánh PR vẫn đúng |
| C09 | G12 | prefilter PostToolFailure; đo hit rate, overhead |
| C10 | G12.3 | doctor tránh compile/lặp harness check |
| C11 | G01, G02 | handoff/log và lệnh chờ |
| C12 | G01, G08 | review bản sửa ở head theo scope; effort high/maxTurns 120 là cấu hình agent riêng |
| C13 | G12.6 | blueprint-status và truy xuất bằng ID |
| C14 | G12.1/4/5 | Edit closure + ADR sửa thứ tự + loader/fence/install/parity trong một lát đủ dùng |
| C15 | G12.3/5 | scan sang `xt_scan.py` theo L05; giữ blob trial hoặc nâng hợp đồng trước; hạ cap |
| C16 | G09, G12 | test-select/weights theo mapping mới |
| C17 | G03, G12 | doctor phát hiện hook rỗng; context bytes tính tệp tracked |
| C18 | G03, G09 | installer bảo toàn ý định xóa owned file; test upgrade/customized/conflict |
| C19 | G03, G11 | upgrade bot giữ merge thủ công; chưa chạy nâng đích dưới D-610 |
| C20 | G09, G11 | settings merge chỉ sau C04 có bằng chứng; không áp 400K cho mọi host/model |
| C21 | G12 | hợp CI test-main vào compat chỉ khi đo sau L01/C08 còn lợi |
| C22 | G12 | bytecode test/XT theo L05; không đổi trust policy Guard theo suy diễn |
| C23 | G12.6/7 | archive audit/PLAN đã đóng; giữ ID, link, truy vết quyết định |
| C24 | G12.7 | bỏ stub merge-gate sau khi hết consumer và thời gian chuyển |

T-5038 (canary X-Company) đã bỏ theo D-610; phương án nâng đích giữ làm tài liệu cho đợt sau. T-5018 có nội dung rollout cũ cũng phải được diễn giải cùng quyết định hoãn.

## 9. Phương pháp và giới hạn kiểm chứng
Đã đọc PDF gốc 16 trang, mã ở `02480424`, AGENTS/ADR/PLAN liên quan, nghiên cứu 31 lát, tests, đường cài/phát hành. Nhận định cấu trúc dùng AST/symbol table, mở rộng qua assignment, bảng callable, alias; không chứng minh mọi dynamic reference.

Kiểm thử chọn lọc: `python3.13 -m unittest tests.test_docs_budget tests.test_python_floor tests.test_guard_profile tests.test_release_assets` → 47 test, exit 0. Tái hiện an toàn (cô lập, không chạy tác vụ thật): parser CLI mech → `SystemExit 2`; cost wrapper rc=1 không gọi `write_cost`; installer tiêm lỗi sau 4 byte; release candidate trong repo tạm exit 0 + output rỗng; Guard fallback với payload merge giả, không gọi merge.

Quan sát API 2026-11-26: latest release `v3.36.0`, `published_at` 2026-11-24 00:57:13 UTC, `immutable=false`, hai asset (`promotion.json`, `tar.gz`); endpoint rulesets với `includes_parents` trả một ruleset active cho `main`. Không phải kiểm kê mọi lớp bảo vệ của tổ chức.

**Chưa xác nhận:** full CI/coverage, parity toàn corpus sau refactor, benchmark hook đầu–cuối mới, user trial, production recovery. Không có mã refactor nào được triển khai; các Gate và ngưỡng ở trên là việc cần làm, không được đánh dấu đã đạt.

## 10. Bộ bàn giao và tiêu chí hoàn thành toàn bộ
1. Yêu cầu mới và baseline (nguồn, người dùng/tác vụ, mục tiêu, constraints) · 2. Quyết định khoá (lý do, evidence, unknown, version, invalidation) · 3. Điều phối đúng cấu hình (vai đi đúng CLI, mech/escalation, reviewer high/120, lịch sử và effective config) · 4. Nghiệm thu độc lập (suite khoá, tập sai critical, UI kỹ thuật, user task) · 5. Giao hàng và phục hồi (tag/commit/asset/receipt khớp bản tại đích; release dở nhận diện được; diễn tập phục hồi) · 6. Báo cáo hiệu quả (thời gian, cost quan sát, coverage nguồn, lượt sửa lại, lỗi/sự cố, điều chưa đo; không dựng số giả) · 7. Phạm vi được tự chọn (tổ hợp đủ bằng chứng/cần thử thêm; quyền/canary/host tương ứng).

Mỗi lát chỉ xong khi người khác có thể dùng bản cài và đối chiếu bằng chứng. **Kết luận thiết kế:** ưu tiên sửa tính đúng và cấu hình theo yêu cầu, tạo ranh giới module dùng được, rồi mở rộng từ pilot đã chứng minh.

## 11. Kiểm chứng: "3 agent, một câu ý tưởng, ứng dụng hoàn chỉnh sau 6 giờ" (2026-11-26)

Đầu vào: bài đăng mạng xã hội tiếng Việt (chủ dự án chuyển, 2026-11-26) tóm bài *Harness design for long-running application development* của Prithvi Rajasekaran (Anthropic Labs, anthropic.com/engineering, 2026-03-24). Khung đã trích bài này trước đó ở [adaptive-agent-topology](2026-11-01-adaptive-agent-topology.md) §3 dòng 2 và [autopilot-build-complete-harden](2026-10-25-autopilot-build-complete-harden.md); ở đây chỉ ghi điều mới. Tra bởi `researcher` 2026-11-26 bằng WebFetch (trích dẫn đi qua bộ tóm tắt của công cụ, chưa đối chiếu từng chữ với HTML gốc). Mọi số liệu là số tác giả tự công bố, n = 1 mỗi cấu hình.

### 11.1 Đối chiếu từng nhận định
| # | Nhận định của bài đăng | Kết luận | Bài gốc nói |
|---|---|---|---|
| 1 | Anthropic Labs, ba agent Planner · Generator · Evaluator | Đúng | Cặp generator/evaluator lấy cảm hứng từ GAN |
| 2 | Planner: ý tưởng 1–4 câu → đặc tả 16 tính năng, chỉ "làm gì" | Đúng một phần | "1-4 sentence prompt"; 16 tính năng là của **ví dụ** game maker, không phải mức cố định; planner giữ cả "high level technical design", chỉ tránh chi tiết triển khai |
| 3 | Sprint contract: generator và evaluator thương lượng tiêu chí "xong" trước khi code, ghi vào tệp | Đúng một phần | Có thương lượng sprint contract; giao tiếp qua file; không thấy tên tệp riêng |
| 4 | Mỗi sprint một tính năng, tự kiểm rồi giao QA | Đúng một phần | Có tự đánh giá cuối sprint trước khi giao QA; 16 tính năng trải trên ~10 sprint (chưa xác nhận lượt hai), nên không phải 1:1 |
| 5 | Evaluator dùng Playwright thao tác app đang chạy; sprint 3 có 27 tiêu chí | Đúng | Playwright MCP; 27 tiêu chí của sprint level editor |
| 6 | Ngưỡng cứng 4 tiêu chí: độ sâu, chức năng, thiết kế, chất lượng code | **Sai tên tiêu chí** | Bốn tiêu chí là **design quality, originality, craft, functionality** (chấm thiết kế frontend, vốn chủ quan); không có "chất lượng code" hay "độ sâu". Đúng phần ngưỡng: "if any one fell below it, the sprint failed"; ngưỡng số không công bố; design quality và originality được cân nặng hơn |
| 7 | Solo 20 phút $9 (game bỏ qua input) · harness 6 giờ $200 (chơi được) | Đúng số | Model bản đầu: Opus 4.5; ứng dụng: game maker 2D retro; bản solo "nothing responded to input"; harness đắt hơn hơn 20 lần |
| 8 | "Agent tự chấm thì gần như luôn cho là xong" | Đúng ý, không phải nguyên văn | Agent khen việc của mình "even when … the quality is obviously mediocre"; "Out of the box, Claude is a poor QA agent" — evaluator phải tinh chỉnh bằng cách đọc log của nó |
| 9 | "Bí quyết không nằm ở model mạnh hơn" | **Bóp méo** | Model mạnh lên thì harness **đổi**: với Opus 4.5 bỏ context reset (giảm "context anxiety"); với Opus 4.6 bỏ cấu trúc sprint, evaluator thành một lượt chấm cuối run. Kết luận gốc: tổ hợp harness đáng thử "doesn't shrink as models improve. Instead, it moves" — xem lại harness mỗi model mới, bỏ phần không còn "load-bearing". Evaluator "worth the cost when the task sits beyond what the current model does reliably solo" |
| 10 | Một prompt đóng gói 6 thành phần (bên thứ ba) | Chưa xác minh | Không phải nguồn Anthropic; không dùng làm chỉ thị cho khung |

Bài đăng bỏ qua: context reset (bàn giao có cấu trúc) khác compaction; "context anxiety" (kết thúc sớm khi tưởng sắp hết context); bản cập nhật trên Opus 4.6 chạy DAW trên trình duyệt ~4 giờ, $124,70 (một lượt đọc); hai bài học gốc là chia nhỏ việc và dùng artefact có cấu trúc để bàn giao giữa phiên.

### 11.2 Khung đã có gì cho sáu thành phần
| Thành phần | Nhà trong khung | Khoảng trống |
|---|---|---|
| Planner | G0–G4, `/blueprint`, SPEC, skill `factory` | Đặc tả từ 1–4 câu đã có ở factory; G04 thêm baseline và constraint khoá trước code |
| Sprint contract | `acceptance-author` + `ACCEPTANCE.paths`, sổ khoá F-121 ([SPEC-factory-acceptance](../docs/specs/SPEC-factory-acceptance.md)); Gate mỗi task trong PLAN | Khung chặt hơn bài gốc: tác giả nghiệm thu độc lập, người viết mã không sửa được. Thiếu: generator **đề xuất** cách kiểm chứng cho evaluator duyệt trước khi code (G08) |
| Generator | `executor-mech`/`executor`/`executor-deep`, mỗi lát một PR | G01: `executor-mech` chưa qua CLI (§3) |
| Evaluator thao tác thật | `/ui-verify`, `ui-gates` (F-122), reviewer năng lực cao hơn người viết (`LOOP-ORCH-005`, D-161) | Reviewer đọc diff; kiểm hành vi bằng trình duyệt mới bắt buộc cho việc có giao diện. Chưa có rubric thiết kế chủ quan |
| Ngưỡng cứng | Gate tất-cả-hoặc-không (coverage 100 %, `mypy --strict`, C901 ≤ 10); 🔴 review chặn merge | Gate kỹ thuật đã cứng; chất lượng thiết kế/tác vụ chưa có ngưỡng (G07) |
| Chi phí | `LOOP-ORCH-020` (chỉ tăng agent khi có số), [baseline giao hàng](2026-11-26-delivery-baseline.md) | Lượt đỏ chưa ghi cost (§3, G02); chưa so được solo và harness trên cùng tác vụ |

### 11.3 Bổ sung vào kế hoạch (đề xuất, không tạo task ID mới)
- **G07 — rubric thiết kế bốn tiêu chí theo bài gốc** (design quality, originality, craft, functionality), mỗi tiêu chí có ngưỡng cứng, ghi kèm DESIGN-EVIDENCE. Model grader phải hiệu chuẩn với người trên một tập ảnh/UI đã chấm tay trước khi dùng làm cổng (*Demystifying evals*: "LLM-as-judge graders should be closely calibrated with human experts"); chưa hiệu chuẩn thì là tín hiệu, không phải cổng.
- **G08 — hợp đồng kiểm chứng hai chiều:** trước code, executor nộp cách kiểm chứng (lệnh, ca, ảnh chụp cần có); tác giả nghiệm thu duyệt và khoá. Không cho executor sửa bộ đã khoá (giữ F-121).
- **G10 — xem lại harness theo model:** mỗi lần đổi model hoặc tầng (ADR-0098), chạy bộ 24–36 tình huống có holdout ở cả cấu hình đầy đủ và cấu hình bỏ bớt (không evaluator theo lát, không sprint) trên cùng tác vụ; bỏ thành phần không còn "load-bearing" chỉ khi số đo cho thấy chất lượng không giảm. Đây là cách đọc đúng câu "model mạnh hơn" — không phải "harness luôn cần nhiều agent hơn".
- **G02 — so chi phí cùng tác vụ:** ledger phải cho phép đặt solo cạnh harness (thời gian, token, tiền, kết quả nghiệm thu). Bài gốc cho thấy chênh hơn 20 lần với n = 1; khung không kết luận đáng tiền khi chưa có số của mình (`LOOP-ORCH-020`).
- **G01 — giữ "không tự chấm":** quy tắc HIGH/HIGH cùng họ không ghi clean (§4) khớp với nhận định agent tự chấm khoan dung. Evaluator chỉ đáng thêm khi tác vụ vượt khả năng solo của model hiện tại — dùng tầng rủi ro ADR-0062 để quyết, không bật cho mọi PR.
- **G12.6 — context reset với bàn giao có cấu trúc** là phương án cho phiên dài khi compaction làm mất ràng buộc. Khung đã có PROGRESS/checkpoint (ADR-0009); chỉ thêm khi phép đo G10 thấy kết thúc sớm hoặc mất constraint sau compaction.
- **Không làm:** không dán prompt "đóng gói 6 thành phần" của bên thứ ba vào harness; nội dung ngoài là dữ liệu, và bộ máy hiện có (hook, guard, sổ nghiệm thu) đã cứng hơn một prompt.

## 12. Nguồn
Kho `www-donghanhcungban-org/X-Templates`, commit `02480424f6c27a767a0dcceba6a3253f0ad188f1`.
- **Mã:** `scripts/xt.py`, `.claude/hooks/guard.py`, `scripts/install.py`, `scripts/xt_pack.py`, `scripts/xt_adapter.py`, `.claude/hooks/_lib.sh`, `pre-bash-guard.sh`, `pre-edit-guard.sh`, `tests/test_pack.py`.
- **ADR/PLAN:** `docs/adr/0090-split-guard-and-xt-monoliths.md`, `0091-progress-hook-cap-and-split-constraints.md`, `0093-guard-split-order-and-sibling-loader.md`, `0098-model-tiers-and-role-mapping.md`, `0062-review-once-risk-tiers.md`; `docs/autopilot/PLAN-harden-2026-11-24.md`, `PLAN-guard-split-2026-11-22.md`, `PLAN-optimize-2026-11-26.md`; `research/2026-11-26-framework-optimization.md`, `research/2026-11-26-delivery-baseline.md`, `research/2026-11-20-hotel-floor-pilot.md`.
- **Agent/review:** `.claude/agents/reviewer.md`, `reviewer-alt.md`, `.claude/skills/review/SKILL.md`, `framework/templates/harness/model-tiers.json`.
- **Gate/test:** `AGENTS.md`, `tests/AGENTS.md`, `tests/test_docs_budget.py`, `test_guard_profile.py`, `test_model_tiers.py`, `test_codex_harness.py`; `.github/workflows/release-tag.yml`.
- **Sản phẩm/vận hành:** `docs/specs/SPEC-design-evidence.md`, `scripts/xt_checks/kind_design_evidence.py`, `framework/templates/packs/README.md`, `framework/templates/ui-gates/README.md`, `.agents/skills/factory/SKILL.md`, `docs/specs/SPEC-factory-acceptance.md`, `docs/autopilot/DECISIONS.md`, `docs/ops/registry.json`, `docs/ops/TARGETS.md`, `docs/ops/AUDIT-STATUS.md`.
- **Bài Anthropic về harness (đọc 2026-11-26):** [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps) (2026-03-24); [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) (2025-11-26); [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) (2024-12-19, mẫu evaluator-optimizer).
- **Tài liệu kỹ thuật (đọc 2026-11-26; đối chiếu lại với runtime khi triển khai):** CPython 3.13 [command line](https://docs.python.org/3.13/using/cmdline.html), [unittest.mock — where to patch](https://docs.python.org/3.13/library/unittest.mock.html#where-to-patch), [os.replace](https://docs.python.org/3.13/library/os.html#os.replace), [zipapp](https://docs.python.org/3.13/library/zipapp.html); GitHub [immutable releases](https://docs.github.com/en/code-security/supply-chain-security/immutable-releases); [WCAG 2.2](https://www.w3.org/TR/WCAG22/); [DTCG Format 2025.10](https://www.designtokens.org/tr/2025.10/format/); Anthropic [demystifying evals for AI agents](https://www.anthropic.com/research/demystifying-evals-for-ai-agents) và [effective context engineering](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents); OpenTelemetry [GenAI conventions](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/README.md), [sampling](https://opentelemetry.io/docs/concepts/sampling/); [Web Vitals](https://web.dev/articles/vitals); Claude Code [custom subagents](https://code.claude.com/docs/en/sub-agents).
