
from django.db.models import Sum
from calendar import month_name


def resolve_cashflow(report):
    revenue = report.revenue_set.aggregate(total=Sum("amount"))["total"] or 0
    tithes = report.tithe_set.aggregate(total=Sum("amount"))["total"] or 0

    overhead = report.overhead_set.aggregate(total=Sum("amount"))["total"] or 0
    variable = report.variable_expenditure_set.aggregate(
        total=Sum("price")
    )["total"] or 0

    revenue_total = revenue + tithes
    expense_total = overhead + variable

    return {
        "revenue_total": revenue_total,
        "expense_total": expense_total,
        "balance": revenue_total - expense_total,
    }


def build_financial_statements(reports, months):
    report_map = {r.period_start.month: r for r in reports}

    statements = []

    for m in months:
        report = report_map.get(m)

        if report:
            data = resolve_cashflow(report)

            statements.append({
                "month": m,
                "label": month_name[m],
                "report_id": report.id,
                "is_missing": False,
                **data
            })
        else:
            statements.append({
                "month": m,
                "label": month_name[m],
                "report_id": None,
                "is_missing": True,
                "revenue_total": 0,
                "expense_total": 0,
                "balance": 0,
            })

    return statements