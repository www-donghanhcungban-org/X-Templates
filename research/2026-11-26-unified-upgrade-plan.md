---
title: Kế hoạch nâng cấp hợp nhất — tách xt.py/guard.py, review high/120, giao hàng theo bằng chứng (đề xuất)
kind: research
updated: 2026-11-26
---

# Kế hoạch nâng cấp hợp nhất (đề xuất, 2026-11-26)

> **Trạng thái: đề xuất, chưa phải PLAN.** Bản chuyển từ PDF "Kế hoạch nâng cấp hợp nhất" (40 trang, đối chiếu mã ở commit `02480424`). Chưa có task ID đăng ký, chưa sửa mã. Khi triển khai phải ánh xạ vào PLAN đang có (không lập kế hoạch cạnh tranh), giữ task đã xong, và ghi rõ ADR bị thay thế. **D-610** (hoãn nâng dự án đích) vẫn hiệu lực.
>
> Bản chuyển này gồm: tổng quan, hiện trạng, lỗi đã tái hiện, chính sách reviewer, backlog G01–G12, thứ tự/Cửa A–E, đo hiệu quả, ánh xạ 31 lát, phương pháp và nguồn. Các mục giữa PDF (kiến trúc XT/Guard, hiệu năng/packaging, hợp đồng dữ liệu, UI/UX, agent, chi phí/pilot — trang 7–26) **chưa được chuyển vào đây**; đối chiếu bản PDF gốc khi triển khai.

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

## 11. Nguồn
Kho `www-donghanhcungban-org/X-Templates`, commit `02480424f6c27a767a0dcceba6a3253f0ad188f1`.
- **Mã:** `scripts/xt.py`, `.claude/hooks/guard.py`, `scripts/install.py`, `scripts/xt_pack.py`, `scripts/xt_adapter.py`, `.claude/hooks/_lib.sh`, `pre-bash-guard.sh`, `pre-edit-guard.sh`, `tests/test_pack.py`.
- **ADR/PLAN:** `docs/adr/0090-split-guard-and-xt-monoliths.md`, `0091-progress-hook-cap-and-split-constraints.md`, `0093-guard-split-order-and-sibling-loader.md`, `0098-model-tiers-and-role-mapping.md`, `0062-review-once-risk-tiers.md`; `docs/autopilot/PLAN-harden-2026-11-24.md`, `PLAN-guard-split-2026-11-22.md`, `PLAN-optimize-2026-11-26.md`; `research/2026-11-26-framework-optimization.md`, `research/2026-11-26-delivery-baseline.md`, `research/2026-11-20-hotel-floor-pilot.md`.
- **Agent/review:** `.claude/agents/reviewer.md`, `reviewer-alt.md`, `.claude/skills/review/SKILL.md`, `framework/templates/harness/model-tiers.json`.
- **Gate/test:** `AGENTS.md`, `tests/AGENTS.md`, `tests/test_docs_budget.py`, `test_guard_profile.py`, `test_model_tiers.py`, `test_codex_harness.py`; `.github/workflows/release-tag.yml`.
- **Sản phẩm/vận hành:** `docs/specs/SPEC-design-evidence.md`, `scripts/xt_checks/kind_design_evidence.py`, `framework/templates/packs/README.md`, `framework/templates/ui-gates/README.md`, `.agents/skills/factory/SKILL.md`, `docs/specs/SPEC-factory-acceptance.md`, `docs/autopilot/DECISIONS.md`, `docs/ops/registry.json`, `docs/ops/TARGETS.md`, `docs/ops/AUDIT-STATUS.md`.
- **Tài liệu kỹ thuật (đọc 2026-11-26; đối chiếu lại với runtime khi triển khai):** CPython 3.13 [command line](https://docs.python.org/3.13/using/cmdline.html), [unittest.mock — where to patch](https://docs.python.org/3.13/library/unittest.mock.html#where-to-patch), [os.replace](https://docs.python.org/3.13/library/os.html#os.replace), [zipapp](https://docs.python.org/3.13/library/zipapp.html); GitHub [immutable releases](https://docs.github.com/en/code-security/supply-chain-security/immutable-releases); [WCAG 2.2](https://www.w3.org/TR/WCAG22/); [DTCG Format 2025.10](https://www.designtokens.org/tr/2025.10/format/); Anthropic [demystifying evals for AI agents](https://www.anthropic.com/research/demystifying-evals-for-ai-agents) và [effective context engineering](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents); OpenTelemetry [GenAI conventions](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/README.md), [sampling](https://opentelemetry.io/docs/concepts/sampling/); [Web Vitals](https://web.dev/articles/vitals); Claude Code [custom subagents](https://code.claude.com/docs/en/sub-agents).
