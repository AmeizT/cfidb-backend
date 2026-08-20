from copy import deepcopy

TITHES_ANALYTICS_TABLE_SCHEMA = {
    "intent": "finance",    
    "columns": [
        {"id": "label", "label": "Month"},
        {"id": "total", "label": "Monthly Total", "formatter": "currency"},
        {"id": "previous_total", "label": "Prev. Month Total", "formatter": "currency"},
        {"id": "change", "label": "Change %", "formatter": "percentage"},
        {"id": "givers", "label": "Givers", "formatter": "numeric"},
        {"id": "givers_fluctuation", "label": "Fluctuation %", "formatter": "percentage"},
        {"id": "highest_amount", "label": "Highest", "formatter": "currency"},
        {"id": "median", "label": "Median", "formatter": "currency"},
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

def get_tithes_analytics_schema():
    schema = deepcopy(TITHES_ANALYTICS_TABLE_SCHEMA)

    if "variant" in schema:
        schema["variant"]["interaction"] = {
            "editable": False,
            "selectable": False,
            "density": "comfortable",
        }

    return schema


