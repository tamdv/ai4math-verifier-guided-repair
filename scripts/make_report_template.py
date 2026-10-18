"""Creates reports/template_ptit.docx from a reference PTIT report (cover + styles only).

Keeps the reference's page setup, styles, logo and cover layout; replaces the cover
text with Group 6's details and deletes the reference's body (TOC onwards).

Usage:
    python3 scripts/make_report_template.py --ref <reference.docx> [--out reports/template_ptit.docx]
"""

import argparse
from pathlib import Path

from docx import Document

TITLE_LINES = [
    "VERIFIER-GUIDED REPAIR: SỬA CHỨNG MINH LEAN 4",
    "CÓ KIỂM CHỨNG DƯỚI RÀNG BUỘC CHI PHÍ VÀ ĐỘ TRỄ",
]
SUBJECT = "MÔN DỮ LIỆU LỚN"
INFO = {"Giảng viên:": "TS. Nguyễn Kiều Linh", "Nhóm:": "06"}
MEMBERS = [
    ("B25CHHT112", "Đào Văn Tâm"), ("B25CHHT088", "Trần Quang Đức Dũng"),
    ("B25CHHT117", "Lâm Thành Trung"), ("B25CHHT119", "Nguyễn Xuân Tùng"),
    ("B25CHHT125", "Khamsing OUTHAIHUENG"), ("B25CHHT124", "Mekdala Nounou"),
]


def set_text(paragraph, text: str) -> None:
    """Replaces a paragraph's text, keeping the first run's formatting."""
    runs = paragraph.runs
    if not runs:
        paragraph.add_run(text)
        return
    runs[0].text = text
    for r in runs[1:]:
        r._r.getparent().remove(r._r)


def set_cell(cell, lines: list[str]) -> None:
    paras = cell.paragraphs
    for i, line in enumerate(lines):
        if i < len(paras):
            set_text(paras[i], line)
        else:
            new = cell.add_paragraph()
            new.style = paras[0].style
            new.alignment = paras[0].alignment
            run = new.add_run(line)
            if paras[0].runs:
                src = paras[0].runs[0].font
                run.font.size, run.font.bold, run.font.name = src.size, src.bold, src.name
    for p in paras[len(lines):]:
        set_text(p, "")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the PTIT report template")
    parser.add_argument("--ref", required=True)
    parser.add_argument("--out", default="reports/template_ptit.docx")
    args = parser.parse_args()

    doc = Document(args.ref)
    body = doc.element.body
    paras = doc.paragraphs
    # Cover text (indices verified against BaoCao_Nhom8_LinCIR.docx).
    set_text(next(p for p in paras if p.text.startswith("MÔN ")), SUBJECT)
    title_paras = [p for p in paras[:12] if p.style.name == "Body Text" and p.text.isupper()
                   and "HỌC VIỆN" not in p.text]
    for p, line in zip(title_paras, TITLE_LINES):
        set_text(p, line)

    info, members = doc.tables[0], doc.tables[1]
    for row in info.rows:
        key = row.cells[0].text.strip()
        if key in INFO:
            set_cell(row.cells[1], [INFO[key]])
    cells = [c for row in members.rows for c in row.cells]
    for cell, (mssv, name) in zip(cells, MEMBERS):
        set_cell(cell, [mssv, name])

    # Drop everything after the members table except the final section properties.
    after = False
    for el in list(body.iterchildren()):
        if el is members._tbl:
            after = True
            continue
        if after and not el.tag.endswith("}sectPr"):
            body.remove(el)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    doc.save(args.out)
    print(f"[OK] template -> {args.out}")


if __name__ == "__main__":
    main()
