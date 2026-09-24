from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
import re

from django.db.models import Count, F, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.bookkeeper.models import Asset, RemittanceObligation, RemittancePayment, Tithe
from apps.churches.models import Forecast
from apps.people.models import Attendance, SundaySchoolAttendance, Household, AssemblyMembership
from apps.people.models.assembly_membership import MembershipEndReason
from apps.people.models.spaces import Homecell
from apps.people.choices.services import AttendanceCategories
from apps.people.constants import SUNDAY_SCHOOL_START_DATE
from apps.people.services.attendance_totals import attendance_headcount
from apps.reports.models import AssemblyReport
from apps.reports.services.periods import report_period
from apps.reports.services.quarter_engine import calculate_percentage_change


LIMITATIONS = [
    "Leaders ordained: no dated ordination register is available.",
    "Members targets: Forecast stores new-member targets, not total-member targets.",
    "Homecells and households are current registers, not historical month-end snapshots.",
    "Asset disposals and pending approvals: no dated disposal workflow is available.",
    "Financial values use stored report totals, including draft reports; missing months are not zero-filled.",
]


def parse_period(raw=None):
    raw = raw or timezone.localdate().strftime("%Y-%m")
    if not re.fullmatch(r"\d{4}-\d{2}", raw):
        raise ValidationError({"period": "Use YYYY-MM."})
    try:
        value = date.fromisoformat(raw + "-01")
        if value.year < 2:
            raise ValueError("Previous month is outside supported dates")
        return report_period(value)
    except ValueError:
        raise ValidationError({"period": "Use a valid YYYY-MM month."})


def nullable_sum(values):
    values = list(values)
    return sum(values) if values and all(v is not None for v in values) else None


def growth(previous, current):
    change = current - previous if previous is not None and current is not None else None
    ratio = calculate_percentage_change(current, previous) if change is not None else None
    return {"previous": previous, "current": current, "net": change,
            "percent": round(ratio * 100, 2) if ratio is not None else None}


def contributors(assembly_ids, start, end):
    # FinancialBase's active manager excludes trashed entries. Null members are
    # anonymous payments, not identifiable contributors, and are reported separately.
    qs = Tithe.objects.filter(assembly_id__in=assembly_ids, timestamp__range=(start, end))
    rows = qs.filter(member__isnull=False).values(
        "assembly_id", "member_id", "member__first_name", "member__last_name"
    ).annotate(amount=Sum("amount")).order_by("-amount", "member_id")
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["assembly_id"]].append({
            "id": row["member_id"],
            "name": " ".join(filter(None, [row["member__first_name"], row["member__last_name"]])) or "Unnamed member",
            "amount": row["amount"],
        })
    return grouped


def _counts(queryset, field="assembly_id"):
    return {r[field]: r["n"] for r in queryset.values(field).annotate(n=Count("pk"))}


def _attendance(ids, start, end):
    values = defaultdict(lambda: {"general": None, "school": None, "cells": None})
    rows = Attendance.objects.filter(assembly_id__in=ids, timestamp__range=(start, end))
    for row in rows:
        key = {AttendanceCategories.SUNDAY: "general", AttendanceCategories.HOMECELL: "cells"}.get(row.service_type)
        if key and not row.is_special_event:
            values[row.assembly_id][key] = (values[row.assembly_id][key] or 0) + attendance_headcount(row)
    school = SundaySchoolAttendance.objects.filter(
        assembly_id__in=ids, service_date__range=(max(start, SUNDAY_SCHOOL_START_DATE), end)
    ).values("assembly_id").annotate(total=Sum(F("boys") + F("girls")))
    for row in school:
        values[row["assembly_id"]]["school"] = row["total"]
    return values


def _remittances(ids, start, end):
    # Sum payments before joining obligations to avoid multiplying amount_due.
    paid = dict(RemittancePayment.objects.filter(
        obligation__assembly_id__in=ids, obligation__period_start__range=(start, end),
        status=RemittancePayment.Status.VERIFIED, payment_date__lte=end,
    ).values("obligation_id").annotate(total=Sum("amount_paid")).values_list("obligation_id", "total"))
    result = defaultdict(lambda: {"due": Decimal(0), "paid": Decimal(0), "outstanding": Decimal(0)})
    for row in RemittanceObligation.objects.filter(assembly_id__in=ids, period_start__range=(start, end)):
        values = result[row.assembly_id]
        amount = paid.get(row.id, Decimal(0))
        values["due"] += row.amount_due
        values["paid"] += amount
        values["outstanding"] += max(row.amount_due - amount, Decimal(0))
    return result


