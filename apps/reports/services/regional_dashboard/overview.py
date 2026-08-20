from __future__ import annotations

from apps.churches.models import Church
from apps.people.models.spaces import Homecell
from apps.reports.services.regional_dashboard.utils import (
    AssembliesWithReports,
    items_for_zone,
)


def _is_newly_planted(assembly: Church, year: int) -> bool:
    return bool(assembly.established_date and assembly.established_date.year == year)


def _summary_for_items(
    items: AssembliesWithReports,
    *,
    year: int,
) -> dict:
    total_assemblies = len(items)
    expected_reports = total_assemblies * 12
    reports_submitted = 0
    assemblies_with_reports = 0
    total_members = 0
    total_new_members = 0
    late_submissions = 0
    newly_planted = 0
    countries = set()

    for assembly, reports in items:
        if assembly.country:
            countries.add(assembly.country)
        if reports:
            assemblies_with_reports += 1
        if _is_newly_planted(assembly, year):
            newly_planted += 1

        for report in reports:
            reports_submitted += 1
            total_members += report.members_total or 0
            total_new_members += report.total_new_converts or 0
            if getattr(report, "is_late", False):
                late_submissions += 1

    return {
        "countries": len(countries),
        "assemblies": total_assemblies,
        "assemblies_with_reports": assemblies_with_reports,
        "reports_submitted": reports_submitted,
        "expected_reports": expected_reports,
        "report_submission_rate": (
            round((reports_submitted / expected_reports) * 100, 2)
            if expected_reports else 0.0
        ),
        "compliance_rate": (
            round((assemblies_with_reports / total_assemblies) * 100, 2)
            if total_assemblies else 0.0
        ),
        "total_members": total_members,
        "total_new_members": total_new_members,
        "growth_rate": (
            round((total_new_members / total_members) * 100, 2)
            if total_members else 0.0
        ),
        "late_submissions": late_submissions,
        "newly_planted_churches": newly_planted,
    }


def build_region_overview(
    region,
    assemblies_with_reports: AssembliesWithReports,
    *,
    year: int,
) -> dict:
    summary = _summary_for_items(assemblies_with_reports, year=year)
    total_active_homecells = Homecell.objects.filter(
        church__zone__region=region,
        is_archived=False,
    ).count()
    summary["zones"] = region.zones.count()
    summary["total_active_homecells"] = total_active_homecells
    kpis = {
        "report_submission_rate": summary["report_submission_rate"],
        "compliance_rate": summary["compliance_rate"],
        "growth_rate": summary["growth_rate"],
        "late_submissions": summary["late_submissions"],
        "newly_planted_churches": summary["newly_planted_churches"],
    }

    zone_kpis = []
    for zone in region.zones.all():
        zone_items = items_for_zone(zone, assemblies_with_reports)
        zone_kpis.append({
            "id": zone.id,
            "name": zone.name,
            "summary": _summary_for_items(zone_items, year=year),
        })

    alerts = []
    if summary["report_submission_rate"] < 80:
        alerts.append({
            "type": "Reporting",
            "level": "HIGH",
            "message": "Build custom reports on Stripe data with SQL and AI-assisted natural language prompts.",
        })
    if summary["late_submissions"] > 0:
        alerts.append({
            "type": "Timeliness",
            "level": "MEDIUM",
            "message": "Some reports were submitted after the due date.",
        })
    if summary["newly_planted_churches"] == 0:
        alerts.append({
            "type": "Growth",
            "level": "LOW",
            "message": "No newly planted churches are recorded in this period.",
        })

    return {
        "region": {
            "id": region.id,
            "name": region.name,
        },
        "summary": summary,
        "kpis": kpis,
        "zone_kpis": zone_kpis,
        "alerts": alerts,
    }
