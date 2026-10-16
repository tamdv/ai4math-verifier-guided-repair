---
title: "Verifier-Guided Repair: Sửa chứng minh Lean 4 có kiểm chứng dưới ràng buộc chi phí và độ trễ"
subtitle: "Báo cáo bài tập lớn INT4418 – Dữ liệu lớn (Thạc sĩ), Nhóm 6"
author: "Nhóm 6 — Đào Văn Tâm (trưởng nhóm), Trần Quang Đức Dũng, Lâm Thành Trung, Nguyễn Xuân Tùng, Khamsing OUTHAIHUENG, Mekdala Nounou"
date: "10/2026"
lang: vi
---

<!--
TRẠNG THÁI BẢN NHÁP (xoá khối này trước khi nộp)
- Ký hiệu ⟦...⟧ = số liệu/hình chờ kết quả Kaggle (results/raw -> scripts/generate_figures.py).
- Mọi con số trong báo cáo phải truy được tới một run record trong results/raw/ (ghi run_id ở chú thích bảng).
- Trích dẫn: kiểm tra lại năm/hội nghị/arXiv id của [1]–[10] trước khi nộp.
- Độ dài mục tiêu ~12 trang A4 (Hướng dẫn BTL: 8–12; CLAUDE.md: 12–20) — chốt lại với giảng viên.
-->

# Tóm tắt

Các hệ thống tự động hình thức hoá toán học sinh ra hàng nghìn tới hàng chục nghìn chứng minh Lean 4, phần lớn không biên dịch được. Sửa chúng ở quy mô lớn là bài toán *dữ liệu lớn*: mỗi lần kiểm chứng phải nạp thư viện Mathlib (~6 GB), hàng đợi lỗi tăng nhanh, và việc thử lại bằng mô hình ngôn ngữ (LLM) làm chi phí và độ trễ đuôi bùng nổ nếu không được kiểm soát. Chúng tôi xây dựng hệ thống **Verifier-Guided Repair** gồm: (i) bộ kiểm chứng Lean dùng tiến trình REPL thường trú, (ii) bộ phân tích và phân loại lỗi theo taxonomy 7 nhóm rút ra từ thông báo thật của Lean 4.35, (iii) bộ định tuyến sang luật sửa (0 token) hoặc LLM có tiêm thông báo lỗi có cấu trúc, (iv) vòng lặp sửa–kiểm có giới hạn số lần thử, thời gian và ngân sách, cùng (v) bộ kiểm toán ngữ nghĩa chống "sửa bằng cách đổi đề". Trên tập lỗi ⟦N⟧ mẫu sinh từ ⟦S⟧ chứng minh đã kiểm chứng (Lean Workbook) kèm lỗi "trôi phiên bản" tự nhiên, REPL thường trú giảm thời gian kiểm chứng từ 63–107 s xuống P50 3 ms / P95 23 ms mỗi định lý. Đưa thông báo lỗi có cấu trúc vào prompt tăng tỷ lệ sửa thành công (đã kiểm toán) từ ⟦x⟧% (baseline thử lại nguyên prompt) lên ⟦y⟧%; định tuyến lai với ngân sách ⟦k⟧ đạt ⟦z⟧% với chi phí ⟦c⟧ USD/1.000 mẫu. Thông lượng tăng ⟦s⟧× khi tăng từ 1 lên 4 worker ở mức 10K mẫu.

**Từ khoá:** Lean 4, sửa chứng minh tự động, LLM, kiểm chứng hình thức, hàng đợi worker, độ trễ đuôi.

# 1. Giới thiệu

**Bối cảnh.** Trong chuỗi AI4Math của lớp, Nhóm 5 tự động dịch đề toán sang Lean 4 theo lô; đầu ra của họ là đầu vào của nhóm chúng tôi. Một tỷ lệ lớn ứng viên không biên dịch được vì lỗi cú pháp, thiếu import, tên lemma sai hoặc đã đổi, sai kiểu, tactic không đóng được mục tiêu hay vượt ngân sách heartbeat. Cách phổ biến là *thử lại nguyên prompt*, vốn bỏ qua thông tin quý nhất có sẵn: thông báo lỗi của chính trình kiểm chứng.