def _period_metrics(assembly, records, start, end, attendance, remittances):
    """The same period formulas serve monthly and YTD assembly summaries."""
    selected = [r for r in records if start <= r.period_start and r.period_end <= end]
    return {
        "report_count": len(selected),
        "expected_reports": end.month - start.month + 1,
        "attendance": {**attendance, "total": nullable_sum(r.attendance_total for r in selected)},
        # Stored income includes tithes, and stored expenses include verified
        # remittance cash payments. Do not recalculate either domain here.
        "finance": {
            "tithes": nullable_sum(r.tithe_total for r in selected),
            "other_revenue": nullable_sum(r.income_total - r.tithe_total for r in selected),
            "expenses": nullable_sum(r.expense_total for r in selected),
            **remittances,
        },
        "plants": [{"id": assembly.id, "name": assembly.name, "date": assembly.established_date}]
            if assembly.established_date and start <= assembly.established_date <= end else [],
    }


def build_assembly_summaries(assemblies, start, end):
    """Canonical monthly assembly summaries plus YTD, loaded in bounded queries.

    Both APIs call this path. Regional code only selects the YTD display fields
    and rolls up these rows; it never queries/calculates domain metrics itself.
    """
    assemblies = list(assemblies.select_related("zone", "zone__region").order_by("name"))
    ids = [a.id for a in assemblies]
    first = date(start.year, 1, 1)
    previous_start, previous_end = report_period(start - timedelta(days=1))
    reports = defaultdict(list)
    for report in AssemblyReport.objects.filter(
        assembly_id__in=ids, period_start__gte=min(first, previous_start), period_end__lte=end
    ).order_by("period_start"):
        reports[report.assembly_id].append(report)
    attendance = _attendance(ids, first, end)
    monthly_attendance = _attendance(ids, start, end) if start != first else attendance
    remittances = _remittances(ids, first, end)
    monthly_remittances = _remittances(ids, start, end) if start != first else remittances
    giving = contributors(ids, start, end)
    previous_giving = contributors(ids, previous_start, previous_end)
    forecasts = {f.assembly_id: f for f in Forecast.objects.filter(
        assembly_id__in=ids, year=start.year, month=start.month, status=Forecast.Status.ACTIVE)}
    homecells = _counts(Homecell.objects.filter(church_id__in=ids, is_archived=False), "church_id")
    households = _counts(Household.objects.filter(assembly_id__in=ids))
    new_households = _counts(Household.objects.filter(assembly_id__in=ids, created_at__date__range=(start, end)))
    added_assets = _counts(Asset.objects.filter(assembly_id__in=ids, acquisition_date__range=(start, end)))
    memberships = AssemblyMembership.objects.filter(assembly_id__in=ids)
    new_members = _counts(memberships.filter(joined_on__range=(start, end), transfer__isnull=True))
    transfers_in = _counts(memberships.filter(joined_on__range=(start, end), transfer__isnull=False))
    transfers_out = _counts(memberships.filter(ended_on__range=(start, end), end_reason=MembershipEndReason.TRANSFERRED))
    removals = _counts(memberships.filter(ended_on__range=(start, end)).exclude(end_reason=MembershipEndReason.TRANSFERRED))
    rows = []
    for assembly in assemblies:
        records = reports[assembly.id]
        current = next((r for r in records if r.period_start == start), None)
        previous = next((r for r in records if r.period_start == previous_start), None)
        forecast = forecasts.get(assembly.id)
        members = growth(previous.members_total if previous else None, current.members_total if current else None)
        contributors_list = giving[assembly.id]
        missing_remittances = {"due": None, "paid": None, "outstanding": None}
        monthly = _period_metrics(assembly, records, start, end, monthly_attendance[assembly.id],
                                  monthly_remittances.get(assembly.id, missing_remittances))
        ytd = _period_metrics(assembly, records, first, end, attendance[assembly.id],
                              remittances.get(assembly.id, missing_remittances))
        targets = []
        for key, achieved, target in [
            ("Tithes", current.tithe_total if current else None, forecast.tithes_collected if forecast else None),
            ("Attendance", current.attendance_total if current else None, forecast.attendance if forecast else None),
            ("Members", members["current"], None),
        ]:
            targets.append({"name": key, "achieved": achieved, "target": target,
                            "percent": round(float(achieved / target) * 100, 2) if target and achieved is not None else None})
        rows.append({
            "id": assembly.id, "name": assembly.name, "currency": assembly.currency or None,
            "zone_id": assembly.zone_id, "zone_name": assembly.zone.name if assembly.zone else "Unassigned zone",
            "region_name": assembly.zone.region.name if assembly.zone and assembly.zone.region else None,
            "report_count": monthly["report_count"], "expected_reports": monthly["expected_reports"],
            "attendance": monthly["attendance"],
            "ytd": ytd,
            "monthly_attendance": monthly_attendance[assembly.id],
            "finance": monthly["finance"], "membership": {**members, "new": new_members.get(assembly.id, 0),
                "transfers_in": transfers_in.get(assembly.id, 0), "transfers_out": transfers_out.get(assembly.id, 0),
                "removals": removals.get(assembly.id, 0), "households": households.get(assembly.id, 0),
                "new_households": new_households.get(assembly.id, 0)},
            "outreach": {"plants": monthly["plants"],
                "homecells": homecells.get(assembly.id, 0), "ordained": None},
            "targets": targets,
            "giving": {"count": len(contributors_list), "previous_count": len(previous_giving[assembly.id]),
                       "top": contributors_list[:5]},
            "assets": {"added": added_assets.get(assembly.id, 0), "disposals": None, "pending": None},
        })
    return rows


