"""Builds reports/report.docx from reports/report.md on the PTIT template.

The template (reports/template_ptit.docx, made by scripts/make_report_template.py)
supplies page setup, styles and the cover page. This script appends:
MỤC LỤC (TOC field), DANH MỤC HÌNH VÀ BẢNG, DANH MỤC TỪ VIẾT TẮT, TÓM TẮT, then
"CHƯƠNG N." chapters, KẾT LUẬN, TÀI LIỆU THAM KHẢO and PHỤ LỤC.

Conventions of the reference report applied here:
- body: Normal, justified, 1 cm first-line indent; lists: List Bullet;
- chapters (Heading 1) start on a new page; sections are Heading 2 "N.k. …";
  chapters without "##" sections get them from their bold lead-ins ("**Bối cảnh.** …");
- captions use the Caption style, numbered per chapter ("Bảng 6.2:", "Hình 6.1:");
  table captions above tables, figure captions below figures; in-text references
  ("Bảng 7", "Hình 4–5") are renumbered accordingly.

Open the result in Word, press Ctrl/Cmd+A then F9 (or right-click → Update Field)
to fill the TOC and lists, then File → Save As PDF.

Usage:
    python3 scripts/build_report_docx.py [--md reports/report.md] [--out reports/report.docx]
"""

import argparse
import copy
import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

TEMPLATE = Path("reports/template_ptit.docx")
CODE_FONT = "Consolas"
INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*)")
CHAPTER_RE = re.compile(r"^# (\d+)\. (.+)$")
ABBREVIATIONS = [
    ("LLM", "Large Language Model", "Mô hình ngôn ngữ lớn"),
    ("REPL", "Read–Eval–Print Loop", "Tiến trình Lean thường trú nhận lệnh kiểm chứng"),
    ("RQ", "Research Question", "Câu hỏi nghiên cứu"),
    ("P50 / P95", "50th / 95th percentile", "Trung vị / phân vị 95 (độ trễ đuôi)"),
    ("USS / RSS", "Unique / Resident Set Size", "Bộ nhớ riêng / bộ nhớ thường trú của tiến trình"),
    ("k", "Attempt budget", "Số lần thử sửa tối đa mỗi mẫu"),
    ("SYN_01 … TAC_07", "Error taxonomy codes", "Mã nhóm lỗi trong taxonomy v0.2"),
]


# --------------------------------------------------------------------------- helpers
def add_field(paragraph, instr: str, placeholder: str = "") -> None:
    run = paragraph.add_run()
    for tag, attrs, text in (("w:fldChar", {"w:fldCharType": "begin"}, None),
                             ("w:instrText", {"xml:space": "preserve"}, instr),
                             ("w:fldChar", {"w:fldCharType": "separate"}, None)):
        el = OxmlElement(tag)
        for k, v in attrs.items():
            el.set(qn(k), v)
        if text:
            el.text = text
        run._r.append(el)
    if placeholder:
        paragraph.add_run(placeholder)
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    paragraph.add_run()._r.append(end)


def add_inline(paragraph, text: str, size: float | None = None) -> None:
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = CODE_FONT
            run.font.size = Pt((size or 13) - 2)
            continue
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            run = paragraph.add_run(part[1:-1])
            run.italic = True
        else:
            run = paragraph.add_run(part)
        if size:
            run.font.size = Pt(size)


def shade(cell, fill: str) -> None:
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    cell._tc.get_or_add_tcPr().append(shd)


