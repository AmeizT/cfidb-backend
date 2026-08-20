from __future__ import annotations

import calendar
from collections import Counter, defaultdict
from typing import Any, Iterable

from apps.reports.models.section_status import ReportSectionStatus


class ReportStatus:
    SUBMITTED = "SUBMITTED"
    INCOMPLETE = "INCOMPLETE"
    NOT_SUBMITTED = "NOT_SUBMITTED"
    SKIPPED = "SKIPPED"


_SECTION_STATUS = ReportSectionStatus.Status


def calculate_report_compliance(report):
    sections = list(report.sections.all())

    stats = Counter({status: 0 for status in ReportSectionStatus.Status.values})

    for section in sections:
        stats[section.status] += 1

    total = len(sections)
    submitted = stats["completed"] + stats["no_activity"]
    skipped = stats["skipped"]
    pending = stats["not_started"] + stats["in_progress"]

    progress = round(((submitted + skipped) / total) * 100, 2) if total else 0
    compliance_score = round((submitted / total) * 100, 2) if total else 0

    if total == 0:
        status = "NO_DATA"
    elif pending > 0:
        status = "IN_PROGRESS"
    elif skipped > 0:
        status = "PARTIALLY_COMPLIANT"
    else:
        status = "FULLY_COMPLIANT"

    return {
        "total_sections": total,
        "submitted": submitted,
        "skipped": skipped,
        "pending": pending,
        "progress": progress,
        "compliance_score": compliance_score,
        "status": status,
    }


def derive_report_status(sections: Iterable[ReportSectionStatus]) -> str:
    statuses = {section.status for section in sections}

    if not statuses or statuses == {_SECTION_STATUS.NOT_STARTED}:
        return ReportStatus.NOT_SUBMITTED

    if statuses == {_SECTION_STATUS.SKIPPED}:
        return ReportStatus.SKIPPED

    if statuses & {_SECTION_STATUS.NOT_STARTED, _SECTION_STATUS.IN_PROGRESS}:
        return ReportStatus.INCOMPLETE

    return ReportStatus.SUBMITTED


def derive_report_status_from_counts(
    *,
    submitted: int,
    skipped: int,
    pending: int,
    total: int,
) -> str:
    if total == 0 or (submitted == 0 and skipped == 0):
        return ReportStatus.NOT_SUBMITTED

    if skipped == total:
        return ReportStatus.SKIPPED

    if pending > 0:
        return ReportStatus.INCOMPLETE

    return ReportStatus.SUBMITTED


def _section_payload(section: ReportSectionStatus | None) -> dict[str, Any]:
    if section is None:
        return {"status": _SECTION_STATUS.NOT_STARTED.upper()}

    payload: dict[str, Any] = {"status": section.status.upper()}

    if section.status in {_SECTION_STATUS.COMPLETED, _SECTION_STATUS.NO_ACTIVITY}:
        payload["submitted_at"] = section.updated_at

    elif section.status == _SECTION_STATUS.SKIPPED:
        payload["skip_reason"] = section.skip_reason
        payload["skip_reason_display"] = (
            section.get_skip_reason_display() if section.skip_reason else None
        )
        payload["skip_notes"] = section.skip_notes
        payload["skipped_at"] = section.updated_at
        payload["follow_up_status"] = section.follow_up_status.upper()
        payload["follow_up_notes"] = section.follow_up_notes
        payload["follow_up_assigned_to"] = (
            section.follow_up_assigned_to_id
            if section.follow_up_assigned_to_id else None
        )

    return payload


def build_compliance(
    assembly,
    year: int,
    *,
    required_sections: list[str] | None = None,
) -> dict[str, Any]:
    if required_sections is None:
        required_sections = [choice[0] for choice in ReportSectionStatus.Section.choices]

    from apps.reports.models import AssemblyReport

    reports = (
        AssemblyReport.objects
        .filter(assembly=assembly, period_start__year=year)
        .prefetch_related("sections")
        .order_by("period_start")
    )

    return build_compliance_from_reports(
        assembly,
        list(reports),
        year,
        required_sections=required_sections,
    )


