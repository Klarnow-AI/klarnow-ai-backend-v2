"""Generate proposal PDF using ReportLab."""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from app.modules.revenue.models import Proposal


def _get_content_dict(proposal: Proposal) -> dict:
    """Safe access to proposal content dict."""
    c = proposal.content
    return c if isinstance(c, dict) else {}


def build_proposal_pdf(
    proposal: Proposal,
    pack_name: str,
    client_name: str | None,
) -> bytes:
    """
    Build a PDF document for the proposal.

    Args:
        proposal: Proposal model instance
        pack_name: Display name of the pack
        client_name: Display name of the client (or None)

    Returns:
        PDF file as bytes
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="ProposalTitle",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=12,
    )
    heading_style = styles["Heading2"]
    body_style = styles["Normal"]

    story = []

    story.append(Paragraph("Proposal", title_style))
    story.append(Paragraph(f"Pack: {pack_name}", body_style))
    if client_name:
        story.append(Paragraph(f"Client: {client_name}", body_style))
    story.append(Spacer(1, 0.25 * inch))

    story.append(Paragraph("Summary", heading_style))
    story.append(Paragraph(f"Amount: {proposal.amount} {proposal.currency}", body_style))
    if proposal.due_date:
        story.append(Paragraph(f"Due date: {proposal.due_date}", body_style))
    story.append(Spacer(1, 0.2 * inch))

    content = _get_content_dict(proposal)
    description = content.get("description")
    if isinstance(description, str) and description.strip():
        story.append(Paragraph("Description", heading_style))
        story.append(Paragraph(description.replace("\n", "<br/>"), body_style))
        story.append(Spacer(1, 0.2 * inch))

    line_items = content.get("line_items")
    if isinstance(line_items, list) and len(line_items) > 0:
        story.append(Paragraph("Line items", heading_style))
        table_data = [["Item", "Amount", "Description"]]
        for item in line_items:
            if isinstance(item, dict):
                label = str(item.get("label", ""))
                amount = str(item.get("amount") or "")
                desc = str(item.get("description", ""))
                table_data.append([label, amount, desc])
        t = Table(table_data, colWidths=[1.5 * inch, 1 * inch, 3 * inch])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0e0e0")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("TOPPADDING", (0, 0), (-1, 0), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 0.2 * inch))

    terms = content.get("terms")
    if isinstance(terms, str) and terms.strip():
        story.append(Paragraph("Terms", heading_style))
        story.append(Paragraph(terms.replace("\n", "<br/>"), body_style))

    doc.build(story)
    return buffer.getvalue()
