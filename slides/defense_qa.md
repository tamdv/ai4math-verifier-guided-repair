# Bộ câu hỏi vấn đáp dự kiến — Nhóm 6

Mỗi thành viên trả lời được **toàn bộ** danh sách (yêu cầu chung: "khi bảo vệ phải hiểu toàn bộ pipeline"); phần in đậm theo tên là người trả lời chính. Số liệu: `results/figures/*.md`, `reports/report.md`.

## A. Bài toán và vai trò Big Data — Tâm
1. **Nút thắt Big Data của đề tài là gì?** Không phải một phép toán mà là quy mô + lập lịch + chi phí: kiểm chứng nguội nạp Mathlib 63–107 s/tệp; 10⁴ ứng viên xếp hàng trên vài worker CPU; mỗi lần thử LLM tốn token và hàng giây; log phải phát lại được.
2. **Chỉ số chính là gì, vì sao?** Tỷ lệ sửa thành công *đã kiểm toán* (RQ1/RQ2) và thông lượng ổn định (RQ3). Compile rate đơn thuần bị thổi phồng: LLM k=3 biên dịch 75,0% nhưng thành công thật 65,1%.
3. **Baseline có công bằng không?** Cùng hold-out 284 mẫu, cùng mô hình, nhiệt độ 0, seed 42, timeout 60 s, phần cứng, cùng tiền xử lý (bỏ chú thích). Khác biệt duy nhất: có/không chẩn đoán Lean.
4. **Vì sao chi phí blind cao hơn dù prompt ngắn hơn?** Không có chẩn đoán, mô hình viết lại toàn bộ tệp: 783 token ra/lần so với 389 — token ra đắt gấp 8,3 lần token vào.

## B. Dữ liệu — Nounou
5. **Nhãn lấy từ đâu?** Từ thông báo Lean 4.35 thật qua parser, không từ toán tử gây lỗi; khớp với nhóm dự kiến 94,4%, tái lập 17.031/17.031.
6. **Chống rò rỉ thế nào?** Chia 70/30 theo băm `seed_id`: mọi biến thể của cùng định lý ở cùng phía; 0/4.776 seed ở cả hai phía; 0 bản trùng SHA-256.
7. **Lỗi tự nhiên là gì?** 1.110 chứng minh cũ không còn biên dịch với Mathlib hiện tại (đổi tên lemma, cú pháp `∑ x in`). Khó hơn hẳn: 7,7% (k=1) so với 56,1% lỗi tổng hợp — nhưng hold-out chỉ 13 mẫu tự nhiên (hạn chế).
8. **Vì sao bỏ tập 50 lỗi tuần 1?** Chỉ 15/50 nhãn viết tay khớp Lean thật, 14/50 mẫu thậm chí biên dịch được.

## C. Parser & taxonomy — Khamsing
9. **Vì sao thêm TAC_07?** Lỗi phổ biến nhất trong dữ liệu thật là tactic không đóng mục tiêu (`unsolved goals`, `linarith failed`); v0.1 xếp chúng vào UNK.
10. **Chọn lỗi chính thế nào?** Lỗi vị trí sớm nhất *sau khi loại hệ quả*: `unsolved goals` báo ở dòng khai báo nhưng là hệ quả của tactic hỏng bên dưới → độ khớp nhãn 85,1% → 95,0%.
11. **Thiếu import nhận ra bằng cách nào khi Lean không báo "missing import"?** Mã không có `import` nhưng dùng ký hiệu Mathlib (ℝ, `nlinarith`…) và lỗi là `unknown …`/`unexpected token` → IMP_02.

## D. Luật sửa — Trung
12. **Vì sao hybrid kém LLM thuần?** Luật được thử trước trên 203/284 mẫu nhưng chỉ đúng 33%; với k=1, luật sai là hết lượt. R0 97%, R7 100%, nhưng R2/R3/R4/R5/R6 0% trên tệp hoàn chỉnh.
13. **Cải tiến thế nào?** Router chỉ dùng luật có độ chính xác cao *đo trên tập train* (không trên hold-out để tránh rò rỉ), còn lại chuyển LLM.
14. **Vì sao R5 (đổi tên) 0% dù lỗi tự nhiên chủ yếu là đổi tên?** Lỗi tự nhiên thường có nhiều lỗi đan xen; đổi tên một lemma chưa đủ để cả tệp biên dịch.