**Vì sao là bài toán Dữ liệu lớn.** Nút thắt không nằm ở một phép toán mà ở *quy mô và lập lịch*: (1) mỗi lần kiểm chứng nguội phải nạp Mathlib, tốn 63–107 s và ~3,5 GB RAM trên máy 16 GB (đo ở §5); (2) số ứng viên tăng từ 10² lên 10⁴ khiến hàng đợi và độ trễ đuôi tăng; (3) mỗi lần thử lại bằng LLM tốn token và thời gian mạng; (4) log sửa lỗi phải lưu được để *phát lại* (replay) và kiểm toán. Đây là bài toán thông lượng–độ trễ–chi phí dưới ràng buộc tài nguyên, đúng phạm vi của môn học.

**Câu hỏi nghiên cứu.**

- **RQ1.** Thông báo lỗi có cấu trúc của Lean có cải thiện tỷ lệ sửa thành công so với thử lại nguyên prompt (cùng dữ liệu, cùng ngân sách, cùng phần cứng) không?
- **RQ2.** Chính sách định tuyến/thử lại nào (rule-only, LLM-only, lai; ngân sách k ∈ {0, 1, 3}) tối ưu tỷ lệ biên dịch dưới ngân sách token và thời gian cố định?
- **RQ3.** Hệ thống mở rộng thế nào theo số ứng viên (100 → 1K → 10K) và số worker (1/2/4) về thông lượng, độ trễ P50/P95 và bộ nhớ đỉnh?

**Đóng góp.** (1) Bộ dữ liệu lỗi Lean 4 *có nhãn từ thông báo thật* kèm tập hold-out tách theo định lý gốc; (2) taxonomy lỗi v0.2 (thêm nhóm TAC_07) đối chiếu với Lean 4.35; (3) pipeline sửa có giới hạn, có kiểm toán ngữ nghĩa và cơ chế kiểm soát chi phí cứng; (4) đánh giá thông lượng/độ trễ/chi phí trên 3 mức quy mô, kèm phân tích nút thắt "khởi động nguội" của Mathlib.

# 2. Công trình liên quan

**Môi trường và dữ liệu chứng minh.** LeanDojo [1] cung cấp công cụ trích xuất dữ liệu và tương tác với Lean, đồng thời cho thấy giá trị của truy hồi premise. Lean Workbook [2] hình thức hoá hàng chục nghìn bài toán thi đấu; ProofNet [3] là benchmark tự hình thức hoá cấp đại học. Chúng tôi dùng bộ chứng minh của Goedel-Prover [4] trên Lean Workbook làm nguồn định lý đúng.

**Sinh và sửa chứng minh bằng LLM.** Baldur [5] sinh toàn bộ chứng minh và sửa bằng cách đưa thông báo lỗi vào mô hình (Isabelle/HOL) — gần nhất với RQ1 của chúng tôi. Self-Debugging [6] cho thấy LLM tự sửa mã tốt hơn khi có phản hồi thực thi. DeepSeek-Prover-V1.5 [7] dùng phản hồi của trình kiểm chứng Lean cho học tăng cường và tìm kiếm cây; DeepSeek-Prover-V2 [8] phân rã mục tiêu con. Draft-Sketch-Prove [9] dùng bản nháp phi hình thức dẫn hướng chứng minh.

**Khoảng trống.** Các công trình trên tối ưu *chất lượng mô hình*; ít công trình báo cáo đồng thời chi phí token, độ trễ đuôi và khả năng mở rộng của *hệ thống kiểm chứng* — phần chiếm phần lớn thời gian thực tế. Chúng tôi coi verifier là tài nguyên khan hiếm cần lập lịch, tương tự tư duy xử lý theo lô và phân tán trong [10].

# 3. Dữ liệu và thu nhận

**Nguồn và giấy phép.** Định lý gốc lấy từ *Goedel-LM/Lean-workbook-proofs* (MIT, 29.750 chứng minh Lean 4 hoàn chỉnh, kèm đề bằng ngôn ngữ tự nhiên trong chú thích). Tệp nguồn (16 MB parquet) được tải bằng `scripts/download_data.sh` với kiểm tra SHA-256; dữ liệu lớn không đưa vào Git.

