from __future__ import annotations

import calendar
from collections import Counter, defaultdict
from datetime import date
from typing import Iterable

from apps.churches.models import Church
from apps.reports.models import AssemblyReport


AssembliesWithReports = list[tuple[Church, list[AssemblyReport]]]


def normalize_period(period: str | None) -> str:
    if period == "monthly":
        return "monthly"
    return "ytd"


def month_name(month: int) -> str:
    return calendar.month_name[month]


def period_key(year: int, month: int) -> str:
    return f"{year}-{month:02d}"


def percent(numerator: float, denominator: float) -> float:
    return round((numerator / denominator) * 100, 2) if denominator else 0.0


def years_between(start: date | None, end: date) -> int | None:
    if start is None:
        return None

    years = end.year - start.year
    if (end.month, end.day) < (start.month, start.day):
        years -= 1
    return years


def risk_level(score: int | float) -> str:
    if score <= 24:
        return "LOW"
    if score <= 49:
        return "MEDIUM"
    if score <= 74:
        return "HIGH"
    return "CRITICAL"


def group_by_country(
    assemblies_with_reports: Iterable[tuple[Church, list[AssemblyReport]]],
) -> dict[tuple[str, str], list[tuple[Church, list[AssemblyReport]]]]:
    grouped: dict[tuple[str, str], list[tuple[Church, list[AssemblyReport]]]] = defaultdict(list)

    for assembly, reports in assemblies_with_reports:
        country = (assembly.country or "Unknown").strip()
        currency = assembly.currency or "ZAR"
        grouped[(country, currency)].append((assembly, reports))

    return grouped


def items_for_zone(
    zone,
    assemblies_with_reports: AssembliesWithReports,
) -> list[tuple[Church, list[AssemblyReport]]]:
    zone_assembly_ids = set(zone.assemblies.values_list("id", flat=True))

    return [
        (assembly, reports)
        for assembly, reports in assemblies_with_reports
        if assembly.id in zone_assembly_ids
    ]


def latest_report(reports: list[AssemblyReport]) -> AssemblyReport | None:
    return max(reports, key=lambda report: report.period_start, default=None)


def earliest_report(reports: list[AssemblyReport]) -> AssemblyReport | None:
    return min(reports, key=lambda report: report.period_start, default=None)


def sum_row_values(rows: list[dict], key: str) -> float:
    return sum(float(row.get(key) or 0) for row in rows)


def count_rows(rows: list[dict], key: str, value) -> int:
    return sum(1 for row in rows if row.get(key) == value)


def top_counter(counter: Counter, limit: int = 5) -> list[dict]:
    return [
        {"driver": key, "count": count}
        for key, count in counter.most_common(limit)
    ]


def user_display_name(user) -> str:
    get_full_name = getattr(user, "get_full_name", None)
    if callable(get_full_name):
        name = get_full_name()
        if name:
            return name

    return getattr(user, "email", None) or str(user)
