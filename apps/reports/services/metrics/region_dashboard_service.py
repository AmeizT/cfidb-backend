from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from typing import Any

from django.db.models import Count # type: ignore

from apps.churches.models import Church, Outreach
from apps.people.models.spaces import Homecell
from apps.reports.models import AssemblyReport
from apps.reports.models.section_status import ReportSectionStatus
from apps.reports.services.compliance_calculator import (
    ReportStatus,
    build_compliance_from_reports,
)
from apps.reports.services.metrics.finance_metrics import get_finance_status
from apps.reports.services.metrics.risk_engine import calculate_risk, get_risk_level


DASHBOARD_DOMAINS = {
    "finance",
    "growth",
    "ministry",
    "leadership",
    "compliance",
    "risk",
}
_TOP_LEVEL_DOMAINS = {"compliance", "risk"}


def _build_ministry_metrics(
    reported_outreaches: int,
    actual_outreaches: int,
    homecells_planted: int,
    homecell_attendance: int,
    *,
    has_reports: bool,
) -> dict[str, Any]:
    ministry_score = (
        min(actual_outreaches / 5, 1) * 40 +
        min(homecells_planted / 3, 1) * 40 +
        min(homecell_attendance / 100, 1) * 20
    )

    if not has_reports and ministry_score == 0:
        ministry_status = "NO_DATA"
    else:
        ministry_status = (
            "HIGH" if ministry_score >= 70 else
            "MODERATE" if ministry_score >= 40 else
            "LOW"
        )

    return {
        "outreaches": reported_outreaches,
        "actual_outreaches": actual_outreaches,
        "homecells_planted": homecells_planted,
        "homecell_attendance": homecell_attendance,
        "status": ministry_status,
    }


def _get_actual_outreach_counts(region, year: int) -> dict[int, int]:
    return {
        row["assembly_id"]: row["total"]
        for row in (
            Outreach.objects
            .filter(
                assembly__zone__region=region,
                outreach_date__year=year,
                status=Outreach.Status.COMPLETED,
            )
            .values("assembly_id")
            .annotate(total=Count("id"))
        )
    }


def _empty_monthly_compliance(assembly: Church, year: int) -> dict[str, Any]:
    return build_compliance_from_reports(assembly, [], year)


def _compliance_status(
    *,
    total_sections: int,
    submitted: int,
    skipped: int,
    pending: int,
    report_status_counts: dict[str, int] | None = None,
) -> str:
    if total_sections == 0:
        return "NO_DATA"

    if report_status_counts:
        expected_reports = sum(report_status_counts.values())
        if (
            expected_reports > 0 and
            report_status_counts.get(ReportStatus.NOT_SUBMITTED, 0) == expected_reports
        ):
            return "NOT_SUBMITTED"

    if pending == 0 and skipped > 0:
        return "COMPLIANT_WITH_EXCEPTIONS"

    if pending == 0:
        return "COMPLIANT"

    return "INCOMPLETE"


def _build_compliance_metrics(
    assembly: Church,
    reports: list[AssemblyReport],
    year: int,
) -> dict[str, Any]:
    monthly = (
        build_compliance_from_reports(assembly, reports, year)
        if reports else
        _empty_monthly_compliance(assembly, year)
    )
    summary = monthly["summary"]

    total_sections = int(summary["total_fields"])
    submitted_sections = int(summary["submitted"])
    skipped_sections = int(summary["skipped"])
    pending_sections = int(summary["pending"])
    progress = (
        round((submitted_sections / total_sections) * 100, 2)
        if total_sections else 0.0
    )
    coverage = (
        round(((submitted_sections + skipped_sections) / total_sections) * 100, 2)
        if total_sections else 0.0
    )

    sections = []
    for report in reports:
        for section in report.sections.all(): # type: ignore
            section_payload = {
                "report_id": report.id, # type: ignore
                "period": report.period_start.isoformat(),
                "name": section.section,
                "status": section.status,
                "reason": section.skip_reason if section.status == "skipped" else None,
                "notes": section.skip_notes,
                "follow_up_status": getattr(section, "follow_up_status", None),
                "follow_up_notes": getattr(section, "follow_up_notes", None),
            }
            sections.append(section_payload)

    return {
        "total_sections": total_sections,
        "submitted": submitted_sections,
        "skipped": skipped_sections,
        "pending": pending_sections,
        "progress": progress,
        "coverage": coverage,
        "status": _compliance_status(
            total_sections=total_sections,
            submitted=submitted_sections,
            skipped=skipped_sections,
            pending=pending_sections,
            report_status_counts=summary["report_status_counts"],
        ),
        "sections": sections,
        "months": monthly["months"],
        "tracked_sections": monthly["tracked_sections"],
        "summary": summary,
    }


