from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.bookkeeper.historical import LEGACY_FINANCE_END, NEW_FINANCE_START, REMITTANCE_RATE
from apps.people.constants import SUNDAY_SCHOOL_START_DATE
from apps.reports.migration.core import (
    ATTENDANCE_MAPPING_VERSION,
    RELATIONSHIP_MAPPING_VERSION,
    MigrationResult,
    canonical_report_for,
    filtered_assemblies,
    in_range,
    is_protected_report,
    load_mapping_manifest,
    mapping_metadata,
    model_checksum,
    stable_checksum,
)
from apps.reports.services.lifecycle import ensure_report
from apps.reports.services.periods import report_period


def _rank(row):
    def value(field):
        item = getattr(row, field, None)
        if item is None:
            return ""
        return item.isoformat() if hasattr(item, "isoformat") else str(item)
    return value("updated_at"), value("created_at"), row.pk


def latest_wins(rows):
    ordered = sorted(rows, key=_rank, reverse=True)
    return (ordered[0], ordered[1:]) if ordered else (None, [])


def _lineage_existing(source, component, mapping_version):
    from apps.reports.models import HistoricalMigrationLineage

    return HistoricalMigrationLineage.objects.filter(
        source_app=source._meta.app_label,
        source_model=source._meta.model_name,
        source_pk=str(source.pk),
        source_component=component,
        mapping_version=mapping_version,
    ).first()


def _create_lineage(
    *, result, source, component, checksum, mapping_version, status,
    target=None, details=None,
):
    from apps.reports.models import HistoricalMigrationLineage

    return HistoricalMigrationLineage.objects.create(
        run_id=result.run_id,
        source_app=source._meta.app_label,
        source_model=source._meta.model_name,
        source_pk=str(source.pk),
        source_component=component,
        target_app=target._meta.app_label if target else "",
        target_model=target._meta.model_name if target else "",
        target_pk=str(target.pk) if target else "",
        status=status,
        source_checksum=checksum,
        mapping_version=mapping_version,
        details=details or {},
    )


def _source_months(assemblies, from_date=None, to_date=None):
    from apps.bookkeeper.models import Expenditure, FixedExpenditure, Income, Overhead, Revenue, Tithe
    from apps.people.models import Attendance, SundaySchoolAttendance

    assembly_ids = list(assemblies.values_list("pk", flat=True))
    dates = set()
    specs = [
        (Attendance.objects.filter(assembly_id__in=assembly_ids), "timestamp"),
        (Tithe.all_objects.filter(assembly_id__in=assembly_ids, is_trash=False), "timestamp"),
        (Revenue.objects.filter(assembly_id__in=assembly_ids), "timestamp"),
        (Overhead.objects.filter(assembly_id__in=assembly_ids), "timestamp"),
        (Income.objects.filter(church_id__in=assembly_ids), "timestamp"),
        (FixedExpenditure.objects.filter(assembly_id__in=assembly_ids), "timestamp"),
        (SundaySchoolAttendance.objects.filter(assembly_id__in=assembly_ids), "service_date"),
    ]
    for queryset, field in specs:
        for assembly_id, value in queryset.exclude(**{f"{field}__isnull": True}).values_list(
            queryset.model._meta.get_field("assembly").attname
            if any(f.name == "assembly" for f in queryset.model._meta.fields)
            else "church_id",
            field,
        ):
            if in_range(value, from_date, to_date):
                dates.add((assembly_id, value.replace(day=1)))
    for row in Expenditure.objects.filter(assembly_id__in=assembly_ids).only(
        "assembly_id", "timestamp", "invoice_date"
    ):
        value = row.timestamp or row.invoice_date
        if value and in_range(value, from_date, to_date):
            dates.add((row.assembly_id, value.replace(day=1)))
    return sorted(dates)