**Xây tập định lý gốc (seed).** Lấy ngẫu nhiên có seed 3.000 chứng minh, kiểm chứng lại với Lean 4.35 + Mathlib (v4.35.0); giới hạn `maxHeartbeats` = 400.000 thay cho "không giới hạn" của dữ liệu gốc. Chứng minh còn biên dịch sạch (không lỗi, không `sorry`) thành *seed*; chứng minh không còn biên dịch được giữ lại thành **lỗi tự nhiên** do trôi phiên bản (đổi tên lemma như `le_div_iff` → `le_div_iff₀`, cú pháp `∑ x in s` cũ, timeout). Ở thử nghiệm 100 mẫu: 67% còn biên dịch. Toàn bộ: ⟦kept/3000⟧.

**Sinh lỗi tổng hợp.** Với mỗi seed, áp dụng tối đa 5 trong 9 toán tử gây lỗi (bảng 1), chọn bằng bộ sinh ngẫu nhiên tất định theo seed. Một đột biến chỉ được giữ nếu Lean *thật sự* báo lỗi (với `sem_sorry`: cảnh báo `sorry`). **Nhãn luôn lấy từ thông báo Lean thật** qua parser, không lấy từ toán tử.

| Toán tử | Nhóm dự kiến | Cách gây lỗi |
|---|---|---|
| `syn_drop_paren`, `syn_drop_assign` | SYN_01 | xoá một `)` trong phát biểu; xoá `:=` |
| `imp_drop_import` | IMP_02 | xoá toàn bộ dòng `import` |
| `id_lemma_typo`, `id_tactic_typo` | ID_03 | xoá 1 ký tự tên lemma; viết sai tên tactic |
| `typ_change_type` | TYP_04 | đổi kiểu một biến ℝ ↔ ℕ |
| `tac_weaken` | TAC_07 | thay `nlinarith [...]` bằng `linarith`… |
| `tmo_low_heartbeats` | TMO_05 | hạ `maxHeartbeats` xuống 500 |
| `sem_sorry` | SEM_06 | thay chứng minh bằng `sorry` |

*Bảng 1. Toán tử sinh lỗi.*

**Lược đồ bản ghi.** `error_id, source (synthetic|natural), seed_id, mutation_op, intended_category, code, original_code, diagnostics[], primary_message, category, route, statement, split, sha256`.

**Khử trùng lặp, chia tập, các mức.** Khử trùng lặp theo SHA-256 của mã. Chia train/hold-out 70/30 **theo seed** (băm `seed_id`) để mọi biến thể của cùng một định lý nằm cùng một phía — tránh rò rỉ khi thiết kế luật trên train. Ba mức lồng nhau 100 ⊂ 1K ⊂ 10K. Phân bố nhãn và bảng nhầm lẫn "dự kiến → thật": ⟦bảng từ run gen-errors⟧.

**Chất lượng nhãn.** Tập 50 lỗi viết tay ban đầu (tuần 1) chỉ khớp 15/50 với Lean thật; 14/50 mẫu thậm chí biên dịch được — lý do chúng tôi chuyển sang nhãn sinh từ trình kiểm chứng.

**Hạn chế dữ liệu.** Lỗi tổng hợp có thể dễ hơn lỗi do LLM sinh ra; bài toán thiên về bất đẳng thức thi đấu (Lean Workbook); chưa có dữ liệu thật từ Nhóm 5 (dự kiến dùng làm tập đánh giá bổ sung).

# 4. Phương pháp và kiến trúc

**Tổng quan.** Hàng đợi ứng viên → parser & taxonomy → router → (luật | LLM) → worker kiểm chứng Lean → kiểm toán ngữ nghĩa → (thành công | thử lại nếu còn ngân sách | lưu thất bại) → kho log phát lại được. ⟦Hình kiến trúc — lấy từ docs/architecture.md⟧

**Bộ kiểm chứng REPL thường trú.** Mỗi worker giữ một tiến trình Lean REPL đã nạp Mathlib một lần (môi trường 0) và một môi trường lõi rỗng; mỗi ứng viên được kiểm trong môi trường gốc nên các lần kiểm cô lập với nhau. Dòng `import` được kiểm tra tồn tại trong bản build (để lỗi IMP_02 vẫn quan sát được) rồi bỏ đi; mã không import chạy trong môi trường lõi. Kết quả khớp 74/74 lần với Lean chạy nguội từng tệp.

**Taxonomy và parser.** 7 nhóm (bảng 2), so khớp theo thứ tự ưu tiên trên văn bản thông báo thật; IMP_02 còn được suy ra từ ngữ cảnh (mã không import nhưng dùng ℝ, `nlinarith`…). Lỗi chính = lỗi có vị trí sớm nhất.