def _church_is_newly_planted(assembly: Church, year: int) -> bool:
    established_date = getattr(assembly, "established_date", None)
    return bool(established_date and established_date.year == year)


def _build_church_planting_metrics(
    assemblies: list[Church],
    year: int,
) -> dict[str, Any]:
    planted = [
        assembly
        for assembly in assemblies
        if _church_is_newly_planted(assembly, year)
    ]
    by_country: dict[str, int] = defaultdict(int)
    by_zone: dict[str, int] = defaultdict(int)

    for assembly in planted:
        by_country[assembly.country or "Unknown"] += 1
        zone_name = assembly.zone.name if assembly.zone else "Unassigned"
        by_zone[zone_name] += 1

    active_count = sum(1 for assembly in assemblies if assembly.status == "open")
    closed_count = sum(1 for assembly in assemblies if assembly.status == "closed")

    return {
        "year": year,
        "newly_planted_count": len(planted),
        "active_assemblies": active_count,
        "closed_assemblies": closed_count,
        "by_country": dict(by_country),
        "by_zone": dict(by_zone),
        "assemblies": [
            {
                "id": assembly.id, # type: ignore
                "name": assembly.name,
                "country": assembly.country,
                "zone": assembly.zone.name if assembly.zone else None,
                "established_date": assembly.established_date.isoformat()
                if assembly.established_date else None,
                "status": assembly.status,
            }
            for assembly in planted
        ],
    }


