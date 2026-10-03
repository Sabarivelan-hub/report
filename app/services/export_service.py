"""Report Export Service supporting PDF, DOCX, and JSON generation."""

import io
import json
import logging
from typing import Dict, Any

# python-docx
try:
    import docx
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
except ImportError:
    docx = None

# ReportLab for PDF
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib import colors
except ImportError:
    colors = None

logger = logging.getLogger(__name__)


class ExportService:
    """Renders final report content into PDF, Word DOCX, and JSON formats."""

    @staticmethod
    def to_json(report_data: Dict[str, Any]) -> str:
        """Render report as clean, pretty-printed JSON."""
        return json.dumps(report_data, indent=2, default=str)

    @staticmethod
    def to_docx(report_data: Dict[str, Any]) -> io.BytesIO:
        """Render report as a styled Microsoft Word document (.docx)."""
        if docx is None:
            raise RuntimeError("python-docx is not installed.")

        doc = docx.Document()

        # Styles
        title_text = report_data.get("title", "IntelliReport Report")
        title = doc.add_heading(title_text, level=0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        subtitle_text = report_data.get("subtitle")
        if subtitle_text:
            sub = doc.add_paragraph(subtitle_text)
            sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
            sub.runs[0].font.italic = True
            sub.runs[0].font.size = Pt(12)

        # Metadata table
        meta = report_data.get("metadata", {})
        if meta:
            p_meta = doc.add_paragraph()
            p_meta.add_run("Metadata:\n").bold = True
            for k, v in meta.items():
                p_meta.add_run(f"• {k.replace('_', ' ').capitalize()}: {v}\n")

        doc.add_paragraph().paragraph_format.space_after = Pt(12)

        # Executive Summary
        exec_sum = report_data.get("executive_summary")
        if exec_sum:
            doc.add_heading("Executive Summary", level=1)
            doc.add_paragraph(exec_sum)

        # Sections
        sections = report_data.get("sections", [])
        for section in sections:
            sec_title = section.get("title", "Section")
            doc.add_heading(sec_title, level=1)

            sec_content = section.get("content", "")
            # Split markdown lines
            for line in sec_content.split("\n"):
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("### "):
                    doc.add_heading(stripped[4:], level=3)
                elif stripped.startswith("## "):
                    doc.add_heading(stripped[3:], level=2)
                elif stripped.startswith("- ") or stripped.startswith("* "):
                    doc.add_paragraph(stripped[2:], style="List Bullet")
                else:
                    doc.add_paragraph(stripped)

            # Bullet points
            bullets = section.get("bullet_points", [])
            for bp in bullets:
                doc.add_paragraph(bp, style="List Bullet")

        # Conclusions & Recommendations
        concl = report_data.get("conclusions_and_recommendations")
        if concl:
            doc.add_heading("Conclusions & Recommendations", level=1)
            doc.add_paragraph(concl)

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer

    @staticmethod
    def to_pdf(report_data: Dict[str, Any]) -> io.BytesIO:
        """Render report as a high-fidelity PDF document using ReportLab."""
        buffer = io.BytesIO()

        # Build document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=54,
            leftMargin=54,
            topMargin=54,
            bottomMargin=54,
        )

        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=8,
            alignment=1,  # Center
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=14,
            alignment=1,
        )
        h1_style = ParagraphStyle(
            "H1",
            parent=styles["Heading1"],
            fontSize=15,
            leading=19,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=14,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#334155"),
            spaceAfter=6,
        )
        bullet_style = ParagraphStyle(
            "Bullet",
            parent=body_style,
            leftIndent=15,
            firstLineIndent=-10,
            spaceAfter=3,
        )

        story = []

        # Title
        story.append(Paragraph(report_data.get("title", "IntelliReport AI Report"), title_style))
        sub = report_data.get("subtitle")
        if sub:
            story.append(Paragraph(sub, subtitle_style))

        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceBefore=4, spaceAfter=12))

        # Executive summary
        exec_sum = report_data.get("executive_summary")
        if exec_sum:
            story.append(Paragraph("Executive Summary", h1_style))
            story.append(Paragraph(exec_sum.replace("\n", "<br/>"), body_style))
            story.append(Spacer(1, 10))

        # Sections
        sections = report_data.get("sections", [])
        for section in sections:
            story.append(Paragraph(section.get("title", "Section"), h1_style))
            content = section.get("content", "")
            for p in content.split("\n\n"):
                if p.strip():
                    story.append(Paragraph(p.strip().replace("\n", "<br/>"), body_style))

            bullets = section.get("bullet_points", [])
            for b in bullets:
                story.append(Paragraph(f"&bull; {b}", bullet_style))

            story.append(Spacer(1, 8))

        # Conclusions
        concl = report_data.get("conclusions_and_recommendations")
        if concl:
            story.append(Paragraph("Conclusions & Recommendations", h1_style))
            story.append(Paragraph(concl.replace("\n", "<br/>"), body_style))

        doc.build(story)
        buffer.seek(0)
        return buffer