def backfill_monthly_reports(*, apply=False, assembly=None, from_date=None, to_date=None):
    from apps.churches.models import Church
    from apps.reports.models import AssemblyReport

    result = MigrationResult(dry_run=not apply)
    assemblies = filtered_assemblies(assembly)
    months = _source_months(assemblies, from_date, to_date)
    for assembly_id, month in months:
        church = Church.objects.get(pk=assembly_id)
        start, end = report_period(month)
        touching = list(AssemblyReport.objects.filter(
            assembly_id=assembly_id,
            period_start__lte=end,
            period_end__gte=start,
        ).order_by("id"))
        exact = [row for row in touching if row.period_start == start and row.period_end == end]
        if len(touching) != 1 or len(exact) != 1:
            if touching:
                result.add(
                    f"CONFLICT REPORT {church.name} {start:%Y-%m}: "
                    + ", ".join(f"#{row.pk}[{row.period_start}..{row.period_end}]" for row in touching),
                    kind="conflicts",
                )
                continue
            if apply:
                report = ensure_report(
                    assembly=church,
                    period_start=start,
                    historical_backfill=True,
                )
                result.affected_report_ids.add(report.pk)
            result.add(f"CREATE HISTORICAL REPORT {church.name} {start:%Y-%m}", kind="created")
            continue
        report = exact[0]
        missing_sections = 6 - report.sections.count()
        if missing_sections and is_protected_report(report):
            result.add(
                f"PROTECTED REPORT #{report.pk} {church.name} {start:%Y-%m}: "
                f"{missing_sections} section(s) missing; manual review required",
                kind="conflicts",
            )
        elif missing_sections:
            if apply:
                ensure_report(assembly=church, period_start=start)
            result.add(
                f"REPAIR SECTIONS Report #{report.pk}: {missing_sections} missing",
                kind="updated",
            )
        else:
            result.add(f"EXISTS Report #{report.pk} {church.name} {start:%Y-%m}", kind="skipped")
    return result


def _relationship_specs(assembly_ids):
    from apps.bookkeeper.models import Expenditure, Overhead, Revenue
    from apps.people.models import Attendance, SundaySchoolAttendance

    return [
        (Attendance.objects.filter(assembly_id__in=assembly_ids), "assembly", "timestamp"),
        (Revenue.objects.filter(assembly_id__in=assembly_ids), "assembly", "timestamp"),
        (Overhead.objects.filter(assembly_id__in=assembly_ids), "assembly", "timestamp"),
        (Expenditure.objects.filter(assembly_id__in=assembly_ids), "assembly", "expenditure_date"),
        (SundaySchoolAttendance.objects.filter(assembly_id__in=assembly_ids), "assembly", "service_date"),
    ]


def _authoritative_legacy_monthly(assembly_ids, from_date=None, to_date=None):
    from apps.bookkeeper.models import FixedExpenditure, Income

    authoritative = []
    superseded = []
    specs = (
        (Income.objects.filter(church_id__in=assembly_ids).exclude(timestamp=None), "church_id"),
        (FixedExpenditure.objects.filter(assembly_id__in=assembly_ids), "assembly_id"),
    )
    for queryset, assembly_attr in specs:
        rows = [row for row in queryset if in_range(row.timestamp, from_date, to_date)]
        for candidates in _group_monthly(rows, assembly_attr).values():
            winner, older = latest_wins(candidates)
            authoritative.append(winner)
            superseded.extend((row, winner) for row in older)
    return authoritative, superseded


def _authoritative_tithes(assembly_ids, from_date=None, to_date=None):
    from apps.bookkeeper.models import Tithe

    rows = list(Tithe.all_objects.filter(assembly_id__in=assembly_ids, is_trash=False))
    groups = defaultdict(list)
    anonymous = []
    for row in rows:
        if not in_range(row.timestamp, from_date, to_date):
            continue
        if row.member_id is None:
            anonymous.append(row)
        else:
            groups[(row.assembly_id, row.member_id, row.timestamp.year, row.timestamp.month)].append(row)
    authoritative, superseded = list(anonymous), []
    for candidates in groups.values():
        winner, older = latest_wins(candidates)
        authoritative.append(winner)
        superseded.extend((row, winner) for row in older)
    return authoritative, superseded


