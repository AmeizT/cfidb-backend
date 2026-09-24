"""Canonical lifecycle section states used by both PDF chips and completion."""
from apps.reports.models.section_status import ReportSectionStatus
from apps.reports.services.lifecycle import get_report_sections, is_section_required
from apps.reports.models import AssemblyReport

Section = ReportSectionStatus.Section
Status = ReportSectionStatus.Status

# Presentation groups only: EX contains two independently required backend sections.
PDF_SECTION_MAP = (
    ("AT", "Attendance", (Section.GENERAL_ATTENDANCE,)),
    ("SAT", "Sunday School Attendance", (Section.SUNDAY_SCHOOL_ATTENDANCE,)),
    ("TI", "Tithes", (Section.TITHES,)),
    ("IN", "Income", (Section.REVENUE,)),
    ("EX", "Expenses", (Section.OPERATING_EXPENSES, Section.ACTIVITY_OTHER_EXPENSES)),
    ("RM", "Remittance", ()),  # Not a ReportSectionStatus.Section.
)


def section_state(section):
    status = str((section or {}).get("status", Status.NOT_STARTED)).lower()
    if status in {Status.COMPLETED, Status.NO_ACTIVITY}:
        return "present"
    if status == Status.IN_PROGRESS:
        return "progress"
    if status == Status.SKIPPED:
        return "skipped"
    if status == "not_required":
        return "unavailable"
    return "missing"


def resolve_section_display(sections):
    states = {key: section_state(sections.get(key)) for key in Section.values}
    required = [state for state in states.values() if state != "unavailable"]
    completion = round(100 * required.count("present") / len(required), 2) if required else 0
    badges = []
    for label, _name, keys in PDF_SECTION_MAP:
        group = [states[key] for key in keys if states[key] != "unavailable"]
        if not group:
            state = "unavailable"
        elif len(set(group)) == 1:
            state = group[0]
        elif "skipped" in group:
            state = "skipped"
        else:
            state = "progress"
        badges.append((label, state))
    return badges, completion


def resolved_report_sections(report):
    """Read effective statuses without persisting or inferring from report.status."""
    return {
        item["key"]: {
            "status": item["status"],
            "skip_reason": item["object"].skip_reason,
        }
        for item in get_report_sections(report)
    }


def missing_report_sections(period_start):
    report = AssemblyReport(period_start=period_start)
    return {
        key: {"status": Status.NOT_STARTED if is_section_required(report, key) else "not_required"}
        for key in Section.values
    }
