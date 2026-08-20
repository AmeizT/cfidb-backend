from decimal import Decimal

def get_finance_status(balance, income):
    if income <= 0:
        return "TIGHT"

    ratio = balance / income

    if ratio >= Decimal("0.20"):
        return "SURPLUS"

    if ratio >= 0:
        return "TIGHT"

    return "DEFICIT"


def get_finance_metrics(report):
    offerings = report.income_total - report.tithe_total
    income = report.income_total + report.tithe_total

    return {
        "tithes": report.tithe_total,
        "offerings": 0,
        "income": report.income_total,
        "total_income": income,
        "expenditure": report.expense_total,
        "remittance": 0,  # add later
        "assets_valuation": 0,  # add later
        "balance": report.balance,
        "status": get_finance_status(
            report.balance,
            income,
        ),
    }