def backfill_report_relationships(*, apply=False, assembly=None, from_date=None, to_date=None):
    from apps.bookkeeper.models import Expenditure
    from apps.reports.models import HistoricalMigrationLineage

    result = MigrationResult(dry_run=not apply)
    assemblies = filtered_assemblies(assembly)
    assembly_ids = list(assemblies.values_list("pk", flat=True))
    specs = _relationship_specs(assembly_ids)
    tithes, superseded_tithes = _authoritative_tithes(assembly_ids, from_date, to_date)
    legacy_monthly, superseded_legacy = _authoritative_legacy_monthly(
        assembly_ids, from_date, to_date
    )
    specs.append((tithes, "assembly", "timestamp"))
    specs.extend([
        ([row for row in legacy_monthly if row._meta.model_name == "income"], "church", "timestamp"),
        ([row for row in legacy_monthly if row._meta.model_name == "fixedexpenditure"], "assembly", "timestamp"),
    ])

    for old, winner in [*superseded_tithes, *superseded_legacy]:
        if old._meta.model_name == "tithe":
            checksum = model_checksum(old, ["assembly_id", "member_id", "timestamp", "amount", "is_trash"])
            message = (
                f"DUPLICATE TITHE {old.assembly.name} {old.timestamp:%Y-%m} member={old.member_id}: "
                f"selected #{winner.pk}; superseded #{old.pk}"
            )
            reason = "latest active member/month tithe"
        else:
            assembly_field = "church_id" if old._meta.model_name == "income" else "assembly_id"
            checksum = model_checksum(old, [assembly_field, "timestamp"])
            message = (
                f"DUPLICATE MONTHLY {old._meta.model_name.upper()} {old.timestamp:%Y-%m}: "
                f"selected #{winner.pk}; superseded #{old.pk}"
            )
            reason = "latest authoritative monthly report"
        existing = _lineage_existing(old, "report_relationship", RELATIONSHIP_MAPPING_VERSION)
        result.add(message, kind="skipped")
        if apply and existing is None:
            _create_lineage(
                result=result, source=old, component="report_relationship", checksum=checksum,
                mapping_version=RELATIONSHIP_MAPPING_VERSION,
                status=HistoricalMigrationLineage.Status.SUPERSEDED,
                target=winner,
                details={"selected_source_pk": winner.pk, "reason": reason},
            )

    for rows, assembly_field, date_field in specs:
        iterable = rows.iterator() if hasattr(rows, "iterator") else iter(rows)
        for row in iterable:
            value = (row.timestamp or row.invoice_date) if isinstance(row, Expenditure) else getattr(row, date_field)
            if value is None or not in_range(value, from_date, to_date):
                continue
            if row._meta.model_name == "sundayschoolattendance" and value < SUNDAY_SCHOOL_START_DATE:
                result.add(
                    f"PRE-LAUNCH SUNDAY SCHOOL #{row.pk} {value}: manual review required",
                    kind="conflicts",
                )
                continue
            source_report = getattr(row, "report", None)
            if source_report and is_protected_report(source_report):
                result.add(f"PROTECTED SOURCE REPORT #{source_report.pk}: skip {row}", kind="conflicts")
                continue
            try:
                report = canonical_report_for(getattr(row, assembly_field), value)
            except ValidationError as exc:
                result.add(f"RELATIONSHIP CONFLICT {row._meta.label} #{row.pk}: {exc}", kind="conflicts")
                continue
            if is_protected_report(report):
                result.add(f"PROTECTED TARGET REPORT #{report.pk}: skip {row}", kind="conflicts")
                continue
            if row.report_id == report.pk:
                result.add(f"LINK EXISTS {row._meta.label} #{row.pk} -> Report #{report.pk}", kind="skipped")
                continue
            checksum = model_checksum(row, [
                getattr(row._meta.get_field(assembly_field), "attname"),
                "timestamp" if hasattr(row, "timestamp") else date_field,
            ])
            if apply:
                with transaction.atomic():
                    row.__class__._base_manager.filter(pk=row.pk).update(report_id=report.pk)
                    existing = _lineage_existing(row, "report_relationship", RELATIONSHIP_MAPPING_VERSION)
                    if existing is None:
                        _create_lineage(
                            result=result, source=row, component="report_relationship",
                            checksum=checksum, mapping_version=RELATIONSHIP_MAPPING_VERSION,
                            status=HistoricalMigrationLineage.Status.MIGRATED,
                            target=report,
                            details={"previous_report_id": row.report_id},
                        )
                result.affected_report_ids.add(report.pk)
            result.add(
                f"LINK {row._meta.label} #{row.pk}: {row.report_id or 'null'} -> Report #{report.pk}",
                kind="updated",
            )
    if apply:
        _recalculate_reports(result.affected_report_ids)
    return result


