# System Card — Verifier-Guided Repair (Nhóm 6, INT4418)

## 1. Hệ thống làm gì
Nhận một tệp Lean 4 không biên dịch được, phân loại lỗi từ chẩn đoán thật của Lean, sửa bằng luật (0 token) hoặc LLM, rồi **chỉ chấp nhận bản sửa khi Lean biên dịch được và kiểm toán ngữ nghĩa xác nhận đề bài không bị thay đổi**. Vòng lặp có giới hạn số lần thử, thời gian và chi phí.

| Thành phần | Mã nguồn |
|---|---|
| Kiểm chứng Lean (REPL thường trú, pool worker) | `src/lean_repl.py`, `src/verifier_pool.py` |
| Parser & taxonomy v0.2 | `src/error_parser.py`, `docs/error_taxonomy_v0.2.md` |
| Luật sửa R0–R7 | `src/rule_repair.py` |
| Sửa bằng LLM (blind / diagnostic) | `src/llm_repair.py`, `configs/prompts/repair_v1.yaml` |
| Vòng lặp có giới hạn | `src/repair_pipeline.py` |
| Kiểm toán ngữ nghĩa | `src/semantic_auditor.py` |
| Kiểm soát chi phí | `src/cost_guard.py`, `configs/budget.yaml` |

## 2. Mô hình và phụ thuộc bên ngoài
- **LLM:** Google Gemini `gemini-3.5-flash-lite` qua Gemini API (trả phí, credit Google AI Pro); so sánh phụ `gemini-3.6-flash`. Nhiệt độ 0, seed 42, `thinking_level=minimal`. Dữ liệu gửi đi: mã Lean (đã bỏ chú thích) và thông báo lỗi; không có dữ liệu cá nhân.
- **Trình kiểm chứng:** Lean 4.35.0, Mathlib v4.35.0, Lean REPL v4.35.0 (Apache-2.0), phiên bản ghim trong `lean_ws/lake-manifest.json`.
- **Dữ liệu:** Goedel-LM/Lean-workbook-proofs (MIT). Xem `docs/data_card_lean_errors.md`.

## 3. Mục đích sử dụng
- **Phù hợp:** sửa hàng loạt ứng viên chứng minh do pipeline tự hình thức hoá sinh ra (đầu ra Nhóm 5); nghiên cứu đánh đổi chất lượng–chi phí–độ trễ của vòng sửa có kiểm chứng.
- **Không phù hợp:** dùng kết quả như chứng minh đúng *mà không chạy lại Lean*; dùng để "chứng minh" một phát biểu khác đề gốc; dùng cho ngôn ngữ/phiên bản Lean khác mà không sinh lại nhãn.

## 4. Cơ chế an toàn
| Rủi ro | Biện pháp |
|---|---|
| "Sửa" bằng cách đổi đề (làm yếu kết luận, đổi ℝ→ℕ, thêm giả thiết) | Phát biểu định lý phải trùng bản gốc (sau chuẩn hoá khoảng trắng); bị loại với lý do `statement_changed` |
| Lách kiểm chứng (`sorry`, `admit`, `axiom`, `native_decide`, `implemented_by`, `unsafe`) | Kiểm tra cả cảnh báo `sorry` của Lean lẫn mã nguồn (bỏ qua chú thích) |
| Vòng lặp vô hạn với lỗi không sửa được | Ngân sách lần thử *k*, ngân sách thời gian 300 s/mẫu, dừng khi ứng viên lặp lại (SHA-256) |
| Tactic chạy mãi / REPL treo hoặc chết | Timeout 60 s/lần kiểm, giới hạn heartbeat; REPL chết → trả `CRASH`, khởi động lại, không gán nhãn từ lần kiểm hỏng |
| Vượt ngân sách API | Trần tháng $8 / lần chạy $2 kiểm tra **trước** mỗi lần gọi; sổ chi tiêu `results/cost_ledger.jsonl`; cache câu trả lời; mô hình chưa có giá bị từ chối |
| Lộ khoá API | Khoá chỉ nằm trong `.env` (gitignore) hoặc Kaggle Secrets; không ghi vào log/run record |

## 5. Hạn chế đã biết
- Kiểm toán phát biểu dựa trên văn bản: phát biểu tương đương nhưng viết khác bị tính là đổi đề (đếm thiếu thành công, không đếm thừa).
- Nhãn và luật R5 (bảng đổi tên) gắn với Mathlib v4.35.0.
- Dữ liệu đánh giá chủ yếu là lỗi tổng hợp trên bài toán thi đấu; khả năng tổng quát sang lỗi do LLM sinh trong pipeline thật (Nhóm 5) chưa được đo.
- Một họ LLM (Gemini Flash); chưa so với mô hình chuyên Lean.
- Thông lượng bị giới hạn bởi CPU: 4 worker trên 4 vCPU tăng tốc ~2,4–2,6× (không tuyến tính) do tranh chấp CPU; mỗi worker cần ~3,5 GB RAM (đếm RSS trùng phần Mathlib dùng chung — báo cáo cả USS).

## 6. Đánh giá
Chỉ số chính: tỷ lệ sửa thành công **đã kiểm toán** và thông lượng ổn định; phụ: tỷ lệ biên dịch, lần thử/mẫu, token và USD/thành công, thời gian phục vụ P50/P95, thời gian chờ P95, bộ nhớ đỉnh. Mọi số liệu truy được tới run record trong `results/raw/` (commit, máy, phần mềm, seed, tham số). Kết quả: xem `reports/report.md` §6–7.

## 7. Liên hệ và trách nhiệm
Nhóm 6, INT4418, PTIT — trưởng nhóm Đào Văn Tâm. Mã do AI hỗ trợ được khai báo trong `docs/ai_use_statement.md` và đã được kiểm chứng bằng kiểm thử tự động và chạy Lean thật.
