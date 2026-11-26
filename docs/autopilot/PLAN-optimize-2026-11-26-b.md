# PLAN X-Templates 2026-11-26 — tối ưu khung đợt 2 (hàng rào, mẫu cài cho đích, CI)

> Duyệt: D-608 (đợt 1), D-610 (chỉ sửa trong repo khung, chưa nâng đích), D-611, D-612, D-613 · Căn cứ: [nghiên cứu tối ưu](../../research/2026-11-26-framework-optimization.md) §lát C02–C13 · Đợt trước: [PLAN-optimize-2026-11-26](PLAN-optimize-2026-11-26.md)

## Tóm tắt
- Đợt 2 làm các lát C02–C13 của nghiên cứu: hàng rào (trần thông báo cổng đỏ, rào lệnh chèn trong skill, độ sâu subagent, tag glob), mẫu cài cho đích (install ghi nguyên tử, AGENTS mẫu), CI (test-main thoát sớm khi push), hook nhẹ hơn, công cụ không tăng dòng.
- Mỗi lát một nhánh từ `origin/main`, một worktree, một PR; `files:` không giao nhau, trừ `CHANGELOG.md` (rebase khi xung đột).
- Không thêm trọng số test thủ công trừ khi `tests.test_ci_shard` đòi; lát đo trọng số (L02) làm ở đợt 3 cùng tách `guard.py`/`xt.py` (C14, C15, L05).
- `guard.py` và `xt.py` đang đúng trần dòng: C06 và C10 phải 0 dòng ròng; không nới trần.
- Dự án đích nhận các thay đổi này khi cắt bản kế; không mở PR ở repo đích (D-610).

## Ngân sách
- Số vòng: mặc định `--single-session` · Chi phí dịch vụ ngoài: 0 · Timeout Gate: 1200 giây · Hạn: phiên hiện hành.

## Task

### Lát 1 — hàng rào và harness
- [ ] `T-5039` trần thông báo cổng commit đỏ ≤ 8 000 ký tự, log đầy đủ trong thư mục git, vẫn fail-closed (files: .claude/hooks/pre-bash-guard.sh, tests/test_hook_gate_output.py, framework/11-autonomous-loop/context-and-token-budget.md, CHANGELOG.md; topo: parallel; exec: deep) — Gate: `python3 -m unittest tests.test_hook_gate_output tests.test_hooks`
- [ ] `T-5040` settings: hook `PreSkillShellCommand` dùng lại pre-bash-guard, `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1`, nén sớm theo D-613, pre-compact.sh in chỉ dẫn tóm tắt (sau: T-5035; files: .claude/settings.json, .claude/hooks/pre-compact.sh, xt.yaml, CLAUDE.md, framework/11-autonomous-loop/harness-files.md, framework/11-autonomous-loop/orchestration-and-subagents.md, tests/test_hook_skill_shell.py, tests/test_hook_precompact_output.py, CHANGELOG.md; topo: parallel; exec: deep) — Gate: `python3 -m unittest tests.test_hook_skill_shell tests.test_hook_precompact_output tests.test_settings_types tests.test_hooks tests.test_docs_budget`
- [ ] `T-5041` guard chặn mọi glob không nháy ở vị trí tên tag của dạng tạo, 0 dòng ròng, đóng AUD-HAR-541 (D-612) (files: .claude/hooks/guard.py, tests/test_guard_tag_glob_oracle.py, tests/fixtures/autonomy/guard.json, docs/ops/AUDIT-STATUS.md, CHANGELOG.md; topo: parallel; exec: deep) — Gate: `python3 -m unittest tests.test_guard_tag_glob_oracle tests.test_hooks tests.test_green_shell tests.test_green_gh tests.test_docs_budget && python3 scripts/xt.py autonomy-bench`
- [ ] `T-5042` post-tool-failure.sh tiền lọc bằng regex tập cha trước khi gọi python (files: .claude/hooks/post-tool-failure.sh, tests/test_post_tool_failure_prefilter.py, CHANGELOG.md; topo: parallel) — Gate: `python3 -m unittest tests.test_post_tool_failure_prefilter tests.test_hooks`

