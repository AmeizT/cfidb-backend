from __future__ import annotations

from dataclasses import dataclass
from html import escape
from io import BytesIO
import re
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.churches.models import Region, Zone
from apps.reports.models import AuditLog
from apps.reports.services.metrics.region_dashboard_service import get_region_reports
from apps.reports.services.regional_dashboard.compliance import (
    build_assembly_compliance_row,
)


MONTH_NAMES = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}

SECTION_ORDER = [
    "attendance",
    "tithes",
    "income",
    "expenditure",
    "remittance",
    "junior_members",
]

SECTION_LABELS = {
    "attendance": "AT",
    "tithes": "TI",
    "income": "IN",
    "expenditure": "EX",
    "remittance": "RM",
    "junior_members": "JM",
}

SECTION_NAMES = {
    "attendance": "Attendance",
    "tithes": "Tithes",
    "income": "Income",
    "expenditure": "Expenditure",
    "remittance": "Remittance",
    "junior_members": "Junior Members",
}


@dataclass
class RegionalCompliancePdfResult:
    buffer: BytesIO
    filename: str


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_footer(page_count)
            super().showPage()
        super().save()

    def _draw_footer(self, page_count: int):
        width, _height = self._pagesize
        footer_y = 10 * mm

        self.saveState()
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.4)
        self.line(12 * mm, footer_y + 7, width - 12 * mm, footer_y + 7)
        self.setFont("Helvetica", 7)
        self.setFillColor(colors.HexColor("#475569"))
        self.drawString(
            12 * mm,
            footer_y,
            "CFI Database - Regional Monthly Compliance Report",
        )
        self.drawCentredString(
            width / 2,
            footer_y,
            "Confidential - for authorised church administration use only",
        )
        self.drawRightString(
            width - 12 * mm,
            footer_y,
            f"Page {self._pageNumber} of {page_count}",
        )
        self.restoreState()


def _int_param(query_params, name: str, default: int | None = None) -> int | None:
    raw_value = query_params.get(name)
    if raw_value in (None, ""):
        return default

    try:
        return int(raw_value)
    except (TypeError, ValueError):
        raise ValidationError({name: "Enter a valid number."})


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "regional"


def _parse_period_month(item: dict[str, Any]) -> int | None:
    period = item.get("period")
    if isinstance(period, str):
        match = re.match(r"^\d{4}-(\d{2})$", period)
        if match:
            return int(match.group(1))

    month = item.get("month")
    if isinstance(month, str):
        for month_number, month_name in MONTH_NAMES.items():
            if month.lower() == month_name.lower():
                return month_number

    return None


