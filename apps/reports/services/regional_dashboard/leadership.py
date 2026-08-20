from __future__ import annotations

from decimal import Decimal
from typing import Any

from apps.bookkeeper.models import Asset
from apps.churches.models import ChurchMeeting
from apps.people.models.spaces import Homecell
from apps.reports.models import AssemblyReport
from apps.reports.services.regional_dashboard.schemas import get_leadership_table_schema
from apps.reports.services.regional_dashboard.utils import (
    AssembliesWithReports,
    group_by_country,
    items_for_zone,
    normalize_period,
    percent,
    user_display_name,
)


def _assets_valuation(assembly) -> float:
    total = Decimal("0.00")

    for asset in Asset.objects.filter(assembly=assembly):
        total += (asset.acquisition_cost or Decimal("0.00")) * asset.units

    return float(round(total, 2))


def _leadership_status(
    *,
    assigned_pastors_count: int,
    meetings_conducted: int,
    verification_rate: float,
    reports_count: int,
) -> str:
    if assigned_pastors_count == 0:
        return "NO_ASSIGNED_PASTOR"
    if reports_count == 0 and meetings_conducted == 0:
        return "NO_DATA"
    if verification_rate < 70 or meetings_conducted == 0:
        return "NEEDS_ATTENTION"
    return "HEALTHY"


def build_assembly_leadership_row(
    assembly,
    reports: list[AssemblyReport],
    *,
    country: str,
    year: int,
) -> dict[str, Any]:
    assigned_pastors = [
        user_display_name(user)
        for user in assembly.assigned_pastors.all()
    ]
    assigned_pastors_count = len(assigned_pastors)
    homecell_leaders = Homecell.objects.filter(
        church=assembly,
        is_archived=False,
        leader__isnull=False,
    ).count()
    leaders_count = assigned_pastors_count + homecell_leaders
    meetings_conducted = ChurchMeeting.objects.filter(
        assembly=assembly,
        starts_at__year=year,
        status=ChurchMeeting.Status.COMPLETED,
    ).count()
    reports_verified = sum(
        1 for report in reports
        if getattr(report, "is_leader_verified", False)
    )
    unverified_reports = max(len(reports) - reports_verified, 0)
    verification_rate = percent(reports_verified, len(reports))
    leadership_status = _leadership_status(
        assigned_pastors_count=assigned_pastors_count,
        meetings_conducted=meetings_conducted,
        verification_rate=verification_rate,
        reports_count=len(reports),
    )

    return {
        "id": assembly.id,
        "name": assembly.name,
        "zone": assembly.zone.name if assembly.zone else None,
        "country": country,
        "assigned_pastors_count": assigned_pastors_count,
        "assigned_pastors": assigned_pastors,
        "leaders_count": leaders_count,
        "meetings_conducted": meetings_conducted,
        "reports_verified": reports_verified,
        "unverified_reports": unverified_reports,
        "verification_rate": verification_rate,
        "assets_valuation": _assets_valuation(assembly),
        "leadership_status": leadership_status,
    }


def _summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    reports_verified = sum(row["reports_verified"] for row in rows)
    unverified_reports = sum(row["unverified_reports"] for row in rows)
    total_reports = reports_verified + unverified_reports

    return {
        "assemblies": len(rows),
        "assigned_pastors_count": sum(row["assigned_pastors_count"] for row in rows),
        "leaders_count": sum(row["leaders_count"] for row in rows),
        "meetings_conducted": sum(row["meetings_conducted"] for row in rows),
        "reports_verified": reports_verified,
        "unverified_reports": unverified_reports,
        "verification_rate": percent(reports_verified, total_reports),
        "assets_valuation": round(sum(row["assets_valuation"] for row in rows), 2),
        "assemblies_without_pastors": sum(
            1 for row in rows if row["assigned_pastors_count"] == 0
        ),
        "assemblies_needing_attention": sum(
            1 for row in rows
            if row["leadership_status"] in {"NEEDS_ATTENTION", "NO_ASSIGNED_PASTOR"}
        ),
    }


def build_region_leadership_module(
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
                build_assembly_leadership_row(
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
        "table_schema": get_leadership_table_schema(),
    }
