import calendar
from collections import defaultdict
from datetime import date

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from apps.bookkeeper.models import Expenditure, Overhead, Revenue, Tithe
from apps.reports.models import AssemblyReport
from apps.reports.services.lifecycle import ensure_report


class BatchEntryValidationError(Exception):
    def __init__(self, errors, message="Some entries are invalid."):
        self.errors = errors
        self.message = message
        super().__init__(message)


def _error_detail(exc):
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            return exc.message_dict
        return {"non_field_errors": list(exc.messages)}
    if isinstance(exc, ValidationError):
        detail = exc.detail
        return detail if isinstance(detail, dict) else {"non_field_errors": detail}
    return {"non_field_errors": [str(exc)]}


def _period_bounds(period):
    year, month = (int(part) for part in period.split("-"))
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def resolve_report(*, assembly, period, report_id=None):
    period_start, period_end = _period_bounds(period)
    queryset = AssemblyReport.objects.filter(
        assembly=assembly,
        period_start=period_start,
        period_end=period_end,
        status=AssemblyReport.Status.DRAFT,
    )
    if report_id is not None:
        report = queryset.filter(pk=report_id).first()
        if report is None:
            raise BatchEntryValidationError({"report": ["The selected draft report is outside the active assembly or reporting period."]})
        return report
    matches = list(queryset[:2])
    if len(matches) > 1:
        raise BatchEntryValidationError({"report": ["Multiple canonical draft reports exist for this period."]})
    if matches:
        return matches[0]
    try:
        return ensure_report(assembly=assembly, period_start=period_start, period_end=period_end)
    except DjangoValidationError as exc:
        raise BatchEntryValidationError(_error_detail(exc)) from exc


def validate_dates(entries, period, field):
    start, end = _period_bounds(period)
    errors = {}
    for index, entry in enumerate(entries):
        value = entry.get(field)
        if value and not start <= value <= end:
            errors[str(index)] = {field: ["Date must be inside the selected reporting period."]}
    if errors:
        raise BatchEntryValidationError({"entries": errors})


def _duplicate_errors(entries, key, field, message, allow_null=False):
    seen = {}
    errors = {}
    for index, entry in enumerate(entries):
        value = key(entry)
        if value is None and allow_null:
            continue
        if value in seen:
            errors[str(index)] = {field: [message]}
        else:
            seen[value] = index
    return errors


def _refresh_reports(instances):
    reports = {instance.report_id: instance.report for instance in instances if instance.report_id}
    for report in reports.values():
        report.calculate_totals()
        report.save()
        report.refresh_from_db()
    return {
        str(report_id): {
            "id": report_id,
            "period_start": report.period_start,
            "period_end": report.period_end,
            "status": report.status,
            "attendance_total": report.attendance_total,
            "income_total": report.income_total,
            "expense_total": report.expense_total,
            "tithe_total": report.tithe_total,
            "balance": report.balance,
        }
        for report_id, report in reports.items()
    }


@transaction.atomic
def create_tithes(*, assembly, user, period, entries, report_id=None):
    validate_dates(entries, period, "timestamp")
    report = resolve_report(assembly=assembly, period=period, report_id=report_id)
    errors = _duplicate_errors(
        entries, lambda row: row.get("member_id"), "member",
        "This member appears more than once in this submission.", allow_null=True,
    )
    member_ids = [row["member_id"] for row in entries if row.get("member_id")]
    invalid_members = set(
        Tithe._meta.get_field("member").related_model.objects.filter(pk__in=member_ids)
        .exclude(assembly=assembly).values_list("pk", flat=True)
    )
    existing = set()
    if report and member_ids:
        existing = set(Tithe.objects.filter(report=report, member_id__in=member_ids).values_list("member_id", flat=True))
    for index, row in enumerate(entries):
        member_id = row.get("member_id")
        if member_id in invalid_members:
            errors[str(index)] = {"member": ["Member is outside the active assembly."]}
        elif member_id in existing:
            errors[str(index)] = {"member": ["A tithe has already been recorded for this member in the selected reporting period."]}
    if errors:
        raise BatchEntryValidationError({"entries": errors})
    return _save_instances(Tithe, assembly, user, entries, report)