| Mã | Nhóm | Định tuyến |
|---|---|---|
| SYN_01 | cú pháp | luật |
| IMP_02 | thiếu import | luật |
| ID_03 | định danh không tồn tại/đổi tên | lai |
| TYP_04 | sai kiểu / thiếu instance | LLM |
| TMO_05 | vượt heartbeat | điều khiển hệ thống |
| SEM_06 | `sorry` / đổi đề | kiểm toán |
| TAC_07 | tactic không đóng mục tiêu | LLM |

*Bảng 2. Taxonomy v0.2 (chi tiết: docs/error_taxonomy_v0.2.md).*

**Luật sửa (0 token).** R0 khôi phục `import Mathlib`; R1–R2 ngoặc/từ khoá; R3 bảng import; R4 bí danh định danh; R5 bảng đổi tên Mathlib (đã kiểm tra tồn tại trong mã nguồn v4.35.0); R6 cú pháp toán tử lớn; R7 khôi phục ngân sách heartbeat.

**Sửa bằng LLM.** Hai chế độ dùng chung system prompt (cấm `sorry`/`axiom`, giữ nguyên phát biểu): *blind* — chỉ đưa tệp lỗi (baseline theo đề bài); *diagnostic* — mã đánh số dòng + tối đa 5 thông báo lỗi kèm nhãn taxonomy. Trước khi gửi, chú thích được thay bằng khoảng trắng (giữ nguyên dòng và cột vì Lean nhạy thụt lề), giảm ~55–60% token; áp dụng như nhau cho mọi chiến lược. Mô hình: Gemini 3.5 Flash-Lite, nhiệt độ 0, seed 42, `thinking_level=minimal`.

**Vòng lặp có giới hạn.** Với mỗi mẫu, tối đa *k* lần thử và ngân sách thời gian 300 s; mỗi ứng viên được kiểm chứng và kiểm toán; dừng khi thành công, hết ngân sách, không có luật áp dụng (rule-only) hoặc **ứng viên lặp lại** (khử trùng lặp theo SHA-256) — đảm bảo không lặp vô hạn với lỗi không sửa được. Mỗi lần thử ghi một sự kiện (engine, luật, nhãn, trạng thái, token, độ trễ, mã ứng viên) vào log nén để phát lại.

**Kiểm toán ngữ nghĩa.** Thành công ⇔ biên dịch, không `sorry`, không cấu trúc cấm (`sorry`, `admit`, `axiom`, `native_decide`, `implemented_by`, `unsafe`) ngoài chú thích, và phát biểu định lý trùng bản gốc sau chuẩn hoá khoảng trắng. Kiểm tra dạng văn bản là bảo thủ: có thể đếm thiếu, không đếm thừa.

**Lập lịch và kiểm soát chi phí.** Pool luồng, mỗi worker sở hữu một REPL; hàng đợi FIFO; đo riêng thời gian chờ và thời gian phục vụ. Trước mỗi lần gọi LLM trả phí, chi phí xấu nhất được kiểm với trần tháng/lần chạy; vượt trần → từ chối trước khi gọi. Bộ đệm câu trả lời (khoá = băm toàn bộ yêu cầu) khiến các lần lặp lại không tốn phí.

**Độ phức tạp.** Với *N* ứng viên, *k* lần thử, *W* worker, thời gian kiểm chứng trung bình *v* và độ trễ LLM *ℓ*: thời gian ≈ *T₀* + *N·k̄·(v + p·ℓ)/W*, trong đó *T₀* là thời gian nạp Mathlib song song của worker (một lần), *k̄* ≤ *k* là số lần thử trung bình và *p* là tỷ lệ lần thử đi qua LLM. Bộ nhớ ≈ *W*·3,5 GB (REPL) — giới hạn số worker trên một máy.

# 5. Thiết lập thực nghiệm

**Phần cứng.** Thực nghiệm chạy trên Kaggle CPU notebook (4 vCPU, ~30 GB RAM; thông số chi tiết từng lần chạy ghi trong run record). Máy phát triển (Apple M1, 16 GB) chỉ dùng để phát triển và kiểm thử đơn vị: tại đây kiểm chứng nguội mất 63–107 s/tệp, RSS ~3,5 GB, và hai worker REPL đẩy swap lên >14 GB — lý do chuyển thực nghiệm.

