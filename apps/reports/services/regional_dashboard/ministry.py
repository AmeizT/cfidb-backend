from __future__ import annotations

from typing import Any

from django.db.models import Sum

from apps.churches.models import ChurchMeeting, Outreach
from apps.people.models.spaces import Homecell
from apps.reports.models import AssemblyReport
from apps.reports.services.regional_dashboard.schemas import get_ministry_table_schema
from apps.reports.services.regional_dashboard.utils import (
    AssembliesWithReports,
    group_by_country,
    items_for_zone,
    normalize_period,
    percent,
)


def _ministry_status(score: float, has_activity: bool) -> str:
    if not has_activity:
        return "NO_DATA"
    if score >= 75:
        return "ACTIVE"
    if score >= 45:
        return "STABLE"
    if score > 0:
        return "LOW_ACTIVITY"
    return "INACTIVE"


def build_assembly_ministry_row(
    assembly,
    reports: list[AssemblyReport],
    *,
    country: str,
    year: int,
) -> dict[str, Any]:
    outreach_qs = Outreach.objects.filter(
        assembly=assembly,
        outreach_date__year=year,
    )
    planned_outreaches = outreach_qs.exclude(status=Outreach.Status.CANCELLED).count()
    actual_outreaches = outreach_qs.filter(status=Outreach.Status.COMPLETED).count()
    reported_outreaches = sum(getattr(report, "total_outreaches", 0) or 0 for report in reports)

    if planned_outreaches == 0 and reported_outreaches:
        planned_outreaches = reported_outreaches

    completed_outreach_qs = outreach_qs.filter(status=Outreach.Status.COMPLETED)
    volunteers = completed_outreach_qs.aggregate(total=Sum("outreach_team_size"))["total"] or 0
    homecells_planted = sum(
        getattr(report, "total_homecells_planted", 0) or 0
        for report in reports
    )
    homecell_attendance = sum(
        getattr(report, "total_homecell_attendance", 0) or 0
        for report in reports
    )
    active_homecells = Homecell.objects.filter(
        church=assembly,
        is_archived=False,
    ).count()
    completed_meetings = ChurchMeeting.objects.filter(
        assembly=assembly,
        starts_at__year=year,
        status=ChurchMeeting.Status.COMPLETED,
    ).count()
    ministry_events = actual_outreaches + completed_meetings
    outreach_completion_rate = percent(actual_outreaches, planned_outreaches)
    ministry_score = round(
        min(outreach_completion_rate, 100) * 0.35 +
        min(active_homecells / 3, 1) * 25 +
        min(homecell_attendance / 100, 1) * 20 +
        min(ministry_events / 12, 1) * 20,
        2,
    )
    has_activity = any([
        planned_outreaches,
        actual_outreaches,
        homecells_planted,
        active_homecells,
        homecell_attendance,
        ministry_events,
        volunteers,
    ])

    return {
        "id": assembly.id,
        "name": assembly.name,
        "zone": assembly.zone.name if assembly.zone else None,
        "country": country,
        "planned_outreaches": planned_outreaches,
        "actual_outreaches": actual_outreaches,
        "outreach_completion_rate": outreach_completion_rate,
        "homecells_planted": homecells_planted,
        "active_homecells": active_homecells,
        "homecell_attendance": homecell_attendance,
        "ministry_events": ministry_events,
        "volunteers": volunteers,
        "ministry_score": ministry_score,
        "ministry_status": _ministry_status(ministry_score, has_activity),
    }


def _summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    planned_outreaches = sum(row["planned_outreaches"] for row in rows)
    actual_outreaches = sum(row["actual_outreaches"] for row in rows)

    return {
        "assemblies": len(rows),
        "planned_outreaches": planned_outreaches,
        "actual_outreaches": actual_outreaches,
        "outreach_completion_rate": percent(actual_outreaches, planned_outreaches),
        "homecells_planted": sum(row["homecells_planted"] for row in rows),
        "active_homecells": sum(row["active_homecells"] for row in rows),
        "homecell_attendance": sum(row["homecell_attendance"] for row in rows),
        "ministry_events": sum(row["ministry_events"] for row in rows),
        "volunteers": sum(row["volunteers"] for row in rows),
        "active_assemblies": sum(
            1 for row in rows if row["ministry_status"] in {"ACTIVE", "STABLE"}
        ),
        "inactive_assemblies": sum(
            1 for row in rows if row["ministry_status"] in {"INACTIVE", "NO_DATA"}
        ),
    }


def build_region_ministry_module(
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
                build_assembly_ministry_row(
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
            "monthly_available": period_mode == "monthly",
        },
        "zones": zones_output,
        "table_schema": get_ministry_table_schema(),
    }
