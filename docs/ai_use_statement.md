# AI-USE STATEMENT (BẢN TUYÊN BỐ SỬ DỤNG AI)
### HỌC PHẦN: DỮ LIỆU LỚN (INT4418) - NHÓM 6: VERIFIER-GUIDED REPAIR

> **Quy định học phần:** Theo Hướng dẫn Bài tập lớn INT4418 và Đề cương chi tiết, việc sử dụng các mô hình AI/LLM phải được công khai minh bạch, có định lượng cụ thể, và toàn bộ mã nguồn cũng như kết luận đều phải được nhóm học viên kiểm chứng độc lập (thông qua Lean 4 compiler và automated tests).

---

## 1. Bảng số liệu định lượng tổng hợp (Quantitative Summary)

* **Tổng số phiên/hạng mục AI hỗ trợ:** `40`
* **Ước tính số dòng mã & tài liệu AI đồng hành:** `~11278` dòng
* **Cơ chế kiểm chứng bắt buộc:** 100% mã nguồn được xác minh qua unit test tự động và trình kiểm chứng Lean 4; không chấp nhận mã chưa kiểm chứng.

### Phân bổ theo loại tác vụ:
| Loại tác vụ | Số lần ghi nhận | Tỷ trọng (%) |
|:---|:---:|:---:|
| Code | 8 | 20.0% |
| Documentation | 5 | 12.5% |
| Code Generation | 2 | 5.0% |
| Docs | 2 | 5.0% |
| Experiment | 2 | 5.0% |
| Workspace Setup | 1 | 2.5% |
| Governance & Harness | 1 | 2.5% |
| Academic Proposal | 1 | 2.5% |
| Taxonomy Design | 1 | 2.5% |
| Dataset Curation | 1 | 2.5% |
| Baseline Implementation | 1 | 2.5% |
| Testing & QA | 1 | 2.5% |
| Team Roster & Governance | 1 | 2.5% |
| Team Role Adjustment | 1 | 2.5% |
| Environment & Tooling | 1 | 2.5% |
| Lean 4 Interactive Verification | 1 | 2.5% |
| Data Contract & Replayable Store | 1 | 2.5% |
| System Architecture Documentation | 1 | 2.5% |
| Architecture Refinement | 1 | 2.5% |
| Docs+Code | 1 | 2.5% |
| Code+Debug | 1 | 2.5% |
| Analysis+Docs | 1 | 2.5% |
| CodeGeneration | 1 | 2.5% |
| Infrastructure | 1 | 2.5% |
| Refactoring | 1 | 2.5% |
| Visualization | 1 | 2.5% |

### Phân bổ theo mô hình / công cụ AI:
| Mô hình / Công cụ | Số lần ghi nhận | Tỷ trọng (%) |
|:---|:---:|:---:|
| Claude Code / Antigravity | 31 | 77.5% |
| Claude Opus 5.5 | 8 | 20.0% |
| GitHub Copilot (MAI-Code-1.1-Flash) | 1 | 2.5% |

---

## 2. Nhật ký chi tiết hoạt động AI hỗ trợ (Chronological AI Activity Log)

