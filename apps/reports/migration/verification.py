from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal

from django.apps import apps
from django.db.models import F, Sum

from apps.people.constants import SUNDAY_SCHOOL_START_DATE
from apps.bookkeeper.historical import LEGACY_FINANCE_END
from apps.people.services.attendance_totals import calculate_report_attendance
from apps.reports.migration.core import filtered_assemblies, in_range, is_protected_report
from apps.reports.migration.core import (
    ATTENDANCE_MAPPING_VERSION,
    load_mapping_manifest,
    mapping_metadata,
    model_checksum,
)
from apps.reports.services.lifecycle import REQUIRED_SECTIONS
from apps.reports.services.periods import period_findings, report_period


@dataclass
class Finding:
    code: str
    severity: str
    message: str
    details: dict


class VerificationReport:
    def __init__(self):
        self.findings = []
        self.counts = defaultdict(int)

    def add(self, code, severity, message, **details):
        self.findings.append(Finding(code, severity, message, details))
        self.counts[severity] += 1

    @property
    def blocked(self):
        return bool(self.counts["blocker"] or self.counts["high"])

    def payload(self):
        return {
            "status": "blocked" if self.blocked else "pass",
            "counts": dict(self.counts),
            "findings": [asdict(item) for item in self.findings],
        }


def _correct_report(row, value):
    if row.report_id is None:
        return False
    start, end = report_period(value)
    return (
        row.report.assembly_id == getattr(row, "assembly_id", getattr(row, "church_id", None))
        and row.report.period_start == start
        and row.report.period_end == end
    )


def _verify_reports(report, assembly_ids, from_date, to_date):
    from apps.reports.models import AssemblyReport

    queryset = AssemblyReport.objects.filter(assembly_id__in=assembly_ids).prefetch_related("sections", "versions")
    for finding in period_findings(queryset):
        details = finding.to_dict()
        details.pop("code", None)
        details.pop("message", None)
        report.add(finding.code, "blocker", finding.message, **details)
    for row in queryset:
        if not in_range(row.period_start, from_date, to_date):
            continue
        sections = list(row.sections.values_list("section", flat=True))
        missing = sorted(set(REQUIRED_SECTIONS) - set(sections))
        duplicates = len(sections) - len(set(sections))
        if missing or duplicates:
            report.add(
                "report_sections_invalid", "high",
                f"Report #{row.pk} does not have exactly six unique required sections.",
                report_id=row.pk, missing=missing, duplicate_count=duplicates,
            )
        if row.is_historical_backfill and is_protected_report(row):
            report.add(
                "historical_report_became_versioned", "warning",
                f"Historical backfill Report #{row.pk} is versioned/submitted; confirm this was manual.",
                report_id=row.pk,
            )


def _verify_relationships(report, assembly_ids, from_date, to_date):
    from apps.bookkeeper.models import Expenditure, Overhead, Revenue
    from apps.people.models import Attendance, SundaySchoolAttendance
    from apps.reports.migration.runner import (
        _authoritative_legacy_monthly,
        _authoritative_tithes,
    )

    specs = [
        (Attendance.objects.filter(assembly_id__in=assembly_ids), "timestamp"),
        (Revenue.objects.filter(assembly_id__in=assembly_ids), "timestamp"),
        (Overhead.objects.filter(assembly_id__in=assembly_ids), "timestamp"),
        (SundaySchoolAttendance.objects.filter(assembly_id__in=assembly_ids), "service_date"),
    ]
    authoritative_tithes, superseded_tithes = _authoritative_tithes(
        assembly_ids, from_date, to_date
    )
    authoritative_legacy, superseded_legacy = _authoritative_legacy_monthly(
        assembly_ids, from_date, to_date
    )
    specs.extend([
        (authoritative_tithes, "timestamp"),
        (authoritative_legacy, "timestamp"),
    ])
    for queryset, date_field in specs:
        rows = queryset.select_related("report") if hasattr(queryset, "select_related") else queryset
        for row in rows:
            value = getattr(row, date_field)
            if value is None or not in_range(value, from_date, to_date):
                continue
            if row._meta.model_name == "sundayschoolattendance" and value < SUNDAY_SCHOOL_START_DATE:
                report.add(
                    "prelaunch_sunday_school", "high",
                    f"SundaySchoolAttendance #{row.pk} predates the collection launch.",
                    source_pk=row.pk, service_date=value.isoformat(),
                )
                continue
            if not _correct_report(row, value):
                report.add(
                    "incorrect_report_relationship", "high",
                    f"{row._meta.label} #{row.pk} is not linked to its canonical assembly/month report.",
                    source_pk=row.pk, current_report_id=row.report_id, date=value.isoformat(),
                )
    from apps.reports.models import HistoricalMigrationLineage
    for old, winner in [*superseded_tithes, *superseded_legacy]:
        if not HistoricalMigrationLineage.objects.filter(
            source_app=old._meta.app_label,
            source_model=old._meta.model_name,
            source_pk=str(old.pk),
            status=HistoricalMigrationLineage.Status.SUPERSEDED,
        ).exists():
            report.add(
                "unresolved_superseded_duplicate", "high",
                f"{old._meta.label} #{old.pk} is superseded by #{winner.pk} but lacks lineage.",
                source_pk=old.pk, selected_source_pk=winner.pk,
            )
    for row in Expenditure.objects.filter(assembly_id__in=assembly_ids).select_related("report"):
        value = row.timestamp or row.invoice_date
        if value and in_range(value, from_date, to_date) and not _correct_report(row, value):
            report.add(
                "incorrect_expenditure_report", "high",
                f"Expenditure #{row.pk} is not linked using timestamp/invoice_date.",
                source_pk=row.pk, current_report_id=row.report_id, date=value.isoformat(),
            )


