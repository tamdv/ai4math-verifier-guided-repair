# Kịch bản demo — Nhóm 6, Verifier-Guided Repair (≈ 6 phút)

**Luồng bắt buộc theo đề bài:** lỗi → phân loại → sửa → Lean kiểm tra (+ kiểm toán ngữ nghĩa).
**Chế độ chính: phát lại từ log thực nghiệm** (`--replay`, $0, không cần Lean/mạng — an toàn khi bảo vệ).
Chế độ chạy thật (Lean + Gemini) chỉ dùng nếu máy demo có ≥ 16 GB RAM rảnh và đã nạp sẵn Mathlib.

## Chuẩn bị (trước buổi bảo vệ, 5 phút)
```bash
cd ai4math-verifier-guided-repair && source .venv/bin/activate
python -m pytest tests -q                       # 96 passed — mở sẵn kết quả
ls data/errors/errors_1k.jsonl                  # dataset v1.0 đã có trên máy demo
export LLM=results/raw/logs/exp-llm_only-b3-w4-20261017101714-3f7a7e.jsonl.gz
export HYB=results/raw/logs/exp-hybrid-b3-w4-20261017102347-852e82.jsonl.gz
```
Mở sẵn: `results/figures/fig_ablation.png`, `fig_cost_quality.png`, `fig_scale_speedup.png`, `results/figures/table_rule_precision.md`.
Phóng to terminal (cỡ chữ ≥ 18).

## Cảnh 1 — Luật sửa 0 token (1 phút) · người trình bày: Trung
```bash
python scripts/demo_repair.py --replay $HYB --error-id E000880 --data data/errors/errors_1k.jsonl
```
Nói: "Tệp này mất dòng `import Mathlib`. Lean không báo 'thiếu import' mà báo `unknown namespace BigOperators` — parser vẫn nhận ra IMP_02 vì mã dùng ký hiệu Mathlib mà không import. Router gửi sang luật R0, Lean chấp nhận, kiểm toán đạt — **0 token, vài chục ms**."

## Cảnh 2 — Cùng loại lỗi, chỉ dùng LLM: kiểm toán chặn gian lận (2 phút) · Tùng
```bash
python scripts/demo_repair.py --replay $LLM --error-id E000003 --data data/errors/errors_1k.jsonl
```
Chỉ vào từng lần thử:
1. **Lần 1:** Gemini trả mã *biên dịch được* nhưng chứa `sorry` → kiểm toán **FAIL (uses_sorry, forbidden_construct)**. "Nếu chỉ đo compile rate, đây đã bị tính là thành công."
2. **Lần 2:** không biên dịch → vòng lặp đưa thông báo lỗi mới vào prompt.
3. **Lần 3:** biên dịch + kiểm toán PASS. Tổng **4.583 token** so với 0 token của luật.

Thông điệp: kiểm toán ngữ nghĩa là bắt buộc (17–26% bản sửa LLM đổi đề/lách); router đúng tiết kiệm chi phí.

## Cảnh 3 — Vòng lặp có giới hạn sửa được ở lần 2 (1 phút) · Khamsing
```bash
python scripts/demo_repair.py --replay $LLM --error-id E000197 --data data/errors/errors_1k.jsonl
```
Nói: "Chứng minh bị thay bằng `sorry` (SEM_06). Lần 1 sai, Lean báo lỗi; lần 2 nhận chẩn đoán mới và sửa đúng. 82,7% thành công đến ngay lần 1, 12,4% ở lần 2 — đó là lý do k=3 thêm 11 điểm %."

## Cảnh 4 — Kết quả và quy mô (2 phút) · Tâm, Dũng
Mở hình đã chuẩn bị:
- `fig_ablation.png`: blind 31,7% → LLM+chẩn đoán 53,9% → k=3 65,1%.
- `fig_cost_quality.png`: biên Pareto; chẩn đoán vừa tốt hơn vừa rẻ hơn blind.
- `fig_scale_speedup.png`: 1→2 worker 1,76×, 2→4 worker chỉ +7% — nút thắt CPU (Dũng giải thích REPL + process group).

## Phương án dự phòng
| Sự cố | Xử lý |
|---|---|
| Không có `data/errors/errors_1k.jsonl` trên máy demo | bỏ `--data` (vẫn hiện các lần thử, không hiện mã gốc) hoặc tải dataset từ Kaggle `g6-errors-v1` |
| Terminal lỗi | mở `slides/` (ảnh chụp các cảnh) |
| Hội đồng muốn xem chạy thật | `python scripts/demo_repair.py --data data/errors/errors_1k.jsonl --error-id E000880 --strategy hybrid --budget 3` (cần Lean, ~2 phút nạp Mathlib; luật R0 không tốn token) |
