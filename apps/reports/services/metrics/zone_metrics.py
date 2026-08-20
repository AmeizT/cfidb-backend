def get_zone_finance(zone_reports):
    return {
        "tithes": sum(r.tithe_total for r in zone_reports),
        "income": sum(r.income_total for r in zone_reports),
        "expenditure": sum(r.expense_total for r in zone_reports),
        "balance": sum(r.balance for r in zone_reports),
    }


def get_zone_compliance(zone_reports):
    total = len(zone_reports)

    compliant = sum(
        1
        for r in zone_reports
        if r.get_compliance()["status"] == "COMPLIANT"
    )

    return {
        "assemblies": total,
        "compliant_assemblies": compliant,
        "compliance_rate": round(
            compliant / total * 100,
            2
        ) if total else 0,
    }


from apps.reports.services.aggregation.zone import (
    group_reports_by,
    aggregate_finance,
    aggregate_growth,
    aggregate_ministry,
    aggregate_compliance,
)
from apps.reports.models import AssemblyReport

def serialize_zone_assemblies(grouped):
    return [
        {
            "assembly_id": assembly_id,
            "reports": [
                {
                    "id": r.id,
                    "period_start": r.period_start,
                    "period_end": r.period_end,
                    "status": r.status,
                    "income": float(r.income_total),
                    "expenditure": float(r.expense_total),
                    "balance": float(r.balance),
                }
                for r in items
            ]
        }
        for assembly_id, items in grouped.items()
    ]

def get_zone_reports(zone, year, month=None):
    qs = AssemblyReport.objects.filter(
        assembly__zone=zone,
        period_start__year=year
    ).select_related("assembly")

    if month:
        qs = qs.filter(period_start__month=month)

    return qs


def get_zone_metrics(zone, year, month=None):
    reports = list(get_zone_reports(zone, year, month))
    grouped = group_reports_by(reports, lambda r: r.assembly_id)

    return {
        "zone": {
            "id": zone.id,
            "name": zone.name,
        },

        "summary": {
            "assemblies": len({r.assembly_id for r in reports}), # type: ignore
            "reports": len(reports),
        },

        "compliance": aggregate_compliance(reports),
        "finance": aggregate_finance(reports),
        "growth": aggregate_growth(reports),
        "ministry": aggregate_ministry(reports),

        "assemblies": serialize_zone_assemblies(grouped)
    }