def page_break(doc) -> None:
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def front_heading(doc, text: str) -> None:
    """Unnumbered centred title like the reference's 'MỤC LỤC' (not in the TOC)."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(16)


def chapter(doc, text: str) -> None:
    h = doc.add_heading(text, level=1)
    h.paragraph_format.page_break_before = True


def body_para(doc, text: str) -> None:
    p = doc.add_paragraph(style="Normal")
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.first_line_indent = Cm(1)
    add_inline(p, text)


def caption(doc, text: str) -> None:
    p = doc.add_paragraph(style="Caption")
    add_inline(p, text)


def table(doc, rows: list[list[str]]) -> None:
    ncols = len(rows[0])
    size = 12 if ncols <= 5 else 11
    t = doc.add_table(rows=len(rows), cols=ncols)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j in range(ncols):
            cell = t.cell(i, j)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            add_inline(p, row[j] if j < len(row) else "", size=size)
            if i == 0:
                for r in p.runs:
                    r.bold = True
                shade(cell, "E8EEF6")
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def code(doc, lines: list[str]) -> None:
    for ln in lines:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        r = p.add_run(ln or " ")
        r.font.name = CODE_FONT
        r.font.size = Pt(9.5)
    doc.add_paragraph()


# --------------------------------------------------------------------------- numbering
def caption_map(lines: list[str]) -> dict[str, str]:
    """Old global numbers ('Bảng 7', 'Hình 3') -> per-chapter numbers ('Bảng 6.2')."""
    mapping, chap, counters = {}, "0", {}
    for ln in lines:
        m = CHAPTER_RE.match(ln)
        if m:
            chap, counters = m.group(1), {"Bảng": 0, "Hình": 0}
            continue
        for kind, pat in (("Bảng", r"^\*Bảng (\d+)\."), ("Hình", r"^!\[Hình (\d+)\.")):
            mm = re.match(pat, ln.strip())
            if mm:
                counters[kind] = counters.get(kind, 0) + 1
                mapping[f"{kind} {mm.group(1)}"] = f"{kind} {chap}.{counters[kind]}"
    return mapping


def caption_label(text: str, mapping: dict[str, str]) -> str:
    """'Bảng 7. Ablation …' -> 'Bảng 6.2: Ablation …' (caption prefix, then in-text refs)."""
    m = re.match(r"^(Bảng|Hình) (\d+)\.\s*(.*)$", text)
    if not m:
        return renumber(text, mapping)
    label = mapping.get(f"{m.group(1)} {m.group(2)}", f"{m.group(1)} {m.group(2)}")
    return f"{label}: {renumber(m.group(3), mapping)}"


def renumber(text: str, mapping: dict[str, str]) -> str:
    def rng(m: re.Match) -> str:
        a, b = mapping.get(f"{m.group(1)} {m.group(2)}"), mapping.get(f"{m.group(1)} {m.group(3)}")
        if a and b:
            return f"{a}–{b.split(' ')[1]}"
        return m.group(0)

    text = re.sub(r"(Bảng|Hình) (\d+)–(\d+)", rng, text)
    return re.sub(r"(Bảng|Hình) (\d+)(?![\d.,])", lambda m: mapping.get(m.group(0), m.group(0)), text)


# --------------------------------------------------------------------------- build
def build(md_path: Path, out_path: Path) -> dict[str, int]:
    text = md_path.read_text(encoding="utf-8")
    if text.startswith("---"):
        text = text.split("---", 2)[2]
    lines = text.splitlines()
    mapping = caption_map(lines)

    doc = Document(TEMPLATE)
    page_break(doc)
    front_heading(doc, "MỤC LỤC")
    add_field(doc.add_paragraph(), 'TOC \\o "1-2" \\h \\z \\u',
              "(Mở trong Word: Ctrl/Cmd+A rồi F9 để cập nhật mục lục)")
    page_break(doc)
    front_heading(doc, "DANH MỤC HÌNH VÀ BẢNG")
    add_field(doc.add_paragraph(), 'TOC \\h \\z \\t "Caption,1"',
              "(Mở trong Word: Ctrl/Cmd+A rồi F9 để cập nhật danh mục)")
    page_break(doc)
    front_heading(doc, "DANH MỤC TỪ VIẾT TẮT")
    table(doc, [["Viết tắt", "Tiếng Anh", "Ý nghĩa"], *[list(a) for a in ABBREVIATIONS]])

    stats = {"chapters": 0, "sections": 0, "tables": 0, "figures": 0}
    chap_no, sec_no, has_sections = "", 0, False
    # chapters that already contain "##" sections keep them; others get them from bold lead-ins
    chapters_with_sections, cur = set(), None
    for ln in lines:
        m = CHAPTER_RE.match(ln)
        if m:
            cur = m.group(1)
        elif ln.startswith("## ") and cur:
            chapters_with_sections.add(cur)

    i = 0
    while i < len(lines):
        ln = renumber(lines[i], mapping)
        stripped = ln.strip()
        if ln.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            code(doc, lines[i + 1:j])
            i = j + 1
            continue
        if ln.startswith("|"):
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append(renumber(lines[i], mapping))
                i += 1
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in block
                    if not re.match(r"^\|[\s:|-]+\|$", r.strip())]
            k = i
            while k < len(lines) and not lines[k].strip():
                k += 1
            if k < len(lines) and lines[k].strip().startswith("*Bảng"):
                caption(doc, caption_label(lines[k].strip().strip("*"), mapping))
                i = k + 1
            table(doc, rows)
            stats["tables"] += 1
            continue
        m_img = re.match(r"^!\[(.*)\]\((.*)\)\s*$", stripped)
        m_chap = CHAPTER_RE.match(lines[i])
        if m_img:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(str((md_path.parent / m_img.group(2)).resolve()), width=Cm(14))
            caption(doc, caption_label(m_img.group(1), mapping))
            stats["figures"] += 1
        elif m_chap:
            chap_no, sec_no = m_chap.group(1), 0
            has_sections = chap_no in chapters_with_sections
            title = m_chap.group(2).upper()
            if title.startswith("KẾT LUẬN"):
                chapter(doc, title)  # unnumbered, as in the reference
            else:
                chapter(doc, f"CHƯƠNG {chap_no}. {title}")
            stats["chapters"] += 1
        elif ln.startswith("# "):
            chap_no, has_sections = "", True
            chapter(doc, ln[2:].strip().upper())
        elif ln.startswith("## "):
            doc.add_heading(ln[3:].strip(), level=2)
            stats["sections"] += 1
        elif (chap_no and not has_sections and stripped.startswith("**")
              and re.match(r"^\*\*([^*]+?)\.\*\*\s*(.*)$", stripped)):
            m = re.match(r"^\*\*([^*]+?)\.\*\*\s*(.*)$", stripped)
            sec_no += 1
            doc.add_heading(f"{chap_no}.{sec_no}. {m.group(1)}", level=2)
            stats["sections"] += 1
            if m.group(2):
                body_para(doc, m.group(2))
        elif stripped.startswith("- "):
            add_inline(doc.add_paragraph(style="List Bullet"), stripped[2:])
        elif stripped.startswith("*Bảng"):
            pass  # consumed with its table
        elif re.match(r"^\[\d+\]", stripped):
            p = doc.add_paragraph(style="Normal")
            p.paragraph_format.left_indent = Cm(1)
            p.paragraph_format.first_line_indent = Cm(-1)
            add_inline(p, stripped)
        elif stripped:
            body_para(doc, stripped)
        i += 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)
    stats["renumbered"] = len(mapping)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Build report.docx from report.md")
    parser.add_argument("--md", default="reports/report.md")
    parser.add_argument("--out", default="reports/report.docx")
    args = parser.parse_args()
    print(f"[OK] {args.out}: {build(Path(args.md), Path(args.out))}")


if __name__ == "__main__":
    main()
