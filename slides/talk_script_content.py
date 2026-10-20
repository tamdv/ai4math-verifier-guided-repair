"""Talk script content for slides/Slides_Nhom6_VerifierRepair.pptx (single source).

Used by:
  slides/build_talk_script.py  -> KichBan_ThuyetTrinh_Nhom6.docx / .pdf (full speech per slide)
  slides/build_slides.py       -> speaker notes of the .pptx ("<speaker>: <notes>")

Conventions inside `speech` strings:
  [[...]]      stage direction, rendered grey in brackets, not read aloud
  {name}       number filled from results/raw, configs and the cost ledger (see INFRA in build_talk_script.py)
One entry per slide, in slide order. `cut=True` marks a paragraph that can be dropped when the talk runs long.
"""

TITLE = "Kịch bản thuyết trình Nhóm 6: Verifier-Guided Repair"
TARGET_MIN = 15
SYLLABLES_PER_MIN = 160

SPEAKERS = {
    "Tâm": "Đào Văn Tâm",
    "Dũng": "Trần Quang Đức Dũng",
    "Trung": "Lâm Thành Trung",
    "Tùng": "Nguyễn Xuân Tùng",
    "Khamsing": "Khamsing OUTHAIHUENG",
    "Nounou": "Mekdala Nounou",
}

