# ERROR TAXONOMY v0.2 - PHÂN LOẠI LỖI LEAN 4 & CHIẾN LƯỢC SỬA
### DỰ ÁN AI4MATH - NHÓM 6: VERIFIER-GUIDED REPAIR

*Cập nhật 2026-10-16, duyệt bởi Đào Văn Tâm. Thay thế [v0.1](error_taxonomy_v0.1.md).*

---

## 1. Thay đổi so với v0.1

| Thay đổi | Lý do (bằng chứng) |
|---|---|
| **Thêm `TAC_07` – TACTIC_FAILURE** | Khi kiểm chứng bằng Lean 4.35 thật, nhóm lỗi phổ biến nhất là tactic không đóng được mục tiêu (`unsolved goals`, `linarith failed`, `omega could not prove`). v0.1 không có nhóm này nên parser trả `UNK_99` cho 13/50 mẫu. |
| Dấu hiệu nhận biết lấy từ **thông báo thật** của Lean 4.35 + Mathlib | Nhãn v0.1 viết tay; chỉ 15/50 khớp với Lean thật (xem `data_sample/error_dataset_50_lean.summary.json`). |
| `IMP_02` nhận diện thêm từ ngữ cảnh code | Thiếu `import Mathlib` không sinh lỗi "missing import" mà sinh `Unknown identifier` / `unexpected token` ở ký hiệu Mathlib (ℝ, `nlinarith`…). Parser kiểm tra: code không có `import` + dùng tên Mathlib → `IMP_02`. |
| `SEM_06` gắn với cảnh báo `sorry` + Semantic Auditor | Lean chấp nhận file có `sorry` (chỉ cảnh báo); auditor là nơi duy nhất chặn được. |

---

## 2. Bảng phân loại 7 nhóm lỗi

| Mã | Tên | Dấu hiệu trong Lean 4.35 (ví dụ thật) | Định tuyến | Rule hiện có |
|:---|:---|:---|:---:|:---|
| `SYN_01` | SYNTAX_ERROR | `unexpected token 'in'; expected ','` · `unexpected end of input; expected ':='` | Rule | R1 ngoặc, R2 từ khóa, R6 cú pháp `∑ x in` → `∑ x ∈` |
| `IMP_02` | MISSING_IMPORT | `unknown module prefix 'Mathlib'` · `object file ... of module X does not exist` · *code không import nhưng dùng ℝ/`nlinarith`* | Rule | R0 thêm `import Mathlib`, R3 bảng import |
| `ID_03` | UNKNOWN_IDENTIFIER | ``Unknown identifier `le_div_iff` `` · ``Unknown constant `Nat.add_com` `` · ``Invalid field `len` `` · `unknown tactic` | Hybrid | R4 alias, R5 đổi tên Mathlib (`le_div_iff` → `le_div_iff₀`…) |
| `TYP_04` | TYPE_MISMATCH | `type mismatch` · `failed to synthesize instance HAdd Real Float Real` · `Invalid field notation` | LLM | — |
| `TMO_05` | TIMEOUT_EXCEEDED | `(deterministic) timeout at whnf, maximum number of heartbeats (400000)` | System control | R7 khôi phục ngân sách heartbeats |
| `SEM_06` | SEMANTIC_MISMATCH | ``declaration uses `sorry` `` · compile được nhưng đổi phát biểu | Semantic audit | — (không được "sửa" bằng cách đổi đề) |
| **`TAC_07`** | **TACTIC_FAILURE** | `unsolved goals` · `linarith failed to find a contradiction` · `omega could not prove the goal` · ``Tactic `decide` proved that the proposition ... is false`` | LLM | — |
| `UNK_99` | UNKNOWN | Không khớp mẫu nào | LLM | — |

Thứ tự so khớp trong parser (lỗi đầu tiên khớp sẽ thắng): `TMO_05` → `IMP_02` → `SYN_01` → `ID_03` → `TYP_04` → `TAC_07` → `SEM_06`. Cài đặt: [src/error_parser.py](../src/error_parser.py); kiểm thử bằng thông báo thật: `tests/test_error_parser.py::TestRealLeanMessages`.

---

## 3. Toán tử sinh lỗi tương ứng (dataset tổng hợp)

| Toán tử | Nhóm dự kiến | Cách gây lỗi |
|---|---|---|
| `syn_drop_paren`, `syn_drop_assign` | SYN_01 | Xoá một `)` trong phát biểu; xoá `:=` |
| `imp_drop_import` | IMP_02 | Xoá toàn bộ dòng `import` |
| `id_lemma_typo`, `id_tactic_typo` | ID_03 | Xoá 1 ký tự trong tên lemma; viết sai tên tactic |
| `typ_change_type` | TYP_04 | Đổi kiểu một biến ℝ ↔ ℕ trong phát biểu |
| `tac_weaken` | TAC_07 | Thay tactic mạnh bằng tactic yếu (`nlinarith [...]` → `linarith`) |
| `tmo_low_heartbeats` | TMO_05 | Hạ `maxHeartbeats` xuống 500 |
| `sem_sorry` | SEM_06 | Thay toàn bộ chứng minh bằng `sorry` |

Nhãn cuối cùng **luôn lấy từ thông báo Lean thật** qua parser, không lấy từ toán tử; bảng nhầm lẫn "dự kiến → thật" được ghi trong run record của bước sinh dữ liệu. Ngoài ra còn tập **lỗi tự nhiên**: chứng minh cũ không còn biên dịch với Mathlib hiện tại (đổi tên lemma, cú pháp cũ).

---

## 4. Tiêu chí an toàn ngữ nghĩa (đã cài đặt)

Một bản sửa chỉ được tính là **thành công** khi qua cả 4 kiểm tra ([src/semantic_auditor.py](../src/semantic_auditor.py)):
1. Lean biên dịch không lỗi.
2. Không khai báo nào dùng `sorry`.
3. Không có `sorry`, `admit`, `axiom`, `native_decide`, `implemented_by`, `unsafe` trong mã (bỏ qua comment).
4. Phát biểu định lý (tên, giả thiết, kết luận) **giống hệt** bản gốc sau khi chuẩn hóa khoảng trắng.

Giới hạn: kiểm tra (4) dựa trên văn bản nên một phát biểu tương đương nhưng viết khác sẽ bị coi là "đổi đề". Cách này bảo thủ: có thể đếm thiếu thành công, nhưng không bao giờ đếm thừa.
