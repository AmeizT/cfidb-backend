from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import TableStyle
from reportlab.lib import pagesizes


def generate_zone_report_pdf(zone, year, month):
    from apps.reports.models import AssemblyCompliance

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=pagesizes.A4
    )

    elements = []
    styles = getSampleStyleSheet()

    # Title
    elements.append(
        Paragraph(
            f"Zone Compliance Report - {zone.name} ({month}/{year})",
            styles["Heading1"],
        )
    )
    elements.append(Spacer(1, 20))

    data = [["Assembly", "Status"]]

    records = (
        AssemblyCompliance.objects.filter(
            zone=zone,
            year=year,
            month=month,
        )
        .select_related("assembly")
        .order_by("assembly__name")
    )

    for r in records:
        data.append([r.assembly.name, r.status])

    table = Table(data)

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ]
        )
    )

    elements.append(table)

    doc.build(elements)

    buffer.seek(0)
    return buffer