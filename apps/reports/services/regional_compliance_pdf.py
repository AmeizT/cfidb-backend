from __future__ import annotations

from dataclasses import dataclass
from html import escape
from io import BytesIO
import re
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Flowable,
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

SECTION_ORDER = ["attendance", "sunday_school_attendance", "tithes", "income", "expenditure", "remittance"]
SECTION_LABELS = dict(zip(SECTION_ORDER, ["AT", "SAT", "TI", "IN", "EX", "RM"]))
SECTION_NAMES = dict(zip(SECTION_ORDER, ["Attendance", "Sunday School Attendance", "Tithes", "Income", "Expenses", "Remittance"]))
SECTION_NAMES.update({
    "general_attendance": "Attendance", "revenue": "Income",
    "operating_expenses": "Operating Expenses", "activity_other_expenses": "Activity & Other Expenses",
    "junior_members": "Junior Members",
})


def _section_state(section):
    value = section.get("status") if isinstance(section, dict) else section
    status = str(value or "MISSING").upper()
    if status in {"SUBMITTED", "SUB", "COMPLETED", "NO_ACTIVITY", "PRESENT"}:
        return "present"
    if status in {"DRAFT", "IN_PROGRESS", "INCOMPLETE"}:
        return "progress"
    if status in {"SKIPPED", "SKP"}:
        return "skipped"
    return "missing"


def _badge_entries(sections):
    # Display aliases only. Never recalculate completion or report status here.
    entries = []
    aliases = {"attendance": "general_attendance", "income": "revenue"}
    for key in SECTION_ORDER:
        source_key = aliases.get(key, key)
        if source_key in sections:
            state = _section_state(sections[source_key])
        elif key in sections:
            state = _section_state(sections[key])
        elif key == "expenditure" and any(k in sections for k in ("operating_expenses", "activity_other_expenses")):
            states = [_section_state(sections.get(k)) for k in ("operating_expenses", "activity_other_expenses")]
            state = states[0] if states[0] == states[1] else "skipped" if "skipped" in states else "progress"
        elif key == "remittance":
            # The current reporting schema has no remittance section. Absence
            # of a tracked field is not evidence of a missing submission.
            state = "unavailable"
        else:
            state = "missing"
        entries.append((SECTION_LABELS[key], state))
    return entries


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
        lines.append(f"Due {_format_date(due_date)}" if due_date else "-")

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


# Keep the renderer's existing sans-serif family (also the application's fallback).
CONTENT_WIDTH = 268 * mm
INK = colors.HexColor("#10213D")
MUTED = colors.HexColor("#64748B")
BORDER = colors.HexColor("#DFE7F1")
STATE_COLORS = {
    "present": (colors.HexColor("#DCF5E6"), colors.HexColor("#087443")),
    "progress": (colors.HexColor("#FFF0C4"), colors.HexColor("#9B6200")),
    "missing": (colors.HexColor("#FDE2E7"), colors.HexColor("#BC243C")),
    "skipped": (colors.HexColor("#EDF0F5"), colors.HexColor("#64748B")),
    "unavailable": (colors.HexColor("#EDF0F5"), colors.HexColor("#64748B")),
    "legend": (colors.HexColor("#EAF2FF"), colors.HexColor("#284C83")),
}


def _build_styles():
    styles = getSampleStyleSheet()
    specs = {
        "ReportTitle": dict(fontName="Helvetica-Bold", fontSize=25, leading=30, textColor=INK, alignment=TA_LEFT, spaceAfter=0),
        "SectionTitle": dict(fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=INK, spaceAfter=8),
        "BodySmall": dict(fontName="Helvetica", fontSize=8.5, leading=11.5, textColor=INK),
        "BodySmallBold": dict(fontName="Helvetica-Bold", fontSize=8.5, leading=11.5, textColor=INK),
        "TableHeader": dict(fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=colors.white),
        "RightSmall": dict(fontName="Helvetica", fontSize=10, leading=13, textColor=INK, alignment=TA_RIGHT),
        "Muted": dict(fontName="Helvetica", fontSize=8, leading=11, textColor=MUTED),
        "Subtitle": dict(fontName="Helvetica", fontSize=11, leading=15, textColor=MUTED),
        "MetricValue": dict(fontName="Helvetica-Bold", fontSize=25, leading=30, textColor=INK),
        "Legend": dict(fontName="Helvetica", fontSize=7.5, leading=10, textColor=INK),
    }
    for name, values in specs.items():
        styles.add(ParagraphStyle(name=name, **values))
    return styles


