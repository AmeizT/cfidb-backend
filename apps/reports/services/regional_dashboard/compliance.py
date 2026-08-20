from __future__ import annotations

from datetime import datetime
from typing import Any

from apps.reports.models import AssemblyReport
from apps.reports.models.section_status import ReportSectionStatus
from apps.reports.services.compliance_calculator import (
    ReportStatus,
    derive_report_status,
)
from apps.reports.services.regional_dashboard.schemas import get_compliance_table_schema
from apps.reports.services.regional_dashboard.utils import (
    AssembliesWithReports,
    group_by_country,
    items_for_zone,
    month_name,
    normalize_period,
    percent,
    period_key,
    risk_level,
)


SECTION_CODES = [choice[0] for choice in ReportSectionStatus.Section.choices]
SUBMITTED_WORKFLOW_STATUSES = {
    AssemblyReport.Status.SUBMITTED,
    AssemblyReport.Status.UNDER_REVIEW,
    AssemblyReport.Status.APPROVED,
}


def _report_by_month(reports: list[AssemblyReport]) -> dict[int, AssemblyReport]:
    return {report.period_start.month: report for report in reports}


def _section_status(section) -> dict[str, Any]:
    if section is None:
        return {
            "status": "MISSING",
            "skip_reason": None,
        }

    return {
        "status": section.status.upper(),
        "skip_reason": section.skip_reason if section.status == "skipped" else None,
    }


def _report_status(report: AssemblyReport | None) -> str:
    if report is None:
        return ReportStatus.NOT_SUBMITTED

    sections = list(report.sections.all())
    derived_status = derive_report_status(sections)

    if report.status == AssemblyReport.Status.DRAFT and derived_status == ReportStatus.NOT_SUBMITTED:
        return "DRAFT"

    return derived_status


def _current_status(
    *,
    missing_reports: int,
    incomplete_reports: int,
    skipped_reports: int,
    late_reports: int,
    compliance_rate: float,
    completion_rate: float,
) -> str:
    if compliance_rate == 100 and completion_rate == 100 and late_reports == 0:
        return "COMPLIANT"
    if missing_reports or incomplete_reports:
        return "INCOMPLETE"
    if skipped_reports:
        return "COMPLIANT_WITH_EXCEPTIONS"
    if late_reports:
        return "LATE"
    return "NO_DATA"


def _compliance_risk_level(
    *,
    missing_reports: int,
    late_reports: int,
    completion_rate: float,
) -> str:
    score = min((missing_reports * 8) + (late_reports * 4) + max(0, 100 - completion_rate), 100)
    return risk_level(score)


def build_assembly_compliance_row(
    assembly,
    reports: list[AssemblyReport],
    *,
    country: str,
    year: int,
) -> dict[str, Any]:
    reports_by_month = _report_by_month(reports)
    monthly_compliance = []
    submitted_reports = 0
    missing_reports = 0
    incomplete_reports = 0
    skipped_reports = 0
    late_reports = 0
    on_time_reports = 0
    total_completion = 0.0
    days_late_total = 0
    last_submitted_at: datetime | None = None
    last_missing_period: str | None = None
    has_skipped_sections = False

    for month in range(1, 13):
        report = reports_by_month.get(month)
        status = _report_status(report)
        sections_payload = {}
        submitted_sections = 0
        covered_sections = 0

        if report is None:
            missing_reports += 1
            last_missing_period = period_key(year, month)
            sections_payload = {
                section_code: _section_status(None)
                for section_code in SECTION_CODES
            }
        else:
            sections_by_code = {section.section: section for section in report.sections.all()}
            for section_code in SECTION_CODES:
                section = sections_by_code.get(section_code)
                sections_payload[section_code] = _section_status(section)

                if section is None:
                    continue
                if section.status in {
                    ReportSectionStatus.Status.COMPLETED,
                    ReportSectionStatus.Status.NO_ACTIVITY,
                }:
                    submitted_sections += 1
                    covered_sections += 1
                elif section.status == ReportSectionStatus.Status.SKIPPED:
                    covered_sections += 1
                    has_skipped_sections = True

            if status in {ReportStatus.SUBMITTED, ReportStatus.SKIPPED}:
                submitted_reports += 1
            elif status == ReportStatus.INCOMPLETE or status == "DRAFT":
                incomplete_reports += 1

            if status == ReportStatus.SKIPPED:
                skipped_reports += 1

            if getattr(report, "is_late", False):
                late_reports += 1
                days_late_total += getattr(report, "days_late", 0) or 0
            elif report.submitted_at or report.status in SUBMITTED_WORKFLOW_STATUSES:
                on_time_reports += 1

            if report.submitted_at and (
                last_submitted_at is None or report.submitted_at > last_submitted_at
            ):
                last_submitted_at = report.submitted_at

        completion = percent(submitted_sections, len(SECTION_CODES))
        total_completion += completion

        monthly_compliance.append({
            "month": month_name(month),
            "period": period_key(year, month),
            "report_status": status,
            "is_submitted": status in {ReportStatus.SUBMITTED, ReportStatus.SKIPPED},
            "is_late": bool(getattr(report, "is_late", False)) if report else False,
            "submitted_at": report.submitted_at if report else None,
            "due_date": getattr(report, "due_date", None) if report else None,
            "days_late": getattr(report, "days_late", 0) or 0 if report else 0,
            "completion": completion,
            "coverage": percent(covered_sections, len(SECTION_CODES)),
            "sections": sections_payload,
        })

    expected_reports = 12
    compliance_rate = percent(submitted_reports, expected_reports)
    on_time_rate = percent(on_time_reports, submitted_reports)
    completion_rate = round(total_completion / expected_reports, 2)
    average_days_late = round(days_late_total / late_reports, 2) if late_reports else 0.0
    current_status = _current_status(
        missing_reports=missing_reports,
        incomplete_reports=incomplete_reports,
        skipped_reports=skipped_reports,
        late_reports=late_reports,
        compliance_rate=compliance_rate,
        completion_rate=completion_rate,
    )

    return {
        "id": assembly.id,
        "name": assembly.name,
        "zone": assembly.zone.name if assembly.zone else None,
        "country": country,
        "expected_reports": expected_reports,
        "submitted_reports": submitted_reports,
        "missing_reports": missing_reports,
        "incomplete_reports": incomplete_reports,
        "skipped_reports": skipped_reports,
        "late_reports": late_reports,
        "on_time_reports": on_time_reports,
        "compliance_rate": compliance_rate,
        "on_time_rate": on_time_rate,
        "completion_rate": completion_rate,
        "average_days_late": average_days_late,
        "current_status": current_status,
        "risk_level": _compliance_risk_level(
            missing_reports=missing_reports,
            late_reports=late_reports,
            completion_rate=completion_rate,
        ),
        "last_submitted_at": last_submitted_at,
        "last_missing_period": last_missing_period,
        "has_skipped_sections": has_skipped_sections,
        "monthly_compliance": monthly_compliance,
    }


