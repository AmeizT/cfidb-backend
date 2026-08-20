# from apps.reports.models import AssemblyReport
# from apps.reports.services.summary_engine import QUARTER_MAP
# from apps.reports.services.summary_engine import resolve_cashflow,build_time_statements

# QUARTER_MAP = {
#     1: [1, 2, 3],
#     2: [4, 5, 6],
#     3: [7, 8, 9],
#     4: [10, 11, 12],
# }


# def finance_quarter_engine(assembly, reports, year, quarter):
#     months = QUARTER_MAP[quarter]

#     statements = build_time_statements(
#         reports=reports,
#         months=months,
#         mode="finance"
#     )

#     return {
#         "data": {
#             "view": "quarter",
#             "year": year,
#             "quarter": quarter,
#             "statements": statements,
#         },
#         "meta": finance_meta(statements, reports, year, quarter)
#     }


# def finance_meta(statements, reports, year, quarter):
#     valid = [s for s in statements if not s["is_missing"]]

#     total_revenue = sum(s["revenue_total"] for s in valid)
#     total_expense = sum(s["expense_total"] for s in valid)

#     best_month = max(valid, key=lambda x: x["balance"]) if valid else None
#     worst_month = min(valid, key=lambda x: x["balance"]) if valid else None

#     return {
#         "total_revenue": total_revenue,
#         "total_expense": total_expense,
#         "quarter_total": sum(s["balance"] for s in valid),
#         "average": (sum(s["balance"] for s in valid) / len(valid)) if valid else 0,
#         "best_month": best_month,
#         "worst_month": worst_month,
#         "missing": len([s for s in statements if s["is_missing"]]),
#     }





from apps.reports.services.analytics.cashflow_engine import build_cashflow_year


def get_cashflow_year(assembly, year):
    return build_cashflow_year(assembly=assembly, year=year)