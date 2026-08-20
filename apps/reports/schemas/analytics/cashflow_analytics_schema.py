from copy import deepcopy

CASHFLOW_ANALYTICS_TABLE_SCHEMA = {
    "intent": "finance",    
    "columns": [
        {"id": "label", "label": "Month"},
        {"id": "revenue_total", "label": "Revenue", "formatter": "currency"},
        {"id": "expense_total", "label": "Expenditure", "formatter": "currency"},
        {"id": "balance", "label": "Balance", "formatter": "currency"},
        {"id": "previous_balance", "label": "Previous Balance", "formatter": "currency"},
        {"id": "change", "label": "Change %", "formatter": "percentage"},
    ],
    "footer": {
        "enabled": False,
        # "sumFields": ["amount"],
    },
    "variant": {
        "mode": "list",
        "border": "y",
        "theme": "neutral",
        "interaction": {
            "editable": False,
            "selectable": False,
            "density": "comfortable"
        }
    },
}

def get_cashflow_analytics_schema():
    schema = deepcopy(CASHFLOW_ANALYTICS_TABLE_SCHEMA)

    if "variant" in schema:
        schema["variant"]["interaction"] = {
            "editable": False,
            "selectable": False,
            "density": "comfortable",
        }

    return schema