def _format_percent(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0

    if number.is_integer():
        return f"{int(number)}%"

    return f"{number:.1f}%"


def _format_date(value: Any, *, include_time: bool = False) -> str:
    if value in (None, ""):
        return "-"

    if hasattr(value, "date"):
        local_value = timezone.localtime(value) if timezone.is_aware(value) else value
        value_date = local_value.date()
        time_text = local_value.strftime("%H:%M") if include_time else ""
    else:
        value_date = value
        time_text = ""

    day = value_date.day
    month_name = MONTH_NAMES.get(value_date.month, "")
    date_text = f"{day} {month_name} {value_date.year}"

    return f"{date_text}, {time_text}" if time_text else date_text


def _completion_band(value: Any) -> str:
    try:
        completion = float(value)
    except (TypeError, ValueError):
        completion = 0.0

    if completion >= 100:
        return "Complete"
    if completion >= 75:
        return "Near complete"
    if completion >= 25:
        return "Partial"
    return "Needs attention"


def _normalize_report_status(status: Any) -> str:
    status_text = str(status or "").upper()
    if status_text in {"SUBMITTED", "SKIPPED"}:
        return "SUBMITTED"
    if status_text in {"DRAFT", "INCOMPLETE"}:
        return "DRAFT"
    return "NOT_SUBMITTED"


def _monthly_status_label(item: dict[str, Any]) -> str:
    status = _normalize_report_status(item.get("report_status"))
    completion = float(item.get("completion") or 0)

    if status == "SUBMITTED" and completion >= 100:
        return "Submitted"
    if status == "SUBMITTED":
        return "Partial submission"
    if status == "DRAFT":
        return "Draft"
    return "Not submitted"


def _section_marker(section: dict[str, Any] | None) -> str:
    status = str((section or {}).get("status") or "MISSING").upper()
    if status == "SUBMITTED":
        return "SUB"
    if status == "SKIPPED":
        return "SKP"
    return "MIS"


def _section_status_text(sections: dict[str, Any]) -> str:
    markers = [
        f"{SECTION_LABELS[section]}: {_section_marker(sections.get(section))}"
        for section in SECTION_ORDER
    ]
    return "   ".join(markers)


def _submitted_on_text(item: dict[str, Any]) -> str:
    submitted_at = item.get("submitted_at")
    due_date = item.get("due_date")
    lines = []

    if submitted_at:
        lines.append(_format_date(submitted_at))
        if item.get("is_late"):
            days_late = int(item.get("days_late") or 0)
            suffix = "day" if days_late == 1 else "days"
            lines.append(f"Late by {days_late} {suffix}")
    else:
        lines.append("-")
        if due_date:
            lines.append(f"Due {_format_date(due_date)}")

    return "<br/>".join(escape(line) for line in lines)


def _period_label(year: int, from_month: int, to_month: int) -> str:
    if from_month == to_month:
        return f"{MONTH_NAMES[from_month]} {year}"

    return f"{MONTH_NAMES[from_month]}-{MONTH_NAMES[to_month]} {year}"


def _validate_period(query_params) -> tuple[int, int, int]:
    today = timezone.localdate()
    year = _int_param(query_params, "year", today.year)
    from_month = _int_param(query_params, "from_month", today.month)
    to_month = _int_param(query_params, "to_month", from_month)

    if year is None or from_month is None or to_month is None:
        raise ValidationError("A reporting year and month range are required.")

    if year > today.year:
        raise ValidationError(
            "Monthly compliance reports cannot be generated for future periods."
        )

    if from_month < 1 or from_month > 12 or to_month < 1 or to_month > 12:
        raise ValidationError("Month values must be between 1 and 12.")

    if from_month > to_month:
        raise ValidationError(
            "The end month must be the same as or after the start month."
        )

    if year == today.year and to_month > today.month:
        raise ValidationError(
            "Monthly compliance reports cannot be generated for future periods."
        )

    return year, from_month, to_month


def _user_can_access_region(user, region: Region) -> bool:
    if not user or not user.is_authenticated:
        return False

    if getattr(user, "is_superuser", False) or getattr(user, "is_admin", False):
        return True

    if getattr(user, "is_db_staff", False):
        return True

    assigned_regions = getattr(user, "assigned_regions", None)
    if assigned_regions is not None and assigned_regions.filter(pk=region.pk).exists():
        return True

    return False


def _visible_zone_ids(user, region: Region) -> set[int] | None:
    assigned_regions = getattr(user, "assigned_regions", None)
    has_region_access = (
        assigned_regions is not None
        and assigned_regions.filter(pk=region.pk).exists()
    )

    if (
        getattr(user, "is_superuser", False)
        or getattr(user, "is_admin", False)
        or getattr(user, "is_db_staff", False)
        or has_region_access
    ):
        return None

    assigned_zones = getattr(user, "assigned_zones", None)
    if assigned_zones is None:
        return set()

    return set(
        assigned_zones.filter(region=region).values_list("id", flat=True)
    )


def _scope_rows(
    *,
    region: Region,
    user,
    year: int,
    zone_id: int | None,
    country: str | None,
) -> tuple[list[dict[str, Any]], Zone | None]:
    visible_zone_ids = _visible_zone_ids(user, region)
    selected_zone = None

    if zone_id is not None:
        selected_zone = Zone.objects.filter(pk=zone_id, region=region).first()
        if selected_zone is None:
            raise ValidationError({"zone_id": "Select a zone in the requested region."})

        if visible_zone_ids is not None and selected_zone.id not in visible_zone_ids:
            raise PermissionDenied("You do not have access to the selected zone.")

    rows = []
    for assembly, reports in get_region_reports(region=region, year=year):
        assembly_zone_id = getattr(assembly, "zone_id", None)
        if visible_zone_ids is not None and assembly_zone_id not in visible_zone_ids:
            continue

        if selected_zone is not None and assembly_zone_id != selected_zone.id:
            continue

        assembly_country = (assembly.country or "Unknown").strip()
        if country and assembly_country.lower() != country.strip().lower():
            continue

        rows.append(
            build_assembly_compliance_row(
                assembly,
                reports,
                country=assembly_country,
                year=year,
            )
        )

    rows.sort(
        key=lambda row: (
            str(row.get("country") or "").lower(),
            str(row.get("zone") or "").lower(),
            str(row.get("name") or "").lower(),
        )
    )

    return rows, selected_zone


def _selected_month_items(
    row: dict[str, Any],
    *,
    from_month: int,
    to_month: int,
) -> list[dict[str, Any]]:
    items = []
    for item in row.get("monthly_compliance", []):
        month_number = _parse_period_month(item)
        if month_number is None:
            continue

        if from_month <= month_number <= to_month:
            items.append({**item, "month_number": month_number})

    return sorted(items, key=lambda item: item["month_number"])


def _records_by_month(
    rows: list[dict[str, Any]],
    *,
    from_month: int,
    to_month: int,
) -> dict[int, list[tuple[dict[str, Any], dict[str, Any]]]]:
    records = {month: [] for month in range(from_month, to_month + 1)}

    for row in rows:
        for item in _selected_month_items(
            row,
            from_month=from_month,
            to_month=to_month,
        ):
            records[item["month_number"]].append((row, item))

    return records


def _summary_metrics(
    *,
    rows: list[dict[str, Any]],
    records: dict[int, list[tuple[dict[str, Any], dict[str, Any]]]],
    month_count: int,
) -> dict[str, Any]:
    monthly_items = [item for month_records in records.values() for _, item in month_records]
    submitted = sum(
        1 for item in monthly_items
        if _normalize_report_status(item.get("report_status")) == "SUBMITTED"
    )
    not_submitted = sum(
        1 for item in monthly_items
        if _normalize_report_status(item.get("report_status")) == "NOT_SUBMITTED"
    )
    draft = sum(
        1 for item in monthly_items
        if _normalize_report_status(item.get("report_status")) == "DRAFT"
    )
    average_completion = (
        sum(float(item.get("completion") or 0) for item in monthly_items)
        / len(monthly_items)
        if monthly_items else 0
    )

    return {
        "Assemblies included": len(rows),
        "Assembly-month records expected": len(rows) * month_count,
        "Submitted reports": submitted,
        "Not submitted reports": not_submitted,
        "Draft reports": draft,
        "Average completion": _format_percent(average_completion),
        "Fully compliant assembly-months": sum(
            1
            for item in monthly_items
            if _normalize_report_status(item.get("report_status")) == "SUBMITTED"
            and float(item.get("completion") or 0) >= 100
        ),
        "Late submissions": sum(1 for item in monthly_items if item.get("is_late")),
    }


def _scope_text(
    *,
    selected_zone: Zone | None,
    country: str | None,
    assembly_count: int,
) -> str:
    parts = []
    if selected_zone is not None:
        parts.append(selected_zone.name)
    if country:
        parts.append(country)
    if not parts:
        return f"All assemblies ({assembly_count})"

    parts.append(f"{assembly_count} assemblies")
    return " - ".join(parts)


def _filename(
    *,
    region: Region,
    year: int,
    from_month: int,
    to_month: int,
    selected_zone: Zone | None,
    country: str | None,
) -> str:
    parts = [
        "regional-compliance",
        _slug(region.name),
        str(year),
        _slug(MONTH_NAMES[from_month]),
    ]

    if from_month != to_month:
        parts.append(_slug(MONTH_NAMES[to_month]))

    if selected_zone is not None:
        parts.append(_slug(selected_zone.name))

    if country:
        parts.append(_slug(country))

    return f"{'-'.join(parts)}.pdf"


def _p(text: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(text if text is not None else "")), style)