**Phần mềm.** Lean 4.35.0, Mathlib v4.35.0, Lean REPL v4.35.0, Python 3.x, google-genai; phiên bản ghi trong mỗi run record.

**Baseline và chiến lược.** `none` (sàn), `rule_only`, `blind` (thử lại nguyên prompt đúng 1 lần — baseline bắt buộc), `llm_only` (có thông báo lỗi), `hybrid` (router). Mọi chiến lược dùng **cùng tập hold-out, cùng timeout Lean 60 s, cùng phần cứng, cùng seed**.

**Ma trận thí nghiệm.**

| Nhóm | Dữ liệu | Cấu hình | Lặp |
|---|---|---|---|
| RQ1 | hold-out mức 1K (~300) | blind k=1 vs llm_only k=1 | 3 |
| RQ2 | hold-out mức 1K | rule_only k=3; hybrid k∈{1,3}; llm_only k=3; none | 3 |
| RQ3 (chỉ Lean, $0) | mức 100 / 1K / 10K | rule_only k=1 × 1/2/4 worker | 3 |
| RQ3 + LLM | hold-out mức 10K (~3.000) | hybrid k=1, 4 worker | 1 |
| Mô hình mạnh hơn | hold-out mức 1K | llm_only k=1, Gemini 3.6 Flash | 1 |

*Bảng 3. Ma trận thí nghiệm. Lần lặp 2–3 của cấu hình LLM dùng bộ đệm câu trả lời (độ trễ LLM khi đó là độ trễ đệm — nêu ở §7).*

**Chỉ số.** *Chính:* tỷ lệ sửa thành công đã kiểm toán (RQ1/RQ2), thông lượng ổn định (RQ3). *Phụ:* tỷ lệ biên dịch, số lần thử/mẫu, token/thành công, chi phí USD, thời gian phục vụ P50/P95, thời gian chờ hàng đợi P95, bộ nhớ đỉnh. Thông lượng ổn định loại trừ thời gian nạp Mathlib của worker (báo cáo riêng). Kết quả lặp báo cáo **trung vị và khoảng min–max**.

**Tái lập.** Mỗi lần chạy ghi `results/raw/run_<run_id>.json` (commit, phiên bản dữ liệu, máy, phần mềm, tham số, seed, timeout, chỉ số, trạng thái) và log từng mẫu `results/raw/logs/<run_id>.jsonl.gz`. Lệnh tái lập: Phụ lục C.

# 6. Kết quả

## 6.1. Chi phí kiểm chứng: khởi động nguội là nút thắt

| Cách kiểm chứng | Thời gian / định lý | RAM |
|---|---|---|
| `lake env lean` mỗi tệp (nguội) | 63–107 s | ~3,5 GB mỗi lần |
| REPL thường trú (nạp Mathlib 1 lần: ~107 s) | P50 3 ms · P95 23 ms | ~3,5 GB / worker |

*Bảng 4. Đo trên máy phát triển, 50 mẫu.* ⟦Bổ sung số đo nạp Mathlib trên Kaggle từ `worker_startup_ms`⟧

## 6.2. RQ1 – Thông báo lỗi có cấu trúc

⟦Bảng: blind vs llm_only — success %, compile %, tokens/success, cost; trung vị [min–max] — từ table_ablation⟧

## 6.3. RQ2 – Định tuyến và ngân sách thử lại

⟦Hình fig_ablation; hình fig_cost_quality (Pareto); bình luận điểm nằm trên biên⟧

## 6.4. RQ3 – Khả năng mở rộng

⟦Hình fig_scale_throughput, fig_scale_speedup, fig_scale_latency; bảng table_scale; phân tích tăng tốc so với tuyến tính, bộ nhớ đỉnh theo số worker⟧

# 7. Ablation, phân tích lỗi và mối đe doạ tính hợp lệ

**Theo nhóm lỗi.** ⟦Hình fig_category_heatmap: nhóm nào luật đủ, nhóm nào cần LLM⟧

**Phân loại thất bại.** ⟦Thống kê `stop_reason` (budget_exhausted / duplicate / no_rule / wall_budget) và `audit_reasons` (statement_changed, uses_sorry, forbidden_construct) từ log⟧