def _verify_attendance(report, assembly_ids, from_date, to_date):
    from apps.people.models import Attendance, SundaySchoolAttendance
    from apps.reports.models import AssemblyReport

    historical = Attendance.objects.filter(
        assembly_id__in=assembly_ids,
        collection_schema=Attendance.CollectionSchema.LEGACY,
    )
    for row in historical:
        if not in_range(row.timestamp, from_date, to_date):
            continue
        gender_values = [
            row.men, row.women, row.visitor_men, row.visitor_women,
            row.new_convert_men, row.new_convert_women, row.altar_call_men,
            row.altar_call_women, row.baptism_men, row.baptism_women,
        ]
        if any(value is not None for value in gender_values):
            report.add(
                "historical_gender_not_null", "high",
                f"Attendance #{row.pk} does not mark all uncollected gender values as null.",
                source_pk=row.pk,
            )
        expected = row.adults + row.children + row.online_viewers
        if row.headcount != expected:
            report.add(
                "historical_headcount_mismatch", "blocker",
                f"Attendance #{row.pk} headcount is {row.headcount}; expected {expected}.",
                source_pk=row.pk, visitors_excluded=row.guest_attendance,
            )
        if row.total_adults != row.adults or row.total_visitors != row.guest_attendance:
            report.add(
                "historical_normalized_totals_mismatch", "high",
                f"Attendance #{row.pk} normalized preservation fields are inconsistent.",
                source_pk=row.pk,
            )
        from apps.reports.models import HistoricalMigrationLineage
        lineage = HistoricalMigrationLineage.objects.filter(
            source_model="attendance",
            source_pk=str(row.pk),
            source_component="historical_headcount",
            mapping_version=ATTENDANCE_MAPPING_VERSION,
        ).first()
        if lineage:
            current_checksum = model_checksum(row, [
                "adults", "children", "guest_attendance", "new_converts",
                "altar_call", "baptisms", "online_viewers", "timestamp", "assembly_id",
            ])
            if lineage.source_checksum != current_checksum:
                report.add(
                    "legacy_attendance_changed", "blocker",
                    f"Legacy Attendance #{row.pk} changed after migration lineage was recorded.",
                    source_pk=row.pk,
                )
    for row in SundaySchoolAttendance.objects.filter(assembly_id__in=assembly_ids):
        if row.service_date < SUNDAY_SCHOOL_START_DATE:
            report.add(
                "prelaunch_sunday_school", "high",
                f"SundaySchoolAttendance #{row.pk} predates 2026-09-01.", source_pk=row.pk,
            )
    for assembly_report in AssemblyReport.objects.filter(assembly_id__in=assembly_ids):
        if not in_range(assembly_report.period_start, from_date, to_date):
            continue
        expected = calculate_report_attendance(assembly_report)
        if assembly_report.attendance_total != expected["headcount"]:
            report.add(
                "report_attendance_total_mismatch", "high",
                f"Report #{assembly_report.pk} attendance_total is stale or uses the wrong semantics.",
                report_id=assembly_report.pk,
                stored=assembly_report.attendance_total,
                expected=expected["headcount"],
            )


