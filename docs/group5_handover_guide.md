# Hướng dẫn bàn giao dữ liệu Nhóm 5 sang Nhóm 6

Tài liệu này dành cho Nhóm 5. Nó nói rõ Nhóm 5 cần gửi gì, gửi theo cách nào và sẽ nhận lại gì. Lược đồ đầy đủ nằm ở [data_contract_group5_group6.md](data_contract_group5_group6.md), phiên bản v0.1.

## 1. Cách trao đổi

Hai nhóm trao đổi bằng file theo lô. Nhóm 6 không mở API và Nhóm 5 cũng không cần gọi API nào. Nhóm 5 gửi một file, Nhóm 6 chạy sửa lỗi rồi gửi lại file kết quả.

Kênh gửi là thư mục chung của lớp hoặc một GitHub Release. File lớn hơn 50 MB không đưa vào Git.

## 2. Nhóm 5 cần gửi gì

Một file JSONL hoặc Parquet, mã hóa UTF-8, đặt tên theo mẫu

```
autoformalization_errors_<split>_<timestamp>_<git_commit>.jsonl
```

Từ 1.000 bản ghi trở lên thì nên dùng Parquet. Kèm theo file là một dòng SHA-256 của chính file đó để Nhóm 6 kiểm tra khi tải về.

Mỗi dòng là một ứng viên mã Lean 4 do Nhóm 5 sinh ra. Năm trường bắt buộc:

| Trường | Nội dung |
|:---|:---|
| candidate_id | Khóa duy nhất của ứng viên |
| problem_id | Mã bài toán gốc |
| candidate_code | Toàn bộ file Lean, gồm cả các dòng import |
| statement_natural | Đề bài bằng ngôn ngữ tự nhiên, không được rỗng |
| split | train, validation, test hoặc holdout |

Các trường nên có: source_dataset, generator_metadata, checksum_sha256 của candidate_code, created_at.

Trường compiler_diagnostics không bắt buộc. Nhóm 6 luôn biên dịch lại mọi ứng viên bằng Lean 4.35.0 và Mathlib v4.35.0, nên thông báo lỗi dùng để sửa luôn khớp với bộ kiểm chứng chấm kết quả. Nếu Nhóm 5 dùng phiên bản Lean khác, xin ghi rõ trong generator_metadata.

Nhóm 5 có thể gửi cả ứng viên đã biên dịch được. Nhóm 6 sẽ đánh dấu chúng là ALREADY_VALID và không tốn lượt sửa nào.

File mẫu đúng hợp đồng: [data_sample/group5_input_sample.jsonl](../data_sample/group5_input_sample.jsonl), gồm 14 bản ghi trải đủ sáu nhóm lỗi và một ứng viên đã hợp lệ.

## 3. Nhóm 6 kiểm tra đầu vào thế nào

Bản ghi bị loại và ghi vào rejected.jsonl khi rơi vào một trong ba trường hợp:

* thiếu một trường bắt buộc, lý do missing_fields;
* checksum_sha256 không khớp candidate_code, lý do checksum_mismatch;
* candidate_code trùng hệt một bản ghi trước đó, lý do duplicate_code.

## 4. Nhóm 5 nhận lại gì

Thư mục kết quả gồm ba file.

**feedback_group5.jsonl.** Mỗi bản ghi được chấp nhận có đúng một dòng:

| Trường | Ý nghĩa |
|:---|:---|
| candidate_id, problem_id | Lấy từ đầu vào |
| final_status | SUCCESS, FAILED, ALREADY_VALID hoặc VERIFIER_ERROR |
| error_category | Mã lỗi theo taxonomy v0.2, ví dụ ID_03 hoặc TAC_07 |
| repaired_code | Mã đã sửa, chỉ có khi SUCCESS |
| repair_strategy | rule_repair hoặc llm_repair, chỉ có khi SUCCESS |
| attempts_used, stop_reason | Số lượt thử và lý do dừng |
| last_audit_reasons | Lý do bộ kiểm duyệt từ chối ở lượt cuối, ví dụ statement_changed |
| total_tokens | Số token LLM đã dùng cho ứng viên này |

**repaired_v1.jsonl và repaired_v1.parquet.** Chỉ gồm các bản sửa đã qua Lean và qua bộ kiểm duyệt ngữ nghĩa, theo [output_contract_group6.md](output_contract_group6.md). Đây là dữ liệu gửi tiếp cho Nhóm 7 và Nhóm 8.

**rejected.jsonl.** Các bản ghi bị loại ở bước kiểm tra đầu vào.

Một bản sửa chỉ được tính SUCCESS khi đủ bốn điều kiện: biên dịch được, không dùng sorry, không thêm axiom hay lệnh cấm, và giữ nguyên phát biểu định lý sau khi chuẩn hóa khoảng trắng.

## 5. Lệnh chạy phía Nhóm 6

Chạy thử không tốn tiền, chỉ dùng luật:

```bash
python3 scripts/repair_batch.py --input data_sample/group5_input_sample.jsonl \
    --strategy rule_only --budget 3 --workers 1
```

Chạy thật với LLM, cần GEMINI_API_KEY và đặt trần chi phí cho lô:

```bash
python3 scripts/repair_batch.py --input <file của Nhóm 5> \
    --strategy llm_only --budget 3 --workers 4 --run-cap 1.0
```

Kết quả nằm ở data/group5_out/<tên file đầu vào>. Mỗi lần chạy ghi một bản ghi nguồn gốc vào results/raw/ và nhật ký từng mẫu vào results/raw/logs/.

Lần chạy thử trên file mẫu với rule_only, ngày 19/10/2026: 14 bản ghi được chấp nhận, 4 SUCCESS nhờ luật R0 và R7, 9 FAILED, 1 ALREADY_VALID, chi phí 0 USD. Các lỗi còn lại cần LLM, khớp với độ chính xác luật đã đo trong báo cáo.

## 6. Ước tính chi phí và thời gian

Theo số đo trên tập hold-out 1K, cấu hình llm_only với k bằng 3 sửa được 65,1% ứng viên lỗi, tốn khoảng 2,45 USD cho mỗi 1.000 ứng viên. Với 4 worker trên CPU Kaggle, thông lượng khoảng 2,9 mẫu mỗi giây ở bước kiểm chứng. Nhóm 6 sẽ báo ước tính trước khi chạy mọi lô có dùng LLM.

## 7. Liên hệ

Đầu mối Nhóm 6: Đào Văn Tâm. Khi thay đổi lược đồ, hai nhóm tăng số phiên bản hợp đồng và cập nhật file mẫu.
