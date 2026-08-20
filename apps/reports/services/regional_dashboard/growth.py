from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.utils import timezone

from apps.reports.models import AssemblyReport
from apps.reports.services.regional_dashboard.schemas import get_growth_table_schema
from apps.reports.services.regional_dashboard.utils import (
    AssembliesWithReports,
    earliest_report,
    group_by_country,
    items_for_zone,
    latest_report,
    normalize_period,
    percent,
    years_between,
)


NEW_PLANT_WINDOW_DAYS = 730


def _is_newly_planted(assembly, today) -> bool:
    return bool(
        assembly.established_date and
        assembly.established_date >= today - timedelta(days=NEW_PLANT_WINDOW_DAYS)
    )


def _growth_status(
    *,
    is_newly_planted: bool,
    has_reports: bool,
    growth_rate: float,
    net_growth: int,
) -> str:
    if is_newly_planted:
        return "NEW_PLANT"
    if not has_reports:
        return "NO_DATA"
    if net_growth > 0 and growth_rate > 0:
        return "GROWING"
    if net_growth < 0:
        return "DECLINING"
    return "STABLE"


def build_assembly_growth_row(
    assembly,
    reports: list[AssemblyReport],
    *,
    country: str,
    today=None,
) -> dict[str, Any]:
    today = today or timezone.localdate()
    first_report = earliest_report(reports)
    last_report = latest_report(reports)
    previous_members = first_report.members_total if first_report else 0
    total_members = last_report.members_total if last_report else 0
    new_members = sum(report.total_new_converts or 0 for report in reports)
    total_new_converts = new_members
    total_baptisms = sum(report.total_baptisms or 0 for report in reports)
    total_visitors = sum(report.total_visitors or 0 for report in reports)
    net_growth = total_members - previous_members
    lost_members = max((previous_members + new_members) - total_members, 0)
    growth_rate = percent(net_growth, previous_members)
    is_newly_planted = _is_newly_planted(assembly, today)

    return {
        "id": assembly.id,
        "name": assembly.name,
        "zone": assembly.zone.name if assembly.zone else None,
        "country": country,
        "total_members": total_members,
        "previous_members": previous_members,
        "new_members": new_members,
        "lost_members": lost_members,
        "net_growth": net_growth,
        "growth_rate": growth_rate,
        "total_baptisms": total_baptisms,
        "total_visitors": total_visitors,
        "total_new_converts": total_new_converts,
        "established_date": assembly.established_date,
        "is_newly_planted": is_newly_planted,
        "church_age_years": years_between(assembly.established_date, today),
        "growth_status": _growth_status(
            is_newly_planted=is_newly_planted,
            has_reports=bool(reports),
            growth_rate=growth_rate,
            net_growth=net_growth,
        ),
    }


def _summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_members = sum(row["total_members"] for row in rows)
    previous_members = sum(row["previous_members"] for row in rows)
    new_members = sum(row["new_members"] for row in rows)
    lost_members = sum(row["lost_members"] for row in rows)
    net_growth = total_members - previous_members
    declining_rows = [row for row in rows if row["growth_status"] == "DECLINING"]
    fastest = max(rows, key=lambda row: row["growth_rate"], default=None)

    return {
        "assemblies": len(rows),
        "total_members": total_members,
        "previous_members": previous_members,
        "new_members": new_members,
        "lost_members": lost_members,
        "net_growth": net_growth,
        "growth_rate": percent(net_growth, previous_members),
        "total_baptisms": sum(row["total_baptisms"] for row in rows),
        "total_visitors": sum(row["total_visitors"] for row in rows),
        "total_new_converts": sum(row["total_new_converts"] for row in rows),
        "newly_planted_churches": sum(1 for row in rows if row["is_newly_planted"]),
        "fastest_growing_assembly": {
            "id": fastest["id"],
            "name": fastest["name"],
            "growth_rate": fastest["growth_rate"],
        } if fastest else None,
        "declining_assemblies": len(declining_rows),
    }


def build_region_growth_module(
    region,
    assemblies_with_reports: AssembliesWithReports,
    *,
    year: int,
    period: str | None = None,
) -> dict[str, Any]:
    period_mode = normalize_period(period)
    today = timezone.localdate()
    zones_output = []
    all_rows: list[dict[str, Any]] = []

    for zone in region.zones.all():
        zone_items = items_for_zone(zone, assemblies_with_reports)
        zone_rows: list[dict[str, Any]] = []
        countries = []

        for (country_name, currency), country_items in group_by_country(zone_items).items():
            rows = [
                build_assembly_growth_row(
                    assembly,
                    reports,
                    country=country_name,
                    today=today,
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
        "table_schema": get_growth_table_schema(),
    }
