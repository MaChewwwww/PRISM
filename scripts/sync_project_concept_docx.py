from __future__ import annotations

import argparse
import re
from pathlib import Path

from docx import Document
from docx.document import Document as DocumentType
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

OBSIDIAN = "0B0F14"
TEAL = "547D83"
TEAL_LIGHT = "B2D8DC"
SLATE = "475569"
PALE = "EEF4F4"
WHITE = "FFFFFF"
FONT_SANS = "Plus Jakarta Sans"
FONT_SERIF = "Georgia"
FONT_MONO = "Cascadia Mono"


def _shade(cell: object, fill: str) -> None:
    properties = cell._tc.get_or_add_tcPr()  # type: ignore[attr-defined]
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    properties.append(shading)


def _set_cell_margins(cell: object, value: int = 90) -> None:
    properties = cell._tc.get_or_add_tcPr()  # type: ignore[attr-defined]
    margins = properties.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        properties.append(margins)
    for edge in ("top", "start", "bottom", "end"):
        node = margins.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            margins.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def _repeat_table_header(row: object) -> None:
    properties = row._tr.get_or_add_trPr()  # type: ignore[attr-defined]
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    properties.append(repeat)


def _page_number(paragraph: object) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = "PAGE"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend((begin, instruction, end))


def _font(run: object, name: str, size: float, color: str, bold: bool = False) -> None:
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)
    run.bold = bold


INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`)")


def _inline(paragraph: object, text: str) -> None:
    cursor = 0
    for match in INLINE.finditer(text):
        if match.start() > cursor:
            paragraph.add_run(text[cursor : match.start()])
        token = match.group(0)
        if token.startswith("**"):
            paragraph.add_run(token[2:-2]).bold = True
        else:
            run = paragraph.add_run(token[1:-1])
            _font(run, FONT_MONO, 9, OBSIDIAN)
            shading = OxmlElement("w:shd")
            shading.set(qn("w:fill"), "E7EEEE")
            run._r.get_or_add_rPr().append(shading)
        cursor = match.end()
    if cursor < len(text):
        paragraph.add_run(text[cursor:])


def _configure(document: DocumentType, source: Path) -> None:
    section = document.sections[0]
    section.top_margin = Inches(0.72)
    section.bottom_margin = Inches(0.68)
    section.left_margin = Inches(0.78)
    section.right_margin = Inches(0.70)
    section.header_distance = Inches(0.30)
    section.footer_distance = Inches(0.30)

    normal = document.styles["Normal"]
    normal.font.name = FONT_SANS
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_SANS)
    normal.font.size = Pt(10.2)
    normal.font.color.rgb = RGBColor.from_string(OBSIDIAN)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE

    for name, size, color in (
        ("Title", 32, OBSIDIAN),
        ("Heading 1", 22, OBSIDIAN),
        ("Heading 2", 15, TEAL),
        ("Heading 3", 11.5, SLATE),
    ):
        style = document.styles[name]
        style.font.name = FONT_SANS if name != "Title" else FONT_SERIF
        style._element.rPr.rFonts.set(
            qn("w:eastAsia"), FONT_SANS if name != "Title" else FONT_SERIF
        )
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string(color)
        style.font.bold = True
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.space_before = Pt(11 if name != "Heading 1" else 16)
        style.paragraph_format.space_after = Pt(5)

    if "PRISM Code" not in [style.name for style in document.styles]:
        code = document.styles.add_style("PRISM Code", WD_STYLE_TYPE.PARAGRAPH)
    else:
        code = document.styles["PRISM Code"]
    code.font.name = FONT_MONO
    code._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_MONO)
    code.font.size = Pt(8.6)
    code.font.color.rgb = RGBColor.from_string(OBSIDIAN)
    code.paragraph_format.left_indent = Inches(0.18)
    code.paragraph_format.right_indent = Inches(0.12)
    code.paragraph_format.space_before = Pt(3)
    code.paragraph_format.space_after = Pt(7)

    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = header.add_run("PRISM  /  PROJECT CONCEPT")
    _font(run, FONT_SANS, 8, TEAL, bold=True)

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run("ecosystem-consolidation-v1  •  ")
    _font(run, FONT_SANS, 8, SLATE)
    _page_number(footer)

    document.core_properties.title = "PRISM Project Concept"
    document.core_properties.subject = "Governed paper-only decision architecture"
    document.core_properties.author = "PRISM"
    document.core_properties.comments = f"Generated from {source.as_posix()}"


def _cover(document: DocumentType, revision: str) -> None:
    document.add_paragraph("PRISM", style="Title").alignment = WD_ALIGN_PARAGRAPH.CENTER
    tagline = document.add_paragraph()
    tagline.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = tagline.add_run("ONE SIGNAL. MULTIPLE PERSPECTIVES. BETTER DECISIONS.")
    _font(run, FONT_SANS, 11, TEAL, bold=True)
    tagline.paragraph_format.space_after = Pt(34)

    subtitle = document.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run("Project concept and governed skeleton baseline")
    _font(run, FONT_SERIF, 18, OBSIDIAN)
    subtitle.paragraph_format.space_after = Pt(18)

    rule = document.add_table(rows=1, cols=1)
    rule.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = rule.cell(0, 0)
    _shade(cell, TEAL)
    cell.text = ""
    rule.rows[0].height = Pt(5)

    note = document.add_paragraph()
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    note.paragraph_format.space_before = Pt(28)
    note.paragraph_format.left_indent = Inches(0.75)
    note.paragraph_format.right_indent = Inches(0.75)
    _inline(
        note,
        "Paper-only. AI-assisted. Deterministically governed. "
        "Current presentation data is an Illustrative fixture and creates no execution authority.",
    )

    meta = document.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.paragraph_format.space_before = Pt(28)
    run = meta.add_run(f"Revision  {revision}")
    _font(run, FONT_MONO, 9, SLATE)
    meta.add_run().add_break(WD_BREAK.PAGE)


def _contents(document: DocumentType, headings: list[str]) -> None:
    document.add_heading("Contents", level=1)
    for number, heading in enumerate(headings, start=1):
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(3)
        number_run = paragraph.add_run(f"{number:02d}  ")
        _font(number_run, FONT_MONO, 9, TEAL, bold=True)
        text_run = paragraph.add_run(heading)
        _font(text_run, FONT_SANS, 10, OBSIDIAN)
    document.add_page_break()


def _table(document: DocumentType, rows: list[list[str]]) -> None:
    width = max(len(row) for row in rows)
    table = document.add_table(rows=0, cols=width)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    for row_index, values in enumerate(rows):
        cells = table.add_row().cells
        for column, value in enumerate(values):
            cell = cells[column]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            _set_cell_margins(cell)
            cell.text = ""
            paragraph = cell.paragraphs[0]
            _inline(paragraph, value.strip())
            for run in paragraph.runs:
                _font(
                    run,
                    FONT_SANS,
                    8.2,
                    WHITE if row_index == 0 else OBSIDIAN,
                    bold=row_index == 0 or column == 0,
                )
            if row_index == 0:
                _shade(cell, TEAL)
            elif row_index % 2 == 0:
                _shade(cell, PALE)
        if row_index == 0:
            _repeat_table_header(table.rows[-1])
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
    document.add_paragraph().paragraph_format.space_after = Pt(1)


def _parse(markdown: str, document: DocumentType) -> None:
    lines = markdown.splitlines()
    revision_match = re.search(r"Revision: `([^`]+)`", markdown)
    revision = revision_match.group(1) if revision_match else "unversioned"
    headings = [line[3:].strip() for line in lines if line.startswith("## ")]
    _cover(document, revision)
    _contents(document, headings)

    paragraph_buffer: list[str] = []
    in_code = False
    code_buffer: list[str] = []
    index = 0

    def flush_paragraph() -> None:
        if not paragraph_buffer:
            return
        paragraph = document.add_paragraph()
        _inline(paragraph, " ".join(paragraph_buffer))
        paragraph_buffer.clear()

    while index < len(lines):
        line = lines[index].rstrip()
        if line.startswith("```"):
            flush_paragraph()
            if in_code:
                paragraph = document.add_paragraph(style="PRISM Code")
                paragraph.paragraph_format.keep_together = True
                run = paragraph.add_run("\n".join(code_buffer))
                _font(run, FONT_MONO, 8.6, OBSIDIAN)
                shading = OxmlElement("w:shd")
                shading.set(qn("w:fill"), "EEF4F4")
                paragraph._p.get_or_add_pPr().append(shading)
                code_buffer.clear()
                in_code = False
            else:
                in_code = True
            index += 1
            continue
        if in_code:
            code_buffer.append(line)
            index += 1
            continue
        if (
            line.startswith("| ")
            and index + 1 < len(lines)
            and lines[index + 1].startswith("| ---")
        ):
            flush_paragraph()
            rows: list[list[str]] = []
            rows.append([part.strip() for part in line.strip("|").split("|")])
            index += 2
            while index < len(lines) and lines[index].startswith("|"):
                rows.append(
                    [part.strip() for part in lines[index].strip("|").split("|")]
                )
                index += 1
            _table(document, rows)
            continue
        if not line:
            flush_paragraph()
            index += 1
            continue
        if line.startswith(("**One signal.", "Revision: `")):
            flush_paragraph()
            index += 1
            continue
        if line.startswith(("# ", "Revision:")):
            flush_paragraph()
        elif line.startswith("## "):
            flush_paragraph()
            document.add_heading(line[3:].strip(), level=1)
        elif line.startswith("### "):
            flush_paragraph()
            document.add_heading(line[4:].strip(), level=2)
        elif re.match(r"^\d+\. ", line):
            flush_paragraph()
            paragraph = document.add_paragraph(style="List Number")
            _inline(paragraph, re.sub(r"^\d+\. ", "", line))
        elif line.startswith("- "):
            flush_paragraph()
            paragraph = document.add_paragraph(style="List Bullet")
            _inline(paragraph, line[2:])
        else:
            paragraph_buffer.append(line)
        index += 1
    flush_paragraph()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    markdown = args.source.read_text(encoding="utf-8")
    document = Document()
    _configure(document, args.source)
    _parse(markdown, document)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    document.save(args.output)


if __name__ == "__main__":
    main()
