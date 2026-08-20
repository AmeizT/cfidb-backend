class SimpleFinanceSerializer:
    @staticmethod
    def from_report(report):
        revenues = []
        overheads = []
        variable_expenses = []

        # Revenue
        for r in report.revenue_set.all():
            revenues.append({
                "item": r.category.name,
                "amount": r.amount,
                "date": r.timestamp,
            })

        # Overheads (expenses)
        for o in report.overhead_set.all():
            overheads.append({
                "item": o.overhead_type.name,
                "amount": o.amount,
                "date": o.timestamp,
            })

        for e in report.variable_expenditure_set.all():
            variable_expenses.append({
                "item": e.name,
                "amount": e.price * e.quantity,
                "date": e.timestamp,
            })

        total_overheads = sum(o["amount"] for o in overheads)
        total_variable_expenses = sum(e["amount"] for e in variable_expenses)

        total_revenue = sum(r["amount"] for r in revenues)
        total_expenses = total_overheads + total_variable_expenses

        return {
            "revenue": revenues,
            "overheads": overheads,
            "expenses": variable_expenses,
            "totals": {
                "revenue": total_revenue,
                "expenses": total_expenses,
                "balance": total_revenue - total_expenses
            }
        }

def normalize_cashflow(data):
    rows = []

    for item in data.get("revenue", []):
        rows.append({
            "date": item["date"] or None,
            "label": f"{item['item']}" if item.get("date") else item["item"] - {item['date']},
            "type": "revenue",
            "subtype": None,
            "income": item["amount"],
            "expense": 0,
        })

    for item in data.get("overheads", []):
        rows.append({
            "date": item["date"] or None,
            "label": f"{item['item']}" if item.get("date") else item["item"] - {item['date']},
            "type": "expense",
            "subtype": "overhead",
            "income": 0,
            "expense": item["amount"],
        })

    for item in data.get("expenses", []):
        rows.append({
            "date": item["date"] or None,
            "label": f"{item['item']}" if item.get("date") else item["item"] - {item['date']},
            "type": "expense",
            "subtype": "variable",
            "income": 0,
            "expense": item["amount"],
        })

    type_order = {
        ("revenue", None): 0,
        ("expense", "overhead"): 1,
        ("expense", "variable"): 2,
    }

    rows.sort(
        key=lambda x: (
            type_order.get((x["type"], x["subtype"]), 99),
            x["date"] or "",
        )
    )

    totals = {
        "revenue": 0,
        "overheads": 0,
        "variables": 0,
    }

    for row in rows:
        if row["type"] == "revenue":
            totals["revenue"] += row["income"]
        elif row["subtype"] == "overhead":
            totals["overheads"] += row["expense"]
        elif row["subtype"] == "variable":
            totals["variables"] += row["expense"]

    balance = 0
    for row in rows:
        income = row.get("income", 0) or 0
        expense = row.get("expense", 0) or 0
        balance += income
        balance -= expense
        row["balance"] = balance

    # Build final rows with section headers
    final_rows = []
    current_section = None

    section_map = {
        ("revenue", None): "Revenue",
        ("expense", "overhead"): "Overheads",
        ("expense", "variable"): "Other Expenses",
    }
    tone_map = {
        ("revenue", None): "income",
        ("expense", "overhead"): "expense",
        ("expense", "variable"): "expense",
    }

    for row in rows:
        section = section_map.get((row["type"], row["subtype"]))

        if section != current_section:
            final_rows.append({
                "label": section,
                # "income": None,
                # "expense": None,
                "balance": None,
                "is_section": True,
                "tone": tone_map.get((row["type"], row["subtype"]), "neutral"),
            })
            current_section = section

        final_rows.append(row)

    # Append totals at the end
    final_rows.append({
        "label": "Total Revenue",
        "income": totals["revenue"],
        "expense": 0,
        "balance": None,
        "is_total": True,
        "tone": "income",
    })

    final_rows.append({
        "label": "Total Overheads",
        "income": 0,
        "expense": totals["overheads"],
        "balance": None,
        "is_total": True,
        "tone": "expense",
    })

    final_rows.append({
        "label": "Total Other Expenses",
        "income": 0,
        "expense": totals["variables"],
        "balance": None,
        "is_total": True,
        "tone": "expense",
    })

    return final_rows
