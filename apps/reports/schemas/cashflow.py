from copy import deepcopy

CASHFLOW_TABLE_SCHEMA = {
    "intent": "finance",
    "columns": [
        {
            "id": "label",
            "label": "Date, Transaction Type",
            "editable": False,
            "meta": {
                "isSection": True,
                "isTotal": True,
                "indent": True,
                "disableEditForSection": True
            },
        },
        {
            "id": "income",
            "label": "Income",
            "formatter": "currency",
            "isFooterSum": True,
            "editable": False,
            "cellClass": "cell-income",
            "isNumeric": True,
        },
        {
            "id": "expense",
            "label": "Expense",
            "formatter": "currency",
            "isFooterSum": True,
            "editable": False,
            "cellClass": "cell-expense",
            "isNumeric": True,
        },
        {
            "id": "balance",
            "label": "Balance",
            "formatter": "currency",
            "cellClass": "cell-balance",
            "isNumeric": True,
            "meta": {
                "isSticky": True
            },
        },
    ],
    "footer": {
        "enabled": True,
        "sumFields": ["income", "expense"],
    },
    "variant": {
        "mode": "grid",
        "border": "subtle",
        "theme": "neutral",
        "interaction": {
            "editable": False,
            "selectable": False,
            "density": "compact"
        }
    },
}

def get_cashflow_schema(user):
    schema = deepcopy(CASHFLOW_TABLE_SCHEMA)

    if "variant" in schema:
        schema["variant"]["interaction"] = {
            "editable": False,
            "selectable": True,
            "density": "compact",
        }

    return schema