def _html_p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#0F172A"),
            spaceBefore=8,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodySmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1E293B"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodySmallBold",
            parent=styles["BodySmall"],
            fontName="Helvetica-Bold",
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableHeader",
            parent=styles["BodySmallBold"],
            alignment=TA_CENTER,
            textColor=colors.white,
        )
    )
    styles.add(
        ParagraphStyle(
            name="RightSmall",
            parent=styles["BodySmall"],
            alignment=TA_RIGHT,
        )
    )
    return styles


def _add_summary_table(elements, styles, summary: dict[str, Any]):
    data = []
    entries = list(summary.items())
    for index in range(0, len(entries), 2):
        left_key, left_value = entries[index]
        right_key, right_value = entries[index + 1] if index + 1 < len(entries) else ("", "")
        data.append([
            _p(left_key, styles["BodySmallBold"]),
            _p(left_value, styles["RightSmall"]),
            _p(right_key, styles["BodySmallBold"]),
            _p(right_value, styles["RightSmall"]),
        ])

    table = Table(data, colWidths=[68 * mm, 26 * mm, 68 * mm, 26 * mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)


def _month_summary(records: list[tuple[dict[str, Any], dict[str, Any]]]) -> dict[str, Any]:
    items = [item for _, item in records]
    submitted = sum(
        1 for item in items
        if _normalize_report_status(item.get("report_status")) == "SUBMITTED"
    )
    draft = sum(
        1 for item in items
        if _normalize_report_status(item.get("report_status")) == "DRAFT"
    )
    not_submitted = sum(
        1 for item in items
        if _normalize_report_status(item.get("report_status")) == "NOT_SUBMITTED"
    )
    average_completion = (
        sum(float(item.get("completion") or 0) for item in items) / len(items)
        if items else 0
    )

    return {
        "Assemblies": len(records),
        "Submitted": submitted,
        "Draft": draft,
        "Not submitted": not_submitted,
        "Average completion": _format_percent(average_completion),
        "Late submissions": sum(1 for item in items if item.get("is_late")),
    }


def _add_month_section(
    elements,
    styles,
    *,
    month: int,
    year: int,
    records: list[tuple[dict[str, Any], dict[str, Any]]],
):
    elements.append(_p(f"{MONTH_NAMES[month]} {year}", styles["SectionTitle"]))

    summary = _month_summary(records)
    summary_text = "   ".join(f"{key}: {value}" for key, value in summary.items())
    elements.append(_p(summary_text, styles["BodySmall"]))
    elements.append(_p("SUB = Submitted   MIS = Missing   SKP = Skipped", styles["BodySmall"]))
    elements.append(Spacer(1, 4))

    header = [
        _p("Assembly", styles["TableHeader"]),
        _p("Zone", styles["TableHeader"]),
        _p("Country", styles["TableHeader"]),
        _p("Report fields", styles["TableHeader"]),
        _p("Completion", styles["TableHeader"]),
        _p("Report status", styles["TableHeader"]),
        _p("Submitted on", styles["TableHeader"]),
    ]
    data = [header]

    for row, item in records:
        completion = item.get("completion") or 0
        data.append([
            _p(row.get("name", ""), styles["BodySmall"]),
            _p(row.get("zone", ""), styles["BodySmall"]),
            _p(row.get("country", ""), styles["BodySmall"]),
            _p(_section_status_text(item.get("sections") or {}), styles["BodySmall"]),
            _html_p(
                f"{escape(_format_percent(completion))}<br/>{escape(_completion_band(completion))}",
                styles["BodySmall"],
            ),
            _p(_monthly_status_label(item), styles["BodySmall"]),
            _html_p(_submitted_on_text(item), styles["BodySmall"]),
        ])

    table = Table(
        data,
        colWidths=[33 * mm, 22 * mm, 24 * mm, 76 * mm, 24 * mm, 28 * mm, 30 * mm],
        repeatRows=1,
        splitByRow=True,
    )
    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]

    for row_index, (_, item) in enumerate(records, start=1):
        if row_index % 2 == 0:
            table_style.append(
                ("BACKGROUND", (0, row_index), (-1, row_index), colors.HexColor("#F8FAFC"))
            )

        status = _normalize_report_status(item.get("report_status"))
        if status == "SUBMITTED":
            status_color = colors.HexColor("#DCFCE7")
        elif status == "DRAFT":
            status_color = colors.HexColor("#FEF3C7")
        else:
            status_color = colors.HexColor("#FEE2E2")
        table_style.append(("BACKGROUND", (5, row_index), (5, row_index), status_color))

    table.setStyle(TableStyle(table_style))
    elements.append(table)


