from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F, Sum
from django.utils import timezone

from apps.people.constants import SUNDAY_SCHOOL_START_DATE
from apps.reports.models import (
    AssemblyReport,
    AuditLog,
    ReportReopeningRequest,
    ReportSectionSnapshot,
    ReportSectionStatus,
    ReportVersion,
)
from apps.reports.services.periods import report_period


GRACE_PERIOD_DAYS = 7
REQUIRED_SECTIONS = tuple(value for value, _label in ReportSectionStatus.Section.choices)
RESOLVED_SECTION_STATUSES = {
    ReportSectionStatus.Status.COMPLETED,
    ReportSectionStatus.Status.NO_ACTIVITY,
    ReportSectionStatus.Status.SKIPPED,
    "not_required",
}


@dataclass(frozen=True)
class ReportState:
    status: str
    is_overdue: bool
    is_locked: bool
    is_editable: bool
    can_submit: bool
    can_amend: bool
    can_request_reopen: bool
    can_approve_reopen: bool
    completion_percentage: int
    resolved_section_count: int
    required_section_count: int
    submitted_at: datetime | None
    editable_until: datetime | None
    due_at: datetime
    current_version: int | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def get_due_at(report: AssemblyReport) -> datetime:
    local_tz = timezone.get_current_timezone()
    return timezone.make_aware(datetime.combine(report.due_date, time.max), local_tz)


def _is_authenticated(user) -> bool:
    return bool(user and getattr(user, "is_authenticated", False))


def can_view_report(user, report: AssemblyReport) -> bool:
    if not _is_authenticated(user):
        return False
    if user.is_superuser or getattr(user, "is_admin", False) or getattr(user, "is_db_staff", False):
        return True
    if getattr(user, "church_id", None) == report.assembly_id:
        return True
    if getattr(user, "is_db_zone_staff", False):
        return user.assigned_zones.filter(pk=report.assembly.zone_id).exists()
    return False


def can_edit_report(user, report: AssemblyReport) -> bool:
    if not can_view_report(user, report):
        return False
    return bool(
        getattr(user, "church_id", None) == report.assembly_id
        or user.is_superuser
        or getattr(user, "is_admin", False)
        or getattr(user, "is_db_staff", False)
    )


def can_approve_reopening(user, report: AssemblyReport) -> bool:
    if not _is_authenticated(user):
        return False
    if user.is_superuser or getattr(user, "is_admin", False) or getattr(user, "is_db_staff", False):
        return True
    return bool(
        getattr(user, "is_db_zone_staff", False)
        and user.assigned_zones.filter(pk=report.assembly.zone_id).exists()
    )


def _json_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _rows(queryset, fields):
    return [
        {key: _json_value(value) for key, value in row.items()}
        for row in queryset.values(*fields)
    ]