| Thời điểm (UTC) | Giai đoạn | Mô hình / Công cụ | Loại tác vụ | Nội dung thực hiện | Phương thức kiểm chứng | Người kiểm duyệt | Trạng thái |
|:---|:---|:---|:---|:---|:---|:---:|:---:|
| 2026-09-11 01:59 | Tuần 1 | Claude Code / Antigravity | Workspace Setup | Cấu trúc lại thư mục theo chuẩn đề cương PTIT (configs, data_sample, docs, reports, results, scripts, slides, src, tests) và phân loại tệp tin. | Kiểm tra cấu trúc cây thư mục và Git status sạch sẽ | Đào Văn Tâm | ✅ VERIFIED |
| 2026-09-11 01:59 | Tuần 1 | Claude Code / Antigravity | Governance & Harness | Thiết lập hệ thống AI harness (CLAUDE.md, AGENTS.md, CONVENTIONS.md, GitNexus knowledge graph manifest). | Review nội dung quy tắc Big Data và kiểm tra cấu hình GitNexus | Đào Văn Tâm | ✅ VERIFIED |
| 2026-09-11 01:59 | Tuần 1 | Claude Code / Antigravity | Academic Proposal | Soạn thảo Đề cương 1 trang Tuần 1 cho Nhóm 6 (Verifier-Guided Repair) theo đúng 10 mục chuẩn Phụ lục A. | Đối chiếu với rubric chấm điểm và câu hỏi nghiên cứu RQ1, RQ2 | Đào Văn Tâm | ✅ VERIFIED |
| 2026-09-11 01:59 | Tuần 1 | Claude Code / Antigravity | Taxonomy Design | Xây dựng bảng phân loại lỗi Lean 4 (Taxonomy v0.1) gồm 6 nhóm lỗi cốt lõi, cơ chế định tuyến Router và tiêu chí an toàn ngữ nghĩa. | Kiểm tra dấu hiệu nhận biết trong compiler diagnostics của Lean 4 | Đào Văn Tâm | ✅ VERIFIED |
| 2026-09-11 01:59 | Tuần 1 | Claude Code / Antigravity | Dataset Curation | Tạo tập 50 mẫu lỗi Lean 4 thực tế (error_dataset_50.json) chia 34 train (68%) và 16 hold-out (32%) chống rò rỉ dữ liệu. | Kiểm tra schema JSON và tỷ lệ phân chia train/holdout | Đào Văn Tâm | ✅ VERIFIED |
| 2026-09-11 01:59 | Tuần 1 | Claude Code / Antigravity | Code Generation | Cài đặt bộ bóc tách lỗi Lean 4 (src/error_parser.py) phân tích log và định tuyến chiến lược sửa (Rule / LLM / System / Audit). | Chạy bộ kiểm thử tự động unittest (100% pass) | Đào Văn Tâm | ✅ VERIFIED |
| 2026-09-11 01:59 | Tuần 1 | Claude Code / Antigravity | Baseline Implementation | Cài đặt Blind One-Shot Retry Baseline (src/baseline_repair.py) theo đúng đặc tả mục 7 đề tài Nhóm 6, đo latency P50/P95 và chi phí token. | Chạy thực tế end-to-end trên tập 50 lỗi, sinh file log JSON Phụ lục B | Đào Văn Tâm | ✅ VERIFIED |
| 2026-09-11 01:59 | Tuần 1 | Claude Code / Antigravity | Testing & QA | Xây dựng bộ kiểm thử tự động (tests/test_error_parser.py, tests/test_baseline.py) bao phủ các hàm phân loại và baseline. | Thực thi unittest discover, 5/5 tests passed in 0.063s | Đào Văn Tâm | ✅ VERIFIED |
| 2026-09-11 02:11 | Tuần 1 | Claude Code / Antigravity | Team Roster & Governance | Cập nhật danh sách chính thức 6 thành viên, mã học viên và ma trận phân vai chính/dự phòng chuẩn mục 5 BTL vào contributions.md, đề cương và README | Đối chiếu mã học viên và 6 vai trò chuẩn trong hướng dẫn BTL | Đào Văn Tâm | ✅ VERIFIED |
| 2026-09-11 02:14 | Tuần 1 | Claude Code / Antigravity | Team Role Adjustment | Điều chỉnh vai trò theo yêu cầu: Trần Quang Đức Dũng phụ trách Queue & Worker System Lead, Lâm Thành Trung phụ trách Rule-based Repair Lead | Kiểm tra tính nhất quán trong contributions.md, de_cuong_nhom_6_tuan_1.md và README.md | Đào Văn Tâm | ✅ VERIFIED |
| 2026-09-11 02:18 | Tuần 1 | Claude Code / Antigravity | Environment & Tooling | Xây dựng script cài đặt Lean 4 (scripts/install_lean4.sh) và đóng gói môi trường containerized (Dockerfile, docker-compose.yml) | Kiểm tra cú pháp shell script và Docker Compose file | Đào Văn Tâm | ✅ VERIFIED |
| 2026-09-11 03:03 | Tuần 1 | Claude Code / Antigravity | Lean 4 Interactive Verification | Xác thực môi trường Lean 4 và tiện ích VS Code Infoview hoạt động thành công trên máy (hiển thị Goals accomplished trên sample_theorem.lean) | VS Code Lean 4 Infoview hiển thị Goals accomplished thành công | Đào Văn Tâm | ✅ VERIFIED |
| 2026-09-11 03:37 | Tuần 2 | Claude Code / Antigravity | Data Contract & Replayable Store | Xây dựng đặc tả Data Contract v0.1 với Nhóm 5 (docs/data_contract_group5_group6.md), module ReplayableErrorStore (src/error_store.py), demo replay script (scripts/replay_error_run.py) và 4 unit tests mới | Thực thi unittest discover, 9/9 tests passed in 0.183s và chạy thử nghiệm replay thành công | Đào Văn Tâm | ✅ VERIFIED |
| 2026-09-11 07:14 | Tuần 1-2 | Claude Code / Antigravity | System Architecture Documentation | Xây dựng tài liệu kiến trúc hệ thống toàn diện (docs/architecture.md) gồm sơ đồ vĩ mô 8 nhóm, sơ đồ vi mô 4 phân tầng Nhóm 6, Sequence Diagram thực thi và nhúng vào README.md | Kiểm tra cú pháp Mermaid flowchart và sequence diagram | Đào Văn Tâm | ✅ VERIFIED |
| 2026-09-11 07:19 | Tuần 1-2 | Claude Code / Antigravity | Architecture Refinement | Chuẩn hóa sơ đồ kiến trúc hệ thống (bản vẽ ASCII và Mermaid) tích hợp chính xác feedback loop của Bounded Retry Controller và Semantic Safety Check vào architecture.md, README.md và đề cương | Kiểm tra tính nhất quán sơ đồ giữa README, architecture.md và đề cương | Đào Văn Tâm | ✅ VERIFIED |
| 2026-09-11 09:05 | Week 2 | Claude Code / Antigravity | Docs | Structured detailed member task matrix by individual name and deliverables | Human audit against INT4418 guidelines | Đào Văn Tâm | ✅ VERIFIED |
| 2026-09-11 09:19 | Week 2 | Claude Code / Antigravity | Docs | Integrated onboarding quickstart and Git Flow team workflow into README.md | Markdown inspection and git status | Đào Văn Tâm | ✅ VERIFIED |
| 2026-09-11 12:46 | Week 2 | Claude Code / Antigravity | Code | Thực thi và kiểm thử baseline repair trên error dataset mẫu | Kiểm thử thành công qua baseline script | Mekdala Nounou | ✅ VERIFIED |
| 2026-09-12 07:48 | Week 4 | Claude Code / Antigravity | Code Generation | Cài đặt module Rule-based Repair Engine (src/rule_repair.py) gồm 4 luật R1-R4, bảng tra cứu configs/mathlib_import_table.json, bộ unit test và script đánh giá Rule Coverage | 17/17 test cases pass trong tests/test_rule_repair.py, 26/26 toàn bộ unittest pass, đo đạc Rule Coverage đạt 48.0% với latency P95=0.069ms | Lam Thanh Trung | ✅ VERIFIED |
| 2026-09-14 13:44 | Week 1 | GitHub Copilot (MAI-Code-1.1-Flash) | Code | Fix baseline runtime dependency failure and validate repo tests | python -m unittest discover -s tests -v | Khamsing OUTHAIHUENG | ✅ VERIFIED |
| 2026-10-15 09:08 | Week 5 | Claude Opus 5.5 | Code | Lean 4 verifier wrapper (src/lean_verifier.py), 9 unit tests, --verify mode for rule experiment; real compile_rate 20% vs 48% rule hit rate | unittest 35/35 pass; real Lean 4.35.0 compile on 50-sample dataset | Dao Van Tam | ✅ VERIFIED |
| 2026-10-15 09:17 | Week 5 | Claude Opus 5.5 | Code | Mathlib Lake workspace (lean_ws, gitignored), scripts/relabel_dataset.py + 2 tests, AI-vs-human task checklist; relabel shows 15/50 labels agree with real Lean | unittest 37/37 pass; real Lean 4.35.0 + Mathlib compile on 50 samples | Dao Van Tam | ✅ VERIFIED |
| 2026-10-16 07:28 | Week 6 (Day 1) | Claude Opus 5.5 | Code | Lean REPL verifier (500-1000x faster than cold lean), verifier pool, seed builder from Goedel Lean-workbook proofs, 9 mutation operators, parser v0.2 (+TAC_07, real Lean messages), full-file rules R0/R5-R7, semantic auditor, LLM repair (blind/diagnostic) + Gemini client, bounded repair pipeline, experiment runner with provenance | pytest 82/82; REPL vs cold Lean agree on 74/74 checks; real Lean 4.35 + Mathlib runs | Dao Van Tam | ✅ VERIFIED |
| 2026-10-16 07:36 | Week 6 (Day 1) | Claude Opus 5.5 | Code | Cost control: CostGuard (monthly/run hard caps, ledger), SQLite response cache, pre-run estimator with VND, comment stripping preserving line/column (cost option C) | pytest 88/88 incl. cap-blocks-before-call and cache-hit-free tests | Dao Van Tam | ✅ VERIFIED |
| 2026-10-16 08:46 | Week 6 (Day 1) | Claude Opus 5.5 | Docs+Code | Figure/table generator from run records (6 figures, 2 tables), report draft skeleton per Phu luc C, data card; Kaggle notebook flags | pytest 91/91; figures rendered and inspected for overlap | Dao Van Tam | ✅ VERIFIED |
| 2026-10-18 15:30 | Week 7 | Claude Opus 5.5 | Code+Debug | Kaggle execution: per-stage saves, robust input discovery, session notebooks; fixed REPL process-group leak (lake env repl child), REPL crash recovery, primary-error selection (unsolved goals as consequence), fail-fast on missing API key | pytest 96/96; regression test reproduces orphaned child; label agreement 85.1%->95.0% on stored diagnostics | Dao Van Tam | ✅ VERIFIED |
| 2026-10-18 15:30 | Week 7 | Claude Opus 5.5 | Experiment | Kaggle runs 2/2b/3a/3b: dataset v1.0 (17,031), RQ1/RQ2 LLM runs, scale 100/1K/10K x 1/2/4 workers x 3 repeats | 48 run records with provenance; 0 seed leakage, 0 duplicates; real spend $2.97 in cost ledger | Dao Van Tam | ✅ VERIFIED |
| 2026-10-18 15:30 | Week 8 | Claude Opus 5.5 | Analysis+Docs | Figures/tables from raw results, failure analysis (stop/audit reasons, per-rule precision), repaired-v1 export + output contract, README, manifest v1.0, license/privacy note, requirements lock, Dockerfile Lean 4.35, contributions from git history | scripts re-run from results/raw; README demo command executed; pytest 96/96 | Dao Van Tam | ✅ VERIFIED |
| 2026-10-19 04:23 | Integration | Claude Code / Antigravity | CodeGeneration | Group 5 gateway scripts/repair_batch.py: contract validation, Lean re-verification, bounded repair, feedback and repaired-v1 export; sample input and handover guide; gpu field in provenance | 7 unit tests with stub verifier and MockClient; end-to-end rule_only run on real Lean 4.35 over 14 sample records | Nhóm 6 Lead | ✅ VERIFIED |
| 2026-10-19 04:33 | Analysis | Claude Code / Antigravity | Experiment | Offline parser ablation scripts/parser_ablation.py replaying hybrid k=1 1K runs under 5 parser variants; report table 9, R5 leakage note, references trimmed to 8, PR list in contributions, dockerignore | Replay of full parser matches 100% of logged first attempts; 32 new rule candidates verified with local Lean REPL; 4 unit tests; report rebuilt at 20 pages | Nhóm 6 Lead | ✅ VERIFIED |
| 2026-10-19 04:48 | Reproducibility | Claude Code / Antigravity | Infrastructure | Docker image test build, dockerignore, init process for REPL child reaping | Image built (16.6 GB, arm64); pytest 103 passed with --init; gateway run in container identical to host | Nhóm 6 Lead | ✅ VERIFIED |
| 2026-10-10 17:30 | Week 6 | Claude Code / Antigravity | Code | Setup Redis Queue, Verifier Worker Pool, Bounded Controller, and Scalability Benchmark | 14 unit tests pass, 3-tier queue benchmark pass | Trần Quang Đức Dũng | ✅ VERIFIED |
| 2026-10-19 05:31 | Integration | Claude Code / Antigravity | Refactoring | Integrate PR #6 worker queue: conflict resolution, simulated verifier renamed, simulated results isolated, Redis compose profile, requirements | pytest 121 passed including 14 queue tests; analysis scripts glob only results/raw/run_exp-*.json | Nhóm 6 Lead | ✅ VERIFIED |
| 2026-10-19 09:09 | Defense | Claude Code / Antigravity | Documentation | Defense Q&A: model choice and model-swap answers (Flash-Lite rationale, Gemini 3.6 Flash result, DeepSeek-Prover estimate), refreshed test count and Group 5 status | Numbers cross-checked against report.md tables 4, 5, 8 and run records | Nhóm 6 Lead | ✅ VERIFIED |
| 2026-10-20 03:12 | Defense | Claude Code / Antigravity | Documentation | Restructure slide deck: goal slide, highlights with 6/6 acceptance criteria, demo after architecture, one results slide for RQ1-RQ3, rule and parser ablation, conclusion with delivery, roles merged into Q&A, charts moved to appendix P1-P3 | Deck rebuilt and exported with PowerPoint; every slide rendered and checked for overflow; numbers cross-checked with report.md | Nhóm 6 Lead | ✅ VERIFIED |
| 2026-10-20 03:22 | Defense | Claude Code / Antigravity | Visualization | One slide per RQ with its chart; new RQ1 figure fig_rq1_category (blind vs diagnostics by error category, k=1) generated from run records; appendix now ablation and P50/P95 latency | Figure regenerated from results/raw; existing tables and PNGs unchanged; deck exported with PowerPoint and every slide rendered | Nhóm 6 Lead | ✅ VERIFIED |
| 2026-10-20 03:48 | Defense | Claude Code / Antigravity | Documentation | Talk script KichBan_ThuyetTrinh_Nhom6 (docx + pdf) generated by slides/build_talk_script.py from slides/talk_script_content.py; speaker notes synced into the pptx; plain-language summary added to README as single source; appendix numbers computed from run records, configs and cost ledger | Builder checks slide count, notes sync, glossary usage and placeholder sources (all three failure modes tested); every number cross-checked against report.md, replay logs and run records; PDF exported with Word and pages rendered | Nhóm 6 Lead | ✅ VERIFIED |
| 2026-10-20 04:09 | Report | Claude Code / Antigravity | Documentation | Final report sync: 121 tests, precise audit numbers in the conclusion, Redis queue prototype in future work, Group 5 gateway and Docker check in the delivery appendix | Numbers cross-checked with report section 7.1, pytest and the Docker container run; report rebuilt with Word, still 20 pages, last pages rendered | Nhóm 6 Lead | ✅ VERIFIED |
| 2026-10-20 04:25 | Defense | Claude Code / Antigravity | Code | Replay demo runs on a fresh clone with plain Python: lazy yaml import, three demo samples in data_sample, dataset fallback in demo_repair.py, demo script commands updated | Fresh git clone + system python3 3.14 with no packages: all three demo scenes print code, diagnostics, attempts and results; pytest 121 passed | Nhóm 6 Lead | ✅ VERIFIED |
| 2026-10-29 13:08 | Defense | Claude Code / Antigravity | Documentation | 5-minute single-speaker talk script KichBan_RutGon_5Phut_Nhom6 (docx + pdf) generated by slides/build_short_script.py: topic, what the team did, results, with slide cues | All numbers reused from the full talk script and report; timing computed with the same syllable counter (4:05 speech); PDF preview checked | Nhóm 6 Lead | ✅ VERIFIED |

---

## 3. Cam kết liêm chính học thuật (Academic Integrity Affirmation)

1. Nhóm học viên chịu trách nhiệm hoàn toàn về tính chính xác, tính logic toán học và khả năng thực thi của toàn bộ mã nguồn trong dự án.
2. Các phát biểu toán học và mã sửa Lean 4 đều phải được kiểm tra qua trình biên dịch hình thức (`lean` CLI).
3. Mọi kết quả thực nghiệm, số đo độ trễ $P50 / P95$ và thông lượng đều được sinh ra từ các lần chạy thật trên hệ thống thực tế (lưu tại `results/raw/`), không sử dụng số liệu suy diễn từ AI.