def _skipped_appendix_rows(
    records: dict[int, list[tuple[dict[str, Any], dict[str, Any]]]],
    *,
    year: int,
) -> list[list[Any]]:
    rows = []
    for month, month_records in records.items():
        for assembly, item in month_records:
            sections = item.get("sections") or {}
            for section_code in SECTION_ORDER:
                section = sections.get(section_code) or {}
                if str(section.get("status") or "").upper() != "SKIPPED":
                    continue

                reason = section.get("skip_reason")
                if not reason:
                    continue

                rows.append([
                    f"{MONTH_NAMES[month]} {year}",
                    assembly.get("name", ""),
                    SECTION_NAMES[section_code],
                    str(reason).replace("_", " ").title(),
                ])

    return rows


def _add_skipped_appendix(elements, styles, skipped_rows: list[list[Any]]):
    if not skipped_rows:
        return

    elements.append(PageBreak())
    elements.append(_p("Skipped Section Details", styles["SectionTitle"]))

    data = [[
        _p("Month", styles["TableHeader"]),
        _p("Assembly", styles["TableHeader"]),
        _p("Section", styles["TableHeader"]),
        _p("Skip reason", styles["TableHeader"]),
    ]]
    for row in skipped_rows:
        data.append([_p(value, styles["BodySmall"]) for value in row])

    table = Table(
        data,
        colWidths=[34 * mm, 58 * mm, 40 * mm, 92 * mm],
        repeatRows=1,
        splitByRow=True,
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)


