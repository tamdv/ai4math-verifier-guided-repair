# Kết quả giả lập, không dùng trong báo cáo

Sáu run record ở đây do `scripts/run_queue_benchmark.py` sinh ra ngày 10/10/2026 trên máy Windows không cài Lean, thuộc PR #6 của Trần Quang Đức Dũng.

Verifier trong các lần chạy này là bộ giả lập `src/sim_verifier.py`: nó chờ 5 ms rồi kiểm tra ngoặc, từ khoá và import bằng heuristic, không biên dịch Lean và không nạp Mathlib. Vì vậy tỷ lệ thành công 98% và độ trễ khoảng 5 ms ở đây không so sánh được với các lần chạy thật trên Kaggle với Lean 4.35, nơi chiến lược chỉ luật đạt 23,9% và P95 kiểm chứng ở mức 10K là 3,1 đến 6,5 giây.

Các script phân tích chỉ đọc `results/raw/run_exp-*.json` ở thư mục cha, nên thư mục này không đi vào hình hay bảng nào. Giá trị của các file là minh chứng cho cơ chế hàng đợi FIFO và ưu tiên, ack, nack và hàng đợi lỗi chạy đúng.
