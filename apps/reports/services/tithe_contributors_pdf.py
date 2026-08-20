from io import BytesIO
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _money(value, currency):
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        amount = 0

    return f"{currency} {amount:,.2f}"


def _text(value):
    if value is None:
        return "-"

    value = str(value).strip()
    return value if value else "-"


def _paragraph_text(value):
    return escape(_text(value))


def _period_label(year, month):
    if month:
        return f"{year}-{str(month).zfill(2)}"

    return str(year)


def _percentage(value):
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        amount = 0

    return f"{amount * 100:.0f}%"


def build_tithe_contributors_pdf(*, report, rows, year, month):
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    currency = getattr(report.assembly, "currency", None) or ""
    title = f"Tithe Contributors - {report.assembly.name}"
    period_label = _period_label(year, month)

    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    story = [
        Paragraph(title, styles["Title"]),
        Paragraph(f"Period: {period_label}", styles["Normal"]),
        Spacer(1, 8),
    ]

    summary_data = [[
        "Contributor",
        "Cumulative",
        "Median",
        "Interval",
        "Average Payment Date",
        "Commitment",
    ]]

    for row in rows:
        summary_data.append([
            row["contributor"],
            _money(row["cumulative"], currency),
            _money(row["median"], currency),
            row.get("interval") or "-",
            row.get("average_payment_date") or "-",
            _percentage(row.get("commitment")),
        ])

    summary_table = Table(summary_data, repeatRows=1)
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
        ("ALIGN", (1, 1), (2, -1), "RIGHT"),
        ("ALIGN", (5, 1), (5, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([summary_table, Spacer(1, 12)])

    for row in rows:
        story.append(Paragraph(row["contributor"], styles["Heading3"]))
        history_data = [[
            "Month",
            "Amount",
            "Payment Method",
            "Recorded By",
            "Recorded Date",
            "Receipt",
        ]]

        for history in row.get("history", []):
            history_data.append([
                history.get("month") or "-",
                _money(history.get("amount"), currency),
                history.get("payment_method") or "-",
                history.get("recorded_by") or "-",
                history.get("recorded_date") or "-",
                history.get("receipt") or "-",
            ])

        history_table = Table(history_data, repeatRows=1)
        history_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f9fafb")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
            ("ALIGN", (1, 1), (1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.extend([history_table, Spacer(1, 10)])

    document.build(story)
    buffer.seek(0)
    return buffer


def tithe_contributors_pdf_filename(report, year, month):
    assembly = report.assembly.name.lower().replace(" ", "-")
    period = _period_label(year, month)

    return f"{assembly}-tithe-contributors-{period}.pdf"


def build_tithe_contributor_history_pdf(*, report, contributor_name, records, total, year, month):
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    currency = getattr(report.assembly, "currency", None) or ""
    period_label = _period_label(year, month)

    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    story = [
        Paragraph(f"Tithe Contribution History - {_paragraph_text(contributor_name)}", styles["Title"]),
        Paragraph(f"Assembly: {_paragraph_text(report.assembly.name)}", styles["Normal"]),
        Paragraph(f"Contributor: {_paragraph_text(contributor_name)}", styles["Normal"]),
        Paragraph(f"Period: {period_label}", styles["Normal"]),
        Paragraph(f"Total amount contributed: {_money(total, currency)}", styles["Normal"]),
        Spacer(1, 10),
    ]

    table_data = [[
        "Date",
        "Amount",
        "Payment Method",
        "Reference",
        "Notes",
    ]]

    for tithe in records:
        table_data.append([
            tithe.timestamp.strftime("%Y-%m-%d") if tithe.timestamp else "-",
            _money(tithe.amount, currency),
            _text(tithe.payment_method),
            _text(getattr(tithe, "reference_code", "")),
            _text(getattr(tithe, "notes", "")),
        ])

    if len(table_data) == 1:
        table_data.append(["-", _money(0, currency), "-", "-", "No contributions found for this period."])

    table = Table(table_data, repeatRows=1, colWidths=[28 * mm, 30 * mm, 36 * mm, 45 * mm, 120 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)

    document.build(story)
    buffer.seek(0)
    return buffer


def tithe_contributor_history_pdf_filename(contributor_name, year, month):
    slug = re.sub(r"[^a-z0-9]+", "-", (contributor_name or "contributor").lower()).strip("-")
    period = _period_label(year, month)

    return f"tithes-history-{slug or 'contributor'}-{period}.pdf"