def _rollup_compliance_metrics(
    assemblies_metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    total_sections = 0
    submitted = 0
    skipped = 0
    pending = 0
    late_submissions = 0
    on_time_submissions = 0
    unresolved_follow_ups = 0
    report_status_counts: Counter[str] = Counter()
    workflow_status_counts: Counter[str] = Counter()
    missing_by_section: Counter[str] = Counter()
    skipped_by_section: Counter[str] = Counter()
    pending_by_section: Counter[str] = Counter()

    for assembly_metrics in assemblies_metrics:
        compliance = assembly_metrics["compliance"]
        summary = compliance.get("summary", {})
        total_sections += int(compliance.get("total_sections", 0))
        submitted += int(compliance.get("submitted", 0))
        skipped += int(compliance.get("skipped", 0))
        pending += int(compliance.get("pending", 0))
        late_submissions += int(summary.get("late_submissions", 0))
        on_time_submissions += int(summary.get("on_time_submissions", 0))
        unresolved_follow_ups += int(summary.get("unresolved_follow_ups", 0))
        report_status_counts.update(summary.get("report_status_counts", {}))
        workflow_status_counts.update(summary.get("workflow_status_counts", {}))
        missing_by_section.update(summary.get("missing_by_section", {}))
        skipped_by_section.update(summary.get("skipped_by_section", {}))
        pending_by_section.update(summary.get("pending_by_section", {}))

    progress = round((submitted / total_sections) * 100, 2) if total_sections else 0.0
    coverage = (
        round(((submitted + skipped) / total_sections) * 100, 2)
        if total_sections else 0.0
    )
    submitted_reports = (
        sum(report_status_counts.values()) -
        report_status_counts.get(ReportStatus.NOT_SUBMITTED, 0)
    )
    timed_reports = late_submissions + on_time_submissions

    return {
        "total_sections": total_sections,
        "submitted": submitted,
        "skipped": skipped,
        "pending": pending,
        "progress": progress,
        "coverage": coverage,
        "status": _compliance_status(
            total_sections=total_sections,
            submitted=submitted,
            skipped=skipped,
            pending=pending,
            report_status_counts=dict(report_status_counts),
        ),
        "summary": {
            "expected_reports": sum(report_status_counts.values()),
            "submitted_reports": submitted_reports,
            "missing_reports": report_status_counts.get(ReportStatus.NOT_SUBMITTED, 0),
            "late_submissions": late_submissions,
            "on_time_submissions": on_time_submissions,
            "late_rate": (
                round((late_submissions / timed_reports) * 100, 2)
                if timed_reports else 0.0
            ),
            "unresolved_follow_ups": unresolved_follow_ups,
            "report_status_counts": dict(report_status_counts),
            "workflow_status_counts": dict(workflow_status_counts),
            "missing_by_section": dict(missing_by_section),
            "skipped_by_section": dict(skipped_by_section),
            "pending_by_section": dict(pending_by_section),
        },
    }


def _rollup_risk_metrics(
    assemblies_metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    scores = [item["risk"]["score"] for item in assemblies_metrics]
    average_score = round(sum(scores) / len(scores), 2) if scores else 0.0
    distribution = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}

    high_risk_assemblies = []
    for item in assemblies_metrics:
        level = item["risk"]["level"]
        distribution[level] = distribution.get(level, 0) + 1

        if level in {"HIGH", "CRITICAL"}:
            high_risk_assemblies.append({
                "id": item["id"],
                "name": item["name"],
                "score": item["risk"]["score"],
                "level": level,
            })

    return {
        "score": average_score,
        "level": get_risk_level(int(round(average_score))),
        "distribution": distribution,
        "high_risk_assemblies": high_risk_assemblies,
    }


def _extract_domain_metrics(assembly_metrics: dict[str, Any], domain: str) -> dict[str, Any]:
    if domain in _TOP_LEVEL_DOMAINS:
        return assembly_metrics[domain]
    return assembly_metrics["metrics"][domain]


# -----------------------------
# 1. ASSEMBLY LEVEL METRICS
# -----------------------------

def build_assembly_metrics(
    assembly: Church,
    reports: list[AssemblyReport],
    *,
    actual_outreaches: int = 0,
    year: int | None = None,
) -> dict[str, Any]:
    if year is None:
        year = next((report.period_start.year for report in reports), date.today().year)

    compliance = _build_compliance_metrics(assembly, reports, year)

    tithes = 0
    income = 0
    expenditure = 0
    total_members = 0
    total_new_members = 0
    total_outreaches = 0
    total_homecells_planted = 0
    total_homecell_attendance = 0

    for report in reports:
        tithes += report.tithe_total or 0
        income += report.income_total or 0
        expenditure += report.expense_total or 0
        total_members += report.members_total or 0
        total_new_members += report.total_new_converts or 0
        total_outreaches += getattr(report, "total_outreaches", 0) or 0
        total_homecells_planted += getattr(report, "total_homecells_planted", 0) or 0
        total_homecell_attendance += getattr(report, "total_homecell_attendance", 0) or 0

    balance = income - expenditure
    finance = {
        "tithes": float(tithes),
        "income": float(income),
        "total_revenue": float(income),
        "expenditure": float(expenditure),
        "remittance": 0.0,
        "balance": float(balance),
        "status": get_finance_status(balance, income) if reports else "NO_DATA",
    }

    growth_rate = (
        (total_new_members / total_members) * 100
        if total_members > 0 else 0
    )
    if not reports:
        growth_status = "NO_DATA"
    elif total_new_members == 0:
        growth_status = "STAGNANT"
    elif growth_rate <= 3:
        growth_status = "SLOW"
    else:
        growth_status = "GROWING"

    growth = {
        "total_members": total_members,
        "new_members": total_new_members,
        "growth_rate": round(growth_rate, 2),
        "status": growth_status,
        "is_newly_planted": _church_is_newly_planted(assembly, year),
        "established_date": assembly.established_date.isoformat()
        if assembly.established_date else None,
    }
    ministry = _build_ministry_metrics(
        reported_outreaches=total_outreaches,
        actual_outreaches=actual_outreaches,
        homecells_planted=total_homecells_planted,
        homecell_attendance=total_homecell_attendance,
        has_reports=bool(reports),
    )
    leadership = {
        "leaders_count": 0,
        "assets_valuation": 0,
        "meetings_conducted": 0,
        "status": "NO_DATA" if not reports else "UNTRACKED",
    }
    risk = calculate_risk(
        compliance=compliance,
        finance=finance,
        growth=growth,
        ministry=ministry,
    )

    return {
        "id": assembly.id, # type: ignore
        "name": assembly.name,
        "compliance": compliance,
        "risk": risk,
        "metrics": {
            "finance": finance,
            "growth": growth,
            "ministry": ministry,
            "leadership": leadership,
        },
        "reports": len(reports),
    }


# -----------------------------
# 2. COUNTRY LEVEL METRICS
# -----------------------------

def build_country_metrics(
    assemblies_reports: list[list[AssemblyReport]],
    *,
    actual_outreaches: int = 0,
    assemblies: list[Church] | None = None,
    assemblies_metrics: list[dict[str, Any]] | None = None,
    year: int | None = None,
) -> dict[str, Any]:
    tithes = 0.0
    income = 0.0
    expenditure = 0.0
    reported_outreaches = 0
    homecells_planted = 0
    homecell_attendance = 0
    total_members = 0
    total_new_members = 0
    has_reports = False

    for reports in assemblies_reports:
        for report in reports:
            has_reports = True
            tithes += float(report.tithe_total or 0)
            income += float(report.income_total or 0)
            expenditure += float(report.expense_total or 0)
            reported_outreaches += getattr(report, "total_outreaches", 0) or 0
            homecells_planted += getattr(report, "total_homecells_planted", 0) or 0
            homecell_attendance += getattr(report, "total_homecell_attendance", 0) or 0
            total_members += report.members_total or 0
            total_new_members += report.total_new_converts or 0

    total_revenue = income
    balance = total_revenue - expenditure
    growth_rate = (
        (total_new_members / total_members) * 100
        if total_members else 0.0
    )
    compliance = _rollup_compliance_metrics(assemblies_metrics or [])
    risk = _rollup_risk_metrics(assemblies_metrics or [])

    return {
        "finance": {
            "tithes": tithes,
            "income": income,
            "total_revenue": total_revenue,
            "expenditure": expenditure,
            "remittance": 0.0,
            "balance": balance,
            "status": get_finance_status(balance, income) if has_reports else "NO_DATA",
        },
        "growth": {
            "total_members": total_members,
            "new_members": total_new_members,
            "growth_rate": round(growth_rate, 2),
            "status": "NO_DATA" if not has_reports else (
                "STAGNANT" if total_new_members == 0 else
                "SLOW" if growth_rate <= 3 else
                "GROWING"
            ),
            "church_planting": _build_church_planting_metrics(
                assemblies or [],
                year or date.today().year,
            ),
        },
        "ministry": _build_ministry_metrics(
            reported_outreaches=reported_outreaches,
            actual_outreaches=actual_outreaches,
            homecells_planted=homecells_planted,
            homecell_attendance=homecell_attendance,
            has_reports=has_reports,
        ),
        "leadership": {},
        "compliance": compliance,
        "risk": risk,
    }


# -----------------------------
# 3. GROUP BY COUNTRY
# -----------------------------

def group_by_country(
    assemblies_with_reports: list[tuple[Church, list[AssemblyReport]]]
) -> dict[tuple[str, str], list[tuple[Church, list[AssemblyReport]]]]:
    grouped: dict[tuple[str, str], list] = defaultdict(list)

    for assembly, reports in assemblies_with_reports:
        country = (assembly.country or "Unknown").strip()
        currency = assembly.currency or "ZAR"
        grouped[(country, currency)].append((assembly, reports))

    return grouped


def _build_focus_areas(analytics: dict[str, Any]) -> list[dict[str, Any]]:
    focus_areas: list[dict[str, Any]] = []
    compliance = analytics["compliance"]
    risk = analytics["risk"]
    church_planting = analytics["church_planting"]

    if compliance["coverage"] < 80:
        focus_areas.append({
            "type": "COMPLIANCE",
            "priority": "HIGH",
            "title": "Raise monthly section coverage",
            "metric": compliance["coverage"],
        })

    late_rate = compliance["summary"]["late_rate"]
    if late_rate > 20:
        focus_areas.append({
            "type": "TIMELINESS",
            "priority": "MEDIUM",
            "title": "Reduce late report submissions",
            "metric": late_rate,
        })

    if compliance["summary"]["unresolved_follow_ups"] > 0:
        focus_areas.append({
            "type": "FOLLOW_UP",
            "priority": "HIGH",
            "title": "Resolve skipped-section follow-ups",
            "metric": compliance["summary"]["unresolved_follow_ups"],
        })

    high_risk_count = len(risk["high_risk_assemblies"])
    if high_risk_count:
        focus_areas.append({
            "type": "RISK",
            "priority": "HIGH",
            "title": "Review high-risk assemblies",
            "metric": high_risk_count,
        })

    if church_planting["newly_planted_count"] == 0:
        focus_areas.append({
            "type": "GROWTH",
            "priority": "LOW",
            "title": "Track new church planting pipeline",
            "metric": 0,
        })

    return focus_areas


def _build_region_analytics(
    *,
    assemblies: list[Church],
    assemblies_metrics: list[dict[str, Any]],
    year: int,
) -> dict[str, Any]:
    compliance = _rollup_compliance_metrics(assemblies_metrics)
    risk = _rollup_risk_metrics(assemblies_metrics)
    church_planting = _build_church_planting_metrics(assemblies, year)
    expected_reports = len(assemblies) * 12
    submitted_reports = compliance["summary"]["submitted_reports"]

    analytics = {
        "compliance": {
            **compliance,
            "summary": {
                **compliance["summary"],
                "expected_reports": expected_reports,
                "submission_rate": (
                    round((submitted_reports / expected_reports) * 100, 2)
                    if expected_reports else 0.0
                ),
            },
        },
        "risk": risk,
        "church_planting": church_planting,
        "operations": {
            "assemblies_without_reports": [
                {
                    "id": item["id"],
                    "name": item["name"],
                }
                for item in assemblies_metrics
                if item["reports"] == 0
            ],
            "assemblies_with_unresolved_follow_ups": [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "unresolved_follow_ups": item["compliance"]["summary"].get(
                        "unresolved_follow_ups",
                        0,
                    ),
                }
                for item in assemblies_metrics
                if item["compliance"]["summary"].get("unresolved_follow_ups", 0) > 0
            ],
        },
    }
    analytics["focus_areas"] = _build_focus_areas(analytics)
    return analytics