## E. LLM — Tùng
15. **Prompt chẩn đoán gồm gì?** Mã đánh số dòng + tối đa 5 thông báo Lean kèm nhãn taxonomy; system prompt cấm `sorry`/`axiom`, giữ nguyên phát biểu, trả về 1 khối ```lean.
16. **Vì sao bỏ chú thích không làm hỏng mã?** Ký tự chú thích thay bằng khoảng trắng, giữ nguyên dòng và cột (Lean nhạy thụt lề, chẩn đoán dùng dòng:cột); 500/500 seed vẫn biên dịch, giảm 66% ký tự.
17. **Vì sao Gemini 3.6 Flash kém hơn Flash-Lite?** Nhiều lỗi biên dịch hơn (125 vs 76) và đổi phát biểu thường hơn; cả hai chạy `thinking_level=minimal` — có thể bất lợi cho mô hình lớn. Chúng tôi không kết luận "mô hình lớn kém hơn".
18. **Kiểm soát chi phí ra sao?** Kiểm chi phí xấu nhất với trần tháng $8 / lần chạy trước mỗi lần gọi; sổ chi tiêu; bộ đệm câu trả lời. Tổng thực tế $2,97.

## F. Worker & quy mô — Dũng
19. **REPL thường trú khác gì chạy `lean` từng tệp?** Nạp Mathlib một lần cho mỗi worker (11–25 s trên Kaggle), sau đó mỗi định lý P50 3 ms / P95 23 ms thay vì 63–107 s; kết quả khớp 74/74 với chạy nguội. Mỗi lần kiểm trong môi trường gốc nên không rò trạng thái.
20. **Vì sao 4 worker chỉ nhanh 1,88×?** 4 REPL tranh 4 vCPU với tiến trình điều phối và tactic nặng: từ 2→4 worker chỉ +7–11% thông lượng, P95 phục vụ tăng gấp đôi (3,1 → 6,5 s ở 10K). Hệ thống bị giới hạn bởi CPU; mở rộng tiếp phải phân tán qua nhiều máy.
21. **Lỗi lớn nhất gặp khi chạy?** `lake env repl` sinh tiến trình `repl` con; huỷ `lake` khi timeout để lại `repl` chạy 100% CPU + 3,5 GB → treo sau ~16 timeout. Sửa: chạy trong process group riêng, huỷ cả nhóm; có test tái hiện.
22. **Vì sao báo cáo USS chứ không phải RSS?** RSS cộng trùng phần Mathlib các worker ánh xạ chung (35 GB trên máy 31 GB); USS (bộ nhớ riêng) 12,6 → 21,1 GB.
23. **Không lặp vô hạn bằng cách nào?** Ngân sách k lần thử, ngân sách 300 s/mẫu, dừng khi ứng viên lặp lại (SHA-256) — cắt 4,6% mẫu ở LLM k=3.

## G. Tái lập & trung thực
24. **Hội đồng chạy lại thế nào?** README: `pytest` (không cần Lean), demo replay ($0); thực nghiệm đầy đủ bằng notebook `notebooks/sessions/` trên Kaggle; hình bằng `generate_figures.py` từ `results/raw/`.
25. **AI được dùng thế nào?** Trợ lý lập trình (Claude) hỗ trợ mã, thực nghiệm, tài liệu — khai báo trong `docs/ai_use_log.jsonl`; mọi mã qua 96 test và Lean thật; mọi số liệu truy được tới run record. Gemini là *đối tượng nghiên cứu*, không viết báo cáo.
26. **Hạn chế lớn nhất?** Lỗi tổng hợp và ít lỗi tự nhiên trong hold-out; kiểm toán dạng văn bản; một họ LLM; chưa có dữ liệu thật của Nhóm 5.
