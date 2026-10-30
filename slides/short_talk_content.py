"""Single source for the 5-minute version: one entry per main slide of Slides_Nhom6_RutGon_5Phut.pptx.

Used by slides/build_slides_short.py (deck + speaker notes) and slides/build_short_script.py (Word script).
Backup slides after the Q&A slide have no speech: members open them while answering questions.
"""

SPEAKER = "Đào Văn Tâm"

SLIDES = [
    {"part": "Mở đầu", "speech": [
        "Em chào cô và các bạn. Em là Đào Văn Tâm, đại diện Nhóm 6. Đề tài của nhóm là Verifier-Guided Repair: tự động "
        "sửa các chứng minh toán học viết bằng Lean bị lỗi, trong giới hạn chi phí và thời gian."]},
    {"part": "Đề tài là gì", "speech": [
        "Lean là ngôn ngữ viết chứng minh toán học để máy tính kiểm tra được từng bước. Mô hình ngôn ngữ lớn, gọi tắt là "
        "LLM, viết được hàng loạt chứng minh Lean, nhưng nhiều chứng minh bị Lean từ chối, có khi chỉ vì thiếu một dòng "
        "khai báo thư viện. Trong chuỗi dự án của lớp, Nhóm 5 sinh chứng minh, Nhóm 6 sửa các chứng minh lỗi, và chỉ nhận "
        "bản sửa khi Lean chấp nhận và đề bài giữ nguyên. Đây là bài toán dữ liệu lớn vì mỗi lần Lean kiểm tra từ đầu mất "
        "hơn một phút, số chứng minh lên tới hàng chục nghìn, và mỗi lần gọi LLM đều tốn tiền."]},
    {"part": "Nhóm đã làm gì", "speech": [
        "Nhóm làm bốn việc. Thứ nhất, tạo tập 17.031 chứng minh lỗi, nhãn lỗi lấy từ chính thông báo của Lean, và tách riêng "
        "tập kiểm tra để không lộ đáp án. Thứ hai, xây vòng sửa lỗi: đọc thông báo lỗi và xếp vào bảy nhóm; sửa bằng luật "
        "viết sẵn không tốn tiền, hoặc nhờ LLM sửa kèm thông báo lỗi; cho Lean kiểm tra lại; rồi kiểm toán để chặn bản sửa "
        "gian lận như bỏ qua chứng minh hay đổi đề. Mỗi mẫu được thử tối đa ba lần. Thứ ba, giữ Lean chạy liên tục và chạy "
        "nhiều bản song song để kiểm tra nhanh. Thứ tư, đặt trần chi phí cho LLM và ghi lại mọi lần chạy để tái lập được. "
        "Thực nghiệm chạy trên Kaggle với ba mức 100, 1.000 và 10.000 mẫu, mỗi cấu hình lặp ba lần, dùng Gemini 3.5 Flash-Lite."]},
    {"part": "Kết quả RQ1", "speech": [
        "Về kết quả. Câu hỏi thứ nhất: gửi kèm thông báo lỗi có giúp không. Có. So với chỉ yêu cầu thử lại, tỷ lệ sửa thành "
        "công tăng từ 31,7% lên 53,9%, và chi phí giảm 45%, vì mô hình chỉ sửa đúng chỗ hỏng thay vì viết lại cả tệp."]},
    {"part": "Kết quả RQ2", "speech": [
        "Câu hỏi thứ hai: nên thử mấy lần và sửa bằng cách nào. Cho LLM thử tối đa ba lần đạt 65,1%, tốn 2,45 đô la Mỹ cho "
        "1.000 mẫu. Luật viết sẵn đúng 97 đến 100% với lỗi thiếu khai báo thư viện và lỗi vượt giới hạn tính toán, nhưng kém "
        "với các lỗi còn lại."]},
    {"part": "Kết quả RQ3", "speech": [
        "Câu hỏi thứ ba: hệ thống mở rộng ra sao. Giữ Lean chạy liên tục làm thời gian kiểm tra một chứng minh giảm từ 63 đến "
        "107 giây xuống khoảng 3 mili giây. Với 10.000 mẫu, 2 tiến trình nhanh gấp 1,76 lần, nhưng 4 tiến trình chỉ nhanh "
        "1,88 lần, vì máy chỉ có 4 nhân CPU."]},
    {"part": "Kiểm toán", "speech": [
        "Bước kiểm toán là bắt buộc: với ba lần thử, 75% bản sửa được Lean chấp nhận, nhưng chỉ 65,1% là sửa thật, phần còn "
        "lại đổi đề hoặc bỏ qua chứng minh."]},
    {"part": "Kết luận", "speech": [
        "Tóm lại, gửi thông báo lỗi giúp sửa tốt hơn và rẻ hơn, kiểm toán là bắt buộc, và trình kiểm chứng cần chạy liên "
        "tục, được lập lịch. Toàn bộ thực nghiệm tốn 2,97 đô la Mỹ, và hệ thống đã sẵn sàng nhận dữ liệu thật từ Nhóm 5."]},
    {"part": "Hỏi đáp", "speech": [
        "Em xin cảm ơn cô và các bạn. Phần còn lại xin dành cho câu hỏi; bảng trên slide là thành viên trả lời từng mảng."]},
]

# Q&A routing shown on the last main slide: member, area, backup slide to open (P numbers after the Q&A slide).
QA = [
    ("Đào Văn Tâm", "Câu hỏi nghiên cứu, đánh giá, chi phí", "P5, P6"),
    ("Trần Quang Đức Dũng", "Worker, REPL, mở rộng, hàng đợi", "P7"),
    ("Lâm Thành Trung", "Luật sửa, độ chính xác từng luật", "P4"),
    ("Nguyễn Xuân Tùng", "LLM, prompt, chọn mô hình, demo", "P1"),
    ("Khamsing OUTHAIHUENG", "Phân loại lỗi, kiểm toán, kiến trúc", "P3"),
    ("Mekdala Nounou", "Dữ liệu, chia tập", "P2"),
]