SLIDES = [{'speaker': 'Tâm',
  'notes': 'Chào; đề tài; tóm tắt dễ hiểu 1 phút; lộ trình bốn phần.',
  'speech': ['Em chào cô và các bạn. Em là Đào Văn Tâm, đại diện Nhóm 6. Đề tài của nhóm em là Verifier-Guided '
             'Repair, nghĩa là sửa chứng minh toán học có kiểm chứng, trong giới hạn chi phí và độ trễ.',
             'Em xin tóm tắt đề tài trong một phút. Lean là ngôn ngữ viết chứng minh toán học để máy tính kiểm tra '
             'được từng bước, đi kèm thư viện toán học Mathlib. Mô hình ngôn ngữ lớn, gọi tắt là LLM, hiện viết được '
             'hàng loạt chứng minh Lean, nhưng phần lớn bị trình kiểm chứng từ chối. Ví dụ, chứng minh rằng bình '
             'phương của mọi số thực đều không âm có thể bị từ chối chỉ vì thiếu một dòng khai báo thư viện. Nhóm em '
             'xây dựng hệ thống tự động sửa các chứng minh đó bằng luật hoặc bằng LLM, và chỉ nhận bản sửa khi trình '
             'kiểm chứng chấp nhận và đề bài giữ nguyên. Kết quả chính: gửi kèm thông báo lỗi nâng tỷ lệ sửa thành '
             'công từ 31,7% lên 53,9% và giảm 45% chi phí; giữ trình kiểm chứng chạy liên tục làm thời gian kiểm tra '
             'một chứng minh giảm từ hơn một phút xuống khoảng 3 mili giây.',
             'Bài trình bày gồm bốn phần: bài toán; dữ liệu và kiến trúc kèm demo; kết quả của ba câu hỏi nghiên '
             'cứu; và kết luận.'],
  'transition': 'Trước hết, em xin trình bày vị trí của Nhóm 6 trong chuỗi dự án của lớp.'},
 {'speaker': 'Tâm',
  'notes': 'Vị trí giữa Nhóm 5 và Nhóm 7/8; ba mục tiêu; RQ1 đến RQ3.',
  'speech': ['Trong chuỗi dự án AI4Math của lớp, Nhóm 5 sinh chứng minh Lean, Nhóm 6 sửa các chứng minh lỗi, rồi '
             'chuyển chứng minh đúng cho Nhóm 7 và Nhóm 8.',
             'Mục tiêu gồm ba điểm: chỉ nhận bản sửa mà Lean chấp nhận và đề bài giữ nguyên; chi phí có trần cứng, '
             'và độ trễ được đo ở mức thời gian mà 95% số mẫu xử lý xong, gọi là P95; kết quả tái lập và bàn giao '
             'được.',
             'Ba câu hỏi nghiên cứu là: RQ1, thông báo lỗi của Lean có giúp sửa tốt hơn so với thử lại hay không; '
             'RQ2, nên dùng luật hay LLM, thử mấy lần và tốn bao nhiêu; RQ3, hệ thống mở rộng thế nào khi tăng dữ '
             'liệu và số tiến trình chạy song song.'],
  'transition': 'Tiếp theo là những gì nhóm đã xây dựng.'},
 {'speaker': 'Tâm',
  'notes': 'Bốn thành phần đã xây dựng; đạt 6/6 tiêu chí nghiệm thu; 2,97 USD, 121 test, 67 run record.',
  'speech': ['Nhóm xây dựng bốn thành phần: tập 17.031 chứng minh lỗi có nhãn lấy từ chính Lean; chế độ giữ Lean '
             'chạy liên tục, gọi là REPL, chạy song song trên nhiều tiến trình, mỗi tiến trình gọi là một worker; '
             'vòng sửa gồm luật, LLM và bộ kiểm toán; và cổng nhận dữ liệu từ Nhóm 5 cùng đầu ra cho Nhóm 7 và Nhóm '
             '8.',
             'Bên phải là sáu tiêu chí nghiệm thu tối thiểu của đề bài, và nhóm đạt cả sáu. Toàn bộ thực nghiệm tốn '
             '2,97 USD phí API, có 121 bài kiểm thử và 67 bản ghi lần chạy, gọi là run record.'],
  'transition': 'Vì sao đây là bài toán dữ liệu lớn, bạn Dũng xin giải thích.'},
 {'speaker': 'Dũng',
  'notes': 'Nút thắt: kiểm chứng nguội 63–107 s, 10.000 ứng viên, ~1.000 token mỗi lần, 67 run record.',
  'speech': ['Em là Trần Quang Đức Dũng. Nút thắt của bài toán nằm ở quy mô, lập lịch và chi phí. Kiểm chứng một tệp '
             'theo cách thông thường, tức là khởi động Lean và nạp lại Mathlib, mất 63 đến 107 giây. Ở mức lớn nhất '
             'có 10.000 ứng viên, nên kiểm chứng tuần tự cần hơn 7 ngày. Mỗi lần nhờ LLM sửa tốn khoảng 1.000 token; '
             'token là đơn vị văn bản mà mô hình xử lý và tính phí. Vì vậy hệ thống cần xử lý nhiều mẫu mỗi giây, '
             'giữ P95 thấp trên vài worker chạy bằng CPU, và có trần chi phí.'],
  'transition': 'Tiếp theo, bạn Nounou trình bày về dữ liệu.'},
 {'speaker': 'Nounou',
  'notes': 'Nguồn MIT; 3.666 định lý gốc; 9 cách gây lỗi; 1.110 lỗi tự nhiên; nhãn khớp 94,4%; chia theo định lý '
           'gốc.',
  'speech': ['Em là Mekdala Nounou. Dữ liệu gốc là các chứng minh do mô hình Goedel-Prover viết cho bộ bài toán Lean '
             'Workbook, giấy phép MIT. Lean 4.35 xác nhận 3.666 định lý gốc đúng. Từ đó nhóm tạo lỗi bằng chín cách, '
             'như xoá khai báo thư viện hay gõ sai tên một bổ đề, gọi là lemma. Ngoài ra có 1.110 lỗi tự nhiên do '
             'Mathlib đã đổi tên bổ đề. Tổng cộng có 17.031 mẫu; nhãn lấy từ thông báo thật của Lean, khớp với loại '
             'lỗi dự kiến ở 94,4% số mẫu.',
             'Nhóm chia tập theo định lý gốc, nên không định lý nào nằm ở cả hai phía. Tập kiểm tra để riêng, gọi là '
             'hold-out, có 284 mẫu ở mức 1.000 và 2.907 mẫu ở mức 10.000. Mỗi tệp dữ liệu có mã kiểm tra toàn vẹn, '
             'gọi là checksum.'],
  'transition': 'Tiếp theo, bạn Khamsing trình bày kiến trúc hệ thống.'},
 {'speaker': 'Khamsing',
  'notes': 'Năm bước: parser + taxonomy, router, luật/LLM, Lean REPL, kiểm toán; vòng lặp tối đa k lần, 300 s.',
  'speech': ['Em là Khamsing. Mỗi mẫu đi qua năm bước. Bộ phân tích lỗi, gọi là parser, xếp lỗi vào một trong bảy '
             'nhóm của bảng phân loại, gọi là taxonomy, ví dụ chứng minh để trống bằng lệnh sorry, là lệnh bỏ qua '
             'chứng minh. Bộ định tuyến, gọi là router, gửi lỗi đơn giản cho luật viết sẵn, không tốn token, còn lại '
             'gửi cho LLM kèm thông báo lỗi. Lean REPL kiểm chứng bản sửa. Bộ kiểm toán yêu cầu không dùng sorry hay '
             'axiom, tức là khai báo một điều đúng mà không chứng minh, và phát biểu định lý giữ nguyên. Vòng lặp có '
             'tối đa k lần thử, k bằng 1 hoặc 3, và tối đa 300 giây cho mỗi mẫu.'],
  'transition': 'Bạn Trung trình bày phần demo.'},
 {'speaker': 'Trung',
  'notes': 'Demo phát lại log, 0 USD: E000880 luật R0, 0 token, 73 ms; E000003 LLM, lần 1 dùng sorry bị chặn, lần 3 '
           'đúng, 4.583 token; E000197 đúng ở lần 2, 779 token.',
  'speech': ['Em là Lâm Thành Trung. Demo phát lại nhật ký thực nghiệm nên không cần mạng và không tốn chi phí. '
             '[[Chạy lần lượt ba lệnh trong slides/demo_script.md.]]',
             'Mẫu E000880 bị mất dòng import. Bộ phân loại nhận ra nhóm IMP_02, luật R0 khôi phục dòng khai báo, '
             'Lean chấp nhận: 0 token và 73 mili giây.',
             'Mẫu E000003 chỉ dùng LLM. Lần thử thứ nhất biên dịch được nhưng có chứa sorry nên bị kiểm toán chặn; '
             'lần thứ hai không biên dịch được; lần thứ ba đúng, tổng cộng 4.583 token. Nếu chỉ đo tỷ lệ biên dịch, '
             'lần thứ nhất đã bị tính nhầm là thành công.',
             'Mẫu E000197 sai ở lần thứ nhất; lần thứ hai nhận thông báo lỗi mới và sửa đúng, tốn 779 token.'],
  'transition': 'Bạn Tâm trình bày thiết lập thực nghiệm.'},
 {'speaker': 'Tâm',
  'notes': 'Cùng dữ liệu, phần cứng, seed; 5 chiến lược; k 0/1/3, 3 mức, 1/2/4 worker, 3 lần; Kaggle 4 vCPU 31,3 GB; '
           'Gemini Flash-Lite; độ đo; giả thuyết H1–H3.',
  'speech': ['Mọi so sánh dùng cùng dữ liệu, cùng phần cứng và cùng giá trị khởi tạo ngẫu nhiên, gọi là seed; chỉ '
             'chiến lược thay đổi. Phương pháp cơ sở, gọi là baseline, là thử lại với nguyên đoạn yêu cầu ban đầu, '
             'gọi là prompt; các chiến lược khác là chỉ dùng luật, LLM kèm thông báo lỗi, và kết hợp. Ma trận thí '
             'nghiệm gồm k bằng 0, 1 hoặc 3; ba mức 100, 1.000 và 10.000 mẫu; 1, 2 hoặc 4 worker; mỗi cấu hình chạy '
             '{repeats} lần với seed {seed}.',
             'Hạ tầng là máy ảo CPU của Kaggle, gồm {kaggle_cpus} vCPU, tức là {kaggle_cpus} nhân xử lý ảo, và '
             '{kaggle_ram} GB RAM, chạy Lean {lean_version}. Mô hình là Gemini 3.5 Flash-Lite, nhiệt độ 0, giá '
             '{price_in} USD cho một triệu token đầu vào và {price_out} USD cho một triệu token đầu ra; trần chi phí '
             'là {cap_month} USD mỗi tháng. Nhóm có {kaggle_runs} lần chạy trên Kaggle, tổng thời gian chạy cộng dồn khoảng {kaggle_hours} '
             'giờ; lần chạy dài nhất khoảng {longest_run_h} giờ.',
             'Độ đo chính là tỷ lệ sửa thành công đã kiểm toán, bằng số mẫu có bản sửa được Lean chấp nhận và qua '
             'kiểm toán, chia cho số mẫu hold-out. Ví dụ, 185 trên 284 mẫu là 65,1%. Với RQ3, độ đo chính là thông '
             'lượng, tức là số mẫu xử lý được mỗi giây.',
             'Nhóm đặt ba giả thuyết. H1: thông báo lỗi làm tăng tỷ lệ thành công so với baseline. H2: thêm lần thử '
             'làm tăng cả chất lượng lẫn chi phí, và luật chỉ có lợi với lỗi đơn giản. H3: REPL gỡ được nút thắt '
             'kiểm chứng, nhưng trên một máy, thông lượng không tăng tỷ lệ thuận với số worker.'],
  'transition': 'Bạn Tùng trình bày kết quả của RQ1.'},
 {'speaker': 'Tùng',
  'notes': 'RQ1: 31,7% lên 53,9%, chi phí 2,05 xuống 1,13 USD/1K; 783 so với 389 token ra; theo nhóm lỗi: SYN_01, '
           'TMO_05, IMP_02 tăng mạnh, SEM_06 và TAC_07 hơi giảm.',
  'speech': ['Em là Nguyễn Xuân Tùng. RQ1 so sánh hai cách trên cùng 284 mẫu, mỗi mẫu một lần thử: baseline chỉ yêu '
             'cầu thử lại, còn cách thứ hai gửi kèm thông báo lỗi. Tỷ lệ thành công tăng từ 31,7% lên 53,9%, tức là '
             'tăng 22 điểm phần trăm; chi phí cho 1.000 mẫu giảm từ 2,05 xuống 1,13 USD, tức là giảm 45%.',
             'Chi phí giảm vì khi có thông báo lỗi, mô hình chỉ sửa chỗ hỏng, trung bình 389 token đầu ra thay vì '
             '783, mà token đầu ra đắt gấp 8,3 lần token đầu vào.',
             'Theo nhóm lỗi, thông báo lỗi giúp nhiều nhất ở lỗi cú pháp SYN_01, từ 47% lên 85%; lỗi vượt giới hạn '
             'tính toán TMO_05, từ 10% lên 69%; và IMP_02, từ 3% lên 34%. Hai nhóm SEM_06 và TAC_07 hơi thấp hơn '
             'baseline, vì cần viết chứng minh mới. Vậy H1 đúng trên tổng thể, nhưng không đúng cho mọi nhóm lỗi.'],
  'cut': [1],
  'transition': 'Bạn Tâm trình bày kết quả của RQ2.'},
 {'speaker': 'Tâm',
  'notes': 'RQ2: biên Pareto; LLM k=3 65,1% với 2,45 USD/1K; lai k=3 59,5%; chỉ luật 23,9%, 0 USD; Gemini 3.6 Flash '
           '36,6%.',
  'speech': ['Trục ngang là chi phí LLM cho 1.000 mẫu, trục dọc là tỷ lệ thành công. Đường chấm nối các cấu hình '
             'không bị cấu hình nào khác vừa rẻ hơn vừa tốt hơn, gọi là biên Pareto. Cao nhất là LLM kèm thông báo '
             'lỗi với 3 lần thử: 65,1% và 2,45 USD cho 1.000 mẫu. Kết hợp luật với LLM đạt 59,5% với chi phí thấp '
             'hơn; chỉ dùng luật đạt 23,9% và không tốn tiền. Baseline và Gemini 3.6 Flash nằm dưới biên; Gemini 3.6 '
             'Flash chỉ đạt 36,6%.',
             'H2 đúng ở chỗ thêm lần thử làm tăng cả chất lượng lẫn chi phí. Lý do chiến lược kết hợp thua sẽ có ở '
             'phần phân tích.'],
  'transition': 'Bạn Dũng trình bày kết quả của RQ3.'},
 {'speaker': 'Dũng',
  'notes': 'RQ3: REPL P50 3 ms, P95 23 ms so với 63–107 s; 10K: 1,52 lên 2,86 mẫu/s, tăng tốc 1,76 lần với 2 worker, '
           '1,88 lần với 4; P95 3,1 lên 6,5 s; nghẽn CPU.',
  'speech': ['Khi giữ Lean chạy liên tục và nạp Mathlib một lần cho mỗi worker, thời gian kiểm chứng một định lý còn '
             '3 mili giây ở mức mà một nửa số mẫu nhanh hơn, gọi là P50, và 23 mili giây ở P95, so với 63 đến 107 '
             'giây trước đây. Kết quả khớp với cách thông thường ở 74 trên 74 lần kiểm tra.',
             'Mức tăng tốc bằng thông lượng nhiều worker chia cho thông lượng 1 worker. Ở mức 10.000 mẫu, thông '
             'lượng tăng từ 1,52 lên 2,86 mẫu mỗi giây khi tăng từ 1 lên 4 worker, tức là 1,88 lần; với 2 worker là '
             '1,76 lần. P95 thời gian phục vụ tăng từ 3,1 giây lên 6,5 giây, vì 4 worker dùng chung 4 nhân CPU. Đúng '
             'như H3, muốn mở rộng tiếp thì phải chia việc ra nhiều máy.'],
  'transition': 'Bạn Trung trình bày phần phân tích luật sửa.'},
 {'speaker': 'Trung',
  'notes': 'R0 97%, R7 100%, R1 27%, R2/R3 0%; 203/284 mẫu sang luật, đúng 33%; ablation: khớp nhãn 72,3 lên 96,3%, '
           'token −31%, lai k=1 34,9 xuống 30,3%.',
  'speech': ['Độ chính xác của một luật là tỷ lệ lần áp dụng cho bản sửa qua kiểm toán. R0 khôi phục khai báo thư '
             'viện đúng 97%; R7 tăng giới hạn tính toán, đo bằng đơn vị heartbeat, đúng 100%. Còn R1 chỉ đúng 27%, '
             'R2 và R3 đúng 0%, vì chúng được viết cho đoạn mã ngắn. Router gửi 203 trên 284 mẫu sang luật trước '
             'nhưng luật chỉ đúng 33%, nên với một lần thử, chiến lược kết hợp thua LLM.',
             'Khung bên phải là thí nghiệm loại bỏ từng phần của bộ phân loại để đo đóng góp, gọi là ablation, chạy '
             'lại từ nhật ký. Bộ phân loại đầy đủ nâng độ khớp nhãn từ 72,3% lên 96,3% và giảm 31% token, nhưng '
             'thành công của chiến lược kết hợp giảm từ 34,9% xuống 30,3%, vì nhiều mẫu hơn đi vào luật kém. Điểm '
             'cần cải thiện là chỉ dùng luật có độ chính xác cao.'],
  'cut': [1],
  'transition': 'Bạn Khamsing trình bày vai trò của bộ kiểm toán.'},
 {'speaker': 'Khamsing',
  'notes': 'LLM k=3: biên dịch 75,0% nhưng thành công thật 65,1%; trong mẫu thất bại 17–26% đổi đề, 10–24% chèn '
           'sorry; kiểm toán chặn sorry, admit, axiom, native_decide.',
  'speech': ['Với LLM ba lần thử, 75,0% số mẫu biên dịch được nhưng chỉ 65,1% thành công thật. Trong các mẫu thất '
             'bại, 17% đến 26% bản sửa cuối đã tự ý đổi đề bài, và 10% đến 24% chèn sorry hoặc cấu trúc bị cấm. Bộ '
             'kiểm toán chặn sorry, admit, axiom, native_decide và mọi thay đổi ở phát biểu định lý. Nếu không có '
             'bước này, kết quả sẽ được báo cáo cao hơn thực tế.'],
  'transition': 'Bạn Tâm trình bày phần kết luận.'},
 {'speaker': 'Tâm',
  'notes': 'Ba bài học; bàn giao: cổng Nhóm 5, repaired-v1, Docker, 121 test, notebook, log phát lại; hướng phát '
           'triển.',
  'speech': ['Nhóm rút ra ba bài học: thông báo lỗi của Lean vừa tăng tỷ lệ thành công vừa giảm chi phí; kiểm toán '
             'ngữ nghĩa là bắt buộc; và trình kiểm chứng cần được giữ chạy liên tục và lập lịch, vì trên một máy hệ '
             'thống bị giới hạn bởi CPU.',
             'Về bàn giao, nhóm có cổng nhận dữ liệu từ Nhóm 5, đầu ra định dạng repaired-v1 cho Nhóm 7 và Nhóm 8, '
             'môi trường đóng gói bằng Docker, 121 bài kiểm thử, các notebook Kaggle để chạy lại, và nhật ký phát '
             'lại được.',
             'Hướng phát triển là chạy trên dữ liệu thật của Nhóm 5, thử mô hình chuyên về Lean chạy trên GPU, và '
             'chia worker ra nhiều máy bằng hàng đợi Redis mà bạn Dũng đã xây dựng.'],
  'cut': [2],
  'transition': 'Cuối cùng là phân công và hỏi đáp.'},
 {'speaker': 'Tâm',
  'notes': 'Cảm ơn; chuyển câu hỏi theo bảng: Tâm, Dũng, Trung, Tùng, Khamsing, Nounou. Phụ lục P1–P2 chỉ mở khi '
           'được hỏi.',
  'speech': ['Em xin cảm ơn cô và các bạn đã lắng nghe. Khi hỏi đáp, câu hỏi về đánh giá và chi phí xin chuyển cho '
             'em; về worker, REPL và khả năng mở rộng cho bạn Dũng; về luật sửa cho bạn Trung; về LLM, prompt và '
             'việc chọn mô hình cho bạn Tùng; về bộ phân loại và kiểm toán cho bạn Khamsing; về dữ liệu cho bạn '
             'Nounou. Nhóm em rất mong nhận được câu hỏi và góp ý của cô và các bạn.'],
  'transition': None},
 {'speaker': 'Tâm',
  'appendix': True,
  'notes': 'Phụ lục, chỉ mở khi được hỏi: biên dịch so với thành công đã kiểm toán theo từng cấu hình.',
  'speech': ['[[Không trình bày. Mở khi được hỏi về tỷ lệ biên dịch so với thành công thật ở từng cấu hình: khoảng '
             'chênh giữa cột xanh và cột cam là phần bộ kiểm toán chặn.]]'],
  'transition': None},
 {'speaker': 'Dũng',
  'appendix': True,
  'notes': 'Phụ lục, chỉ mở khi được hỏi: P50 và P95 thời gian phục vụ ở 100, 1K, 10K với 1, 2, 4 worker.',
  'speech': ['[[Không trình bày. Mở khi được hỏi về P95 ở từng mức dữ liệu: biểu đồ cho P50 và P95 ở 100, 1.000 và '
             '10.000 mẫu với 1, 2 và 4 worker, trung vị và khoảng min đến max của 3 lần lặp.]]'],
  'transition': None}]

