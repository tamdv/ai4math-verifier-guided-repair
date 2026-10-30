"""5-minute deck -> slides/Slides_Nhom6_RutGon_5Phut.pptx (same design as the full deck).

9 main slides follow slides/short_talk_content.py (speech becomes the speaker notes); the last main slide routes
questions to members. Backup slides P1-P7 come after it so each member can open evidence while answering.
Run:  python slides/build_slides_short.py   then   ./slides/to_pdf.sh Slides_Nhom6_RutGon_5Phut.pptx
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_slides as B  # noqa: E402
from build_slides import (BLUE, BLUE_DARK, FIG, MSO_SHAPE, MUTED, PP_ALIGN, TINT, TINT2, Deck, card, flow,  # noqa: E402
                          image, mini_stat, shape, stat, table, text)
from short_talk_content import QA, SLIDES  # noqa: E402

OUT = B.ROOT / "slides" / "Slides_Nhom6_RutGon_5Phut.pptx"


def notes(i: int) -> str:
    return "Tâm: " + " ".join(SLIDES[i]["speech"])


def main_slides(d: Deck) -> None:
    # 1 cover
    s = d.new("", notes=notes(0), cover=True)
    text(s, 0.8, 1.0, 8.4, 0.5, "DỮ LIỆU LỚN, INT4418 · NHÓM 6", size=20, bold=True, color=BLUE, name="!!title")
    text(s, 0.8, 1.7, 8.6, 2.8, [[("Verifier-Guided Repair", {"size": 44, "bold": True})],
                                 [("Sửa chứng minh Lean 4 có kiểm chứng dưới ràng buộc chi phí và độ trễ",
                                   {"size": 28, "color": BLUE_DARK})]], line=1.05)
    text(s, 0.8, 4.55, 8.6, 2.1, ["Giảng viên: TS. Nguyễn Kiều Linh",
                                  "Đào Văn Tâm · Trần Quang Đức Dũng · Lâm Thành Trung",
                                  "Nguyễn Xuân Tùng · Khamsing OUTHAIHUENG · Mekdala Nounou"], size=20, color=MUTED)

    # 2 topic
    s = d.new("Đề tài: tự động sửa chứng minh Lean bị lỗi, chỉ nhận bản sửa đã kiểm chứng", notes=notes(1))
    flow(s, 1.95, ["Nhóm 5\nứng viên Lean", "Nhóm 6\nphân loại + sửa", "Lean\nkiểm chứng", "Nhóm 7 / 8\nchứng minh đúng"],
         w=2.55, gap=0.55, fills={1: TINT2})
    stat(s, 0.8, 3.85, 3.8, "63–107 s", "kiểm chứng nguội 1 tệp, nạp Mathlib")
    stat(s, 4.95, 3.85, 3.8, "10.000", "ứng viên ở mức lớn nhất")
    stat(s, 9.1, 3.85, 3.6, "~1.000", "token mỗi lần LLM sửa", color=BLUE_DARK)

    # 3 what we did
    s = d.new("Nhóm đã làm gì: dữ liệu, vòng sửa có kiểm toán, kiểm chứng nhanh, kiểm soát chi phí", notes=notes(2))
    cards = [("Dữ liệu", ["17.031 mẫu lỗi", "Nhãn từ Lean"]),
             ("Vòng sửa", ["Luật hoặc LLM", "Kiểm toán, ≤ 3 lần"]),
             ("Kiểm chứng", ["Lean chạy liên tục", "Nhiều worker"]),
             ("Chi phí", ["Trần 8 USD/tháng", "Ghi mọi lần chạy"])]
    for i, (head, body) in enumerate(cards):
        card(s, 0.6 + i * 3.05, 1.95, 2.9, 3.4, head, body, fill=TINT2 if i % 2 else TINT, size=20)
    text(s, 0.6, 5.75, 12.1, 0.8, [[("Thực nghiệm: ", {"bold": True, "color": BLUE_DARK}),
                                    ("Kaggle 4 vCPU · 100 / 1K / 10K mẫu · lặp 3 lần · Gemini 3.5 Flash-Lite", {})]],
         size=20)

    # 4 RQ1
    s = d.new("RQ1: thông báo lỗi tăng 22 điểm % và còn rẻ hơn 45%", notes=notes(3))
    image(s, FIG / "fig_rq1_category_slide.png", 0.5, 1.95, w=8.4)
    mini_stat(s, 9.2, 1.9, "53,9%", "thành công k=1, baseline 31,7%", color=BLUE_DARK)
    mini_stat(s, 9.2, 3.5, "$1,13", "mỗi 1.000 mẫu, baseline $2,05")

    # 5 RQ2
    s = d.new("RQ2: LLM thử 3 lần đạt 65,1%; luật chỉ tốt với lỗi đơn giản", notes=notes(4))
    image(s, FIG / "fig_cost_quality_slide.png", 0.5, 1.85, w=8.4)
    mini_stat(s, 9.2, 1.9, "65,1%", "LLM k=3, $2,45 / 1K mẫu", color=BLUE_DARK)
    mini_stat(s, 9.2, 3.5, "97–100%", "luật với thiếu import, timeout")
    mini_stat(s, 9.2, 5.1, "23,9%", "chỉ dùng luật, $0", color=MUTED)

    # 6 RQ3
    s = d.new("RQ3: REPL nhanh 3–4 bậc; 4 worker chỉ nhanh 1,88× vì nghẽn CPU", notes=notes(5))
    image(s, FIG / "fig_scale_speedup_slide.png", 0.5, 1.8, w=6.3)
    mini_stat(s, 7.2, 1.9, "3 ms · 23 ms", "P50 · P95 với REPL, nguội 63–107 s", color=BLUE_DARK)
    mini_stat(s, 7.2, 3.5, "1,52 → 2,86", "mẫu/s ở 10K, từ 1 lên 4 worker")
    mini_stat(s, 7.2, 5.1, "1,76× · 1,88×", "tăng tốc với 2 · 4 worker", color=BLUE_DARK)

    # 7 audit
    s = d.new("Kiểm toán là bắt buộc: không có nó, tỷ lệ thành công bị thổi phồng", notes=notes(6))
    stat(s, 0.8, 2.0, 3.8, "75,0%", "Lean chấp nhận, LLM k=3", color=MUTED)
    stat(s, 4.8, 2.0, 3.8, "65,1%", "thành công thật sau kiểm toán", color=BLUE_DARK)
    stat(s, 8.8, 2.0, 3.9, "17–26%", "bản sửa thất bại đã đổi đề")
    card(s, 0.8, 4.35, 11.9, 2.15, "Kiểm toán chặn", ["sorry, admit, axiom, native_decide",
                                                      "Thay đổi tên, giả thiết hoặc kết luận của định lý"])

    # 8 conclusion
    s = d.new("Kết luận: chẩn đoán, kiểm toán, REPL thường trú; sẵn sàng nhận dữ liệu Nhóm 5", notes=notes(7))
    card(s, 0.6, 1.9, 7.4, 4.6, "Ba bài học", ["Thông báo lỗi: tốt hơn và rẻ hơn",
                                                "Kiểm toán ngữ nghĩa là bắt buộc",
                                                "Kiểm chứng cần chạy liên tục, lập lịch"])
    stat(s, 8.5, 1.95, 4.2, "$2,97", "toàn bộ thực nghiệm", color=BLUE_DARK)
    stat(s, 8.5, 4.05, 4.2, "6 / 6", "tiêu chí nghiệm thu")

    # 9 Q&A routing
    s = d.new("Cảm ơn cô và các bạn · Hỏi đáp", notes=notes(8))
    table(s, 0.6, 1.85, 12.1, [["Thành viên", "Mảng trả lời", "Slide dự phòng"]] + [list(r) for r in QA],
          [4.0, 5.6, 2.5], size=20)


def backup_slides(d: Deck) -> None:
    s = d.new("Dự phòng P1 · Demo: lỗi → phân loại → sửa → Lean kiểm tra → kiểm toán",
              notes="Tùng: phát lại log, $0. Lệnh trong slides/demo_script.md.")
    card(s, 0.6, 1.9, 3.9, 4.6, "E000880 · luật", ["Thiếu import Mathlib", "R0 sửa, Lean OK", "0 token · 73 ms"])
    card(s, 4.75, 1.9, 3.9, 4.6, "E000003 · LLM", ["Lần 1: dùng sorry → bị chặn", "Lần 2: không biên dịch",
                                                    "Lần 3: đúng · 4.583 token"], fill=TINT2)
    card(s, 8.9, 1.9, 3.9, 4.6, "E000197 · vòng lặp", ["Chứng minh là sorry", "Lần 1 sai, lần 2 đúng", "779 token"])

    s = d.new("Dự phòng P2 · Dataset 17.031 lỗi có nhãn lấy từ chính Lean",
              notes="Nounou: nguồn MIT, 3.666 định lý gốc, 9 cách gây lỗi, chia theo định lý gốc, hold-out 284 và 2.907.")
    stat(s, 0.8, 1.95, 2.9, "17.031", "mẫu lỗi, dataset v1.0")
    stat(s, 3.85, 1.95, 2.9, "3.666", "định lý gốc đã kiểm chứng")
    stat(s, 6.9, 1.95, 2.9, "1.110", "lỗi tự nhiên do Mathlib đổi")
    stat(s, 9.95, 1.95, 2.9, "94,4%", "nhãn khớp loại lỗi dự kiến", color=BLUE_DARK)
    card(s, 0.6, 4.3, 3.9, 2.3, "Chống rò rỉ", ["Chia theo định lý gốc", "0 trùng giữa hai phía"])
    card(s, 4.75, 4.3, 3.9, 2.3, "Ba mức quy mô", ["100 ⊂ 1K ⊂ 10K mẫu", "Hold-out: 284 · 2.907"], fill=TINT2)
    card(s, 8.9, 4.3, 3.8, 2.3, "Provenance", ["Nguồn MIT, checksum", "Run record mỗi lần"])

    s = d.new("Dự phòng P3 · Kiến trúc: mỗi bản sửa qua Lean và kiểm toán",
              notes="Khamsing: phân loại 7 nhóm lỗi, router, luật hoặc LLM, Lean REPL, kiểm toán; vòng lặp tối đa k lần.")
    flow(s, 2.05, ["Parser +\ntaxonomy", "Router", "Luật / LLM", "Lean REPL", "Kiểm toán"], w=2.0, gap=0.5,
         fills={4: TINT2})
    card(s, 0.6, 3.75, 3.9, 2.75, "7 nhóm lỗi", ["Cú pháp, import, định danh", "Kiểu, timeout, sorry",
                                                 "Tactic thất bại"])
    card(s, 4.75, 3.75, 3.9, 2.75, "Vòng lặp có giới hạn", ["Tối đa k = 1 hoặc 3 lần", "300 s mỗi mẫu",
                                                             "Dừng nếu ứng viên lặp"])
    card(s, 8.9, 3.75, 3.8, 2.75, "Kiểm toán", ["Lean chấp nhận", "Không sorry / axiom", "Giữ nguyên phát biểu"],
         fill=TINT2)

    s = d.new("Dự phòng P4 · Luật đúng gần hoàn hảo, luật sai kéo chiến lược lai xuống",
              notes="Trung: R0 97%, R7 100%, R1 27%, R2 và R3 0%; 203/284 mẫu sang luật, đúng 33%; ablation bộ phân loại.")
    table(s, 0.6, 1.95, 6.9, [["Luật", "Áp dụng", "Chính xác"],
                              ["R0 khôi phục import", "99", "97%"], ["R7 ngân sách heartbeat", "81", "100%"],
                              ["R1 cân bằng ngoặc", "99", "27%"], ["R3 bảng import", "253", "0%"],
                              ["R2 chèn từ khoá", "126", "0%"]], [3.5, 1.5, 1.9], size=20)
    card(s, 7.8, 1.95, 4.9, 4.6, "Ablation bộ phân loại", ["Khớp nhãn 72,3% → 96,3%", "Token giảm 31%",
                                                           "Lai k=1 lại giảm 34,9% → 30,3%",
                                                           "Nút thắt: độ chính xác của luật"], fill=TINT2)

    s = d.new("Dự phòng P5 · Thiết lập: cùng dữ liệu, phần cứng và seed, chỉ đổi chiến lược",
              notes="Tâm: Kaggle 4 vCPU 31 GB; baseline thử lại nguyên prompt; k 0/1/3; 3 mức; 1/2/4 worker; 3 lần lặp.")
    card(s, 0.6, 1.9, 3.9, 3.5, "Chiến lược", ["Không sửa · chỉ luật", "Blind là baseline", "LLM + chẩn đoán · lai"])
    card(s, 4.75, 1.9, 3.9, 3.5, "Ma trận", ["k = 0 / 1 / 3", "100 / 1K / 10K mẫu", "1 / 2 / 4 worker · 3 lần"])
    card(s, 8.9, 1.9, 3.9, 3.5, "Môi trường", ["Kaggle 4 vCPU, 31 GB", "Lean 4.35 + Mathlib", "Gemini Flash-Lite"],
         fill=TINT2)
    text(s, 0.6, 5.7, 12.1, 0.8, [[("Tổng chi phí API cho toàn bộ thực nghiệm: ", {"bold": True, "color": BLUE_DARK}),
                                   ("$2,97", {"bold": True})]], size=22)

    s = d.new("Dự phòng P6 · Ablation: biên dịch và thành công đã kiểm toán",
              notes="Tâm: khoảng chênh giữa cột xanh và cột cam là phần kiểm toán chặn.")
    image(s, FIG / "fig_ablation_slide.png", 0.55, 1.75, w=12.2)

    s = d.new("Dự phòng P7 · Độ trễ phục vụ P50 và P95 ở 3 mức dữ liệu",
              notes="Dũng: P50 và P95 ở 100, 1K, 10K với 1, 2, 4 worker; trung vị và min đến max của 3 lần lặp.")
    image(s, FIG / "fig_scale_latency_slide.png", 1.4, 1.75, h=5.2)


def build() -> int:
    B.TALK = []  # full-talk notes must not leak into this deck
    B.OUT = OUT
    d = Deck()
    main_slides(d)
    backup_slides(d)
    d.save()
    OUT.with_suffix(".generated.sha256").write_text(B._sha(OUT))  # lets the next build overwrite safely
    return d.n


if __name__ == "__main__":
    print(OUT, build(), "slides")
