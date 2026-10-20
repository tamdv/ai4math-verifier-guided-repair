"""Build the talk script KichBan_ThuyetTrinh_Nhom6.docx from slides/talk_script_content.py.

Checks before writing (any failure stops the build):
  * the number of entries equals the number of slides in Slides_Nhom6_VerifierRepair.pptx;
  * every speaker note in the .pptx equals "<speaker>: <notes>" (run slides/build_slides.py to sync);
  * every glossary term is used in the speech at least once;
  * every {placeholder} in the speech is filled from results/raw, configs or the cost ledger.

Run:  python slides/build_talk_script.py   then   ./slides/talk_to_pdf.sh   (Word export)
"""
import collections
import glob
import json
import re
import statistics
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT  # noqa: F401
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from pptx import Presentation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import talk_script_content as C  # noqa: E402

PPTX = ROOT / "slides" / "Slides_Nhom6_VerifierRepair.pptx"
OUT = ROOT / "slides" / "KichBan_ThuyetTrinh_Nhom6.docx"
RAW = ROOT / "results" / "raw"

FONT = "Times New Roman"
SIZE = 13
ACCENT = RGBColor(0x14, 0x4F, 0xB0)
HEAD_FILL = "1E6FE8"
GREY = RGBColor(0x80, 0x80, 0x80)


def fail(msg: str) -> None:
    sys.exit(f"[LỖI] {msg}")


def vn(x: float, nd: int = 1) -> str:
    """Vietnamese number format: decimal comma, thousands dot."""
    s = f"{x:,.{nd}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return s.rstrip("0").rstrip(",") if nd and "," in s else s


# ---------------------------------------------------------------- slides


def slide_info() -> list[dict]:
    prs = Presentation(PPTX)
    out = []
    for i, s in enumerate(prs.slides):
        texts = [sh for sh in s.shapes if sh.has_text_frame]
        title = next((sh.text_frame.text for sh in texts if sh.name == "!!title"), "")
        if i == 0:  # cover: the big title sits in the textbox after the course line
            names = [sh for sh in texts if sh.name != "!!title" and sh.text_frame.text.strip()]
            title = names[0].text_frame.paragraphs[0].text if names else title
        notes = s.notes_slide.notes_text_frame.text if s.has_notes_slide else ""
        out.append({"title": " ".join(title.split()), "notes": notes.strip()})
    return out


# ---------------------------------------------------------------- numbers from results


