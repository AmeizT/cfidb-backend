def aggregate_finance(reports):
    return {
        "tithes": float(sum(r.tithe_total for r in reports)),
        "income": float(sum(r.income_total for r in reports)),
        "expenditure": float(sum(r.expense_total for r in reports)),
        "balance": float(sum(r.balance for r in reports)),
    }