def _verify_tithes(report, assembly_ids, from_date, to_date):
    from apps.bookkeeper.models import Tithe
    from apps.reports.models import HistoricalMigrationLineage
    from apps.reports.migration.runner import latest_wins

    groups = defaultdict(list)
    for row in Tithe.all_objects.filter(assembly_id__in=assembly_ids, is_trash=False):
        if in_range(row.timestamp, from_date, to_date) and row.member_id is not None:
            groups[(row.assembly_id, row.member_id, row.timestamp.year, row.timestamp.month)].append(row)
    for key, rows in groups.items():
        if len(rows) > 1:
            winner, older = latest_wins(rows)
            linked = [row.pk for row in rows if row.report_id]
            resolved = len(linked) == 1 and linked[0] == winner.pk and all(
                HistoricalMigrationLineage.objects.filter(
                    source_model="tithe",
                    source_pk=str(row.pk),
                    status=HistoricalMigrationLineage.Status.SUPERSEDED,
                ).exists()
                for row in older
            )
            report.add(
                "duplicate_active_tithe",
                "warning" if resolved else "high",
                "Duplicate Tithe submissions are resolved by latest-wins lineage."
                if resolved else "Multiple active Tithe submissions are not fully resolved.",
                key=list(key), candidates=[row.pk for row in rows],
                selected=winner.pk, linked_candidates=linked, resolved=resolved,
            )
    for row in Tithe.all_objects.filter(assembly_id__in=assembly_ids, is_trash=True).exclude(report=None):
        report.add(
            "trashed_tithe_linked", "high",
            f"Trashed Tithe #{row.pk} is linked to Report #{row.report_id}.", source_pk=row.pk,
        )