def _group_monthly(rows, assembly_attr):
    groups = defaultdict(list)
    for row in rows:
        assembly_id = getattr(row, assembly_attr)
        groups[(assembly_id, row.timestamp.year, row.timestamp.month)].append(row)
    return groups


def _format_duplicate(label, winner, older):
    candidates = ", ".join(f"#{row.pk}" for row in [winner, *older])
    return (
        f"DUPLICATE MONTHLY {label.upper()} | Assembly: "
        f"{getattr(winner, 'assembly', getattr(winner, 'church', None))} | "
        f"Period: {winner.timestamp:%Y-%m} | Candidates: {candidates} | "
        f"Selected: #{winner.pk} | Superseded: "
        f"{', '.join(f'#{row.pk}' for row in older)} | Reason: latest authoritative monthly report"
    )


def _record_superseded(result, older, winner, mapping_version, apply):
    from apps.reports.models import HistoricalMigrationLineage

    for row in older:
        checksum = model_checksum(row, [field.name for field in row._meta.fields if field.name != "report"])
        existing = _lineage_existing(row, "record", mapping_version)
        if apply and existing is None:
            _create_lineage(
                result=result, source=row, component="record", checksum=checksum,
                mapping_version=mapping_version,
                status=HistoricalMigrationLineage.Status.SUPERSEDED,
                target=winner,
                details={"selected_source_pk": winner.pk, "reason": "latest authoritative monthly report"},
            )


def _migrate_component(
    *, result, source, component, amount, mapping_version, target_model,
    target_lookup, target_values, apply,
):
    from apps.reports.models import HistoricalMigrationLineage

    checksum = stable_checksum({
        "source_pk": source.pk,
        "component": component,
        "amount": str(amount),
        "mapping_version": mapping_version,
    })
    existing_lineage = _lineage_existing(source, component, mapping_version)
    if existing_lineage:
        if existing_lineage.source_checksum != checksum:
            result.add(
                f"CHECKSUM CONFLICT {source._meta.label} #{source.pk}/{component}",
                kind="conflicts",
            )
        else:
            result.add(
                f"ALREADY MIGRATED {source._meta.label} #{source.pk}/{component}",
                kind="skipped",
            )
        return None
    if amount == 0:
        if apply:
            _create_lineage(
                result=result, source=source, component=component, checksum=checksum,
                mapping_version=mapping_version,
                status=HistoricalMigrationLineage.Status.SKIPPED,
                details={"reason": "zero-valued component evaluated"},
            )
        result.add(f"ZERO COMPONENT {source._meta.label} #{source.pk}/{component}", kind="skipped")
        return None
    collision = target_model.objects.filter(**target_lookup).first()
    if collision:
        result.add(
            f"TARGET CONFLICT {source._meta.label} #{source.pk}/{component} -> "
            f"{target_model._meta.label} #{collision.pk} (no matching lineage)",
            kind="conflicts",
        )
        return None
    target = target_model(**target_values)
    if apply:
        target_model.objects.bulk_create([target])
        _create_lineage(
            result=result, source=source, component=component, checksum=checksum,
            mapping_version=mapping_version,
            status=HistoricalMigrationLineage.Status.MIGRATED,
            target=target,
            details={"amount": str(amount)},
        )
        result.affected_report_ids.add(target.report_id)
    result.add(
        f"MIGRATE {source._meta.label} #{source.pk}/{component} -> {target_model._meta.label} {amount}",
        kind="created",
    )
    return target


def _authoritative_tithe_total(assembly_id, year, month):
    rows, _ = _authoritative_tithes([assembly_id])
    return sum(
        (row.amount for row in rows if row.timestamp.year == year and row.timestamp.month == month),
        Decimal("0.00"),
    )


