"""Build slides/KichBan_RutGon_5Phut_Nhom6.docx: a 5-minute single-speaker version of the talk.

Three parts: what the project is, what the team did, results. Uses the same deck (slide cues in grey).
Timing uses the same syllable count as build_talk_script.py (160 syllables per minute).
Run:  python slides/build_short_script.py
"""
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_talk_script import ACCENT, GREY, heading, mmss, para, run, seconds, setup, syllables, table  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "slides" / "KichBan_RutGon_5Phut_Nhom6.docx"

# (part, slides to show, paragraphs)
PARTS = [
    ("Mở đầu", "Slide 1", [
        "Em chào cô và các bạn. Em là Đào Văn Tâm, đại diện Nhóm 6. Đề tài của nhóm là Verifier-Guided Repair: tự động "
        "sửa các chứng minh toán học viết bằng Lean bị lỗi, trong giới hạn chi phí và thời gian.",
    ]),
    ("Đề tài là gì", "Slide 2, rồi slide 4", [
        "Lean là ngôn ngữ viết chứng minh toán học để máy tính kiểm tra được từng bước. Mô hình ngôn ngữ lớn, gọi tắt là "
        "LLM, viết được hàng loạt chứng minh Lean, nhưng nhiều chứng minh bị Lean từ chối, có khi chỉ vì thiếu một dòng "
        "khai báo thư viện. Trong chuỗi dự án của lớp, Nhóm 5 sinh chứng minh, Nhóm 6 sửa các chứng minh lỗi, và chỉ nhận "
        "bản sửa khi Lean chấp nhận và đề bài giữ nguyên. Đây là bài toán dữ liệu lớn vì mỗi lần Lean kiểm tra từ đầu mất "
        "hơn một phút, số chứng minh lên tới hàng chục nghìn, và mỗi lần gọi LLM đều tốn tiền.",
    ]),
    ("Nhóm đã làm gì", "Slide 3, 5, 6, rồi slide 8", [
        "Nhóm làm bốn việc. Thứ nhất, tạo tập 17.031 chứng minh lỗi, nhãn lỗi lấy từ chính thông báo của Lean, và tách riêng "
        "tập kiểm tra để không lộ đáp án. Thứ hai, xây vòng sửa lỗi: đọc thông báo lỗi và xếp vào bảy nhóm; sửa bằng luật "
        "viết sẵn không tốn tiền, hoặc nhờ LLM sửa kèm thông báo lỗi; cho Lean kiểm tra lại; rồi kiểm toán để chặn bản sửa "
        "gian lận như bỏ qua chứng minh hay đổi đề. Mỗi mẫu được thử tối đa ba lần. Thứ ba, giữ Lean chạy liên tục và chạy "
        "nhiều bản song song để kiểm tra nhanh. Thứ tư, đặt trần chi phí cho LLM và ghi lại mọi lần chạy để tái lập được. "
        "Thực nghiệm chạy trên Kaggle với ba mức 100, 1.000 và 10.000 mẫu, mỗi cấu hình lặp ba lần, dùng Gemini 3.5 Flash-Lite.",
    ]),
    ("Kết quả", "Slide 9, 10, 11, 13", [
        "Về kết quả. Câu hỏi thứ nhất: gửi kèm thông báo lỗi có giúp không. Có. So với chỉ yêu cầu thử lại, tỷ lệ sửa thành "
        "công tăng từ 31,7% lên 53,9%, và chi phí giảm 45%, vì mô hình chỉ sửa đúng chỗ hỏng thay vì viết lại cả tệp.",
        "Câu hỏi thứ hai: nên thử mấy lần và sửa bằng cách nào. Cho LLM thử tối đa ba lần đạt 65,1%, tốn 2,45 đô la Mỹ cho "
        "1.000 mẫu. Luật viết sẵn đúng 97 đến 100% với lỗi thiếu khai báo thư viện và lỗi vượt giới hạn tính toán, nhưng kém "
        "với các lỗi còn lại.",
        "Câu hỏi thứ ba: hệ thống mở rộng ra sao. Giữ Lean chạy liên tục làm thời gian kiểm tra một chứng minh giảm từ 63 đến "
        "107 giây xuống khoảng 3 mili giây. Với 10.000 mẫu, 2 tiến trình nhanh gấp 1,76 lần, nhưng 4 tiến trình chỉ nhanh "
        "1,88 lần, vì máy chỉ có 4 nhân CPU.",
        "Bước kiểm toán là bắt buộc: với ba lần thử, 75% bản sửa được Lean chấp nhận, nhưng chỉ 65,1% là sửa thật, phần còn "
        "lại đổi đề hoặc bỏ qua chứng minh.",
    ]),
    ("Kết luận", "Slide 14, rồi slide 15", [
        "Tóm lại, gửi thông báo lỗi giúp sửa tốt hơn và rẻ hơn, kiểm toán là bắt buộc, và trình kiểm chứng cần chạy liên "
        "tục, được lập lịch. Toàn bộ thực nghiệm tốn 2,97 đô la Mỹ, và hệ thống đã sẵn sàng nhận dữ liệu thật từ Nhóm 5. "
        "Em xin cảm ơn cô và các bạn.",
    ]),
]

SKIP = "Bỏ qua khi trình bày bản rút gọn: slide 7 demo, slide 12 phân tích luật, hai slide phụ lục."


def main() -> None:
    timing, clock = [], 0
    for part, slides, paras in PARTS:
        sec = seconds(sum(syllables(p) for p in paras))
        clock += sec
        timing.append((part, slides, sec, clock))

    doc = Document()
    setup(doc)
    para(doc, "Kịch bản rút gọn 5 phút: Nhóm 6", bold=True, color=ACCENT, size=20, align=WD_ALIGN_PARAGRAPH.CENTER)
    para(doc, "Verifier-Guided Repair · Môn INT4418 Dữ liệu lớn · Người trình bày: Đào Văn Tâm",
         align=WD_ALIGN_PARAGRAPH.CENTER)
    para(doc, f"Lời nói khoảng {mmss(clock)} ở tốc độ 160 tiếng mỗi phút; cộng thời gian chuyển slide và ngắt nghỉ là "
              "khoảng 5 phút. Dùng cùng bộ slide với bản đầy đủ. Chữ xám là chỉ dẫn, không đọc thành tiếng. "
              f"{SKIP}", italic=True, color=GREY, size=11)
    rows = [["Phần", "Slide mở", "Thời lượng", "Mốc"]] + [[p, s, mmss(t), mmss(c)] for p, s, t, c in timing]
    table(doc, rows, [4.2, 6.4, 3.0, 3.0])
    for (part, slides, paras), (_, _, sec, clock_at) in zip(PARTS, timing):
        heading(doc, f"{part} · {mmss(sec)} · mốc {mmss(clock_at)}", 2)
        p = para(doc)
        run(p, f"[{slides}]", color=GREY, size=10)
        for text in paras:
            para(doc, text)
    doc.save(OUT)
    print(f"[OK] {OUT.relative_to(ROOT)}: lời nói {mmss(clock)}")


if __name__ == "__main__":
    main()