def infra() -> dict:
    runs = [json.loads(Path(f).read_text()) for f in sorted(glob.glob(str(RAW / "run_*.json")))]
    kag = [r for r in runs if r["machine"].get("os", "").startswith("Linux")]
    exp = [r for r in kag if r["run_id"].startswith("exp-")]
    if not exp:
        fail("không tìm thấy run record thực nghiệm trên Kaggle trong results/raw")
    groups = collections.defaultdict(list)
    for r in exp:
        p = r["parameters"]
        groups[(p["strategy"], p["budget"], p["workers"], Path(p["data"]).name, p.get("model", ""))].append(r)
    reps = statistics.mode(len(v) for v in groups.values())
    exp_h = sum(r["metrics"].get("wall_time_s", 0) for r in exp) / 3600
    m = exp[0]["machine"]
    lean = re.search(r"version ([\d.]+)", exp[0]["software"].get("lean", "")).group(1)
    w1_10k = [r["metrics"]["wall_time_s"] for r in exp
              if r["parameters"]["workers"] == 1 and Path(r["parameters"]["data"]).name == "errors_10k.jsonl"]
    prices = re.search(r"gemini-3\.5-flash-lite:\s*\{input:\s*([\d.]+),\s*output:\s*([\d.]+)\}",
                       (ROOT / "configs" / "llm_prices.yaml").read_text())
    budget = (ROOT / "configs" / "budget.yaml").read_text()
    cap_m = re.search(r"monthly_cap_usd:\s*([\d.]+)", budget).group(1)
    cap_r = re.search(r"run_cap_usd:\s*([\d.]+)", budget).group(1)
    ledger = [json.loads(x) for x in (ROOT / "results" / "cost_ledger.jsonl").read_text().splitlines() if x.strip()]
    client = (ROOT / "src" / "llm_client.py").read_text()
    llm = {k: re.search(rf"^\s+{k}: [^=\n]+= ([^,\n]+),", client, re.M).group(1).strip('"') for k in
           ("temperature", "max_output_tokens", "seed", "thinking_level")}
    seeds = [r for r in kag if r["run_id"].startswith("build-seeds")]
    gen = [r for r in kag if r["run_id"].startswith("gen-errors")]
    dev = next((r["machine"] for r in runs if r["machine"].get("os", "").startswith("macOS")
                and r["machine"].get("ram_gb")), {})
    days = collections.Counter(r["timestamp"][:10] for r in kag)
    return {
        "repeats": reps, "seed": exp[0]["seed"],
        "kaggle_cpus": m["cpu_count"], "kaggle_ram": vn(m["ram_gb"]), "kaggle_os": m["os"].split("-with")[0],
        "lean_version": lean, "python": exp[0]["software"].get("python", "?"),
        "price_in": f"{float(prices.group(1)):.2f}".replace(".", ","), "price_out": f"{float(prices.group(2)):.2f}".replace(".", ","),
        "cap_month": vn(float(cap_m), 0), "cap_run": vn(float(cap_r), 0),
        "kaggle_runs": len(exp), "kaggle_hours": vn(exp_h, 1),
        "longest_run_h": vn(statistics.median(w1_10k) / 3600, 1),
        "cost_total": vn(sum(x.get("cost_usd", 0) for x in ledger), 2), "ledger_rows": len(ledger),
        "llm": llm, "groups": groups, "seeds_h": vn(sum(r["metrics"].get("wall_time_s", 0) for r in seeds) / 3600, 1),
        "gen_h": vn(sum(r["metrics"].get("verify_wall_s", 0) for r in gen) / 3600, 1),
        "dataset": gen[0]["metrics"] if gen else {}, "dev": dev, "days": days,
        "notebooks": sorted(p.name for p in (ROOT / "notebooks" / "sessions").glob("*.ipynb")),
    }


# ---------------------------------------------------------------- text processing


STAGE = re.compile(r"\[\[(.+?)\]\]")


def syllables(text: str) -> int:
    n = 0
    for tok in STAGE.sub(" ", text).split():
        digits = len(re.findall(r"\d", tok))
        n += digits + 1 if digits else 1
    return n


def seconds(n_syll: int) -> int:
    s = n_syll / C.SYLLABLES_PER_MIN * 60
    return int(5 * round(s / 5))


def mmss(s: int) -> str:
    return f"{s // 60}:{s % 60:02d}"


def annotation(g: dict) -> str:
    parts = [f'đọc "{g["read"]}"']
    if g["abbr"]:
        parts.append(f"viết tắt của {g['abbr']}")
    parts.append(g["meaning"])
    return "[" + "; ".join(parts) + "]"


def segment(text: str, pending: dict) -> list[tuple[str, str]]:
    """Split a paragraph into (kind, text) runs: 'say', 'stage', 'note'; annotate first uses of pending terms."""
    runs: list[tuple[str, str]] = []
    pos = 0
    for m in STAGE.finditer(text):
        runs += _annotate(text[pos:m.start()], pending)
        runs.append(("stage", f"[{m.group(1)}]"))
        pos = m.end()
    runs += _annotate(text[pos:], pending)
    return runs


def _annotate(text: str, pending: dict) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    while text:
        best = None
        for key, g in pending.items():
            for form in g["forms"]:
                m = re.search(rf"(?<!\w){re.escape(form)}(?!\w)", text)
                if m and (best is None or (m.start(), -len(form)) < (best[0].start(), -len(best[2]))):
                    best = (m, key, form)
        if not best:
            out.append(("say", text))
            break
        m, key, _ = best
        out.append(("say", text[:m.end()]))
        out.append(("note", " " + annotation(pending.pop(key))))
        text = text[m.end():]
    return out