def build_compliance_from_reports(
    assembly,
    reports,
    year: int,
    *,
    required_sections: list[str] | None = None,
) -> dict[str, Any]:
    if required_sections is None:
        required_sections = [choice[0] for choice in ReportSectionStatus.Section.choices]

    reports_by_month = {
        report.period_start.month: report
        for report in sorted(reports, key=lambda item: item.period_start)
    }

    tracked_sections: list[dict[str, Any]] = []
    missing_by_section: dict[str, int] = defaultdict(int)
    skipped_by_section: dict[str, int] = defaultdict(int)
    pending_by_section: dict[str, int] = defaultdict(int)
    report_status_counts: Counter[str] = Counter()
    workflow_status_counts: Counter[str] = Counter()

    submitted_fields = 0
    skipped_fields = 0
    pending_fields = 0
    total_fields = 0
    total_completion = 0.0
    compliant_months = 0
    late_submissions = 0
    on_time_submissions = 0
    unresolved_follow_ups = 0
    total_days_late = 0
    max_days_late = 0

    for month in range(1, 13):
        report = reports_by_month.get(month)
        month_name = calendar.month_name[month]
        sections_payload: dict[str, Any] = {}
        month_submitted = 0
        month_skipped = 0
        month_pending = 0

        if report is None:
            for section_code in required_sections:
                sections_payload[section_code] = _section_payload(None)
                missing_by_section[section_code] += 1
                pending_by_section[section_code] += 1
                month_pending += 1
                total_fields += 1

            report_status = ReportStatus.NOT_SUBMITTED
            workflow_status = ReportStatus.NOT_SUBMITTED
            is_late_submission = False
            days_late = None
            due_date = None
            submitted_at = None
            created_at = None
            report_id = None

        else:
            sections_by_code = {section.section: section for section in report.sections.all()}

            for section_code in required_sections:
                section = sections_by_code.get(section_code)
                sections_payload[section_code] = _section_payload(section)
                total_fields += 1

                if section is None or section.status in {_SECTION_STATUS.NOT_STARTED, _SECTION_STATUS.IN_PROGRESS}:
                    missing_by_section[section_code] += 1
                    pending_by_section[section_code] += 1
                    month_pending += 1
                    continue

                if section.status in {_SECTION_STATUS.COMPLETED, _SECTION_STATUS.NO_ACTIVITY}:
                    month_submitted += 1
                    submitted_fields += 1
                    continue

                if section.status == _SECTION_STATUS.SKIPPED:
                    month_skipped += 1
                    skipped_fields += 1
                    skipped_by_section[section_code] += 1

                    if section.follow_up_status != ReportSectionStatus.FollowUpStatus.RESOLVED:
                        unresolved_follow_ups += 1

            report_status = derive_report_status_from_counts(
                submitted=month_submitted,
                skipped=month_skipped,
                pending=month_pending,
                total=len(required_sections),
            )
            workflow_status = (report.status or "").upper()
            is_late_submission = bool(getattr(report, "is_late", False))
            days_late = getattr(report, "days_late", None)
            due_date = getattr(report, "due_date", None)
            submitted_at = report.submitted_at
            created_at = report.created_at
            report_id = report.id

            if submitted_at:
                if is_late_submission:
                    late_submissions += 1
                    total_days_late += days_late or 0
                    max_days_late = max(max_days_late, days_late or 0)
                else:
                    on_time_submissions += 1

        pending_fields += month_pending
        report_status_counts[report_status] += 1
        workflow_status_counts[workflow_status] += 1

        progress = (
            round((month_submitted / len(required_sections)) * 100, 2)
            if required_sections else 0.0
        )
        coverage = (
            round(((month_submitted + month_skipped) / len(required_sections)) * 100, 2)
            if required_sections else 0.0
        )

        if report_status == ReportStatus.SUBMITTED:
            compliant_months += 1

        total_completion += progress
        tracked_sections.append({
            "month": month,
            "month_name": month_name,
            "report_id": report_id,
            "report_status": report_status,
            "workflow_status": workflow_status,
            "is_late_submission": is_late_submission,
            "days_late": days_late,
            "due_date": due_date,
            "submitted_at": submitted_at,
            "created_at": created_at,
            "is_leader_verified": getattr(report, "is_leader_verified", False) if report else False,
            "total_sections": len(required_sections),
            "submitted": month_submitted,
            "skipped": month_skipped,
            "pending": month_pending,
            "progress": progress,
            "coverage": coverage,
            "completion": progress,
            "sections": sections_payload,
        })

    missing_fields = total_fields - submitted_fields - skipped_fields
    reports_with_coverage = (
        sum(report_status_counts.values()) -
        report_status_counts.get(ReportStatus.NOT_SUBMITTED, 0)
    )
    timed_reports = late_submissions + on_time_submissions
    average_days_late = (
        round(total_days_late / late_submissions, 2)
        if late_submissions else 0.0
    )

    summary = {
        "average_completion": round(total_completion / 12, 2),
        "total_fields": float(total_fields),
        "submitted": float(submitted_fields),
        "skipped": float(skipped_fields),
        "pending": float(pending_fields),
        "missing": float(missing_fields),
        "overall": (
            round((submitted_fields / total_fields) * 100, 2)
            if total_fields else 0.0
        ),
        "coverage": (
            round(((submitted_fields + skipped_fields) / total_fields) * 100, 2)
            if total_fields else 0.0
        ),
        "compliant_months": float(compliant_months),
        "expected_reports": 12,
        "created_reports": len(reports),
        "submitted_reports": reports_with_coverage,
        "missing_reports": max(12 - reports_with_coverage, 0),
        "late_submissions": late_submissions,
        "on_time_submissions": on_time_submissions,
        "late_rate": (
            round((late_submissions / timed_reports) * 100, 2)
            if timed_reports else 0.0
        ),
        "average_days_late": average_days_late,
        "max_days_late": max_days_late,
        "unresolved_follow_ups": unresolved_follow_ups,
        "report_status_counts": dict(report_status_counts),
        "workflow_status_counts": dict(workflow_status_counts),
        "missing_by_section": dict(missing_by_section),
        "skipped_by_section": dict(skipped_by_section),
        "pending_by_section": dict(pending_by_section),
    }

    return {
        "assembly": assembly.id,
        "assembly_name": assembly.name,
        "year": year,
        "required_sections": required_sections,
        "months": tracked_sections,
        "tracked_sections": tracked_sections,
        "summary": summary,
    }