class SectionBadges(Flowable):
    """Vector chips with fixed dimensions, wrapping as a group if needed."""
    badge_width = 25
    badge_height = 18
    gap = 3

    def __init__(self, entries):
        super().__init__()
        self.entries = entries
        self.columns = len(entries)

    def wrap(self, available_width, available_height):
        self.columns = max(1, min(len(self.entries), int((available_width + self.gap) // (self.badge_width + self.gap))))
        self.width = self.columns * (self.badge_width + self.gap) - self.gap
        rows = (len(self.entries) + self.columns - 1) // self.columns
        self.height = rows * (self.badge_height + self.gap) - self.gap
        return self.width, self.height

    def draw(self):
        c = self.canv
        for index, (label, state) in enumerate(self.entries):
            x = (index % self.columns) * (self.badge_width + self.gap)
            y = self.height - self.badge_height - (index // self.columns) * (self.badge_height + self.gap)
            background, foreground = STATE_COLORS[state]
            c.setFillColor(background)
            c.roundRect(x, y, self.badge_width, self.badge_height, 4, stroke=0, fill=1)
            c.setFillColor(foreground)
            c.setFont("Helvetica-Bold", 7)
            c.drawCentredString(x + self.badge_width / 2, y + (9 if state == "unavailable" else 6), label)
            if state == "unavailable":
                c.setFont("Helvetica", 5)
                c.drawCentredString(x + self.badge_width / 2, y + 3, "N/A")
            if state == "skipped":
                c.setLineWidth(0.5)
                c.line(x + 5, y + 4, x + self.badge_width - 5, y + 4)


def _add_report_header(elements, styles, title, period):
    heading = Table([[_p(title, styles["ReportTitle"]), _p(period, styles["RightSmall"])]], colWidths=[CONTENT_WIDTH - 145, 145])
    heading.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    elements.extend([heading, _p("Track report submission status for all assemblies in the region.", styles["Subtitle"]), Spacer(1, 18)])


def _add_report_details(elements, styles, details):
    cells = []
    for label, value in details:
        cells.append([_p(label, styles["Muted"]), Spacer(1, 6), _p(value, styles["BodySmallBold"])])
    table = Table([[ _p("Report details", styles["SectionTitle"]), "", "", "", "" ], cells], colWidths=[CONTENT_WIDTH * n for n in [.23, .22, .18, .20, .17]])
    table.setStyle(TableStyle([
        ("SPAN", (0, 0), (-1, 0)), ("BOX", (0, 0), (-1, -1), .6, BORDER),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LINEAFTER", (0, 1), (3, 1), .5, BORDER),
    ]))
    elements.extend([table, Spacer(1, 24)])


def _add_summary_table(elements, styles, summary):
    entries = list(summary.items())
    rows = []
    card_width = (CONTENT_WIDTH - 30) / 4
    for start in range(0, len(entries), 4):
        cards = []
        for label, value in entries[start:start + 4]:
            card = Table([
                [_p(label, styles["Muted"])],
                [_p(value, styles["MetricValue"])],
            ], colWidths=[card_width], minRowHeights=[36, 42])
            card.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), .6, BORDER),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFCFF")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]))
            if cards:
                cards.append("")
            cards.append(card)
        rows.append(cards)
        if start == 0:
            rows.append([""] * 7)
    grid = Table(rows, colWidths=[card_width, 10, card_width, 10, card_width, 10, card_width], rowHeights=[None, 12, None])
    grid.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(grid)


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


def _add_section_legend(elements, styles):
    sections = []
    for key in SECTION_ORDER:
        sections.append([SectionBadges([(SECTION_LABELS[key], "legend")]), _p("Expenses (combined)" if key == "expenditure" else SECTION_NAMES[key], styles["Legend"])])
    legend = Table([sum(sections[:3], []), sum(sections[3:], [])], colWidths=[31, 112, 31, 112, 31, 112])
    legend.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    status_lines = []
    for label, state in [("Submitted / Present", "present"), ("Draft / In progress", "progress"), ("Missing", "missing")]:
        foreground = STATE_COLORS[state][1].hexval().replace("0x", "#")
        status_lines.append(_html_p(f'<font size="12" color="{foreground}"><b>•</b></font>  {label}', styles["Legend"]))
    status_lines.append(Spacer(1, 4))
    status_lines.append(_p("Grey N/A = not tracked; underlined = skipped", styles["Legend"]))
    outer = Table([
        [_p("Report Sections", styles["BodySmallBold"]), _p("Status key", styles["BodySmallBold"])],
        [legend, status_lines],
    ], colWidths=[CONTENT_WIDTH * .65, CONTENT_WIDTH * .35])
    outer.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), .6, BORDER),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBEFORE", (1, 0), (1, -1), .5, BORDER),
    ]))
    elements.extend([outer, Spacer(1, 13)])


