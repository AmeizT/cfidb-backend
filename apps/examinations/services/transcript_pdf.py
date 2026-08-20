from io import BytesIO

from django.utils import timezone
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

from apps.examinations.services.results import ACADEMIC_YEARS


def _display_number(value):
    return "—" if value is None else f"{value:.2f}"


def _page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawCentredString(A4[0] / 2, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def render_transcript_pdf(transcript):
    output = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="Institution",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#172554"),
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="TranscriptTitle",
        parent=styles["Heading2"],
        alignment=TA_CENTER,
        fontSize=11,
        textColor=colors.HexColor("#475569"),
        spaceAfter=14,
    ))
    styles.add(ParagraphStyle(
        name="ExamName",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
    ))

    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=18 * mm,
        title="Student Examination Transcript",
        author="CFI Workspace",
    )
    student = transcript["student"]
    story = [
        Paragraph("Cornerstone Bible Academy", styles["Institution"]),
        Paragraph("Official Examination Transcript", styles["TranscriptTitle"]),
    ]
    details = Table([
        ["Student", student["full_name"], "Student number", student["student_number"]],
        ["Academic period", transcript["academic_period"], "Generated", timezone.localdate().isoformat()],
    ], colWidths=[29 * mm, 58 * mm, 31 * mm, 42 * mm])
    details.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([details, Spacer(1, 8 * mm)])

    for index, year in enumerate(ACADEMIC_YEARS):
        if index and len(story) > 20:
            story.append(PageBreak())
        story.append(Paragraph(f"{year} Examination Results", styles["Heading3"]))
        rows = [["Examination", "Date", "Score", "Total", "%", "Status", "Grade"]]
        for result in transcript["results"][str(year)]:
            score = (
                _display_number(result["score"])
                if result["status"] == "scored" else result["status"].title()
            )
            rows.append([
                Paragraph(result["examination_name"], styles["ExamName"]),
                result["examination_date"].isoformat() if result["examination_date"] else "—",
                score,
                _display_number(result["total_marks"]),
                _display_number(result["percentage"]),
                result["status"].title(),
                result["grade"] or "—",
            ])
        if len(rows) == 1:
            rows.append(["No examination results", "", "", "", "", "", ""])

        table = Table(rows, repeatRows=1, colWidths=[55 * mm, 23 * mm, 20 * mm, 18 * mm, 16 * mm, 23 * mm, 14 * mm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("SPAN", (0, 1), (-1, 1)) if len(rows) == 2 and rows[1][0] == "No examination results" else ("LEFTPADDING", (0, 0), (0, 0), 4),
        ]))
        story.extend([
            table,
            Paragraph(
                f"{year} yearly average: {_display_number(transcript['yearly_averages'][str(year)])}%",
                styles["BodyText"],
            ),
            Spacer(1, 5 * mm),
        ])

    summary = Table([
        ["Overall average", f"{_display_number(transcript['overall_average'])}%", "Final grade", transcript["final_grade"] or "—"],
        ["Overall result", transcript["overall_result"] or "—", "Examinations written", str(transcript["examinations_written"])],
    ], colWidths=[40 * mm, 40 * mm, 45 * mm, 35 * mm])
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#93c5fd")),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([Spacer(1, 2 * mm), summary])
    doc.build(story, onFirstPage=_page_number, onLaterPages=_page_number)
    return output.getvalue()