# -----------------------------
# 4. BUILD REGION DASHBOARD
# -----------------------------

def build_region_dashboard(
    region,
    assemblies_with_reports: list[tuple[Church, list[AssemblyReport]]],
    *,
    year: int | None = None,
) -> dict[str, Any]:
    assembly_lookup: dict[int, tuple[Church, list[AssemblyReport]]] = {
        assembly.id: (assembly, reports) # type: ignore
        for assembly, reports in assemblies_with_reports
    }
    if year is None:
        year = next(
            (
                report.period_start.year
                for _, reports in assemblies_with_reports
                for report in reports
            ),
            date.today().year,
        )

    actual_outreaches_by_assembly = _get_actual_outreach_counts(region, year)
    zones_output = []
    all_assembly_metrics: list[dict[str, Any]] = []

    for zone in region.zones.all():
        zone_assembly_ids: set[int] = set(
            zone.assemblies.values_list("id", flat=True)
        )
        zone_items = [
            assembly_lookup[assembly_id]
            for assembly_id in zone_assembly_ids
            if assembly_id in assembly_lookup
        ]

        if not zone_items:
            zones_output.append({"id": zone.id, "name": zone.name, "countries": []})
            continue

        zone_grouped = group_by_country(zone_items)
        zone_countries = []

        for (country_name, currency), items in zone_grouped.items():
            assemblies_metrics = [
                build_assembly_metrics(
                    assembly,
                    reports,
                    actual_outreaches=actual_outreaches_by_assembly.get(
                        assembly.id, # type: ignore
                        0,
                    ),
                    year=year,
                )
                for assembly, reports in items
            ]
            all_assembly_metrics.extend(assemblies_metrics)

            country_report_lists = [reports for _, reports in items]
            country_actual_outreaches = sum(
                actual_outreaches_by_assembly.get(assembly.id, 0) # type: ignore
                for assembly, _ in items
            )
            country_assemblies = [assembly for assembly, _ in items]

            zone_countries.append({
                "name": country_name,
                "currency": currency,
                "assemblies": assemblies_metrics,
                "region_metrics": build_country_metrics(
                    country_report_lists,
                    actual_outreaches=country_actual_outreaches,
                    assemblies=country_assemblies,
                    assemblies_metrics=assemblies_metrics,
                    year=year,
                ),
            })

        zones_output.append({
            "id": zone.id,
            "name": zone.name,
            "countries": zone_countries,
        })

    all_countries = {
        assembly.country
        for assembly, _ in assemblies_with_reports
        if assembly.country
    }
    total_reports = 0
    assemblies_with_report = 0
    total_members = 0
    total_new_members = 0
    fastest_growing_assembly = None
    fastest_growth_rate = None

    for assembly, reports in assemblies_with_reports:
        if reports:
            assemblies_with_report += 1

        assembly_members = 0
        assembly_new_members = 0

        for report in reports:
            members = report.members_total or 0
            new_members = report.total_new_converts or 0

            total_reports += 1
            total_members += members
            total_new_members += new_members
            assembly_members += members
            assembly_new_members += new_members

        if assembly_members <= 0:
            continue

        assembly_growth_rate = (assembly_new_members / assembly_members) * 100
        if fastest_growth_rate is None or assembly_growth_rate > fastest_growth_rate:
            fastest_growth_rate = assembly_growth_rate
            fastest_growing_assembly = {
                "id": assembly.id, # type: ignore
                "name": assembly.name,
                "growth_rate": round(assembly_growth_rate, 2),
            }

    total_assemblies = len(assemblies_with_reports)
    compliance_rate = (
        round((assemblies_with_report / total_assemblies) * 100, 2)
        if total_assemblies else 0.0
    )
    growth_rate = (
        round((total_new_members / total_members) * 100, 2)
        if total_members else 0.0
    )
    total_active_homecells = Homecell.objects.filter(
        church__zone__region=region,
        is_archived=False,
    ).count()
    total_actual_outreaches = sum(actual_outreaches_by_assembly.values())
    assemblies = [assembly for assembly, _ in assemblies_with_reports]
    analytics = _build_region_analytics(
        assemblies=assemblies,
        assemblies_metrics=all_assembly_metrics,
        year=year,
    )

    return {
        "region": {
            "id": region.id,
            "name": region.name,
        },
        "summary": {
            "zones": len(zones_output),
            "countries": len(all_countries),
            "assemblies": total_assemblies,
            "reports_submitted": total_reports,
            "expected_reports": total_assemblies * 12,
            "report_submission_rate": analytics["compliance"]["summary"]["submission_rate"],
            "compliance_rate": compliance_rate,
            "growth_rate": growth_rate,
            "total_members": total_members,
            "total_new_members": total_new_members,
            "fastest_growing_assembly": fastest_growing_assembly,
            "total_active_homecells": total_active_homecells,
            "total_actual_outreaches": total_actual_outreaches,
            "newly_planted_churches": analytics["church_planting"]["newly_planted_count"],
            "late_submissions": analytics["compliance"]["summary"]["late_submissions"],
            "unresolved_follow_ups": analytics["compliance"]["summary"]["unresolved_follow_ups"],
            "high_risk_assemblies": len(analytics["risk"]["high_risk_assemblies"]),
        },
        "analytics": analytics,
        "zones": zones_output,
    }


