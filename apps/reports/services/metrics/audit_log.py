from __future__ import annotations

from typing import Any

from django.db.models import QuerySet

from apps.reports.models.section_status import ReportSectionStatus
from apps.reports.services.compliance_calculator import derive_report_status


def get_skipped_sections_audit_log(
    *,
    region_id: int | None = None,
    zone_id: int | None = None,
    country: str | None = None,
    assembly_id: int | None = None,
    reason: str | None = None,
    follow_up_status: str | None = None,
    year: int | None = None,
) -> QuerySet[ReportSectionStatus]:
    qs = (
        ReportSectionStatus.objects
        .filter(status=ReportSectionStatus.Status.SKIPPED)
        .select_related(
            "report",
            "report__assembly",
            "report__assembly__zone",
            "report__assembly__zone__region",
            "follow_up_assigned_to",
        )
        .prefetch_related("report__sections")
    )

    if region_id is not None:
        qs = qs.filter(report__assembly__zone__region_id=region_id)
    if zone_id is not None:
        qs = qs.filter(report__assembly__zone_id=zone_id)
    if country:
        qs = qs.filter(report__assembly__country__iexact=country)
    if assembly_id is not None:
        qs = qs.filter(report__assembly_id=assembly_id)
    if reason:
        qs = qs.filter(skip_reason=reason)
    if follow_up_status:
        qs = qs.filter(follow_up_status=follow_up_status)
    if year is not None:
        qs = qs.filter(report__period_start__year=year)

    return qs.order_by("-report__period_start", "report__assembly__name", "section")


def _user_label(user) -> str | None:
    if user is None:
        return None

    get_full_name = getattr(user, "get_full_name", None)
    if callable(get_full_name):
        name = get_full_name()
        if name:
            return name

    return getattr(user, "email", None) or str(user)


def serialize_audit_log_row(section: ReportSectionStatus) -> dict[str, Any]:
    report = section.report
    assembly = report.assembly
    zone = assembly.zone
    region = zone.region if zone else None

    return {
        "section_id": section.id,
        "report_id": report.id,
        "assembly_id": assembly.id,
        "assembly_name": assembly.name,
        "zone_id": zone.id if zone else None,
        "zone": zone.name if zone else None,
        "region_id": region.id if region else None,
        "region": region.name if region else None,
        "country": assembly.country,
        "period": report.period_start.isoformat(),
        "month": report.period_start.month,
        "year": report.period_start.year,
        "section_skipped": section.section,
        "reason_for_skipping": (
            section.get_skip_reason_display() if section.skip_reason else None
        ),
        "skip_reason": section.skip_reason,
        "skip_notes": section.skip_notes,
        "skipped_at": section.updated_at,
        "follow_up_status": section.follow_up_status.upper(),
        "follow_up_action": section.follow_up_status.upper(),
        "follow_up_notes": section.follow_up_notes,
        "follow_up_assigned_to": _user_label(section.follow_up_assigned_to),
        "report_status": derive_report_status(report.sections.all()),
        "workflow_status": (report.status or "").upper(),
        "is_late_submission": bool(getattr(report, "is_late", False)),
        "days_late": getattr(report, "days_late", None),
        "due_date": getattr(report, "due_date", None),
        "submitted_at": report.submitted_at,
    }


def build_audit_log_payload(
    *,
    region_id: int | None = None,
    zone_id: int | None = None,
    country: str | None = None,
    assembly_id: int | None = None,
    reason: str | None = None,
    follow_up_status: str | None = None,
    year: int | None = None,
) -> dict[str, Any]:
    rows = [
        serialize_audit_log_row(section)
        for section in get_skipped_sections_audit_log(
            region_id=region_id,
            zone_id=zone_id,
            country=country,
            assembly_id=assembly_id,
            reason=reason,
            follow_up_status=follow_up_status,
            year=year,
        )
    ]

    by_reason: dict[str, int] = {}
    by_assembly: dict[str, int] = {}
    by_follow_up_status: dict[str, int] = {}
    unresolved_count = 0

    for row in rows:
        reason_label = row["reason_for_skipping"] or "Unspecified"
        by_reason[reason_label] = by_reason.get(reason_label, 0) + 1
        by_assembly[row["assembly_name"]] = by_assembly.get(row["assembly_name"], 0) + 1
        by_follow_up_status[row["follow_up_status"]] = (
            by_follow_up_status.get(row["follow_up_status"], 0) + 1
        )

        if row["follow_up_status"] != ReportSectionStatus.FollowUpStatus.RESOLVED.upper():
            unresolved_count += 1

    return {
        "results": rows,
        "summary": {
            "total_skipped_sections": len(rows),
            "by_reason": by_reason,
            "by_assembly": by_assembly,
            "by_follow_up_status": by_follow_up_status,
            "unresolved_count": unresolved_count,
        },
    }