def _migrate_remittance(result, fixed, report, mapping_version, apply):
    from apps.bookkeeper.models import RemittanceObligation, RemittancePayment
    from apps.reports.models import HistoricalMigrationLineage

    component = "remittance_obligation"
    tithe_total = _authoritative_tithe_total(fixed.assembly_id, fixed.timestamp.year, fixed.timestamp.month)
    rate = Decimal(REMITTANCE_RATE)
    amount_due = (tithe_total * rate).quantize(Decimal("0.01"))
    checksum = stable_checksum({
        "source_pk": fixed.pk,
        "component": component,
        "tithe_total": str(tithe_total),
        "rate": str(rate),
        "amount_due": str(amount_due),
        "legacy_remittance": str(fixed.remittance),
    })
    existing_lineage = _lineage_existing(fixed, component, mapping_version)
    obligation = RemittanceObligation.objects.filter(
        assembly_id=fixed.assembly_id, period_start=report.period_start
    ).first()
    if existing_lineage:
        if existing_lineage.source_checksum == checksum:
            result.add(f"ALREADY MIGRATED remittance obligation FixedExpenditure #{fixed.pk}", kind="skipped")
        else:
            result.add(f"CHECKSUM CONFLICT remittance obligation FixedExpenditure #{fixed.pk}", kind="conflicts")
        return
    if obligation:
        result.add(f"TARGET CONFLICT remittance obligation #{obligation.pk} has no lineage", kind="conflicts")
        return
    obligation = RemittanceObligation(
        assembly_id=fixed.assembly_id,
        report=report,
        period_start=report.period_start,
        tithe_total_snapshot=tithe_total,
        rate=rate,
        amount_due=amount_due,
        source_fixed_expenditure=fixed,
    )
    if apply:
        RemittanceObligation.objects.bulk_create([obligation])
        _create_lineage(
            result=result, source=fixed, component=component, checksum=checksum,
            mapping_version=mapping_version,
            status=HistoricalMigrationLineage.Status.MIGRATED,
            target=obligation,
            details={"tithe_total_snapshot": str(tithe_total), "rate": str(rate), "amount_due": str(amount_due)},
        )
    result.add(f"MIGRATE REMITTANCE DUE FixedExpenditure #{fixed.pk}: {amount_due}", kind="created")

    payment_component = "remittance_payment"
    payment_checksum = stable_checksum({
        "source_pk": fixed.pk,
        "amount": str(fixed.remittance),
        "receipt": str(fixed.remittance_receipt),
        "verified": fixed.is_remittance_verified,
        "moderator": fixed.remittance_moderator_id,
    })
    if not fixed.remittance or not fixed.remittance_receipt:
        if apply:
            _create_lineage(
                result=result, source=fixed, component=payment_component,
                checksum=payment_checksum, mapping_version=mapping_version,
                status=HistoricalMigrationLineage.Status.SKIPPED,
                details={"reason": "no receipt-backed historical payment claim"},
            )
        result.add(
            f"NO PAYMENT CLAIM FixedExpenditure #{fixed.pk}: remittance remains due only",
            kind="skipped",
        )
        return
    verified = bool(fixed.is_remittance_verified and fixed.remittance_moderator_id)
    payment = RemittancePayment(
        obligation=obligation,
        report=report,
        amount_paid=fixed.remittance,
        payment_date=fixed.timestamp,
        receipt=fixed.remittance_receipt.name,
        status=RemittancePayment.Status.VERIFIED if verified else RemittancePayment.Status.PENDING,
        submitted_by=fixed.created_by,
        submitted_at=fixed.created_at,
        verified_by=fixed.remittance_moderator if verified else None,
        verified_at=fixed.updated_at if verified else None,
        review_notes="Migrated from legacy FixedExpenditure remittance evidence.",
        source_fixed_expenditure=fixed,
    )
    if apply:
        RemittancePayment.objects.bulk_create([payment])
        _create_lineage(
            result=result, source=fixed, component=payment_component,
            checksum=payment_checksum, mapping_version=mapping_version,
            status=HistoricalMigrationLineage.Status.MIGRATED,
            target=payment,
            details={"legacy_verified": fixed.is_remittance_verified, "status": payment.status},
        )
        result.affected_report_ids.add(report.pk)
    result.add(
        f"MIGRATE REMITTANCE CLAIM FixedExpenditure #{fixed.pk}: {fixed.remittance} ({payment.status})",
        kind="created",
    )