def build_region_dashboard_module(
    region,
    assemblies_with_reports: list[tuple[Church, list[AssemblyReport]]],
    domain: str,
    *,
    year: int | None = None,
) -> dict[str, Any]:
    if domain not in DASHBOARD_DOMAINS:
        raise ValueError(f"Unsupported dashboard domain: {domain}")

    dashboard = build_region_dashboard(
        region,
        assemblies_with_reports,
        year=year,
    )

    zones = []
    for zone in dashboard["zones"]:
        countries = []

        for country in zone["countries"]:
            countries.append({
                "name": country["name"],
                "currency": country["currency"],
                "assemblies": [
                    {
                        "id": assembly["id"],
                        "name": assembly["name"],
                        "reports": assembly["reports"],
                        "data": _extract_domain_metrics(assembly, domain),
                    }
                    for assembly in country["assemblies"]
                ],
                "region_metrics": country["region_metrics"].get(domain, {}),
            })

        zones.append({
            "id": zone["id"],
            "name": zone["name"],
            "countries": countries,
        })

    module_analytics = dashboard.get("analytics", {}).get(domain)
    if domain == "growth":
        module_analytics = {
            "church_planting": dashboard.get("analytics", {}).get("church_planting", {}),
        }

    return {
        "region": dashboard["region"],
        "summary": dashboard["summary"],
        "module": domain,
        "analytics": module_analytics or {},
        "zones": zones,
    }