def _add_month_section(elements, styles, *, month, year, records):
    _add_report_header(elements, styles, "Compliance Reports", f"{MONTH_NAMES[month]} {year}")
    summary = _month_summary(records)
    elements.extend([_p("   |   ".join(f"{key}: {value}" for key, value in summary.items()), styles["Muted"]), Spacer(1, 12)])
    _add_section_legend(elements, styles)
    header = [_p(label, styles["TableHeader"]) for label in ["Assembly", "Zone", "Country", "Sections", "Completion", "Report status", "Submitted on"]]
    data = [header]
    for row, item in records:
        completion = float(item.get("completion") or 0)
        state = "present" if completion >= 100 else "progress" if completion > 0 else "missing"
        band = "Complete" if completion >= 100 else "In progress" if completion > 0 else "Needs attention"
        foreground = STATE_COLORS[state][1].hexval().replace("0x", "#")
        data.append([
            _p(row.get("name", ""), styles["BodySmallBold"]),
            _p(row.get("zone", ""), styles["BodySmall"]),
            _p(row.get("country", ""), styles["BodySmall"]),
            SectionBadges(_badge_entries(item.get("sections") or {})),
            _html_p(f'<font color="{foreground}"><b>{escape(_format_percent(completion))}</b></font><br/><font color="#64748B">{band}</font>', styles["BodySmall"]),
            _p(_monthly_status_label(item), styles["BodySmall"]),
            _html_p(_submitted_on_text(item), styles["BodySmall"]),
        ])
    table = Table(data, colWidths=[n * mm for n in [42, 24, 28, 67, 32, 36, 39]], repeatRows=1, splitByRow=True, splitInRow=False, minRowHeights=[29] + [35] * len(records))
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3C4D65")),
        ("GRID", (0, 0), (-1, -1), .35, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]
    for index, (_, item) in enumerate(records, 1):
        commands.append(("BACKGROUND", (0, index), (-1, index), colors.white if index % 2 else colors.HexColor("#F7F9FC")))
        status = _normalize_report_status(item.get("report_status"))
        state = "present" if status == "SUBMITTED" else "progress" if status == "DRAFT" else "missing"
        commands.append(("BACKGROUND", (5, index), (5, index), STATE_COLORS[state][0]))
    table.setStyle(TableStyle(commands))
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
            for section_code, section in sections.items():
                section = section or {}
                if str(section.get("status") or "").upper() != "SKIPPED":
                    continue

                reason = section.get("skip_reason")
                if not reason:
                    continue

                rows.append([
                    f"{MONTH_NAMES[month]} {year}",
                    assembly.get("name", ""),
                    SECTION_NAMES.get(section_code, section_code.replace("_", " ").title()),
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
        colWidths=[40 * mm, 78 * mm, 62 * mm, 88 * mm],
        minRowHeights=[29] + [30] * len(skipped_rows),
        repeatRows=1,
        splitByRow=True,
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3C4D65")),
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

    elements = [_p("CFI Database", styles["BodySmallBold"]), Spacer(1, 22)]
    _add_report_header(elements, styles, "Regional Monthly Compliance Report", _period_label(year, from_month, to_month))
    elements.append(Spacer(1, 10))
    _add_report_details(elements, styles, [
        ("Region", region.name), ("Scope", scope),
        ("Reporting period", _period_label(year, from_month, to_month)),
        ("Generated", _format_date(generated_at, include_time=True)),
        ("Generated by", generated_by),
    ])
    elements.append(_p("Report Summary", styles["SectionTitle"]))
    elements.append(Spacer(1, 6))

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

    def page_background(c, _doc):
        c.saveState()
        c.setFillColor(colors.HexColor("#F8FAFD"))
        c.rect(0, 0, *_doc.pagesize, fill=1, stroke=0)
        c.restoreState()

    doc.build(elements, canvasmaker=NumberedCanvas, onFirstPage=page_background, onLaterPages=page_background)
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