### Lát 2 — mẫu cài cho dự án đích
- [ ] `T-5043` install.py ghi nguyên tử (tệp tạm + `os.replace`), hook 0 byte coi là hỏng, lỗi ghi in cách khôi phục (files: scripts/install.py, tests/test_install.py, tests/test_install_atomic.py, CHANGELOG.md; topo: parallel; exec: deep) — Gate: `python3 -m unittest tests.test_install tests.test_install_new tests.test_install_atomic && python3 -m mypy --strict --python-version 3.13 scripts/install.py`
- [ ] `T-5044` AGENTS mẫu: tra blueprint bằng `blueprint-status` thay vì đọc trọn tệp; thêm phạm vi tìm kiếm (files: framework/templates/AGENTS.md, CHANGELOG.md; topo: parallel) — Gate: `grep -c 'blueprint-status' framework/templates/AGENTS.md && python3 scripts/xt.py validate && python3 -m unittest tests.test_docs_budget tests.test_install`
- [ ] `T-5045` thân agent executor/reviewer thêm hai dòng phòng ngừa (ghi rồi đọc log là hai lệnh; lệnh dài chia lượt ≤ 4 phút); sinh lại gương `.codex` (files: .claude/agents/executor.md, .claude/agents/executor-deep.md, .claude/agents/reviewer.md, .claude/agents/reviewer-alt.md, .codex/agents/, tests/test_model_tiers.py, CHANGELOG.md; topo: parallel) — Gate: `python3 -m unittest tests.test_model_tiers tests.test_codex_harness tests.test_docs_budget && python3 scripts/xt.py validate`
- [ ] `T-5046` skill /complete: rà bản sửa ở head trước merge, sổ đi cùng PR sửa, bản sửa xanh giả kèm bộ sinh biến thể (D-611); đồng bộ gương `.agents/skills` (files: .claude/skills/complete/SKILL.md, .agents/skills/complete/SKILL.md, framework/11-autonomous-loop/orchestration-and-subagents.md, CHANGELOG.md; sau: T-5040; topo: parallel) — Gate: `cmp .claude/skills/complete/SKILL.md .agents/skills/complete/SKILL.md && python3 scripts/xt.py validate && python3 -m unittest tests.test_docs_budget tests.test_doc_command_drift tests.test_codex_harness`

### Lát 3 — CI và công cụ
- [ ] `T-5047` job `test-main` thoát sớm ở cấp bước khi sự kiện không phải pull_request (files: .github/workflows/ci.yml, tests/test_ci.py, CHANGELOG.md; topo: parallel) — Gate: `python3 -m unittest tests.test_ci tests.test_ci_shard && python3 scripts/xt.py ci-check`
- [ ] `T-5048` xt.py 0 dòng ròng: `doctor` chỉ chạy lại khi có sửa; `harness-check` nạp guard một lần (files: scripts/xt.py, tests/test_install_new.py, tests/test_doctor.py, tests/test_xt.py, docs/ops/AUDIT-STATUS.md, CHANGELOG.md; topo: parallel) — Gate: `python3 -m unittest tests.test_doctor tests.test_xt tests.test_install_new tests.test_docs_budget && python3 scripts/xt.py harness-check`
- [ ] `T-5049` ghép lại BLUEPRINT của khung theo chữ hiện hành, `— Kiểm:` đủ 17 MUST (files: BLUEPRINT.md, BLUEPRINT-BACKLOG.md, tests/test_xt.py, tests/test_xt_cli.py, CHANGELOG.md; sau: T-5048; topo: parallel) — Gate: `python3 scripts/xt.py blueprint-status BLUEPRINT.md --strict --run && python3 -m unittest tests.test_blueprint_repo006 tests.test_xt_cli tests.test_xt`
