from __future__ import annotations

import calendar
from dataclasses import asdict, dataclass
from datetime import date

from django.core.exceptions import ValidationError


@dataclass(frozen=True)
class ReportPeriodFinding:
    code: str
    report_id: int | None
    assembly_id: int
    period_start: date
    period_end: date
    message: str

    def to_dict(self):
        payload = asdict(self)
        payload["period_start"] = self.period_start.isoformat()
        payload["period_end"] = self.period_end.isoformat()
        return payload


def report_period(value: date) -> tuple[date, date]:
    start = value.replace(day=1)
    end = value.replace(day=calendar.monthrange(value.year, value.month)[1])
    return start, end


def is_canonical_period(period_start: date, period_end: date) -> bool:
    return (period_start, period_end) == report_period(period_start)


def period_findings(queryset=None) -> list[ReportPeriodFinding]:
    """Return every noncanonical, overlapping, or duplicate-month report."""
    from apps.reports.models import AssemblyReport

    reports = list(
        (queryset if queryset is not None else AssemblyReport.objects.all())
        .order_by("assembly_id", "period_start", "period_end", "id")
    )
    findings: list[ReportPeriodFinding] = []
    by_assembly: dict[int, list] = {}
    for report in reports:
        by_assembly.setdefault(report.assembly_id, []).append(report)
        if not is_canonical_period(report.period_start, report.period_end):
            findings.append(ReportPeriodFinding(
                code="noncanonical_period",
                report_id=report.pk,
                assembly_id=report.assembly_id,
                period_start=report.period_start,
                period_end=report.period_end,
                message="Report does not use the first and last day of its calendar month.",
            ))

    by_month: dict[tuple[int, int, int], list] = {}
    for report in reports:
        key = (report.assembly_id, report.period_start.year, report.period_start.month)
        by_month.setdefault(key, []).append(report)
    for (assembly_id, year, month), month_reports in by_month.items():
        if len(month_reports) > 1:
            for report in month_reports:
                findings.append(ReportPeriodFinding(
                    code="multiple_reports_same_month",
                    report_id=report.pk,
                    assembly_id=assembly_id,
                    period_start=report.period_start,
                    period_end=report.period_end,
                    message=(
                        f"Assembly has {len(month_reports)} reports representing {year:04d}-{month:02d}."
                    ),
                ))

    seen_pairs: set[tuple[int, int]] = set()
    for assembly_id, assembly_reports in by_assembly.items():
        for index, report in enumerate(assembly_reports):
            for other in assembly_reports[index + 1:]:
                if other.period_start > report.period_end:
                    break
                pair = (report.pk, other.pk)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                findings.append(ReportPeriodFinding(
                    code="overlapping_reports",
                    report_id=report.pk,
                    assembly_id=assembly_id,
                    period_start=report.period_start,
                    period_end=report.period_end,
                    message=f"Overlaps Report #{other.pk} ({other.period_start} to {other.period_end}).",
                ))
    return findings


def assert_safe_canonical_period(*, assembly, value: date, exclude_report_id=None):
    """Block creation/selection when any competing report touches the month."""
    from apps.reports.models import AssemblyReport

    start, end = report_period(value)
    conflicts = AssemblyReport.objects.filter(
        assembly=assembly,
        period_start__lte=end,
        period_end__gte=start,
    )
    if exclude_report_id is not None:
        conflicts = conflicts.exclude(pk=exclude_report_id)
    conflict_rows = list(conflicts.order_by("period_start", "period_end", "id"))
    if conflict_rows:
        labels = ", ".join(
            f"#{row.pk} [{row.period_start}..{row.period_end}]" for row in conflict_rows
        )
        raise ValidationError({
            "period": f"Canonical report period is blocked by existing report(s): {labels}."
        })
    return start, end