**Mối đe doạ tính hợp lệ.**
- *Dữ liệu tổng hợp:* đột biến có thể dễ/khó khác lỗi thật; giảm thiểu bằng tập lỗi tự nhiên (trôi phiên bản) và báo cáo tách theo nguồn.
- *Kiểm toán văn bản:* phát biểu tương đương nhưng viết khác bị tính là đổi đề → đếm thiếu thành công.
- *Bộ đệm LLM:* lần lặp 2–3 phản ánh tính tất định của hệ thống ở nhiệt độ 0, không phản ánh biến thiên độ trễ API.
- *Phần cứng chia sẻ:* Kaggle là máy ảo dùng chung; giảm thiểu bằng 3 lần lặp và báo cáo khoảng min–max, chạy cùng ma trận trong cùng phiên.
- *Một họ mô hình:* kết luận về LLM giới hạn ở Gemini Flash; ⟦nếu có: so sánh DeepSeek-Prover-V2-7B⟧.
- *Rò rỉ:* chia theo seed; luật mới (R0, R5–R7) được thiết kế từ lỗi quan sát trên tập 50 mẫu cũ và seed thử nghiệm, không từ hold-out.

# 8. Kết luận và hướng phát triển

⟦Tóm tắt trả lời RQ1–RQ3 bằng số⟧. Hướng phát triển: dùng dữ liệu thật của Nhóm 5; hàng đợi ưu tiên theo nhóm lỗi (lỗi rẻ trước); phân tán worker qua nhiều máy (Redis/RabbitMQ); kiểm toán ngữ nghĩa bằng so sánh kiểu đã elaborate thay cho văn bản; mô hình chuyên Lean mã nguồn mở.

# Tài liệu tham khảo

[1] K. Yang et al., "LeanDojo: Theorem Proving with Retrieval-Augmented Language Models," NeurIPS Datasets and Benchmarks, 2023.
[2] H. Ying et al., "Lean Workbook: A large-scale Lean problem set formalized from natural language math problems," NeurIPS Datasets and Benchmarks, 2024.
[3] Z. Azerbayev et al., "ProofNet: Autoformalizing and Formally Proving Undergraduate-Level Mathematics," arXiv:2302.12433, 2023.
[4] Y. Lin et al., "Goedel-Prover: A Frontier Model for Open-Source Automated Theorem Proving," arXiv:2502.07640, 2025.
[5] E. First, M. Rabe, T. Ringer, Y. Brun, "Baldur: Whole-Proof Generation and Repair with Large Language Models," ESEC/FSE, 2023.
[6] X. Chen, M. Lin, N. Schärli, D. Zhou, "Teaching Large Language Models to Self-Debug," ICLR, 2024.
[7] H. Xin et al., "DeepSeek-Prover-V1.5: Harnessing Proof Assistant Feedback for Reinforcement Learning and Monte-Carlo Tree Search," arXiv:2408.08152, 2024.
[8] Z. Z. Ren et al., "DeepSeek-Prover-V2: Advancing Formal Mathematical Reasoning via Reinforcement Learning for Subgoal Decomposition," arXiv:2504.21801, 2025.
[9] A. Q. Jiang et al., "Draft, Sketch, and Prove: Guiding Formal Theorem Provers with Informal Proofs," ICLR, 2023.
[10] J. Leskovec, A. Rajaraman, J. D. Ullman, *Mining of Massive Datasets*, Cambridge University Press.

# Phụ lục A. Tuyên bố sử dụng AI

⟦Nhúng bảng định lượng và nhật ký từ docs/ai_use_statement.md (sinh bằng scripts/log_ai_use.py)⟧

# Phụ lục B. Phân công và đóng góp

⟦Nhúng từ contributions.md⟧

# Phụ lục C. Lệnh tái lập

```bash
git clone -b feat/verifier-guided-pipeline https://github.com/tamdv/ai4math-verifier-guided-repair.git
cd ai4math-verifier-guided-repair
bash scripts/kaggle_setup.sh                      # Lean 4.35 + Mathlib + REPL, deps, data, tests
python scripts/build_seeds.py --n 3000 --workers 4
python scripts/check_strip_comments.py --workers 4
python scripts/generate_error_dataset.py --workers 4 --max-per-seed 5
python scripts/run_experiment.py --data data/errors/errors_1k.jsonl --split holdout \
    --strategy hybrid --budget 3 --workers 4      # một cấu hình; ma trận đầy đủ: notebooks/kaggle_experiments.ipynb
python scripts/generate_figures.py --input results/raw/ --output results/figures/
```
