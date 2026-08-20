from calendar import month_name
from django.db.models import F, Max, Sum
from apps.reports.models.assembly import AssemblyReport
from apps.reports.services.analytics.kpi_layer import build_kpi_response
from apps.reports.schemas.analytics.cashflow_analytics_schema import get_cashflow_analytics_schema

def resolve_cashflow(report):
    revenue = report.revenue_set.aggregate(total=Sum("amount"))["total"] or 0
    tithes = report.tithe_set.aggregate(total=Sum("amount"))["total"] or 0

    overhead = report.overhead_set.aggregate(total=Sum("amount"))["total"] or 0
    variable = report.variable_expenditure_set.aggregate(
        total=Sum(F("price") * F("quantity"))
    )["total"] or 0

    revenue_total = revenue + tithes
    expense_total = overhead + variable

    return revenue_total, expense_total, revenue_total - expense_total

def build_cashflow_year(assembly, year):
    from apps.reports.services.analytics.year_response import build_year_response

    reports = AssemblyReport.objects.filter(
        assembly=assembly,
        period_start__year=year
    )

    months = range(1, 13)
    report_map = {r.period_start.month: r for r in reports}

    statements = []

    prev_balance = 0.0

    for m in months:
        report = report_map.get(m)

        if report:
            revenue_total, expense_total, balance = resolve_cashflow(report)
            revenue_total = float(revenue_total or 0)
            expense_total = float(expense_total or 0)
            balance = float(balance or 0)
        else:
            revenue_total = expense_total = balance = 0.0

        change = ((balance - prev_balance) / prev_balance) if prev_balance else 0.0

        statements.append({
            "month": m,
            "label": month_name[m],
            "report_id": report.id if report else None, # type: ignore
            "is_missing": report is None,

            # STRICT FINANCE METRICS
            "revenue_total": revenue_total,
            "expense_total": expense_total,
            "balance": balance,

            # KPI
            "previous_balance": prev_balance,
            "change": change,
        })

        prev_balance = balance

    valid = [s for s in statements if not s["is_missing"]]

    total_revenue = sum(s["revenue_total"] for s in valid)
    total_expense = sum(s["expense_total"] for s in valid)
    total_balance = sum(s["balance"] for s in valid)

    ytd = {
        "total_revenue": total_revenue,
        "total_expense": total_expense,
        "net_cashflow": total_balance,
        "months_with_data": len(valid),
        "missing_months": len(statements) - len(valid),
    }

    return build_kpi_response(
        year=year,
        statements=statements,
        domain="finance",
        extra_meta={
            "kpis": ytd,
            "table_schema": get_cashflow_analytics_schema(),
        }
    )