def _verify_finance(report, assembly_ids, from_date, to_date):
    from apps.bookkeeper.models import (
        Expenditure, FixedExpenditure, Income, Overhead, RemittanceObligation,
        RemittancePayment, Revenue,
    )
    from apps.reports.models import HistoricalMigrationLineage
    from apps.reports.migration.runner import (
        _authoritative_legacy_monthly,
        _authoritative_tithe_total,
    )
    from apps.reports.models import AssemblyReport

    finance_lineages = HistoricalMigrationLineage.objects.exclude(target_pk="")
    for lineage in finance_lineages:
        try:
            model = apps.get_model(lineage.target_app, lineage.target_model)
        except LookupError:
            report.add(
                "lineage_target_model_missing", "blocker",
                f"Lineage #{lineage.pk} points to an unknown target model.", lineage_id=lineage.pk,
            )
            continue
        target = model._base_manager.filter(pk=lineage.target_pk).first()
        if target is None:
            report.add(
                "lineage_target_missing", "blocker",
                f"Lineage #{lineage.pk} points to missing target {lineage.target_pk}.",
                lineage_id=lineage.pk,
            )
    for model in (Revenue, Overhead, RemittanceObligation, RemittancePayment):
        for target in model.objects.all():
            exists = HistoricalMigrationLineage.objects.filter(
                target_app=target._meta.app_label,
                target_model=target._meta.model_name,
                target_pk=str(target.pk),
            ).exists()
            source_marked = hasattr(target, "source_fixed_expenditure_id") and target.source_fixed_expenditure_id
            if source_marked and not exists:
                report.add(
                    "migrated_target_without_lineage", "blocker",
                    f"{target._meta.label} #{target.pk} has migration source metadata but no lineage.",
                    target_pk=target.pk,
                )
    for model in (Revenue, Overhead):
        for target in model.objects.filter(
            assembly_id__in=assembly_ids,
            timestamp__lte=LEGACY_FINANCE_END,
        ):
            if not HistoricalMigrationLineage.objects.filter(
                target_app=target._meta.app_label,
                target_model=target._meta.model_name,
                target_pk=str(target.pk),
                status=HistoricalMigrationLineage.Status.MIGRATED,
            ).exists():
                report.add(
                    "pre_cutoff_finance_target_without_lineage", "blocker",
                    f"Pre-cutoff {target._meta.label} #{target.pk} has no migration lineage.",
                    target_pk=target.pk, timestamp=target.timestamp.isoformat(),
                )
    manifest = load_mapping_manifest()
    metadata = mapping_metadata()
    mapping_version = f"{metadata['version']}:{metadata['checksum']}"
    authoritative, superseded = _authoritative_legacy_monthly(
        assembly_ids, from_date, to_date
    )
    for old, winner in superseded:
        resolved = HistoricalMigrationLineage.objects.filter(
            source_model=old._meta.model_name,
            source_pk=str(old.pk),
            status=HistoricalMigrationLineage.Status.SUPERSEDED,
        ).exists()
        report.add(
            f"duplicate_{old._meta.model_name}",
            "warning" if resolved else "high",
            f"Duplicate {old._meta.model_name} #{old.pk} is "
            + ("resolved by lineage." if resolved else "missing superseded lineage."),
            source_pk=old.pk, selected_source_pk=winner.pk, resolved=resolved,
        )
    for source in authoritative:
        mappings = (
            manifest["income_to_revenue"]
            if source._meta.model_name == "income"
            else manifest["fixed_expenditure_to_overhead"]
        )
        for mapping in mappings:
            component = mapping["source_component"]
            amount = getattr(source, component)
            lineage = HistoricalMigrationLineage.objects.filter(
                source_model=source._meta.model_name,
                source_pk=str(source.pk),
                source_component=component,
                mapping_version=mapping_version,
            ).first()
            if lineage is None:
                report.add(
                    "finance_component_missing_lineage", "high",
                    f"{source._meta.label} #{source.pk}/{component} was not evaluated.",
                    source_pk=source.pk, component=component,
                )
                continue
            if amount == 0 and lineage.status != HistoricalMigrationLineage.Status.SKIPPED:
                report.add(
                    "zero_component_not_skipped", "high",
                    f"Zero component {source.pk}/{component} has status {lineage.status}.",
                    lineage_id=lineage.pk,
                )
            if amount != 0:
                try:
                    target_model = apps.get_model(lineage.target_app, lineage.target_model)
                except LookupError:
                    target_model = None
                target = (
                    target_model.objects.filter(pk=lineage.target_pk).first()
                    if target_model else None
                )
                if target is None:
                    report.add(
                        "finance_component_target_missing", "blocker",
                        f"Migrated component {source.pk}/{component} has no target.",
                        lineage_id=lineage.pk,
                    )
                    continue
                if target.amount != amount:
                    report.add(
                        "finance_component_amount_mismatch", "blocker",
                        f"Migrated component {source.pk}/{component} amount differs from its target.",
                        source_amount=str(amount), target_amount=str(target.amount),
                    )
        if source._meta.model_name == "fixedexpenditure":
            obligation_lineage = HistoricalMigrationLineage.objects.filter(
                source_model="fixedexpenditure",
                source_pk=str(source.pk),
                source_component="remittance_obligation",
                mapping_version=mapping_version,
            ).first()
            if obligation_lineage is None:
                report.add(
                    "remittance_obligation_missing_lineage", "high",
                    f"FixedExpenditure #{source.pk} has no evaluated remittance obligation.",
                    source_pk=source.pk,
                )
    investment = Overhead.objects.filter(
        assembly_id__in=assembly_ids,
        overhead_type__name="Investment",
    ).exclude(overhead_type__reporting_group="Operating Expenses")
    if investment.exists():
        report.add(
            "investment_reporting_group", "blocker",
            "Migrated Investment overhead is not classified as Operating Expenses.",
            target_ids=list(investment.values_list("pk", flat=True)),
        )
    legacy_remittance_overhead = Overhead.objects.filter(
        assembly_id__in=assembly_ids,
        overhead_type__name__iexact="Remittance",
    )
    if legacy_remittance_overhead.exists():
        report.add(
            "remittance_migrated_to_overhead", "blocker",
            "Remittance exists as an ordinary Overhead.",
            target_ids=list(legacy_remittance_overhead.values_list("pk", flat=True)),
        )
    for obligation in RemittanceObligation.objects.filter(assembly_id__in=assembly_ids):
        authoritative_tithe_total = _authoritative_tithe_total(
            obligation.assembly_id,
            obligation.period_start.year,
            obligation.period_start.month,
        )
        if obligation.tithe_total_snapshot != authoritative_tithe_total:
            report.add(
                "remittance_tithe_snapshot_mismatch", "blocker",
                f"RemittanceObligation #{obligation.pk} does not snapshot authoritative Tithes.",
                obligation_id=obligation.pk,
                stored=str(obligation.tithe_total_snapshot),
                expected=str(authoritative_tithe_total),
            )
        expected = (obligation.tithe_total_snapshot * obligation.rate).quantize(Decimal("0.01"))
        if obligation.amount_due != expected:
            report.add(
                "remittance_due_mismatch", "blocker",
                f"RemittanceObligation #{obligation.pk} amount_due is incorrect.",
                obligation_id=obligation.pk, stored=str(obligation.amount_due), expected=str(expected),
            )
        verified = obligation.payments.filter(status=RemittancePayment.Status.VERIFIED).aggregate(
            total=Sum("amount_paid")
        )["total"] or Decimal("0.00")
        expected_outstanding = max(obligation.amount_due - verified, Decimal("0.00"))
        if obligation.outstanding_amount != expected_outstanding:
            report.add(
                "remittance_outstanding_mismatch", "blocker",
                f"RemittanceObligation #{obligation.pk} outstanding amount is incorrect.",
                obligation_id=obligation.pk,
            )
    for payment in RemittancePayment.objects.filter(status=RemittancePayment.Status.VERIFIED):
        if not payment.receipt or not payment.verified_by_id or not payment.verified_at:
            report.add(
                "invalid_verified_remittance", "blocker",
                f"Verified RemittancePayment #{payment.pk} lacks required evidence.", payment_id=payment.pk,
            )
    for assembly_report in AssemblyReport.objects.filter(assembly_id__in=assembly_ids):
        if not in_range(assembly_report.period_start, from_date, to_date):
            continue
        revenue = Revenue.objects.filter(report=assembly_report).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        from apps.bookkeeper.models import Tithe
        tithes = Tithe.objects.filter(report=assembly_report).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        overhead = Overhead.objects.filter(report=assembly_report).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        expenditure = Expenditure.objects.filter(report=assembly_report).aggregate(
            total=Sum(F("price") * F("quantity"))
        )["total"] or Decimal("0")
        verified = RemittancePayment.objects.filter(
            report=assembly_report,
            status=RemittancePayment.Status.VERIFIED,
        ).aggregate(total=Sum("amount_paid"))["total"] or Decimal("0")
        expected_income = revenue + tithes
        expected_expenses = overhead + expenditure + verified
        if assembly_report.income_total != expected_income or assembly_report.expense_total != expected_expenses:
            report.add(
                "report_finance_totals_mismatch", "high",
                f"Report #{assembly_report.pk} stored finance totals do not match canonical sources.",
                report_id=assembly_report.pk,
                stored_income=str(assembly_report.income_total), expected_income=str(expected_income),
                stored_expenses=str(assembly_report.expense_total), expected_expenses=str(expected_expenses),
            )
    # Snapshot rows are evidence only: disagreement is deliberately advisory.
    Snapshot = apps.get_model("bookkeeper", "MonthlyFinanceSnapshot")
    snapshots = Snapshot.objects.filter(church_id__in=assembly_ids)
    report.counts["monthly_finance_snapshots_reviewed"] = snapshots.count()
    snapshot_fields = (
        "total_tithes", "total_income", "total_expenses", "balance",
    )
    for snapshot in snapshots:
        start, end = report_period(date(snapshot.year, snapshot.month, 1))
        canonical = AssemblyReport.objects.filter(
            assembly_id=snapshot.church_id,
            period_start=start,
            period_end=end,
        ).first()
        if canonical is None:
            report.add(
                "snapshot_without_canonical_report", "warning",
                f"MonthlyFinanceSnapshot #{snapshot.pk} has no canonical Report for comparison.",
                snapshot_id=snapshot.pk,
            )
            continue
        expected = {
            "total_tithes": canonical.tithe_total,
            "total_income": canonical.income_total,
            "total_expenses": canonical.expense_total,
            "balance": canonical.balance,
        }
        differences = {
            field: {"snapshot": str(getattr(snapshot, field)), "canonical": str(expected[field])}
            for field in snapshot_fields
            if getattr(snapshot, field) != expected[field]
        }
        if differences:
            report.add(
                "snapshot_advisory_difference", "warning",
                f"MonthlyFinanceSnapshot #{snapshot.pk} differs from canonical migrated totals.",
                snapshot_id=snapshot.pk, report_id=canonical.pk, differences=differences,
            )
    report.counts["expenditure_rows"] = Expenditure.objects.filter(assembly_id__in=assembly_ids).count()
    report.counts["legacy_income_rows"] = Income.objects.filter(church_id__in=assembly_ids).count()
    report.counts["legacy_fixed_expenditure_rows"] = FixedExpenditure.objects.filter(assembly_id__in=assembly_ids).count()


def verify_historical_migration(*, assembly=None, from_date=None, to_date=None):
    result = VerificationReport()
    assembly_ids = list(filtered_assemblies(assembly).values_list("pk", flat=True))
    _verify_reports(result, assembly_ids, from_date, to_date)
    _verify_relationships(result, assembly_ids, from_date, to_date)
    _verify_attendance(result, assembly_ids, from_date, to_date)
    _verify_tithes(result, assembly_ids, from_date, to_date)
    _verify_finance(result, assembly_ids, from_date, to_date)
    return result