def get_section_source(report: AssemblyReport, section_key: str) -> dict[str, Any]:
    """Return a permission-neutral aggregate used by current views and snapshots."""
    start, end = report.period_start, report.period_end
    assembly_id = report.assembly_id

    if section_key == ReportSectionStatus.Section.GENERAL_ATTENDANCE:
        from apps.people.models import Attendance

        qs = Attendance.objects.filter(
            assembly_id=assembly_id,
            timestamp__range=(start, end),
            is_deleted=False,
        ).order_by("timestamp", "id")
        rows = _rows(qs, [
            "id", "timestamp", "service_type", "total_adults", "children",
            "total_visitors", "online_viewers", "total_new_converts",
            "collection_schema",
        ])
        from apps.people.services.attendance_totals import attendance_headcount
        total = sum(attendance_headcount(record) for record in qs)
        route = "/engagement/attendance"

    elif section_key == ReportSectionStatus.Section.SUNDAY_SCHOOL_ATTENDANCE:
        from apps.people.models import SundaySchoolAttendance

        qs = SundaySchoolAttendance.objects.filter(
            assembly_id=assembly_id,
            service_date__range=(start, end),
            is_deleted=False,
        ).order_by("service_date", "id")
        rows = _rows(qs, [
            "id", "service_date", "class_name", "boys", "girls", "male_visitors",
            "female_visitors", "male_first_timers", "female_first_timers", "status",
        ])
        total = sum(
            row["boys"] + row["girls"] + row["male_visitors"] + row["female_visitors"]
            + row["male_first_timers"] + row["female_first_timers"]
            for row in rows
        )
        route = "/engagement/attendance/sunday-school"

    elif section_key == ReportSectionStatus.Section.TITHES:
        from apps.bookkeeper.models import Tithe

        qs = Tithe.objects.filter(
            assembly_id=assembly_id,
            timestamp__range=(start, end),
        ).order_by("timestamp", "id")
        rows = _rows(qs, ["id", "timestamp", "amount", "payment_method"])
        total = qs.aggregate(total=Sum("amount"))["total"] or Decimal("0")
        route = "/finance/tithes"

    elif section_key == ReportSectionStatus.Section.REVENUE:
        from apps.bookkeeper.models import Revenue

        qs = Revenue.objects.filter(
            assembly_id=assembly_id,
            timestamp__range=(start, end),
        ).select_related("category", "category__standard_category").order_by("timestamp", "id")
        rows = _rows(qs, [
            "id", "timestamp", "amount", "category_id", "category__name",
            "category__standard_category__id", "category__standard_category__name",
            "category__needs_review", "notes",
        ])
        for row in rows:
            row["reporting_category_id"] = (
                row["category__standard_category__id"] or row["category_id"]
            )
            row["reporting_category"] = (
                row["category__standard_category__name"] or row["category__name"]
            )
        total = qs.aggregate(total=Sum("amount"))["total"] or Decimal("0")
        route = "/finance/revenue"

    elif section_key == ReportSectionStatus.Section.OPERATING_EXPENSES:
        from apps.bookkeeper.models import Overhead

        qs = Overhead.objects.filter(
            assembly_id=assembly_id,
            timestamp__range=(start, end),
        ).select_related("overhead_type", "overhead_type__standard_category").order_by("timestamp", "id")
        rows = _rows(qs, [
            "id", "timestamp", "amount", "overhead_type_id", "overhead_type__name",
            "overhead_type__standard_category__id",
            "overhead_type__standard_category__name", "overhead_type__needs_review", "notes",
        ])
        for row in rows:
            row["reporting_category_id"] = (
                row["overhead_type__standard_category__id"] or row["overhead_type_id"]
            )
            row["reporting_category"] = (
                row["overhead_type__standard_category__name"] or row["overhead_type__name"]
            )
        total = qs.aggregate(total=Sum("amount"))["total"] or Decimal("0")
        route = "/finance/expenses?type=operating"

    elif section_key == ReportSectionStatus.Section.ACTIVITY_OTHER_EXPENSES:
        from apps.bookkeeper.models import Expenditure

        qs = Expenditure.objects.filter(
            assembly_id=assembly_id,
            timestamp__range=(start, end),
        ).order_by("timestamp", "id")
        rows = _rows(qs, [
            "id", "timestamp", "invoice_date", "name", "category", "quantity", "price", "total",
        ])
        total = qs.aggregate(total=Sum(F("price") * F("quantity")))["total"] or Decimal("0")
        route = "/finance/expenses?type=activity-other"

    else:
        raise ValidationError({"section": "Unknown report section."})

    return {
        "record_count": len(rows),
        "total": total,
        "breakdown": rows,
        "source": {
            "route": route,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "report_id": report.pk,
            "record_ids": [row["id"] for row in rows],
        },
    }


def is_section_required(report: AssemblyReport, section_key: str) -> bool:
    return not (
        section_key == ReportSectionStatus.Section.SUNDAY_SCHOOL_ATTENDANCE
        and report.period_start < SUNDAY_SCHOOL_START_DATE
    )


def get_effective_section_status(
    report: AssemblyReport,
    section: ReportSectionStatus,
    source: dict[str, Any],
) -> str:
    if not is_section_required(report, section.section):
        return "not_required"
    if section.status in {
        ReportSectionStatus.Status.SKIPPED,
        ReportSectionStatus.Status.NO_ACTIVITY,
    }:
        return section.status
    if source["record_count"]:
        if section.section == ReportSectionStatus.Section.SUNDAY_SCHOOL_ATTENDANCE:
            has_drafts = any(row.get("status") == "draft" for row in source["breakdown"])
            return ReportSectionStatus.Status.IN_PROGRESS if has_drafts else ReportSectionStatus.Status.COMPLETED
        return ReportSectionStatus.Status.COMPLETED
    if section.status in {ReportSectionStatus.Status.IN_PROGRESS, ReportSectionStatus.Status.COMPLETED}:
        return ReportSectionStatus.Status.IN_PROGRESS
    return ReportSectionStatus.Status.NOT_STARTED


