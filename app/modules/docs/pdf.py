"""PDF export helpers for Docs."""

from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _safe_lines(value: object | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    parts = [line.strip("- ").strip() for line in text.replace(";", "\n").splitlines()]
    return [part for part in parts if part]


def build_document_pdf(document, company_data) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.8 * inch,
        leftMargin=0.8 * inch,
        topMargin=0.8 * inch,
        bottomMargin=0.8 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="DocTitle",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#111827"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        name="DocSubtitle",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#4b5563"),
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        name="DocHeading",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#111827"),
        spaceAfter=6,
        spaceBefore=10,
    )
    body_style = ParagraphStyle(
        name="DocBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#111827"),
        spaceAfter=8,
    )

    story = []
    business_name = getattr(company_data, "business_name", None) or "Klarnow Docs"
    subtitle_parts = [business_name, f"Type: {document.type.replace('_', ' ').title()}"]
    story.append(Paragraph(document.title, title_style))
    story.append(Paragraph(" | ".join(subtitle_parts), subtitle_style))

    inputs = document.inputs_json or {}
    for section in getattr(document, "sections", []) or []:
        story.append(Paragraph(section.section_label, heading_style))
        if section.section_key == "line_items":
            rows = _safe_lines(inputs.get("line_items") or section.content)
            table_data = [["Item"]]
            table_data.extend([[row] for row in rows] or [["No line items provided"]])
            table = Table(table_data, colWidths=[6.4 * inch])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("PADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            story.append(table)
            story.append(Spacer(1, 0.1 * inch))
            continue

        content = (section.content or "").replace("\n", "<br/>")
        story.append(Paragraph(content or "No content available.", body_style))

    signatory = getattr(company_data, "standard_signatory", None)
    footer = getattr(company_data, "standard_footer", None)
    if signatory or footer:
        story.append(Spacer(1, 0.2 * inch))
    if isinstance(signatory, dict) and signatory:
        lines = [str(signatory.get("name") or "").strip(), str(signatory.get("title") or "").strip()]
        signatory_text = "<br/>".join(line for line in lines if line)
        if signatory_text:
            story.append(Paragraph(signatory_text, body_style))
    if footer:
        story.append(Paragraph(str(footer).replace("\n", "<br/>"), subtitle_style))

    doc.build(story)
    return buffer.getvalue()
