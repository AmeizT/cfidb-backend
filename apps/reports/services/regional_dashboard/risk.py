from __future__ import annotations

from collections import Counter
from typing import Any

from apps.reports.models import AssemblyReport
from apps.reports.services.regional_dashboard.compliance import build_assembly_compliance_row
from apps.reports.services.regional_dashboard.finance import build_assembly_finance_row
from apps.reports.services.regional_dashboard.growth import build_assembly_growth_row
from apps.reports.services.regional_dashboard.leadership import build_assembly_leadership_row
from apps.reports.services.regional_dashboard.ministry import build_assembly_ministry_row
from apps.reports.services.regional_dashboard.schemas import get_risk_table_schema
from apps.reports.services.regional_dashboard.utils import (
    AssembliesWithReports,
    group_by_country,
    items_for_zone,
    normalize_period,
    risk_level,
    top_counter,
)


def _recommended_action(score: int, drivers: list[str]) -> str:
    if score >= 75:
        return "Escalate to overseer"
    if any("missed reports" in driver for driver in drivers):
        return "Request missing reports"
    if score >= 50:
        return "Schedule support visit"
    if score >= 25:
        return "Contact assembly leadership"
    return "Monitor"


def _risk_parts(
    *,
    compliance: dict[str, Any],
    finance: dict[str, Any],
    growth: dict[str, Any],
    ministry: dict[str, Any],
    leadership: dict[str, Any],
) -> tuple[dict[str, int], list[str]]:
    drivers: list[str] = []

    reporting_risk = min(
        compliance["missing_reports"] * 6 +
        compliance["incomplete_reports"] * 4 +
        compliance["late_reports"] * 3,
        25,
    )
    if compliance["missing_reports"]:
        drivers.append(f"{compliance['missing_reports']} missed reports")
    if compliance["late_reports"]:
        drivers.append(f"{compliance['late_reports']} late submissions")

    finance_risk = 0
    if finance["total_revenue"] <= 0:
        finance_risk = 12
        drivers.append("No finance data")
    elif finance["balance"] < 0:
        finance_risk = 20
        drivers.append("Negative balance")
    elif finance["financial_health"] in {"STRAINED", "CRITICAL"}:
        finance_risk = 14
        drivers.append(f"{finance['financial_health'].title()} financial health")

    growth_risk = 0
    if growth["growth_status"] == "NO_DATA":
        growth_risk = 8
        drivers.append("No growth data")
    elif growth["growth_status"] == "DECLINING":
        growth_risk = 15
        drivers.append("Declining membership")
    elif growth["new_members"] == 0 and not growth["is_newly_planted"]:
        growth_risk = 8
        drivers.append("No new members")

    ministry_risk = 0
    if ministry["ministry_status"] in {"NO_DATA", "INACTIVE"}:
        ministry_risk = 15
        drivers.append("No outreach activity")
    elif ministry["ministry_status"] == "LOW_ACTIVITY":
        ministry_risk = 8
        drivers.append("Low ministry activity")

    leadership_risk = 0
    if leadership["assigned_pastors_count"] == 0:
        leadership_risk = 15
        drivers.append("No assigned pastor")
    elif leadership["leadership_status"] == "NEEDS_ATTENTION":
        leadership_risk = 8
        drivers.append("Leadership follow-up needed")

    compliance_risk = min(max(0, 100 - compliance["completion_rate"]) * 0.10, 10)
    if compliance["has_skipped_sections"]:
        drivers.append("Skipped report sections")

    return {
        "reporting_risk": int(round(reporting_risk)),
        "finance_risk": int(round(finance_risk)),
        "growth_risk": int(round(growth_risk)),
        "ministry_risk": int(round(ministry_risk)),
        "leadership_risk": int(round(leadership_risk)),
        "compliance_risk": int(round(compliance_risk)),
    }, drivers


def build_assembly_risk_row(
    assembly,
    reports: list[AssemblyReport],
    *,
    country: str,
    currency: str,
    year: int,
) -> dict[str, Any]:
    compliance = build_assembly_compliance_row(
        assembly,
        reports,
        country=country,
        year=year,
    )
    finance = build_assembly_finance_row(
        assembly,
        reports,
        country=country,
        currency=currency,
    )
    growth = build_assembly_growth_row(
        assembly,
        reports,
        country=country,
    )
    ministry = build_assembly_ministry_row(
        assembly,
        reports,
        country=country,
        year=year,
    )
    leadership = build_assembly_leadership_row(
        assembly,
        reports,
        country=country,
        year=year,
    )
    parts, drivers = _risk_parts(
        compliance=compliance,
        finance=finance,
        growth=growth,
        ministry=ministry,
        leadership=leadership,
    )
    score = min(sum(parts.values()), 100)
    level = risk_level(score)

    return {
        "id": assembly.id,
        "name": assembly.name,
        "zone": assembly.zone.name if assembly.zone else None,
        "country": country,
        "risk_score": score,
        "risk_level": level,
        "risk_status": "AT_RISK" if level in {"HIGH", "CRITICAL"} else "STABLE",
        **parts,
        "drivers": drivers,
        "recommended_action": _recommended_action(score, drivers),
    }


def _summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    driver_counter: Counter = Counter()
    for row in rows:
        driver_counter.update(row["drivers"])

    highest = max(rows, key=lambda row: row["risk_score"], default=None)

    return {
        "assemblies": len(rows),
        "low_risk": sum(1 for row in rows if row["risk_level"] == "LOW"),
        "medium_risk": sum(1 for row in rows if row["risk_level"] == "MEDIUM"),
        "high_risk": sum(1 for row in rows if row["risk_level"] == "HIGH"),
        "critical_risk": sum(1 for row in rows if row["risk_level"] == "CRITICAL"),
        "average_risk_score": (
            round(sum(row["risk_score"] for row in rows) / len(rows), 2)
            if rows else 0.0
        ),
        "highest_risk_assembly": {
            "id": highest["id"],
            "name": highest["name"],
            "risk_score": highest["risk_score"],
            "risk_level": highest["risk_level"],
        } if highest else None,
        "top_risk_drivers": top_counter(driver_counter),
    }


def build_region_risk_module(
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
                build_assembly_risk_row(
                    assembly,
                    reports,
                    country=country_name,
                    currency=currency,
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
        "table_schema": get_risk_table_schema(),
    }