# Glossary: every term must appear in the speech at least once (checked by the builder).
# forms: exact strings matched as whole words; the first occurrence in the talk gets the grey annotation.
GLOSSARY = [
    {"term": "ablation", "forms": ["ablation"], "read": "ơ-blây-sần", "abbr": "",
     "meaning": "thí nghiệm loại bỏ từng thành phần để đo đóng góp của thành phần đó"},
    {"term": "admit", "forms": ["admit"], "read": "ợt-mít", "abbr": "",
     "meaning": "lệnh của Lean bỏ qua chứng minh, tương tự sorry"},
    {"term": "AI4Math", "forms": ["AI4Math"], "read": "ây-ai pho mát", "abbr": "Artificial Intelligence for Mathematics",
     "meaning": "trí tuệ nhân tạo cho toán học, tên chuỗi dự án của lớp"},
    {"term": "API", "forms": ["API"], "read": "ây-pi-ai", "abbr": "Application Programming Interface",
     "meaning": "giao diện để chương trình gọi một dịch vụ, ở đây là dịch vụ LLM"},
    {"term": "axiom", "forms": ["axiom"], "read": "ắc-xi-ôm", "abbr": "",
     "meaning": "khai báo một mệnh đề là đúng mà không chứng minh"},
    {"term": "baseline", "forms": ["baseline"], "read": "bết-lai", "abbr": "",
     "meaning": "phương pháp cơ sở dùng để so sánh"},
    {"term": "checksum", "forms": ["checksum"], "read": "chéc-xăm", "abbr": "",
     "meaning": "mã kiểm tra tính toàn vẹn của tệp"},
    {"term": "CPU", "forms": ["CPU"], "read": "xê-pê-u", "abbr": "Central Processing Unit",
     "meaning": "bộ xử lý trung tâm"},
    {"term": "Docker", "forms": ["Docker"], "read": "đốc-cơ", "abbr": "",
     "meaning": "công cụ đóng gói môi trường chạy để chạy lại giống nhau trên máy khác"},
    {"term": "Flash-Lite", "forms": ["Flash-Lite"], "read": "phờ-lát lai", "abbr": "",
     "meaning": "phiên bản nhỏ và rẻ nhất trong họ Gemini Flash"},
    {"term": "GB", "forms": ["GB"], "read": "ghi-ga-bai", "abbr": "gigabyte",
     "meaning": "đơn vị dung lượng, khoảng một tỷ byte"},
    {"term": "Gemini", "forms": ["Gemini"], "read": "giê-mi-nai", "abbr": "",
     "meaning": "họ mô hình LLM của Google"},
    {"term": "Goedel-Prover", "forms": ["Goedel-Prover"], "read": "gơ-đồ pru-vơ", "abbr": "",
     "meaning": "mô hình mã nguồn mở viết chứng minh Lean"},
    {"term": "GPU", "forms": ["GPU"], "read": "giê-pê-u", "abbr": "Graphics Processing Unit",
     "meaning": "bộ xử lý đồ hoạ, thường dùng để chạy mô hình"},
    {"term": "heartbeat", "forms": ["heartbeat"], "read": "hát-bít", "abbr": "",
     "meaning": "đơn vị đo lượng tính toán mà Lean cho phép một chứng minh dùng"},
    {"term": "hold-out", "forms": ["hold-out"], "read": "hâu-ao", "abbr": "",
     "meaning": "tập kiểm tra để riêng, không dùng khi thiết kế hệ thống"},
    {"term": "IMP_02", "forms": ["IMP_02"], "read": "im không hai", "abbr": "Import, mã nhóm lỗi 02",
     "meaning": "nhóm lỗi thiếu khai báo thư viện"},
    {"term": "import", "forms": ["import"], "read": "im-pót", "abbr": "",
     "meaning": "dòng khai báo nạp thư viện ở đầu tệp"},
    {"term": "k", "forms": ["k"], "read": "ca", "abbr": "",
     "meaning": "số lần thử tối đa cho mỗi mẫu"},
    {"term": "Kaggle", "forms": ["Kaggle"], "read": "ca-gồ", "abbr": "",
     "meaning": "nền tảng cung cấp máy ảo miễn phí để chạy notebook"},
    {"term": "Lean", "forms": ["Lean"], "read": "lin", "abbr": "",
     "meaning": "ngôn ngữ viết chứng minh toán học và trình kiểm chứng đi kèm"},
    {"term": "Lean Workbook", "forms": ["Lean Workbook"], "read": "lin uốc-búc", "abbr": "",
     "meaning": "bộ bài toán thi đấu đã viết lại bằng Lean"},
    {"term": "lemma", "forms": ["lemma"], "read": "lem-ma", "abbr": "",
     "meaning": "bổ đề, định lý phụ dùng trong chứng minh"},
    {"term": "LLM", "forms": ["LLM"], "read": "eo-eo-em", "abbr": "Large Language Model",
     "meaning": "mô hình ngôn ngữ lớn"},
    {"term": "Mathlib", "forms": ["Mathlib"], "read": "mát-líp", "abbr": "Mathematics library",
     "meaning": "thư viện toán học chuẩn của Lean"},
    {"term": "MIT", "forms": ["MIT"], "read": "em-ai-ti", "abbr": "Massachusetts Institute of Technology",
     "meaning": "giấy phép mã nguồn mở MIT, cho phép dùng lại tự do"},
    {"term": "native_decide", "forms": ["native_decide"], "read": "nây-típ đi-xai", "abbr": "",
     "meaning": "lệnh dùng mã biên dịch để kiểm tra, bỏ qua một phần kiểm chứng của Lean"},
    {"term": "notebook", "forms": ["notebook"], "read": "nốt-búc", "abbr": "",
     "meaning": "tệp chứa mã và kết quả chạy theo từng ô"},
    {"term": "P50", "forms": ["P50"], "read": "pê năm mươi", "abbr": "Percentile 50",
     "meaning": "trung vị: một nửa số mẫu xử lý nhanh hơn mức này"},
    {"term": "P95", "forms": ["P95"], "read": "pê chín mươi lăm", "abbr": "Percentile 95",
     "meaning": "95% số mẫu xử lý xong trong mức thời gian này"},
    {"term": "Pareto", "forms": ["Pareto"], "read": "pa-rê-tô", "abbr": "",
     "meaning": "biên Pareto: các cấu hình không bị cấu hình nào khác vừa rẻ hơn vừa tốt hơn"},
    {"term": "parser", "forms": ["parser"], "read": "pa-xơ", "abbr": "",
     "meaning": "bộ phân tích thông báo lỗi"},
    {"term": "prompt", "forms": ["prompt", "Prompt"], "read": "prôm", "abbr": "",
     "meaning": "đoạn văn bản yêu cầu gửi cho mô hình"},
    {"term": "RAM", "forms": ["RAM"], "read": "ram", "abbr": "Random Access Memory",
     "meaning": "bộ nhớ trong của máy"},
    {"term": "Redis", "forms": ["Redis"], "read": "rê-đít", "abbr": "Remote Dictionary Server",
     "meaning": "hệ thống lưu dữ liệu trong bộ nhớ, ở đây dùng làm hàng đợi công việc"},
    {"term": "repaired-v1", "forms": ["repaired-v1"], "read": "ri-pe-đờ vê một", "abbr": "repaired version 1",
     "meaning": "định dạng đầu ra phiên bản 1 của Nhóm 6"},
    {"term": "REPL", "forms": ["REPL"], "read": "rép-pồ", "abbr": "Read–Eval–Print Loop",
     "meaning": "chế độ chạy liên tục: nhận lệnh, thực thi, trả kết quả rồi chờ lệnh tiếp"},
    {"term": "router", "forms": ["router"], "read": "rao-tơ", "abbr": "",
     "meaning": "bộ định tuyến chọn cách sửa cho từng lỗi"},
    {"term": "RQ", "forms": ["RQ1", "RQ2", "RQ3"], "read": "a-rờ-quy", "abbr": "Research Question",
     "meaning": "câu hỏi nghiên cứu"},
    {"term": "run record", "forms": ["run record"], "read": "răn ré-cọt", "abbr": "",
     "meaning": "bản ghi không sửa đổi của một lần chạy, gồm commit, dữ liệu, máy, tham số và chỉ số"},
    {"term": "seed", "forms": ["seed"], "read": "xít", "abbr": "",
     "meaning": "giá trị khởi tạo bộ sinh số ngẫu nhiên, cố định để chạy lại ra cùng kết quả"},
    {"term": "SEM_06", "forms": ["SEM_06"], "read": "xem không sáu", "abbr": "Semantic, mã nhóm lỗi 06",
     "meaning": "nhóm lỗi chứng minh còn để trống bằng sorry"},
    {"term": "sorry", "forms": ["sorry"], "read": "so-ri", "abbr": "",
     "meaning": "lệnh của Lean cho phép bỏ qua một chứng minh"},
    {"term": "SYN_01", "forms": ["SYN_01"], "read": "xin không một", "abbr": "Syntax, mã nhóm lỗi 01",
     "meaning": "nhóm lỗi cú pháp"},
    {"term": "TAC_07", "forms": ["TAC_07"], "read": "tắc không bảy", "abbr": "Tactic, mã nhóm lỗi 07",
     "meaning": "nhóm lỗi bước chứng minh thất bại"},
    {"term": "taxonomy", "forms": ["taxonomy"], "read": "tắc-xô-nô-mi", "abbr": "",
     "meaning": "bảng phân loại lỗi"},
    {"term": "TMO_05", "forms": ["TMO_05"], "read": "tê-em-ô không năm", "abbr": "Timeout, mã nhóm lỗi 05",
     "meaning": "nhóm lỗi vượt giới hạn tính toán"},
    {"term": "token", "forms": ["token"], "read": "tô-cần", "abbr": "",
     "meaning": "đơn vị văn bản mà mô hình xử lý và tính phí"},
    {"term": "USD", "forms": ["USD"], "read": "đô la Mỹ", "abbr": "United States Dollar",
     "meaning": "đô la Mỹ"},
    {"term": "vCPU", "forms": ["vCPU"], "read": "vê xê-pê-u", "abbr": "virtual CPU",
     "meaning": "nhân xử lý ảo của máy ảo"},
    {"term": "worker", "forms": ["worker"], "read": "uốc-cơ", "abbr": "",
     "meaning": "một tiến trình xử lý chạy song song với các tiến trình khác"},
]

