from calendar import month_name
from apps.reports.models.assembly import AssemblyReport
from django.db.models import Sum
from apps.reports.schemas.analytics.attendance_analytics_schema import get_attendance_analytics_schema


def build_attendance_year(assembly, year):
    from apps.reports.services.analytics.kpi_layer import build_kpi_response

    reports = AssemblyReport.objects.filter(
        assembly=assembly,
        period_start__year=year,
    )

    months = range(1, 13)
    report_map = {r.period_start.month: r for r in reports}

    statements = []

    prev_total = 0

    for m in months:
        report = report_map.get(m)

        if report:
            total_adults = getattr(report, "total_adults", 0) or 0
            total_children = getattr(report, "total_children", 0) or 0
            total_visitors = getattr(report, "total_visitors", 0) or 0
            online_viewers = getattr(report, "total_online_viewers", 0) or 0
            

            calculated_total = total_adults + total_children + total_visitors + online_viewers
            total = report.attendance_total if report.attendance_total else calculated_total
        else:
            total_adults = 0
            total_children = 0
            total_visitors = 0
            online_viewers = 0
            total = 0

        change = round((total - prev_total) / prev_total, 2) if prev_total else 0.0

        statements.append({
            "month": m,
            "label": month_name[m],
            "report_id": report.id if report else None, # type: ignore
            "is_missing": report is None,

            # STRICT ATTENDANCE METRICS
            "total_adults": total_adults,
            "total_children": total_children,
            "total_visitors": total_visitors,
            "online_viewers": online_viewers,
            "total": total,

            # KPI
            "previous_total": prev_total,
            "change": change,
        })

        prev_total = total

    # YTD calculations
    valid = [s for s in statements if not s["is_missing"]]

    ytd_total_adults = sum(s.get("total_adults", 0) for s in valid)
    ytd_total_children = sum(s.get("total_children", 0) for s in valid)
    ytd_total_visitors = sum(s.get("total_visitors", 0) for s in valid)
    ytd_total_online_viewers = sum(s.get("online_viewers", 0) for s in valid)
    ytd_total = sum(s.get("total", 0) for s in valid)

    totals = sorted([s.get("total", 0) for s in valid])
    n = len(totals)
    if n == 0:
        ytd_median = 0
    elif n % 2 == 1:
        ytd_median = totals[n // 2]
    else:
        ytd_median = (totals[n // 2 - 1] + totals[n // 2]) / 2

    ytd = {
        "total_adults": ytd_total_adults,
        "total_children": ytd_total_children,
        "total_visitors": ytd_total_visitors,
        "total_online_viewers": ytd_total_online_viewers,
        "total_attendance": ytd_total,
        "average_attendance": ytd_total / len(valid) if valid else 0,
        "median_attendance": ytd_median,
    }

    return build_kpi_response(
        year=year,
        statements=statements,
        domain="attendance",
        extra_meta={
            "kpis": ytd,
            "table_schema": get_attendance_analytics_schema(),
        }
    )