def build_summary(assemblies, start, end, *, regional=False, name="", regions=None):
    monthly_rows = build_assembly_summaries(assemblies, start, end)
    rows = monthly_rows
    if regional:
        rows = [{**row,
                 "monthly": {key: row[key] for key in ("attendance", "finance", "outreach", "report_count", "expected_reports")},
                 **{key: row["ytd"][key] for key in ("attendance", "finance", "report_count", "expected_reports")},
                 "outreach": {**row["outreach"], "plants": row["ytd"]["plants"]}}
                for row in monthly_rows]
    first = date(start.year, 1, 1) if regional else start
    zones = {}
    for row in rows:
        zone = zones.setdefault(row["zone_id"], {"id": row["zone_id"], "name": row["zone_name"],
            "region_name": row["region_name"], "assemblies": []})
        zone["assemblies"].append(row)
    for zone in zones.values():
        zone["summary"] = combine(zone["assemblies"])
    return {"period": start.strftime("%Y-%m"), "start": first, "end": end,
            "regional": regional, "name": name, "regions": regions or [],
            "summary": combine(rows), "monthly_summary": combine(monthly_rows),
            "assemblies": rows, "zones": list(zones.values()),
            "limitations": LIMITATIONS}


def available_sum(values):
    """Sum observations, not missing values. All-missing is still unknown."""
    known = [value for value in values if value is not None]
    return sum(known) if known else None


FINANCE_KEYS = ("tithes", "other_revenue", "expenses", "due", "paid", "outstanding")


def combine(rows):
    coverage = {}

    def sums(section, keys, source=None):
        source = rows if source is None else source
        result = {}
        for key in keys:
            values = [row[section][key] for row in source]
            result[key] = available_sum(values)
            coverage[f"{section}.{key}"] = {"available": sum(v is not None for v in values), "total": len(source)}
        return result

    currencies = {row["currency"] for row in rows}
    same_currency = len(currencies) == 1 and None not in currencies
    currency_rows = defaultdict(list)
    for row in rows:
        # Unknown currencies cannot safely be combined with one another either.
        currency_rows[(row["currency"], None if row["currency"] else row["id"])].append(row)
    finance_by_currency = []
    for (currency, assembly_id), group in currency_rows.items():
        finance_by_currency.append({
            "currency": currency, "assembly_id": assembly_id,
            "assembly_name": group[0]["name"] if assembly_id else None,
            "finance": {key: available_sum(r["finance"][key] for r in group) for key in FINANCE_KEYS},
            "coverage": {key: {"available": sum(r["finance"][key] is not None for r in group), "total": len(group)} for key in FINANCE_KEYS},
        })
    targets = []
    for index, label in enumerate(("Tithes", "Attendance", "Members")):
        # Targets require full coverage: do not compare a subset's target with
        # another set of assemblies' achieved values.
        target = nullable_sum(r["targets"][index]["target"] for r in rows)
        achieved = available_sum(r["targets"][index]["achieved"] for r in rows)
        complete_achieved = all(r["targets"][index]["achieved"] is not None for r in rows)
        if index == 0 and not same_currency:
            target = achieved = None
        targets.append({"name": label, "target": target, "achieved": achieved,
            "percent": round(float(achieved / target) * 100, 2) if target and achieved is not None and complete_achieved else None})
    membership = sums("membership", ("previous", "current", "new", "transfers_in", "transfers_out", "removals", "households", "new_households"))
    comparable = [r for r in rows if r["membership"]["previous"] is not None and r["membership"]["current"] is not None]
    comparison = growth(available_sum(r["membership"]["previous"] for r in comparable),
                        available_sum(r["membership"]["current"] for r in comparable))
    membership.update({"net": comparison["net"], "percent": comparison["percent"],
                       "comparable_assemblies": len(comparable)})
    result = {
        "assembly_count": len(rows), "currency": next(iter(currencies)) if same_currency else None,
        "mixed_currencies": len(currencies) > 1,
        "report_count": sum(r["report_count"] for r in rows),
        "expected_reports": sum(r["expected_reports"] for r in rows),
        "attendance": sums("attendance", ("total", "general", "school", "cells")),
        "finance": sums("finance", FINANCE_KEYS) if same_currency else dict.fromkeys(FINANCE_KEYS),
        "finance_by_currency": finance_by_currency,
        "membership": membership,
        "outreach": {"plants": [p for r in rows for p in r["outreach"]["plants"]],
                     **sums("outreach", ("homecells", "ordained"))},
        # Assembly-month identified giver counts, not unique people across churches.
        "giving": sums("giving", ("count", "previous_count")),
        "targets": targets,
        "coverage": coverage,
    }
    return result