# Symbols as they appear on the slides, with how to read them aloud.
SYMBOLS = [
    ("k=1, k=3", "ca bằng một, ca bằng ba", "số lần thử tối đa cho mỗi mẫu"),
    ("P50, P95", "pê năm mươi, pê chín mươi lăm", "phân vị 50 và 95 của thời gian xử lý"),
    ("1K, 10K", "một nghìn, mười nghìn", "1.000 và 10.000 mẫu"),
    ("→", "lên, sang, hoặc chuyển thành", "thay đổi từ giá trị trước sang giá trị sau"),
    ("×", "lần", "hệ số nhân, ví dụ 1,88× là 1,88 lần"),
    ("⊂", "là tập con của", "100 ⊂ 1K ⊂ 10K: tập nhỏ nằm trong tập lớn"),
    ("~", "khoảng", "giá trị xấp xỉ"),
    ("$", "đô la Mỹ", "đơn vị tiền, đọc sau con số: $2,45 là hai phẩy bốn lăm đô la Mỹ"),
    ("%", "phần trăm", "tỷ lệ trên 100"),
    ("điểm %", "điểm phần trăm", "hiệu của hai tỷ lệ phần trăm, ví dụ 53,9% trừ 31,7% là 22 điểm phần trăm"),
    ("ms, s", "mili giây, giây", "đơn vị thời gian, 1 giây bằng 1.000 mili giây"),
    ("·", "và", "dấu phân cách giữa các mục trên slide"),
    ("min–max", "nhỏ nhất đến lớn nhất", "khoảng biến thiên giữa các lần lặp"),
]