def backfill_finance_models(
    *, apply=False, assembly=None, from_date=None, to_date=None, allow_post_cutoff=False
):
    from apps.bookkeeper.models import (
        FixedExpenditure, Income, Overhead, OverheadType, Revenue, RevenueCategory,
    )

    result = MigrationResult(dry_run=not apply)
    manifest = load_mapping_manifest()
    metadata = mapping_metadata()
    mapping_version = f"{metadata['version']}:{metadata['checksum']}"
    assembly_ids = list(filtered_assemblies(assembly).values_list("pk", flat=True))
    income_rows = list(Income.objects.filter(church_id__in=assembly_ids).exclude(timestamp=None))
    fixed_rows = list(FixedExpenditure.objects.filter(assembly_id__in=assembly_ids))
    rows_in_scope = [
        row for row in [*income_rows, *fixed_rows]
        if in_range(row.timestamp, from_date, to_date)
    ]
    post_cutoff = [row for row in rows_in_scope if row.timestamp >= NEW_FINANCE_START]
    if post_cutoff and not allow_post_cutoff:
        raise ValidationError({
            "cutoff": (
                f"Refusing {len(post_cutoff)} legacy finance row(s) dated on/after "
                f"{NEW_FINANCE_START}; use --allow-post-cutoff only after manual approval."
            )
        })
    income_rows = [row for row in income_rows if in_range(row.timestamp, from_date, to_date)]
    fixed_rows = [row for row in fixed_rows if in_range(row.timestamp, from_date, to_date)]

    groups = []
    for label, source_rows, assembly_attr in (
        ("Income", income_rows, "church_id"),
        ("FixedExpenditure", fixed_rows, "assembly_id"),
    ):
        for key, candidates in _group_monthly(source_rows, assembly_attr).items():
            winner, older = latest_wins(candidates)
            groups.append((label, key, winner, older))

    for label, _key, winner, older in sorted(groups, key=lambda item: (item[1], item[0])):
        if older:
            result.add(_format_duplicate(label, winner, older))
        try:
            assembly_obj = winner.church if label == "Income" else winner.assembly
            report = canonical_report_for(assembly_obj, winner.timestamp)
        except ValidationError as exc:
            result.add(f"FINANCE REPORT CONFLICT {label} #{winner.pk}: {exc}", kind="conflicts")
            continue
        if is_protected_report(report):
            result.add(f"PROTECTED REPORT #{report.pk}: skip {label} #{winner.pk}", kind="conflicts")
            continue
        with transaction.atomic():
            _record_superseded(result, older, winner, mapping_version, apply)
            if label == "Income":
                for mapping in manifest["income_to_revenue"]:
                    component = mapping["source_component"]
                    category = RevenueCategory.objects.filter(
                        assembly=None, is_standard=True, name=mapping["target_category"]
                    ).first()
                    if category is None:
                        result.add(f"MISSING REVENUE CATEGORY {mapping['target_category']}", kind="conflicts")
                        continue
                    amount = getattr(winner, component)
                    _migrate_component(
                        result=result, source=winner, component=component, amount=amount,
                        mapping_version=mapping_version, target_model=Revenue,
                        target_lookup={"report": report, "category": category},
                        target_values={
                            "assembly_id": winner.church_id, "report": report,
                            "category": category, "amount": amount, "timestamp": winner.timestamp,
                            "notes": winner.notes, "statement": winner.statement.name if winner.statement else "",
                        },
                        apply=apply,
                    )
            else:
                for mapping in manifest["fixed_expenditure_to_overhead"]:
                    component = mapping["source_component"]
                    overhead_type = OverheadType.objects.filter(
                        assembly=None, is_global=True, name=mapping["target_type"]
                    ).first()
                    if overhead_type is None:
                        result.add(f"MISSING OVERHEAD TYPE {mapping['target_type']}", kind="conflicts")
                        continue
                    amount = getattr(winner, component)
                    _migrate_component(
                        result=result, source=winner, component=component, amount=amount,
                        mapping_version=mapping_version, target_model=Overhead,
                        target_lookup={"report": report, "overhead_type": overhead_type},
                        target_values={
                            "assembly_id": winner.assembly_id, "report": report,
                            "overhead_type": overhead_type, "amount": amount,
                            "timestamp": winner.timestamp, "notes": winner.remarks,
                        },
                        apply=apply,
                    )
                _migrate_remittance(result, winner, report, mapping_version, apply)
        if apply:
            _recalculate_reports({report.pk})
    return result