@transaction.atomic
def create_revenues(*, assembly, user, period, entries, report_id=None):
    validate_dates(entries, period, "timestamp")
    report = resolve_report(assembly=assembly, period=period, report_id=report_id)
    errors = _duplicate_errors(entries, lambda row: row["category_id"], "category", "Category is selected more than once.")
    for index, row in enumerate(entries):
        item = row["category"]
        if not item.is_active or (
            item.is_standard and item.assembly_id is not None
        ) or (
            not item.is_standard and item.assembly_id != assembly.id
        ):
            errors[str(index)] = {"category": ["Category is unavailable for the active assembly."]}
    if report:
        existing = set(Revenue.objects.filter(report=report, category_id__in=[row["category_id"] for row in entries]).values_list("category_id", flat=True))
        for index, row in enumerate(entries):
            if row["category_id"] in existing:
                errors[str(index)] = {"category": ["Revenue has already been recorded for this category in the selected report."]}
    if errors:
        raise BatchEntryValidationError({"entries": errors})
    return _save_instances(Revenue, assembly, user, entries, report)


@transaction.atomic
def create_overheads(*, assembly, user, period, entries, report_id=None):
    validate_dates(entries, period, "timestamp")
    report = resolve_report(assembly=assembly, period=period, report_id=report_id)
    errors = _duplicate_errors(entries, lambda row: row["overhead_type_id"], "overhead_type", "Overhead type is selected more than once.")
    for index, row in enumerate(entries):
        item = row["overhead_type"]
        if not item.is_active or (not item.is_global and item.assembly_id != assembly.id) or (item.is_global and item.assembly_id is not None):
            errors[str(index)] = {"overhead_type": ["Overhead type is unavailable for the active assembly."]}
    if report:
        existing = set(Overhead.objects.filter(report=report, overhead_type_id__in=[row["overhead_type_id"] for row in entries]).values_list("overhead_type_id", flat=True))
        for index, row in enumerate(entries):
            if row["overhead_type_id"] in existing:
                errors[str(index)] = {"overhead_type": ["An overhead already exists for this type in the selected report."]}
    if errors:
        raise BatchEntryValidationError({"entries": errors})
    return _save_instances(Overhead, assembly, user, entries, report)


@transaction.atomic
def create_expenditures(*, assembly, user, period, entries, report_id=None):
    validate_dates(entries, period, "invoice_date")
    report = resolve_report(assembly=assembly, period=period, report_id=report_id)
    errors = _duplicate_errors(
        entries,
        lambda row: (row["invoice_date"], row["category"], row["name"].strip().casefold(), row.get("invoice_number", "").strip().casefold()),
        "name", "This expense duplicates another row in the submission.",
    )
    if errors:
        raise BatchEntryValidationError({"entries": errors})
    normalized = [{
        **row,
        "created_by": user,
        "report": report,
        "timestamp": row["invoice_date"],
        "total": row["price"] * row["quantity"],
    } for row in entries]
    return _save_instances(Expenditure, assembly, user, normalized, report)


def _save_instances(model, assembly, user, entries, report):
    created = []
    try:
        with transaction.atomic():
            for index, attrs in enumerate(entries):
                attrs = dict(attrs)
                attrs.pop("member_id", None)
                attrs.pop("category_id", None)
                attrs.pop("overhead_type_id", None)
                instance = model(assembly=assembly, **attrs)
                if report is not None:
                    instance.report = report
                instance._current_user = user
                try:
                    instance.full_clean()
                    instance.save()
                except (DjangoValidationError, ValidationError) as exc:
                    raise BatchEntryValidationError({"entries": {str(index): _error_detail(exc)}}) from exc
                created.append(instance)
            totals = _refresh_reports(created)
    except IntegrityError as exc:
        raise BatchEntryValidationError({"entries": {"0": {"non_field_errors": ["An entry conflicts with an existing record in this report."]}}}) from exc
    return created, totals
