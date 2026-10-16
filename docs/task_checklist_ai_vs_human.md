# Checklist công việc: AI làm được / Chỉ người làm được

**Nhóm 6 — Verifier-Guided Repair** · cập nhật 2026-10-15

Cách đọc:
- **🤖 AI làm** — AI (Claude Code, Cursor…) viết được code/tài liệu. **Bắt buộc** có một thành viên chạy lại, đọc hiểu, ghi `--auditor` trong `docs/ai_use_log.jsonl` (Rule 5). Người kiểm ghi ở cột *Người duyệt*.
- **👤 Chỉ người làm** — cần quyết định, quan hệ với người khác, tài khoản/tiền, phán đoán học thuật, hoặc trách nhiệm cá nhân khi bảo vệ.

> Nguyên tắc từ *Hướng dẫn BTL*: "Việc sử dụng AI phải được khai báo; mọi code và kết luận do AI hỗ trợ vẫn phải được nhóm kiểm chứng." Mỗi thành viên phải tự giải thích được phần AI viết trong mảng của mình.

---

## 0. Trạng thái nền tảng (đã có)

- [x] 🤖 Lean 4 Verifier wrapper `src/lean_verifier.py` + 9 test — *Người duyệt: Dũng*
- [x] 🤖 Chế độ `--verify` cho `scripts/run_rule_experiment.py` (compile rate thật: **20%**, không phải 48%) — *Người duyệt: Trung*
- [ ] 🤖 Lake workspace có Mathlib (`lean_ws/`, không commit) — *đang làm*

---

## 1. Dữ liệu lỗi & Data Contract (Nounou, Khamsing)

| | Việc | Người duyệt |
|---|---|---|
| 🤖 | Script sinh lại `compiler_log` cho 50 mẫu bằng Lean thật (16/50 mẫu hiện **không lỗi**) | Nounou |
| 🤖 | Script tạo lỗi tự động (mutation: xoá ngoặc, bỏ import, đổi tên lemma…) từ định lý mathlib/ProofNet để có 1K → 10K mẫu | Nounou |
| 🤖 | Dedup SHA-256, cập nhật `manifest.json` + checksum, chia train/holdout 70/30 cố định theo seed | Khamsing |
| 🤖 | Script xuất Parquet cho Nhóm 7 (`scripts/export_to_group7.py`) | Nounou |
| 👤 | **Liên hệ Nhóm 5** lấy candidate lỗi thật, chốt Data Contract v1.0 (schema, tần suất, định dạng) | Nounou |
| 👤 | **Thống nhất với Nhóm 7/8** định dạng bàn giao | Nounou |
| 👤 | Quyết định: giữ, sửa hay bỏ 16 mẫu "không lỗi"; cách trình bày trung thực con số 48% cũ trong báo cáo | Cả nhóm |
| 👤 | Kiểm tra giấy phép dữ liệu (ProofNet MIT, NuminaMath Apache-2.0) và ghi vào data card | Nounou |
| 👤 | Đọc tay mẫu ngẫu nhiên ~30 lỗi sinh tự động xem có "giống lỗi thật" không | Khamsing |

## 2. Parser, Taxonomy & Router (Khamsing)

| | Việc | Người duyệt |
|---|---|---|
| 🤖 | Parser đọc trực tiếp output `lean --json` (thay cho log viết tay) | Khamsing |
| 🤖 | `src/error_router.py` + test: định tuyến Rule / LLM theo taxonomy | Khamsing |
| 🤖 | Script đo Parser Accuracy trên tập đã gán nhãn | Khamsing |
| 👤 | Gán nhãn tay (ground truth) cho tập đo accuracy; xử lý các lỗi mơ hồ giữa 2 nhóm | Khamsing + 1 người |
| 👤 | Quyết định sửa taxonomy v0.1 → v1.0 (gộp/tách nhóm lỗi) | Khamsing, Tâm |

## 3. Rule-based Repair (Trung)

| | Việc | Người duyệt |
|---|---|---|
| 🤖 | Sửa các rule thất bại khi verify thật (ERR-001, 002, 008, 019, 023, 024) + thêm test hồi quy | Trung |
| 🤖 | Báo cáo Rule Coverage theo `compile_rate`, không theo `rule_hit_rate` | Trung |
| 👤 | Quyết định rule nào có nguy cơ **đổi nghĩa đề** (vd. đổi `sqrt` → `Real.sqrt`) và loại bỏ | Trung, Tâm |

## 4. LLM Repair (Tùng)