def _record_audit_event(
    *,
    user,
    region: Region,
    zone_id: int | None,
    country: str | None,
    year: int,
    from_month: int,
    to_month: int,
    assembly_count: int,
):
    content_type = ContentType.objects.get_for_model(Region)
    AuditLog.objects.create(
        user=user,
        content_type=content_type,
        object_id=region.pk,
        content_object=region,
        action=AuditLog.Action.CREATE,
        description="REGIONAL_COMPLIANCE_REPORT_DOWNLOADED",
        new_data={
            "action": "REGIONAL_COMPLIANCE_REPORT_DOWNLOADED",
            "region_id": region.pk,
            "zone_id": zone_id,
            "country": country,
            "year": year,
            "from_month": from_month,
            "to_month": to_month,
            "assembly_count": assembly_count,
            "generated_by": getattr(user, "id", None),
        },
    )


def build_regional_monthly_compliance_pdf(
    *,
    region: Region,
    user,
    query_params,
) -> RegionalCompliancePdfResult:
    if not _user_can_access_region(user, region):
        raise PermissionDenied("You do not have access to this region.")

    year, from_month, to_month = _validate_period(query_params)
    zone_id = _int_param(query_params, "zone_id")
    country = query_params.get("country") or None

    rows, selected_zone = _scope_rows(
        region=region,
        user=user,
        year=year,
        zone_id=zone_id,
        country=country,
    )

    if not rows:
        raise ValidationError("No assemblies are available for the selected report scope.")

    records = _records_by_month(rows, from_month=from_month, to_month=to_month)
    month_count = to_month - from_month + 1
    total_records = sum(len(month_records) for month_records in records.values())

    if total_records == 0:
        raise ValidationError(
            "No monthly compliance data is available for the selected reporting period."
        )

    generated_at = timezone.localtime(timezone.now())
    styles = _build_styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=20 * mm,
        title="Regional Monthly Compliance Report",
    )

    generated_by = getattr(user, "full_name", None) or str(user)
    scope = _scope_text(
        selected_zone=selected_zone,
        country=country,
        assembly_count=len(rows),
    )

    elements = [
        _p("CFI Database", styles["BodySmallBold"]),
        _p("Regional Monthly Compliance Report", styles["ReportTitle"]),
        _p(f"Region: {region.name}", styles["BodySmall"]),
        _p(f"Scope: {scope}", styles["BodySmall"]),
        _p(f"Reporting period: {_period_label(year, from_month, to_month)}", styles["BodySmall"]),
        _p(f"Generated: {_format_date(generated_at, include_time=True)}", styles["BodySmall"]),
        _p(f"Generated by: {generated_by}", styles["BodySmall"]),
        Spacer(1, 8),
        _p("Report Summary", styles["SectionTitle"]),
    ]

    _add_summary_table(
        elements,
        styles,
        _summary_metrics(rows=rows, records=records, month_count=month_count),
    )

    for month in range(from_month, to_month + 1):
        elements.append(PageBreak())
        _add_month_section(
            elements,
            styles,
            month=month,
            year=year,
            records=records[month],
        )

    _add_skipped_appendix(
        elements,
        styles,
        _skipped_appendix_rows(records, year=year),
    )

    doc.build(elements, canvasmaker=NumberedCanvas)
    buffer.seek(0)

    _record_audit_event(
        user=user,
        region=region,
        zone_id=zone_id,
        country=country,
        year=year,
        from_month=from_month,
        to_month=to_month,
        assembly_count=len(rows),
    )

    return RegionalCompliancePdfResult(
        buffer=buffer,
        filename=_filename(
            region=region,
            year=year,
            from_month=from_month,
            to_month=to_month,
            selected_zone=selected_zone,
            country=country,
        ),
    )