# ---------------------------------------------------------------- docx helpers


def shade(cell, fill: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def run(p, text: str, bold=False, italic=False, color=None, size=None):
    r = p.add_run(text)
    r.bold, r.italic = bold, italic
    r.font.name = FONT
    r._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    r.font.size = Pt(size or SIZE)
    if color is not None:
        r.font.color.rgb = color
    return r


def para(doc, text: str = "", bold=False, italic=False, color=None, size=None, align=WD_ALIGN_PARAGRAPH.JUSTIFY):
    p = doc.add_paragraph()
    p.alignment = align
    if text:
        run(p, text, bold, italic, color, size)
    return p


def heading(doc, text: str, level: int):
    p = doc.add_paragraph()
    p.style = doc.styles[f"Heading {level}"]
    run(p, text, bold=True, color=ACCENT, size={1: 17, 2: 14, 3: 13}[level])
    return p


def table(doc, rows: list[list[str]], widths: list[float]):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            c = t.cell(i, j)
            c.width = Cm(widths[j])
            c.text = ""
            p = c.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.line_spacing = 1.1
            run(p, str(v), bold=(i == 0), color=RGBColor(0xFF, 0xFF, 0xFF) if i == 0 else None, size=11)
            if i == 0:
                shade(c, HEAD_FILL)
    doc.add_paragraph()
    return t


def setup(doc) -> None:
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    sec.left_margin = sec.right_margin = Cm(2.2)
    sec.top_margin = sec.bottom_margin = Cm(2.0)
    st = doc.styles["Normal"]
    st.font.name = FONT
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    st.font.size = Pt(SIZE)
    pf = st.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = 1.3
    pf.space_after = Pt(4)
    for lvl in (1, 2, 3):
        h = doc.styles[f"Heading {lvl}"]
        h.font.name = FONT
        h.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        h.paragraph_format.space_before = Pt(12 if lvl == 1 else 8)
        h.paragraph_format.space_after = Pt(4)
    # page number footer
    p = sec.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run()
    for tag, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        if tag:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), tag)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = txt
        r._r.append(el)


def readme_summary() -> list[tuple[str, str]]:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    m = re.search(r"^## Tóm tắt dễ hiểu\n(.+?)(?=^## )", text, flags=re.S | re.M)
    if not m:
        fail("README.md thiếu mục '## Tóm tắt dễ hiểu'")
    parts = re.findall(r"^### (.+?)\n+(.+?)(?=^### |\Z)", m.group(1), flags=re.S | re.M)
    return [(h.strip(), " ".join(b.split())) for h, b in parts]


def members() -> list[tuple[str, str]]:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\|\s*\d+\s*\|\s*(B\w+)\s*\|\s*\**([^|*,]+)", text, flags=re.M)
    return [(name.strip(), code) for code, name in rows]


# ---------------------------------------------------------------- build


