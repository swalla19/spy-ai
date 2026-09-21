"""PDF Generator for University-Grade Examination Papers using ReportLab.

Renders high-quality, formatted exam papers with university header styling,
clean section partitions, aligned marks indicators, and optional answer keys.
"""

import os
import html
from typing import Optional
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas

from models.exam_models import ExamPaper


class NumberedCanvas(canvas.Canvas):
    """Custom canvas that tracks and prints running 'Page X of Y' in the footer."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#475569"))
        # Header rule on later pages
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(40, 755, 572, 755)

        # Footer
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(40, 45, 572, 45)
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(572, 32, page_text)
        self.drawString(40, 32, "Confidential - University Examination Paper")
        self.restoreState()


def safe_text(text: Optional[str]) -> str:
    """Escapes XML entities for ReportLab Paragraphs."""
    if not text:
        return ""
    return html.escape(str(text))


def generate_exam_pdf(
    exam_paper: ExamPaper,
    output_dir: str = "output/generated_papers",
    filename: Optional[str] = None
) -> str:
    """Generates a professional examination paper PDF.

    Returns the absolute path to the generated PDF.
    """
    os.makedirs(output_dir, exist_ok=True)

    if not filename:
        clean_subject = "".join(c for c in exam_paper.exam.subject if c.isalnum() or c in (" ", "_", "-")).rstrip()
        clean_subject = clean_subject.replace(" ", "_")[:25]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Exam_{clean_subject}_{timestamp}.pdf"

    pdf_path = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=45,
        bottomMargin=55
    )

    styles = getSampleStyleSheet()

    # Custom Typography
    title_style = ParagraphStyle(
        "ExamTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4
    )

    subject_style = ParagraphStyle(
        "ExamSubject",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=12
    )

    meta_label = ParagraphStyle(
        "MetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#1e293b")
    )

    meta_val = ParagraphStyle(
        "MetaVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#1e293b")
    )

    section_header = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=14,
        spaceAfter=3
    )

    section_inst = ParagraphStyle(
        "SectionInst",
        parent=styles["Italic"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#475569"),
        spaceAfter=10
    )

    q_stem_style = ParagraphStyle(
        "QuestionStem",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        textColor=colors.HexColor("#0f172a")
    )

    marks_badge = ParagraphStyle(
        "MarksBadge",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#1e293b")
    )

    opt_style = ParagraphStyle(
        "OptionStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#1e293b")
    )

    instructions_header = ParagraphStyle(
        "InstHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=3
    )

    inst_item = ParagraphStyle(
        "InstItem",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155")
    )

    ans_header = ParagraphStyle(
        "AnsHeader",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=8
    )

    ans_text = ParagraphStyle(
        "AnsText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#047857")
    )

    story = []

    # Title & Subject
    story.append(Paragraph(safe_text(exam_paper.exam.title).upper(), title_style))
    story.append(Paragraph(safe_text(exam_paper.exam.subject).upper(), subject_style))

    # Meta banner (Time Allowed & Max Marks)
    meta_table_data = [
        [
            Paragraph(f"<b>Time Allowed:</b> {safe_text(exam_paper.exam.duration)}", meta_label),
            Paragraph(f"<b>Maximum Marks:</b> {exam_paper.exam.total_marks}", meta_val)
        ]
    ]
    meta_table = Table(meta_table_data, colWidths=[266, 266])
    meta_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), 1.0, colors.HexColor("#0f172a")),
        ('LINEABOVE', (0, 0), (-1, -1), 1.0, colors.HexColor("#0f172a")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # General Instructions
    if exam_paper.exam.instructions:
        story.append(Paragraph("<b>GENERAL INSTRUCTIONS:</b>", instructions_header))
        for inst in exam_paper.exam.instructions:
            story.append(Paragraph(f"• {safe_text(inst)}", inst_item))
        story.append(Spacer(1, 12))

    # Sections & Questions
    for section in exam_paper.sections:
        story.append(Paragraph(safe_text(section.name).upper(), section_header))
        if section.instructions:
            story.append(Paragraph(safe_text(section.instructions), section_inst))
        else:
            story.append(Spacer(1, 6))

        for q in section.questions:
            q_elements = []

            # Question row with stem and right-aligned mark
            stem_html = f"<b>Q{q.number}.</b> {safe_text(q.question)}"
            badge_html = f"[{q.marks}]"

            q_table = Table(
                [[
                    Paragraph(stem_html, q_stem_style),
                    Paragraph(badge_html, marks_badge)
                ]],
                colWidths=[485, 45]
            )
            q_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            q_elements.append(q_table)

            # MCQ Options table (2x2 grid or stacked)
            if q.options and len(q.options) >= 2:
                opt_rows = []
                # If 4 options, format as 2 columns for neat paper layout
                if len(q.options) == 4:
                    opt_rows.append([
                        Paragraph(safe_text(q.options[0]), opt_style),
                        Paragraph(safe_text(q.options[1]), opt_style)
                    ])
                    opt_rows.append([
                        Paragraph(safe_text(q.options[2]), opt_style),
                        Paragraph(safe_text(q.options[3]), opt_style)
                    ])
                else:
                    for opt in q.options:
                        opt_rows.append([Paragraph(safe_text(opt), opt_style)])

                col_w = [255, 255] if len(q.options) == 4 else [510]
                opt_table = Table(opt_rows, colWidths=col_w)
                opt_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 18),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ]))
                q_elements.append(opt_table)

            # Internal Choice ("OR" Question)
            if q.internal_choice:
                or_table = Table(
                    [[
                        Paragraph(f"<i><b>--- OR ---</b></i><br/>{safe_text(q.internal_choice)}", q_stem_style),
                        Paragraph(badge_html, marks_badge)
                    ]],
                    colWidths=[485, 45]
                )
                or_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 12),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                q_elements.append(or_table)

            q_elements.append(Spacer(1, 8))
            story.append(KeepTogether(q_elements))

        story.append(Spacer(1, 10))

    # Optional Answer Key Section (appended on fresh page)
    has_answers = any(q.answer for s in exam_paper.sections for q in s.questions)
    if has_answers:
        story.append(PageBreak())
        story.append(Paragraph("CONFIDENTIAL - OFFICIAL EVALUATION SCHEME & ANSWER KEY", ans_header))
        story.append(Spacer(1, 8))

        for section in exam_paper.sections:
            story.append(Paragraph(f"<b>{safe_text(section.name)} - Solutions</b>", section_header))
            story.append(Spacer(1, 4))

            for q in section.questions:
                if q.answer:
                    ans_card = [
                        Paragraph(
                            f"<b>Q{q.number}. ({q.type}, {q.marks}M)</b> [Topic: {safe_text(q.topic)} | Level: {safe_text(q.bloom_level or 'N/A')}]",
                            instructions_header
                        ),
                        Paragraph(f"<b>Answer/Rubric:</b> {safe_text(q.answer)}", ans_text),
                        Spacer(1, 6)
                    ]
                    story.append(KeepTogether(ans_card))

    # Build Document
    doc.build(story, canvasmaker=NumberedCanvas)
    return os.path.abspath(pdf_path)