def _summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    expected_reports = sum(row["expected_reports"] for row in rows)
    submitted_reports = sum(row["submitted_reports"] for row in rows)
    missing_reports = sum(row["missing_reports"] for row in rows)
    incomplete_reports = sum(row["incomplete_reports"] for row in rows)
    skipped_reports = sum(row["skipped_reports"] for row in rows)
    late_reports = sum(row["late_reports"] for row in rows)
    on_time_reports = sum(row["on_time_reports"] for row in rows)
    average_completion = (
        round(sum(row["completion_rate"] for row in rows) / len(rows), 2)
        if rows else 0.0
    )

    return {
        "assemblies": len(rows),
        "expected_reports": expected_reports,
        "submitted_reports": submitted_reports,
        "missing_reports": missing_reports,
        "incomplete_reports": incomplete_reports,
        "skipped_reports": skipped_reports,
        "late_reports": late_reports,
        "compliance_rate": percent(submitted_reports, expected_reports),
        "on_time_rate": percent(on_time_reports, submitted_reports),
        "average_completion": average_completion,
        "compliant_assemblies": sum(1 for row in rows if row["current_status"] == "COMPLIANT"),
        "non_compliant_assemblies": sum(1 for row in rows if row["current_status"] != "COMPLIANT"),
        "assemblies_with_skipped_sections": sum(1 for row in rows if row["has_skipped_sections"]),
    }


def build_region_compliance_module(
    region,
    assemblies_with_reports: AssembliesWithReports,
    *,
    year: int,
    period: str | None = None,
) -> dict[str, Any]:
    period_mode = normalize_period(period)
    zones_output = []
    all_rows: list[dict[str, Any]] = []

    for zone in region.zones.all():
        zone_items = items_for_zone(zone, assemblies_with_reports)
        zone_rows: list[dict[str, Any]] = []
        countries = []

        for (country_name, currency), country_items in group_by_country(zone_items).items():
            rows = [
                build_assembly_compliance_row(
                    assembly,
                    reports,
                    country=country_name,
                    year=year,
                )
                for assembly, reports in country_items
            ]
            zone_rows.extend(rows)
            all_rows.extend(rows)
            countries.append({
                "name": country_name,
                "currency": currency,
                "summary": _summarize_rows(rows),
                "assemblies": rows,
            })

        zones_output.append({
            "id": zone.id,
            "name": zone.name,
            "summary": _summarize_rows(zone_rows),
            "countries": countries,
        })

    return {
        "summary": {
            **_summarize_rows(all_rows),
            "region_id": region.id,
            "region_name": region.name,
            "year": year,
            "period": period_mode,
            "monthly_available": True,
        },
        "zones": zones_output,
        "table_schema": get_compliance_table_schema(),
    }