def get_report_sections(report: AssemblyReport) -> list[dict[str, Any]]:
    existing = {section.section: section for section in report.sections.all()}
    payload = []
    for key, label in ReportSectionStatus.Section.choices:
        section = existing.get(key)
        if section is None:
            section = ReportSectionStatus(report=report, section=key)
        source = get_section_source(report, key)
        status = get_effective_section_status(report, section, source)
        payload.append({
            "object": section,
            "key": key,
            "label": label,
            "status": status,
            "resolved": status in RESOLVED_SECTION_STATUSES,
            "source": source,
        })
    return payload


def validate_report(
    report: AssemblyReport,
    sections: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen = set()
    for item in sections if sections is not None else get_report_sections(report):
        section = item["object"]
        key = item["key"]
        seen.add(key)
        if item["status"] not in RESOLVED_SECTION_STATUSES:
            findings.append({
                "code": "section_unresolved",
                "level": "error",
                "section": key,
                "message": f"{item['label']} is not resolved.",
                "blocking": True,
            })
        if section.status == ReportSectionStatus.Status.NO_ACTIVITY and item["source"]["record_count"]:
            findings.append({
                "code": "no_activity_has_source_records",
                "level": "error",
                "section": key,
                "message": "No activity cannot be confirmed while source records exist.",
                "blocking": True,
            })
        if section.status == ReportSectionStatus.Status.SKIPPED and (
            not section.skip_reason or not (section.skip_notes or "").strip()
        ):
            findings.append({
                "code": "skip_detail_required",
                "level": "error",
                "section": key,
                "message": "A skip reason and detailed explanation are required.",
                "blocking": True,
            })
    for missing in set(REQUIRED_SECTIONS) - seen:
        findings.append({
            "code": "required_section_missing",
            "level": "error",
            "section": missing,
            "message": "A required report section is missing.",
            "blocking": True,
        })
    return findings


def get_report_state(
    report: AssemblyReport,
    user=None,
    *,
    now=None,
    sections: list[dict[str, Any]] | None = None,
) -> ReportState:
    now = now or timezone.now()
    sections = sections if sections is not None else get_report_sections(report)
    resolved = sum(1 for section in sections if section["resolved"])
    required = len(REQUIRED_SECTIONS)
    completion = round((resolved / required) * 100) if required else 0
    due_at = get_due_at(report)
    current_version = report.current_version
    has_amendment = bool(report.amendment_started_at)
    is_locked = bool(current_version and now > current_version.editable_until and not has_amendment)
    is_overdue = bool(
        not report.is_historical_backfill and not current_version and now > due_at
    )
    findings = validate_report(report, sections)
    ready = resolved == required and not any(item["blocking"] for item in findings)

    if report.is_historical_backfill and not current_version:
        status = "historical_backfill"
    elif has_amendment:
        status = "reopened"
    elif current_version:
        status = "locked" if is_locked else "submitted"
    elif is_overdue:
        status = "overdue"
    elif ready:
        status = "ready_to_submit"
    elif resolved or any(section["status"] == ReportSectionStatus.Status.IN_PROGRESS for section in sections):
        status = "draft"
    else:
        status = "not_started"

    editable = not current_version or has_amendment
    owns_edit = can_edit_report(user, report)
    can_submit = bool(owns_edit and editable and ready)
    can_amend = bool(
        owns_edit and current_version and not has_amendment and now <= current_version.editable_until
    )
    can_request = bool(owns_edit and current_version and is_locked and not has_amendment)
    can_approve = bool(
        can_approve_reopening(user, report)
        and report.reopening_requests.filter(status=ReportReopeningRequest.Status.REQUESTED).exists()
    )
    return ReportState(
        status=status,
        is_overdue=is_overdue,
        is_locked=is_locked,
        is_editable=editable and owns_edit,
        can_submit=can_submit,
        can_amend=can_amend,
        can_request_reopen=can_request,
        can_approve_reopen=can_approve,
        completion_percentage=completion,
        resolved_section_count=resolved,
        required_section_count=required,
        submitted_at=current_version.submitted_at if current_version else report.submitted_at,
        editable_until=current_version.editable_until if current_version else report.editable_until,
        due_at=due_at,
        current_version=current_version.version_number if current_version else None,
    )


def _audit(report, actor, description, *, old_data=None, new_data=None):
    return AuditLog.objects.create(
        user=actor if _is_authenticated(actor) else None,
        content_type=ContentType.objects.get_for_model(report),
        object_id=report.pk,
        action=AuditLog.Action.UPDATE,
        description=description,
        old_data=old_data,
        new_data=new_data,
    )


@transaction.atomic
def ensure_report(
    *, assembly, period_start, period_end=None, actor=None, historical_backfill=False
) -> AssemblyReport:
    period_start, calculated_end = report_period(period_start)
    if period_end is not None and period_end != calculated_end:
        raise ValidationError({
            "period_end": f"Expected canonical month end {calculated_end}."
        })
    period_end = calculated_end
    overlapping = list(
        AssemblyReport.objects.select_for_update().filter(
            assembly=assembly,
            period_start__lte=period_end,
            period_end__gte=period_start,
        ).order_by("period_start", "period_end", "id")
    )
    exact = [
        report for report in overlapping
        if report.period_start == period_start and report.period_end == period_end
    ]
    conflicts = [report for report in overlapping if report not in exact]
    if len(exact) > 1 or conflicts:
        rows = conflicts + exact[1:]
        labels = ", ".join(
            f"#{row.pk} [{row.period_start}..{row.period_end}]" for row in rows
        )
        raise ValidationError({
            "period": f"Canonical report creation is blocked by conflicting report(s): {labels}."
        })
    if exact:
        report = exact[0]
        created = False
    else:
        try:
            with transaction.atomic():
                report = AssemblyReport.objects.create(
                    assembly=assembly,
                    period_start=period_start,
                    period_end=period_end,
                    status=AssemblyReport.Status.DRAFT,
                    is_historical_backfill=historical_backfill,
                )
            created = True
        except IntegrityError:
            report = AssemblyReport.objects.get(
                assembly=assembly,
                period_start=period_start,
                period_end=period_end,
            )
            created = False
    sections = [
        ReportSectionStatus(report=report, section=key)
        for key in REQUIRED_SECTIONS
        if not report.sections.filter(section=key).exists()
    ]
    ReportSectionStatus.objects.bulk_create(sections, ignore_conflicts=True)
    if created:
        _audit(report, actor, "Report obligation and draft created")
    return report


def set_section_status(
    *, report: AssemblyReport, section_key: str, status: str, actor,
    skip_reason_code=None, skip_reason_detail=None, no_activity_note=None,
) -> ReportSectionStatus:
    if not can_edit_report(actor, report):
        raise PermissionDenied("You do not have permission to edit this report.")
    state = get_report_state(report, actor)
    if not state.is_editable:
        raise ValidationError({"report": "This submitted report is locked for editing."})
    if section_key not in REQUIRED_SECTIONS:
        raise ValidationError({"section": "Unknown report section."})
    if not is_section_required(report, section_key):
        raise ValidationError({"section": "This report section is not required for the reporting period."})
    if status not in ReportSectionStatus.Status.values:
        raise ValidationError({"status": "Invalid section status."})

    with transaction.atomic():
        section, _ = ReportSectionStatus.objects.select_for_update().get_or_create(
            report=report, section=section_key
        )
        previous = section.status
        source = get_section_source(report, section_key)
        if status == ReportSectionStatus.Status.NO_ACTIVITY and source["record_count"]:
            raise ValidationError({
                "status": "No activity cannot be confirmed while source records exist."
            })
        if status == ReportSectionStatus.Status.SKIPPED:
            if skip_reason_code not in ReportSectionStatus.SkipReason.values:
                raise ValidationError({"skip_reason_code": "Select a valid skip reason."})
            if not (skip_reason_detail or "").strip():
                raise ValidationError({"skip_reason_detail": "A detailed explanation is required."})

        now = timezone.now()
        section.status = status
        section.skip_reason = skip_reason_code if status == ReportSectionStatus.Status.SKIPPED else None
        section.skip_notes = skip_reason_detail.strip() if status == ReportSectionStatus.Status.SKIPPED else None
        section.skipped_by = actor if status == ReportSectionStatus.Status.SKIPPED else None
        section.skipped_at = now if status == ReportSectionStatus.Status.SKIPPED else None
        section.no_activity_confirmed_by = actor if status == ReportSectionStatus.Status.NO_ACTIVITY else None
        section.no_activity_confirmed_at = now if status == ReportSectionStatus.Status.NO_ACTIVITY else None
        section.no_activity_note = no_activity_note if status == ReportSectionStatus.Status.NO_ACTIVITY else None
        if status == ReportSectionStatus.Status.IN_PROGRESS and not section.started_at:
            section.started_by = actor
            section.started_at = now
        if status == ReportSectionStatus.Status.COMPLETED:
            if not source["record_count"]:
                raise ValidationError({"status": "Source records are required before completion."})
            section.completed_by = actor
            section.completed_at = now
        elif status not in {ReportSectionStatus.Status.SKIPPED, ReportSectionStatus.Status.NO_ACTIVITY}:
            section.completed_by = None
            section.completed_at = None
        section.full_clean()
        section.save()
        _audit(
            report, actor, f"Report section changed: {section_key}",
            old_data={"section": section_key, "status": previous},
            new_data={"section": section_key, "status": status},
        )
        return section


@transaction.atomic
def submit_report(*, report: AssemblyReport, actor, declaration_confirmed: bool) -> ReportVersion:
    locked = AssemblyReport.objects.select_for_update().select_related("current_version").get(pk=report.pk)
    if locked.current_version_id and not locked.amendment_started_at:
        return locked.current_version
    if not can_edit_report(actor, locked):
        raise PermissionDenied("You do not have permission to submit this report.")
    if not declaration_confirmed:
        raise ValidationError({"declaration_confirmed": "The declaration is required."})
    findings = validate_report(locked)
    blocking = [item for item in findings if item["blocking"]]
    if blocking:
        raise ValidationError({"findings": blocking})

    submitted_at = timezone.now()
    editable_until = submitted_at + timedelta(days=GRACE_PERIOD_DAYS)
    source_sections = get_report_sections(locked)
    totals = {item["key"]: Decimal(str(item["source"]["total"])) for item in source_sections}
    version_number = (locked.versions.order_by("-version_number").values_list("version_number", flat=True).first() or 0) + 1
    version = ReportVersion.objects.create(
        report=locked,
        version_number=version_number,
        submitted_by=actor,
        submitted_at=submitted_at,
        editable_until=editable_until,
        declaration_confirmed=True,
        validation_findings=findings,
        attendance_total=int(totals[ReportSectionStatus.Section.GENERAL_ATTENDANCE]),
        sunday_school_attendance_total=int(totals[ReportSectionStatus.Section.SUNDAY_SCHOOL_ATTENDANCE]),
        tithe_total=totals[ReportSectionStatus.Section.TITHES],
        revenue_total=totals[ReportSectionStatus.Section.REVENUE],
        operating_expense_total=totals[ReportSectionStatus.Section.OPERATING_EXPENSES],
        activity_other_expense_total=totals[ReportSectionStatus.Section.ACTIVITY_OTHER_EXPENSES],
        net_balance=(
            totals[ReportSectionStatus.Section.TITHES]
            + totals[ReportSectionStatus.Section.REVENUE]
            - totals[ReportSectionStatus.Section.OPERATING_EXPENSES]
            - totals[ReportSectionStatus.Section.ACTIVITY_OTHER_EXPENSES]
        ),
    )
    ReportSectionSnapshot.objects.bulk_create([
        ReportSectionSnapshot(
            version=version,
            section=item["key"],
            label=item["label"],
            status=item["status"],
            total=item["source"]["total"],
            record_count=item["source"]["record_count"],
            breakdown=item["source"]["breakdown"],
            source_references=item["source"]["source"],
            skip_reason_code=item["object"].skip_reason,
            skip_reason_detail=item["object"].skip_notes,
            skipped_by=item["object"].skipped_by,
            skipped_at=item["object"].skipped_at,
            no_activity_confirmed_by=item["object"].no_activity_confirmed_by,
            no_activity_confirmed_at=item["object"].no_activity_confirmed_at,
            no_activity_note=item["object"].no_activity_note,
        )
        for item in source_sections
    ])

    was_amendment = bool(locked.amendment_started_at)
    locked.calculate_totals()
    locked.status = AssemblyReport.Status.SUBMITTED
    locked.current_version = version
    locked.submitted_by = actor
    locked.submitted_at = submitted_at
    locked.editable_until = editable_until
    locked.is_late, locked.days_late = locked._compute_lateness(submitted_at)
    locked.amendment_reason = None
    locked.amendment_started_by = None
    locked.amendment_started_at = None
    locked.amendment_base_version = None
    locked.save()
    locked.reopening_requests.filter(status=ReportReopeningRequest.Status.APPROVED).update(
        status=ReportReopeningRequest.Status.COMPLETED
    )
    _audit(
        locked,
        actor,
        "Report resubmitted" if was_amendment else "Report submitted",
        new_data={"version": version_number, "editable_until": editable_until.isoformat()},
    )
    return version


@transaction.atomic
def start_amendment(*, report: AssemblyReport, actor, reason: str, authorised=False) -> AssemblyReport:
    locked = AssemblyReport.objects.select_for_update().select_related("current_version").get(pk=report.pk)
    if not locked.current_version_id:
        raise ValidationError({"report": "Only submitted reports can be amended."})
    if locked.amendment_started_at:
        raise ValidationError({"report": "An amendment is already in progress."})
    if not (reason or "").strip():
        raise ValidationError({"reason": "An amendment reason is required."})
    if authorised:
        if not can_approve_reopening(actor, locked):
            raise PermissionDenied("You do not have permission to reopen this report.")
    else:
        if not can_edit_report(actor, locked):
            raise PermissionDenied("You do not have permission to amend this report.")
        if timezone.now() > locked.current_version.editable_until:
            raise ValidationError({"report": "The amendment window has closed. Request reopening instead."})
    locked.status = AssemblyReport.Status.DRAFT
    locked.amendment_reason = reason.strip()
    locked.amendment_started_by = actor
    locked.amendment_started_at = timezone.now()
    locked.amendment_base_version = locked.current_version
    locked.save(update_fields=[
        "status", "amendment_reason", "amendment_started_by", "amendment_started_at",
        "amendment_base_version", "updated_at",
    ])
    _audit(
        locked, actor, "Report reopened" if authorised else "Report amendment started",
        new_data={"base_version": locked.current_version.version_number, "reason": reason.strip()},
    )
    return locked


@transaction.atomic
def request_reopening(*, report: AssemblyReport, actor, reason: str) -> ReportReopeningRequest:
    locked = AssemblyReport.objects.select_for_update().select_related("current_version").get(pk=report.pk)
    state = get_report_state(locked, actor)
    if not state.can_request_reopen:
        raise PermissionDenied("This report cannot be requested for reopening.")
    if not (reason or "").strip():
        raise ValidationError({"reason": "A reopening reason is required."})
    request = ReportReopeningRequest.objects.create(
        report=locked, requested_by=actor, request_reason=reason.strip()
    )
    _audit(locked, actor, "Report reopening requested", new_data={"reason": reason.strip()})
    return request


@transaction.atomic
def review_reopening(*, request_obj: ReportReopeningRequest, actor, approve: bool, decision_note: str):
    reopening = ReportReopeningRequest.objects.select_for_update().select_related(
        "report__current_version"
    ).get(pk=request_obj.pk)
    if reopening.status != ReportReopeningRequest.Status.REQUESTED:
        raise ValidationError({"request": "This reopening request has already been reviewed."})
    if not can_approve_reopening(actor, reopening.report):
        raise PermissionDenied("You do not have permission to review this request.")
    reopening.status = (
        ReportReopeningRequest.Status.APPROVED if approve else ReportReopeningRequest.Status.REJECTED
    )
    reopening.reviewed_by = actor
    reopening.reviewed_at = timezone.now()
    reopening.decision_note = (decision_note or "").strip() or None
    reopening.save()
    _audit(
        reopening.report,
        actor,
        "Report reopening approved" if approve else "Report reopening rejected",
        new_data={"decision_note": reopening.decision_note},
    )
    if approve:
        start_amendment(
            report=reopening.report,
            actor=actor,
            reason=reopening.request_reason,
            authorised=True,
        )
    return reopening