def build() -> None:
    slides = slide_info()
    if len(slides) != len(C.SLIDES):
        fail(f"kịch bản có {len(C.SLIDES)} mục nhưng {PPTX.name} có {len(slides)} slide")
    for i, (s, c) in enumerate(zip(slides, C.SLIDES), 1):
        want = f"{c['speaker']}: {c['notes']}"
        if s["notes"] != want:
            fail(f"Notes của slide {i} chưa đồng bộ với kịch bản; chạy lại: python slides/build_slides.py")

    info = infra()
    texts = []
    for i, c in enumerate(C.SLIDES, 1):
        try:
            texts.append([p.format(**info) for p in c["speech"]])
        except KeyError as e:
            fail(f"slide {i}: chưa có nguồn cho số liệu {e}")

    pending = {g["term"]: g for g in C.GLOSSARY}
    rendered, timing, clock = [], [], 0
    for i, (c, paras) in enumerate(zip(C.SLIDES, texts), 1):
        body = [segment(p, pending) for p in paras]
        trans = segment(c["transition"], pending) if c.get("transition") else None
        n = sum(syllables(p) for p in paras) + (syllables(c["transition"]) if c.get("transition") else 0)
        sec = 0 if c.get("appendix") else seconds(n)
        clock += sec
        cut = sum(seconds(syllables(paras[k])) for k in c.get("cut", []))
        rendered.append((body, trans))
        timing.append({"sec": sec, "clock": clock, "cut": cut})
    if pending:
        fail("thuật ngữ trong bảng nhưng không xuất hiện trong lời nói: " + ", ".join(sorted(pending)))

    total = clock
    cut_total = sum(t["cut"] for t in timing)
    names = members()
    code = dict(names)

    doc = Document()
    setup(doc)

    # 1 title
    para(doc, C.TITLE, bold=True, color=ACCENT, size=20, align=WD_ALIGN_PARAGRAPH.CENTER)
    para(doc, "Đề tài: Verifier-Guided Repair, sửa chứng minh Lean 4 có kiểm chứng dưới ràng buộc chi phí và độ trễ",
         align=WD_ALIGN_PARAGRAPH.CENTER)
    para(doc, "Môn INT4418 Dữ liệu lớn · Giảng viên: TS. Nguyễn Kiều Linh · Học viện Công nghệ Bưu chính Viễn thông",
         align=WD_ALIGN_PARAGRAPH.CENTER)
    para(doc, f"Bộ slide: slides/{PPTX.name}, {len(slides)} slide gồm "
              f"{sum(not c.get('appendix') for c in C.SLIDES)} slide trình bày và "
              f"{sum(bool(c.get('appendix')) for c in C.SLIDES)} slide phụ lục", align=WD_ALIGN_PARAGRAPH.CENTER)
    speaker_rows = [["Người trình bày", "Mã học viên", "Slide trình bày"]]
    for short, full in C.SPEAKERS.items():
        idx = [str(i) for i, c in enumerate(C.SLIDES, 1) if c["speaker"] == short and not c.get("appendix")]
        speaker_rows.append([full, code.get(full, "?"), ", ".join(idx)])
    table(doc, speaker_rows, [6.0, 3.5, 6.5])

    # 2 how to use
    heading(doc, "Cách dùng", 1)
    p = para(doc)
    run(p, "Kịch bản khớp từng trang của bộ slide. Mỗi mục ghi người trình bày, thời lượng ước tính và mốc thời gian cộng "
           "dồn. Câu chuyển sang slide sau được in nghiêng. ")
    run(p, "[Chữ xám nhỏ trong ngoặc vuông là chú thích hoặc chỉ dẫn, không đọc thành tiếng.]", color=GREY, size=10)
    para(doc, f"Thời lượng ước tính theo khoảng {C.SYLLABLES_PER_MIN} tiếng mỗi phút. Tổng thời lượng phần trình bày là "
              f"{mmss(total)}, mục tiêu là {C.TARGET_MIN} phút. Phần demo ở slide 7 chạy song song với lời nói; nếu cần "
              f"giải thích thêm trên màn hình thì cộng khoảng 1 phút.")
    cuts = [f"slide {i}" for i, t in enumerate(timing, 1) if t["cut"]]
    para(doc, f"Nếu thời gian bị dài, rút các đoạn đánh dấu [có thể rút] ở {', '.join(cuts)}, tiết kiệm khoảng "
              f"{mmss(cut_total)}. Hai slide phụ lục không trình bày, chỉ mở khi được hỏi.")
    para(doc, "Lời nói ngắn của từng slide đã được ghi vào phần Notes của file .pptx, mở bằng chế độ Presenter View khi "
              "trình chiếu. Khi slide thay đổi, chạy lại python slides/build_slides.py rồi python slides/build_talk_script.py; "
              "script dừng và báo lỗi nếu số slide hoặc Notes không khớp.")

    # 3 timing table
    heading(doc, "Bảng thời lượng", 1)
    rows = [["Slide", "Tiêu đề", "Người nói", "Thời lượng", "Mốc"]]
    for i, (s, c, t) in enumerate(zip(slides, C.SLIDES, timing), 1):
        rows.append([str(i), s["title"], C.SPEAKERS[c["speaker"]].split()[-1] if c["speaker"] != "Khamsing" else "Khamsing",
                     "phụ lục" if c.get("appendix") else mmss(t["sec"]), "" if c.get("appendix") else mmss(t["clock"])])
    table(doc, rows, [1.3, 9.0, 2.4, 2.0, 1.6])

    # 4 plain summary
    heading(doc, "Tóm tắt dễ hiểu, đọc trước khi tập", 1)
    para(doc, "Nguồn: mục Tóm tắt dễ hiểu trong README.md; sửa ở README thì kịch bản cập nhật theo.", italic=True,
         color=GREY, size=11)
    for h, b in readme_summary():
        heading(doc, h, 3)
        para(doc, b)

    # 5 speech per slide
    heading(doc, "Lời trình bày theo từng slide", 1)
    for i, (s, c, (body, trans), t) in enumerate(zip(slides, C.SLIDES, rendered, timing), 1):
        heading(doc, f"Slide {i}. {s['title']}", 2)
        meta = f"Người trình bày: {C.SPEAKERS[c['speaker']]}"
        meta += " · Phụ lục, không trình bày" if c.get("appendix") else f" · Thời lượng {mmss(t['sec'])} · Mốc {mmss(t['clock'])}"
        para(doc, meta, bold=True, size=11, color=ACCENT)
        for k, segs in enumerate(body):
            p = para(doc)
            if k in c.get("cut", []):
                run(p, "[có thể rút] ", color=GREY, size=10)
            for kind, txt in segs:
                if kind == "say":
                    run(p, txt)
                elif kind == "note":
                    run(p, txt, color=GREY, size=10)
                else:
                    run(p, txt + " ", color=GREY, size=10)
        if trans:
            p = para(doc)
            for kind, txt in trans:
                run(p, txt, italic=(kind == "say"),
                    color=None if kind == "say" else GREY, size=None if kind == "say" else 10)

    # Appendix A
    heading(doc, "Phụ lục A. Số liệu thực nghiệm và hạ tầng", 1)
    llm = info["llm"]
    ds = info["dataset"]
    dev = info["dev"]
    rows = [["Mục", "Giá trị", "Nguồn"],
            ["Máy chạy thực nghiệm", f"Kaggle CPU, {info['kaggle_os']}, {info['kaggle_cpus']} vCPU, {info['kaggle_ram']} GB RAM",
             "results/raw/run_exp-*.json, trường machine"],
            ["Máy phát triển", f"macOS {dev.get('cpu', '')}, {dev.get('cpu_count', '?')} nhân, {vn(dev.get('ram_gb', 0))} GB RAM; "
             "chỉ dùng để phát triển và kiểm thử", "results/raw, run record chạy trên macOS"],
            ["Phần mềm", f"Lean {info['lean_version']}, Mathlib cùng phiên bản, Python {info['python']}",
             "trường software của run record; lean_ws/lake-manifest.json"],
            ["Huấn luyện mô hình", "Không huấn luyện; LLM được gọi qua API", "thiết kế hệ thống"],
            ["Cấu hình LLM", f"gemini-3.5-flash-lite; temperature {llm['temperature']}; seed {llm['seed']}; "
             f"thinking_level {llm['thinking_level']}; tối đa {llm['max_output_tokens']} token đầu ra", "src/llm_client.py"],
            ["Giá LLM", f"{info['price_in']} USD cho 1 triệu token vào; {info['price_out']} USD cho 1 triệu token ra",
             "configs/llm_prices.yaml"],
            ["Hạn mức chi phí", f"{info['cap_month']} USD mỗi tháng; {info['cap_run']} USD mỗi lần chạy", "configs/budget.yaml"],
            ["Chi phí thực tế", f"{info['cost_total']} USD qua {info['ledger_rows']} lần gọi được ghi sổ",
             "results/cost_ledger.jsonl"],
            ["Thực nghiệm trên Kaggle", f"{info['kaggle_runs']} lần chạy; tổng thời gian chạy cộng dồn {info['kaggle_hours']} giờ, các phiên chạy song song; "
             f"{info['repeats']} lần lặp mỗi cấu hình; seed {info['seed']}", "results/raw/run_exp-*.json"],
            ["Chuẩn bị dữ liệu trên Kaggle", f"kiểm chứng định lý gốc {info['seeds_h']} giờ; sinh và gắn nhãn lỗi "
             f"{info['gen_h']} giờ", "run_build-seeds, run_gen-errors"],
            ["Dữ liệu đánh giá", f"{vn(ds.get('total_unique', 0), 0)} mẫu lỗi từ {vn(ds.get('seeds', 0), 0)} định lý gốc, "
             f"gồm {vn(ds.get('kept_synthetic', 0), 0)} lỗi tổng hợp và {vn(ds.get('kept_natural', 0), 0)} lỗi tự nhiên; "
             "hold-out 284 mẫu ở mức 1.000 và 2.907 mẫu ở mức 10.000", "run_gen-errors; reports/report.md mục 3"],
            ["Phiên Kaggle", "; ".join(f"{d}: {n} run record" for d, n in sorted(info["days"].items())),
             "trường timestamp của run record"],
            ["Notebook", ", ".join(info["notebooks"]), "notebooks/sessions/"]]
    table(doc, rows, [4.0, 8.0, 4.6])
    para(doc, "Thời gian mỗi lần chạy theo cấu hình, trung vị các lần lặp:", bold=True, size=11)
    rows = [["Chiến lược", "k", "Worker", "Dữ liệu", "Model", "Số lần", "Thời gian mỗi lần"]]
    for (st, b, w, data, model), rs in sorted(info["groups"].items(), key=lambda kv: (kv[0][3], kv[0][0], kv[0][1], kv[0][2])):
        wall = statistics.median(r["metrics"].get("wall_time_s", 0) for r in rs)
        rows.append([st, str(b), str(w), data.replace("errors_", "").replace(".jsonl", ""),
                     model if st in ("blind", "llm_only", "hybrid") else "-", str(len(rs)),
                     f"{vn(wall / 60, 1)} phút"])
    table(doc, rows, [2.6, 0.9, 1.4, 1.6, 4.4, 1.4, 3.2])

    # Appendix B
    heading(doc, "Phụ lục B. Thuật ngữ, tên riêng, viết tắt", 1)
    rows = [["Thuật ngữ", "Cách đọc", "Viết tắt của", "Nghĩa"]]
    for g in sorted(C.GLOSSARY, key=lambda g: g["term"].lower()):
        rows.append([g["term"], g["read"], g["abbr"] or "-", g["meaning"]])
    table(doc, rows, [3.0, 3.2, 4.2, 6.2])

    # Appendix C
    heading(doc, "Phụ lục C. Cách đọc ký hiệu", 1)
    rows = [["Ký hiệu", "Cách đọc", "Nghĩa"]] + [list(s) for s in C.SYMBOLS]
    table(doc, rows, [3.0, 5.0, 8.6])

    doc.save(OUT)
    print(f"[OK] {OUT.relative_to(ROOT)}: {len(slides)} slide, trình bày {mmss(total)}, có thể rút {mmss(cut_total)}, "
          f"{len(C.GLOSSARY)} thuật ngữ")


if __name__ == "__main__":
    build()
