# CONTRIBUTIONS — Nhóm 6, Verifier-Guided Repair (INT4418, PTIT)

Tài liệu này ghi **ai đã làm gì** (truy được qua lịch sử Git) và **phần bảo vệ của từng thành viên**.
Việc dùng AI được khai báo riêng trong [`docs/ai_use_statement.md`](docs/ai_use_statement.md).

## 1. Phân vai (theo Hướng dẫn BTL, mục 5)

| Thành viên | Mã HV | Vai trò chính | Dự phòng |
|---|---|---|---|
| Đào Văn Tâm *(trưởng nhóm)* | B25CHHT112 | Evaluation & Cost Analysis | Queue & Worker System |
| Trần Quang Đức Dũng | B25CHHT088 | Queue & Worker System | Evaluation & Cost Analysis |
| Lâm Thành Trung | B25CHHT117 | Rule-based Repair | LLM Repair Engine |
| Nguyễn Xuân Tùng | B25CHHT119 | LLM Repair Engine | Rule-based Repair |
| Khamsing OUTHAIHUENG | B25CHHT125 | Parser & Taxonomy | Error Dataset & Contract |
| Mekdala Nounou | B25CHHT124 | Error Dataset & Contract | Parser & Taxonomy |

## 2. Đóng góp đã thực hiện (đối chiếu `git log`)

| Giai đoạn | Thành viên | Đóng góp | Bằng chứng |
|---|---|---|---|
| W1–W2 | Đào Văn Tâm | Khởi tạo dự án, đề cương, taxonomy v0.1, 50 lỗi mẫu, parser/baseline ban đầu, data contract v0.1 với Nhóm 5, ReplayableErrorStore, kiến trúc, quy trình AI-use | `1b19f14` … `5fa9fd2`, `efcf899`, `c1e48c9` |
| W3 | Mekdala Nounou | Chạy và kiểm chứng baseline trên tập lỗi mẫu | `e65cf30` |
| W4 | Lâm Thành Trung | Rule engine R1–R4, bảng tra Mathlib import, 17 test, script benchmark (rule coverage 48%) | `23f479b`, `24b7dbd`, `5c3a362`, `b4778cc`, `59582b0` |
| W4 | Khamsing OUTHAIHUENG | Bỏ phụ thuộc numpy của baseline (test pass), tóm tắt tiếng Việt | `ae43a61`, `19ca3f0` |
| W5–W7 | Đào Văn Tâm (có hỗ trợ AI — Claude, đã khai báo) | Lean REPL verifier + worker pool; dataset lỗi v1.0 (17.031 mẫu) từ Lean thật; taxonomy v0.2 (TAC_07); luật R0, R5–R7; LLM repair + kiểm soát chi phí; vòng lặp có giới hạn + kiểm toán ngữ nghĩa; toàn bộ thực nghiệm Kaggle (RQ1–RQ3); hình, phân tích lỗi, tài liệu, báo cáo | nhánh `feat/verifier-guided-pipeline` (từ `6767845`) |

Ghi chú: luật R1–R4 của Trung là nền của module luật hiện tại; số liệu thực nghiệm (bảng độ chính xác từng luật) cho thấy R0/R7 đạt 97–100%, R1 27%, R2–R4 0% trên tệp hoàn chỉnh — một kết quả phân tích quan trọng của báo cáo.

## 3. Phần bảo vệ của từng thành viên

Mỗi người trình bày mảng của mình **và phải trả lời được toàn bộ pipeline** (yêu cầu chung của học phần).

| Thành viên | Trình bày | Tài liệu chuẩn bị |
|---|---|---|
| Đào Văn Tâm | Câu hỏi nghiên cứu, kiến trúc, đánh giá RQ1–RQ3, chi phí | `reports/`, `results/figures/` |
| Trần Quang Đức Dũng | Worker pool, REPL thường trú, scale & nút thắt CPU, lỗi rò rỉ tiến trình | `src/lean_repl.py`, `src/verifier_pool.py`, `table_scale` |
| Lâm Thành Trung | Luật sửa R0–R7, độ chính xác từng luật, vì sao hybrid k=1 kém | `src/rule_repair.py`, `table_rule_precision` |
| Nguyễn Xuân Tùng | LLM repair: blind vs diagnostic, prompt, chi phí token, mô hình so sánh | `src/llm_repair.py`, `configs/prompts/` |
| Khamsing OUTHAIHUENG | Parser & taxonomy v0.2, chọn lỗi gốc, độ khớp nhãn 94,4% | `src/error_parser.py`, `docs/error_taxonomy_v0.2.md` |
| Mekdala Nounou | Dataset v1.0: seed, đột biến, lỗi tự nhiên, chia tập chống rò rỉ, data card | `scripts/generate_error_dataset.py`, `docs/data_card_lean_errors.md` |

## 4. Việc còn mở cho thành viên (ghi tên + commit khi hoàn thành)

| Việc | Người nhận | Trạng thái |
|---|---|---|
| Chạy lại `pytest` + demo replay trên máy cá nhân, báo lỗi nếu có | Mỗi thành viên | ☐ |
| Đối chiếu số liệu trong báo cáo với `results/figures/*.md` | Khamsing, Nounou | ☐ |
| Kiểm tra lại 10 trích dẫn của báo cáo | Tùng | ☐ |
| Slide phần mình phụ trách (theo mục 3) | Mỗi thành viên | ☐ |
| Đọc code mảng mình + trả lời bộ câu hỏi vấn đáp | Mỗi thành viên | ☐ |
| Review PR `feat/verifier-guided-pipeline` → `main` | Dũng, Trung | ☐ |

## 5. Nhật ký tiến độ

| Tuần | Mốc | Trạng thái |
|---|---|---|
| W1 | Đề cương, taxonomy v0.1, 50 lỗi mẫu, baseline plan | ✅ |
| W2 | Data contract Nhóm 5, replayable error store | ✅ |
| W3 | Baseline retry nguyên prompt | ✅ (giả lập W3; baseline thật chạy W7: 31,7%) |
| W4 | Parser + luật sửa | ✅ |
| W5 | Router + LLM repair dùng error context | ✅ |
| W6 | Vòng lặp có giới hạn, timeout, dedup, worker queue | ✅ |
| W7 | Scale 100/1K/10K × 1/2/4 worker × 3 lần; RQ1/RQ2 | ✅ |
| W8 | Ablation, phân tích lỗi, kiểm toán ngữ nghĩa | ✅ (bảng trong `results/figures/`) |
| W9 | Release candidate, README, báo cáo | ⏳ |
| W10 | Demo, bảo vệ, bàn giao | ⏳ |
