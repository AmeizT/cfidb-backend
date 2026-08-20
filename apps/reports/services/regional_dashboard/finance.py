from __future__ import annotations

from typing import Any

from apps.churches.models import Church
from apps.reports.models import AssemblyReport
from apps.reports.services.regional_dashboard.schemas import get_finance_table_schema
from apps.reports.services.regional_dashboard.utils import (
    AssembliesWithReports,
    group_by_country,
    items_for_zone,
    normalize_period,
)


REMITTANCE_RATE = 0.10


def calculate_remittance_owed(tithes: float) -> float:
    return round(tithes * REMITTANCE_RATE, 2)


def get_financial_health(balance: float, total_revenue: float) -> str:
    if total_revenue <= 0:
        return "NO_DATA"

    ratio = balance / total_revenue
    if ratio >= 0.20:
        return "HEALTHY"
    if ratio >= 0:
        return "STABLE"
    if ratio >= -0.20:
        return "STRAINED"
    return "CRITICAL"


def _latest_members(reports: list[AssemblyReport]) -> int | None:
    for report in sorted(reports, key=lambda item: item.period_start, reverse=True):
        if report.members_total:
            return report.members_total
    return None


def _finance_values(
    *,
    tithes: float,
    income_total: float,
    expenditure: float,
    members: int | None = None,
    remittance_paid: float = 0.0,
) -> dict[str, Any]:
    other_revenue = income_total
    total_revenue = tithes + other_revenue
    remittance_owed = calculate_remittance_owed(tithes)
    remittance_balance = remittance_owed - remittance_paid
    balance = total_revenue - expenditure - remittance_paid
    income_concentration = (
        round((tithes / total_revenue) * 100, 2) if total_revenue else 0.0
    )
    avg_tithes_per_member = (
        round(tithes / members, 2) if members else None
    )

    return {
        "tithes": round(tithes, 2),
        "other_revenue": round(other_revenue, 2),
        "total_revenue": round(total_revenue, 2),
        "expenditure": round(expenditure, 2),
        "remittance_owed": remittance_owed,
        "remittance_paid": round(remittance_paid, 2),
        "remittance_balance": round(remittance_balance, 2),
        "balance": round(balance, 2),
        "financial_health": get_financial_health(balance, total_revenue),
        "avg_tithes_per_member": avg_tithes_per_member,
        "income_concentration": income_concentration,
    }


def build_assembly_finance_row(
    assembly: Church,
    reports: list[AssemblyReport],
    *,
    country: str,
    currency: str,
) -> dict[str, Any]:
    tithes = sum(float(report.tithe_total or 0) for report in reports)
    income_total = sum(float(report.income_total or 0) for report in reports)
    expenditure = sum(float(report.expense_total or 0) for report in reports)
    members = _latest_members(reports)

    row = {
        "id": assembly.id, # type: ignore
        "name": assembly.name,
        "zone": assembly.zone.name if assembly.zone else None,
        "country": country,
        "currency": currency,
        **_finance_values(
            tithes=tithes,
            income_total=income_total,
            expenditure=expenditure,
            members=members,
            # No remittance payment model exists yet, so the current module
            # treats paid as zero and keeps owed/balance visible separately.
            remittance_paid=0.0,
        ),
    }

    # Compatibility fields preserved for old table/frontend conventions while
    # the new finance module settles. The current legacy endpoint is unchanged.
    row["assembly"] = assembly.name
    row["income"] = row["total_revenue"]
    row["status"] = row["financial_health"]

    return row


def _summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tithes = sum(row["tithes"] for row in rows)
    other_revenue = sum(row["other_revenue"] for row in rows)
    expenditure = sum(row["expenditure"] for row in rows)
    remittance_paid = sum(row["remittance_paid"] for row in rows)
    members = sum(
        row["tithes"] / row["avg_tithes_per_member"]
        for row in rows
        if row["avg_tithes_per_member"]
    )

    summary = _finance_values(
        tithes=tithes,
        income_total=tithes + other_revenue,
        expenditure=expenditure,
        members=int(members) if members else None,
        remittance_paid=remittance_paid,
    )
    summary["assemblies"] = len(rows)

    # Compatibility fields preserved for consumers that still expect the old
    # finance metric names during the migration window.
    summary["income"] = summary["total_revenue"]
    summary["status"] = summary["financial_health"]

    return summary


def build_region_finance_module(
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
        country_nodes = []

        for (country_name, currency), country_items in group_by_country(zone_items).items():
            rows = [
                build_assembly_finance_row(
                    assembly,
                    reports,
                    country=country_name,
                    currency=currency,
                )
                for assembly, reports in country_items
            ]
            all_rows.extend(rows)
            country_nodes.append({
                "name": country_name,
                "currency": currency,
                "summary": _summarize_rows(rows),
                "assemblies": rows,
            })

        zones_output.append({
            "id": zone.id,
            "name": zone.name,
            "countries": country_nodes,
        })

    return {
        "summary": {
            **_summarize_rows(all_rows),
            "region_id": region.id,
            "region_name": region.name,
            "year": year,
            "period": period_mode,
            # Monthly support will add Jan-Dec buckets here without changing
            # the YTD row shape above.
            "monthly_available": period_mode == "monthly",
        },
        "zones": zones_output,
        "table_schema": get_finance_table_schema(),
    }
