from copy import deepcopy

REPORTS_TABLE_SCHEMA = {
    "intent": "finance",
    "columns": [
        {"id": "period_start", "label": "Period", "formatter": "month"},
        {"id": "tithe_total", "label": "Tithes", "formatter": "currency"},
        {"id": "income_total", "label": "Income", "formatter": "currency"},
        {"id": "expense_total", "label": "Expenses", "formatter": "currency"},
        {"id": "balance", "label": "Balance", "formatter": "currency"},
        {"id": "attendance_total", "label": "Attendance", "formatter": "numeric"},
        {"id": "members_total", "label": "Members", "formatter": "numeric"},
        {"id": "status", "label": "Status"},
    ],
    "footer": {
        "enabled": True,
        "sumFields": [
            "tithe_total",
            "income_total",
            "expense_total",
            "balance",
        ],
    },
    "variant": {
        "mode": "list",
        "border": "y",
        "theme": "neutral",
        "interaction": {
            "editable": False,
            "selectable": False,
            "density": "comfortable",
        },
    },
}

def get_reports_table_schema():
    schema = deepcopy(REPORTS_TABLE_SCHEMA)

    if "variant" in schema:
        schema["variant"]["interaction"] = {
            "editable": True,
            "selectable": True,
            "density": "compact",
        }

    return schema