def build_region_compliance_scorecard(
    region,
    assemblies_with_reports: list[tuple[Church, list[AssemblyReport]]],
    *,
    year: int,
) -> dict[str, Any]:
    dashboard = build_region_dashboard(region, assemblies_with_reports, year=year)

    assemblies = []
    for zone in dashboard["zones"]:
        for country in zone["countries"]:
            for assembly in country["assemblies"]:
                assemblies.append({
                    "id": assembly["id"],
                    "name": assembly["name"],
                    "zone": zone["name"],
                    "country": country["name"],
                    "compliance": assembly["compliance"],
                    "risk": assembly["risk"],
                })

    return {
        "region": dashboard["region"],
        "year": year,
        "summary": dashboard["analytics"]["compliance"],
        "assemblies": assemblies,
    }


# -----------------------------
# 5. DATA FETCHERS
# -----------------------------

def get_region_reports(
    region,
    year: int,
) -> list[tuple[Church, list[AssemblyReport]]]:
    assemblies = (
        Church.objects
        .filter(zone__region=region)
        .select_related("zone", "zone__region")
    )

    reports = (
        AssemblyReport.objects
        .filter(
            assembly__zone__region=region,
            period_start__year=year,
        )
        .select_related("assembly", "assembly__zone")
        .prefetch_related("sections")
        .order_by("assembly_id", "period_start")
    )

    reports_by_assembly: dict[int, list[AssemblyReport]] = defaultdict(list)
    for report in reports:
        reports_by_assembly[report.assembly_id].append(report) # type: ignore

    return [
        (assembly, reports_by_assembly.get(assembly.id, [])) # type: ignore
        for assembly in assemblies
    ]


def get_country_reports(
    region,
    country: str,
    year: int,
) -> list[tuple[Church, list[AssemblyReport]]]:
    assemblies = (
        Church.objects
        .filter(
            zone__region=region,
            country__iexact=country,
        )
        .select_related("zone", "zone__region")
    )

    reports = (
        AssemblyReport.objects
        .filter(
            assembly__zone__region=region,
            assembly__country__iexact=country,
            period_start__year=year,
        )
        .select_related("assembly", "assembly__zone")
        .prefetch_related("sections")
        .order_by("assembly_id", "period_start")
    )

    reports_by_assembly: dict[int, list[AssemblyReport]] = defaultdict(list)
    for report in reports:
        reports_by_assembly[report.assembly_id].append(report) # type: ignore

    return [
        (assembly, reports_by_assembly.get(assembly.id, [])) # type: ignore
        for assembly in assemblies
    ]
