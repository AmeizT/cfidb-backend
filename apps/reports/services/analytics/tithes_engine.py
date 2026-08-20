from calendar import month_name
from django.db.models import Max, Sum
from apps.reports.models.assembly import AssemblyReport
from apps.reports.services.analytics.giver_intelligence_engine import build_giver_intelligence
from apps.reports.services.analytics.kpi_layer import build_kpi_response
from apps.reports.schemas.analytics.tithes_analytics_schema import get_tithes_analytics_schema


def build_tithes_year(assembly, year):
    from apps.reports.services.analytics.year_response import build_year_response

    reports = AssemblyReport.objects.filter(
        assembly=assembly,
        period_start__year=year
    )

    Tithe = reports.first().tithe_set.model if reports.exists() else None # type: ignore
    queryset = Tithe.objects.filter(report__in=reports) if Tithe else None

    months = range(1, 13)
    report_map = {r.period_start.month: r for r in reports}

    statements = []
    prev_total = 0
    prev_givers = 0
    prev_giver_set = set()
    all_previous_givers = set()
    member_month_map = {}

    all_amounts = []

    for m in months:
        report = report_map.get(m)

        qs = queryset.filter(report=report) if report and queryset else queryset.none() if queryset else None

        current_giver_set = set(qs.values_list("member_id", flat=True)) if qs else set()

        total = qs.aggregate(total=Sum("amount"))["total"] if qs else 0
        total = total or 0

        givers = qs.values("member").distinct().count() if qs else 0

        new_givers = len(current_giver_set - all_previous_givers)
        repeat_givers = len(current_giver_set & prev_giver_set)
        lapsed_givers = len(prev_giver_set - current_giver_set)

        all_previous_givers |= current_giver_set
        prev_giver_set = current_giver_set

        highest = qs.aggregate(max=Max("amount"))["max"] if qs else 0

        # Median calculation
        amounts = list(qs.values_list("amount", flat=True)) if qs else []
        amounts = [float(a or 0) for a in amounts]
        all_amounts.extend(amounts)
        amounts.sort()
        n = len(amounts)
        if n == 0:
            median = 0
        elif n % 2 == 1:
            median = amounts[n // 2]
        else:
            median = (amounts[n // 2 - 1] + amounts[n // 2]) / 2

        change = ((total - prev_total) / prev_total) if prev_total else 0
        fluctuation = (givers / prev_givers) if prev_givers else 0

        statements.append({
            "month": m,
            "label": month_name[m],
            "total": total,
            "givers": givers,
            "average": total / givers if givers else 0,
            "median": median,
            "previous_total": prev_total,
            "change": change,
            "givers_fluctuation": fluctuation,
            "highest_amount": highest or 0,
            "new_givers": new_givers,
            "repeat_givers": repeat_givers,
            "lapsed_givers": lapsed_givers,
        })

        prev_total = total
        prev_givers = givers

    ytd_total = sum(s.get("total", 0) for s in statements)
    ytd_givers = sum(s.get("givers", 0) for s in statements)

    # YTD median (across all transactions)
    all_amounts_sorted = sorted(all_amounts)
    n = len(all_amounts_sorted)
    if n == 0:
        ytd_median = 0
    elif n % 2 == 1:
        ytd_median = all_amounts_sorted[n // 2]
    else:
        ytd_median = (all_amounts_sorted[n // 2 - 1] + all_amounts_sorted[n // 2]) / 2

    kpis = {
        "total": ytd_total,
        "givers": ytd_givers,
        "average": (ytd_total / ytd_givers) if ytd_givers else 0,
        "median": ytd_median,
        "previous_total": 0,
        "change": 0,
        "givers_fluctuation": 0,
        "highest_amount": max([s.get("highest_amount", 0) for s in statements] or [0]),
        "new_givers": sum(s.get("new_givers", 0) for s in statements),
        "repeat_givers": sum(s.get("repeat_givers", 0) for s in statements),
        "lapsed_givers": sum(s.get("lapsed_givers", 0) for s in statements),
    }

    # intelligence = build_giver_intelligence(
    #     queryset=queryset or Tithe.objects.none() if Tithe else Tithe.objects.none(),
    #     reports=reports
    # )

    return build_kpi_response(
        year=year,
        statements=statements,
        domain="tithes",
        
        extra_meta={
            # "giver_intelligence": intelligence,
            "kpis": kpis,
            "table_schema": get_tithes_analytics_schema()
        }
    )