| | Việc | Người duyệt |
|---|---|---|
| 🤖 | `src/llm_repair.py`: client Ollama/vLLM/API, đếm token, retry, timeout | Tùng |
| 🤖 | Prompt templates có/không có diagnostic (`configs/prompts/*.yaml`) | Tùng |
| 🤖 | Baseline thật "blind retry" (thay bản giả lập `random < 0.18`) | Tùng |
| 🤖 | Mock LLM test suite (không tốn token) | Tùng |
| 👤 | **Chọn model** (Qwen/DeepSeek local hay API), **cấp API key / máy GPU**, chốt **ngân sách tiền/token** | Tùng, Tâm |
| 👤 | Đọc tay ~20 bản sửa của LLM để phát hiện kiểu "cheat" mới | Tùng |

## 5. Queue, Worker Pool & Bounded Retry (Dũng)

| | Việc | Người duyệt |
|---|---|---|
| 🤖 | Worker pool đa tiến trình gọi `LeanVerifier`, đo queue latency | Dũng |
| 🤖 | Redis queue (FIFO vs Priority), bounded retry controller, dedup task | Dũng |
| 🤖 | Cập nhật `Dockerfile` (đang ghim Lean v4.8.0, lệch với máy) + docker-compose có Redis | Dũng |
| 🤖 | Test khôi phục khi worker chết giữa chừng | Dũng |
| 👤 | **Chuẩn bị máy chạy Tier 3** (4–8 worker, RAM đủ cho Mathlib ~ 4–8 GB/worker) | Dũng, Tâm |
| 👤 | Chọn tham số: số worker, retry budget, timeout cuối cùng | Dũng, Tâm |

## 6. Semantic Audit & Đánh giá (Tâm)

| | Việc | Người duyệt |
|---|---|---|
| 🤖 | `src/semantic_auditor.py`: so sánh chữ ký định lý trước/sau, cấm `sorry`/`axiom`/`native_decide`/`admit` | Tâm |
| 🤖 | `scripts/run_experiment.py` + `configs/exp_scale.yaml` (3 tier × 2 cấu hình worker), ghi provenance đủ Rule 3 (psutil, git hash, version) | Tâm |
| 🤖 | `scripts/generate_figures.py`: P50/P95, throughput, Pareto token–success, ablation | Tâm |
| 👤 | **Bấm chạy và giám sát** benchmark thật; xác nhận số liệu không bị chỉnh tay | Tâm, Dũng |
| 👤 | Đánh giá tay mẫu nghi vấn mà auditor không chắc (có đổi đề không?) | Tâm + 1 người |
| 👤 | Diễn giải kết quả, trả lời RQ1/RQ2, chọn kết luận | Cả nhóm |

## 7. Báo cáo, Slide & Bảo vệ

| | Việc | Người duyệt |
|---|---|---|
| 🤖 | Dàn ý theo Phụ lục C, bảng/hình sinh từ `results/raw/` | Tâm |
| 🤖 | Bản nháp phần Phương pháp, Thiết lập thí nghiệm, Data/System card | Người phụ trách mảng |
| 🤖 | Tổng hợp AI-use statement định lượng (`docs/ai_use_statement.md`) | Tâm |
| 🤖 | Nháp slide và kịch bản demo | Tâm |
| 👤 | **Viết lại bằng giọng nhóm**, kiểm tra từng con số khớp raw results, chịu trách nhiệm học thuật | Cả nhóm |
| 👤 | Phần Thảo luận, Hạn chế, Kết luận (nhận định của nhóm) | Tâm |
| 👤 | **Ký xác nhận AI-use statement** | Cả nhóm |
| 👤 | **Luyện demo live, thuyết trình, bảo vệ vấn đáp cá nhân** — mỗi người phải giải thích được toàn pipeline | Từng người |
| 👤 | Nộp bài, trao đổi với giảng viên | Tâm |

## 8. Quản lý nhóm & Git (mọi người)

| | Việc | Người duyệt |
|---|---|---|
| 🤖 | Sửa link tuyệt đối `/Users/...` trong `contributions.md`, cập nhật README/lệnh chạy | Tâm |
| 🤖 | Thêm `pytest`, `ruff` vào môi trường, CI chạy test | Tâm |
| 👤 | **Mỗi người tự commit/PR trên nhánh của mình** (bằng chứng đóng góp cá nhân) | Từng người |
| 👤 | Review và merge PR vào `main` | Tâm |
| 👤 | Phân công lại khi có người chậm tiến độ | Tâm |

---

### Tóm tắt nhanh

- **AI gánh được phần lớn code, script, test, nháp tài liệu** — với điều kiện có người chạy lại và đọc hiểu.
- **Người bắt buộc làm:** liên lạc Nhóm 5/7/8 và giảng viên · chọn model, cấp API key, máy và ngân sách · gán nhãn và đánh giá tay · quyết định khoa học và cách trình bày trung thực · review/merge · ký AI-use · thuyết trình và bảo vệ cá nhân.
