"""Render the generated concept DOCX as a review PDF when LibreOffice is unavailable.

This is a content-level fallback for the desktop environment: it reads the same
WordprocessingML paragraphs and tables that the DOCX contains, then renders them
with reportlab so every page can still receive visual QA.
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _paragraphs_and_tables(path: Path) -> list[tuple[str, object]]:
    with zipfile.ZipFile(path) as package:
        root = ElementTree.fromstring(package.read("word/document.xml"))
    blocks: list[tuple[str, object]] = []
    body = root.find(f"{NS}body")
    if body is None:
        return blocks
    for child in body:
        if child.tag == f"{NS}tbl":
            rows: list[list[str]] = []
            for row in child.findall(f"{NS}tr"):
                rows.append(
                    [
                        " ".join(
                            node.text or "" for node in cell.iter(f"{NS}t")
                        ).strip()
                        for cell in row.findall(f"{NS}tc")
                    ]
                )
            blocks.append(("table", rows))
        elif child.tag == f"{NS}p":
            text = " ".join(node.text or "" for node in child.iter(f"{NS}t")).strip()
            if text:
                blocks.append(("paragraph", text))
    return blocks


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path", type=Path)
    parser.add_argument("output_path", type=Path)
    args = parser.parse_args()
    args.output_path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "PrismBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.8,
            leading=11,
            spaceAfter=4,
            textColor=colors.HexColor("#0B0F14"),
        )
    )
    styles.add(
        ParagraphStyle(
            "PrismH1",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=20,
            spaceBefore=14,
            spaceAfter=7,
            keepWithNext=True,
            textColor=colors.HexColor("#0B0F14"),
        )
    )
    styles.add(
        ParagraphStyle(
            "PrismH2",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            spaceBefore=10,
            spaceAfter=5,
            keepWithNext=True,
            textColor=colors.HexColor("#547D83"),
        )
    )
    styles.add(
        ParagraphStyle(
            "PrismH3",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            spaceBefore=7,
            spaceAfter=3,
            keepWithNext=True,
            textColor=colors.HexColor("#475569"),
        )
    )
    styles.add(
        ParagraphStyle(
            "PrismCode",
            parent=styles["Code"],
            fontName="Courier",
            fontSize=7.2,
            leading=9,
            leftIndent=7,
            rightIndent=5,
            backColor=colors.HexColor("#EEF4F4"),
            borderPadding=5,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            "PrismCenter",
            parent=styles["BodyText"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#547D83"),
        )
    )

    def footer(canvas: object, document: object) -> None:
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#547D83"))
        canvas.setLineWidth(0.5)
        canvas.line(18 * mm, 14 * mm, 192 * mm, 14 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#475569"))
        canvas.drawString(
            18 * mm, 9 * mm, "PRISM / PROJECT CONCEPT / ecosystem-consolidation-v1"
        )
        canvas.drawRightString(192 * mm, 9 * mm, f"{canvas.getPageNumber()}")
        canvas.restoreState()

    story: list[object] = []
    blocks = _paragraphs_and_tables(args.input_path)
    for kind, value in blocks:
        if kind == "table":
            rows = value  # type: ignore[assignment]
            table = Table(
                [
                    [Paragraph(_escape(cell), styles["PrismBody"]) for cell in row]
                    for row in rows
                ],
                repeatRows=1,
                hAlign="LEFT",
                colWidths=[174 * mm / max(len(rows[0]), 1)] * len(rows[0]),
            )
            table_commands = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#547D83")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#B8C8C9")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
            if len(rows) > 2:
                table_commands.append(
                    ("BACKGROUND", (0, 2), (-1, -1), colors.HexColor("#EEF4F4"))
                )
            table.setStyle(TableStyle(table_commands))
            story.extend((Spacer(1, 3), table, Spacer(1, 5)))
            continue
        text = str(value)
        if text == "PRISM":
            story.append(
                Paragraph(
                    text,
                    ParagraphStyle(
                        "Cover",
                        parent=styles["Title"],
                        alignment=TA_CENTER,
                        fontName="Helvetica-Bold",
                        fontSize=28,
                        leading=32,
                        textColor=colors.HexColor("#0B0F14"),
                    ),
                )
            )
            continue
        if text.startswith("ONE SIGNAL."):
            story.append(Paragraph(_escape(text), styles["PrismCenter"]))
            story.append(Spacer(1, 13))
            continue
        if text.startswith("Revision  "):
            story.append(
                Paragraph(
                    _escape(text),
                    ParagraphStyle(
                        "CoverMeta",
                        parent=styles["PrismBody"],
                        alignment=TA_CENTER,
                        fontName="Courier",
                        fontSize=8,
                        textColor=colors.HexColor("#475569"),
                    ),
                )
            )
            story.append(PageBreak())
            continue
        if text.startswith(
            (
                "Contents",
                "PRISM project concept",
                "Authority chain",
                "Executive summary",
                "Problem and product thesis",
                "Canonical agent topology",
                "Decision vocabulary",
                "Governance baseline",
                "AI Profiles",
                "Market regime",
                "Authorization and execution",
                "ShadowFund and learning",
                "Data, API",
                "Security and operations",
                "Frontend concept",
                "Delivery scope",
                "Success criteria",
            )
        ):
            style = styles["PrismH1"]
        elif text.startswith(("Implemented skeleton", "Deferred engines")):
            style = styles["PrismH2"]
        elif text.startswith(
            (
                "```",
                "signal ->",
                "catalyst and",
                "repository invariants",
                "typed feature",
            )
        ):
            style = styles["PrismCode"]
        else:
            style = styles["PrismBody"]
        story.append(Paragraph(_escape(text), style))

    document = SimpleDocTemplate(
        str(args.output_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="PRISM Project Concept",
    )
    document.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    main()
