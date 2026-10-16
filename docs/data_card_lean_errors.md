# Data Card — Lean 4 Error Dataset v1.0 (Nhóm 6)

| Mục | Nội dung |
|---|---|
| Tên / phiên bản | `lean-errors` v1.0 (`DATA_VERSION = v1.0-mutation+natural`) |
| Mục đích | Đánh giá hệ thống sửa chứng minh Lean 4 có kiểm chứng (RQ1–RQ3 của Nhóm 6) |
| Đơn vị dữ liệu | Một tệp Lean 4 hoàn chỉnh không biên dịch được (hoặc dùng `sorry`) + chẩn đoán thật của Lean |
| Nguồn | Goedel-LM/Lean-workbook-proofs (29.750 chứng minh, giấy phép **MIT**), chứng minh cho bài toán của Lean Workbook |
| Công cụ gán nhãn | Lean 4.35.0 + Mathlib v4.35.0 qua Lean REPL v4.35.0 — nhãn **không viết tay** |
| Tái tạo | `scripts/download_data.sh` (SHA-256) → `build_seeds.py --n 3000` → `generate_error_dataset.py --max-per-seed 5`, seed 42 |
| Lưu trữ | `data/errors/errors_{100,1k,10k,all}.jsonl` (không đưa vào Git); mẫu 100 dòng: `data_sample/errors_sample_100.jsonl` |

## Thành phần
- **Lỗi tổng hợp:** 9 toán tử gây lỗi áp lên chứng minh đã kiểm chứng (xem `docs/error_taxonomy_v0.2.md` §3). Mỗi mẫu giữ `original_code` (bản đúng) làm chuẩn tham chiếu cho kiểm toán ngữ nghĩa.
- **Lỗi tự nhiên:** chứng minh gốc không còn biên dịch với Mathlib hiện tại (đổi tên lemma, cú pháp cũ, timeout). Không có bản đúng tham chiếu; phát biểu lấy từ chính tệp lỗi.

## Trường dữ liệu
`error_id`, `source`, `seed_id`, `mutation_op`, `intended_category`, `code`, `original_code`, `diagnostics[]` (severity, line, column, end_line, end_column, message), `primary_message`, `category` (taxonomy v0.2), `route`, `statement`, `split`, `sha256`.

## Chia tập và quy mô
- Train/hold-out 70/30, **chia theo `seed_id`** (băm SHA-256) — mọi biến thể của một định lý nằm cùng phía, tránh rò rỉ.
- Các mức lồng nhau 100 ⊂ 1K ⊂ 10K ⊂ all sau khi xáo trộn tất định.
- Khử trùng lặp theo SHA-256 của `code`.
- Số lượng thực tế, phân bố nhãn, bảng nhầm lẫn "dự kiến → thật": xem run record `results/raw/run_gen-errors-*.json`.

## Hạn chế và lưu ý sử dụng
- Phân bố bài toán lệch về bất đẳng thức/đại số thi đấu (đặc trưng Lean Workbook).
- Lỗi tổng hợp có thể khác phân bố lỗi do LLM sinh ra; nên báo cáo kết quả tách theo `source`.
- `typ_change_type` đổi phát biểu: bản sửa "chứng minh được phiên bản ℕ" là **đổi đề** và bị kiểm toán loại.
- Nhãn phụ thuộc phiên bản Lean/Mathlib; đổi phiên bản phải sinh lại toàn bộ.
- Không chứa dữ liệu cá nhân.