def backfill_attendance_headcounts(*, apply=False, assembly=None, from_date=None, to_date=None):
    from apps.people.models import Attendance
    from apps.reports.models import HistoricalMigrationLineage

    result = MigrationResult(dry_run=not apply)
    assembly_ids = list(filtered_assemblies(assembly).values_list("pk", flat=True))
    queryset = Attendance.objects.filter(assembly_id__in=assembly_ids, is_deleted=False)
    for row in queryset.order_by("assembly_id", "timestamp", "id"):
        if not in_range(row.timestamp, from_date, to_date):
            continue
        try:
            report = canonical_report_for(row.assembly, row.timestamp)
        except ValidationError as exc:
            result.add(f"ATTENDANCE REPORT CONFLICT #{row.pk}: {exc}", kind="conflicts")
            continue
        if is_protected_report(report) or (row.report and is_protected_report(row.report)):
            result.add(f"PROTECTED REPORT: skip Attendance #{row.pk}", kind="conflicts")
            continue
        checksum = model_checksum(row, [
            "adults", "children", "guest_attendance", "new_converts", "altar_call",
            "baptisms", "online_viewers", "timestamp", "assembly_id",
        ])
        existing = _lineage_existing(row, "historical_headcount", ATTENDANCE_MAPPING_VERSION)
        if existing:
            if existing.source_checksum == checksum:
                result.add(f"ALREADY BACKFILLED Attendance #{row.pk}", kind="skipped")
            else:
                result.add(f"CHECKSUM CONFLICT Attendance #{row.pk}", kind="conflicts")
            continue
        if apply:
            with transaction.atomic():
                Attendance.objects.filter(pk=row.pk).update(
                    collection_schema=Attendance.CollectionSchema.LEGACY,
                    men=None,
                    women=None,
                    visitor_men=None,
                    visitor_women=None,
                    new_convert_men=None,
                    new_convert_women=None,
                    altar_call_men=None,
                    altar_call_women=None,
                    baptism_men=None,
                    baptism_women=None,
                    total_adults=row.adults,
                    total_visitors=row.guest_attendance,
                    total_new_converts=row.new_converts,
                    total_altar_call=row.altar_call,
                    total_baptisms=row.baptisms,
                    report=report,
                )
                _create_lineage(
                    result=result, source=row, component="historical_headcount",
                    checksum=checksum, mapping_version=ATTENDANCE_MAPPING_VERSION,
                    status=HistoricalMigrationLineage.Status.MIGRATED,
                    target=row,
                    details={
                        "formula": "adults + legacy children + online_viewers",
                        "visitors_excluded": True,
                        "gender_breakdown": "not_collected",
                    },
                )
            result.affected_report_ids.add(report.pk)
        result.add(
            f"BACKFILL Attendance #{row.pk}: {row.adults}+{row.children}+{row.online_viewers}="
            f"{row.adults + row.children + row.online_viewers}; visitors {row.guest_attendance} excluded",
            kind="updated",
        )
    if apply:
        _recalculate_reports(result.affected_report_ids)
    return result


def _recalculate_reports(report_ids):
    from apps.reports.models import AssemblyReport

    for report in AssemblyReport.objects.filter(pk__in=report_ids).order_by("pk"):
        if is_protected_report(report):
            continue
        report.calculate_totals()
        report.recalculate_attendance_totals()
        AssemblyReport.objects.filter(pk=report.pk).update(
            income_total=report.income_total,
            expense_total=report.expense_total,
            tithe_total=report.tithe_total,
            balance=report.balance,
        )
