from copy import deepcopy

ATTENDANCE_ANALYTICS_TABLE_SCHEMA = {
    "intent": "attendance",    
    "columns": [
        {"id": "label", "label": "Month"},
        {"id": "total_adults", "label": "Adults", "formatter": "numeric", 
            "meta": {
                "align": "right",
            }
        },
        {"id": "total_children", "label": "Children", "formatter": "numeric", 
            "meta": {
                "align": "right",
            }
        },
        {"id": "total_visitors", "label": "Visitors", "formatter": "numeric", 
            "meta": {
                "align": "right",
            }
        },
        {"id": "online_viewers", "label": "Online Viewers", "formatter": "numeric", 
            "meta": {
                "align": "right",
            }
        },
        {"id": "total", "label": "Total", "formatter": "numeric", 
            "meta": {
                "align": "right",
            }
        },
        {"id": "change", "label": "Change %", "formatter": "percentage", 
            "meta": {
                "trend": True,
            }
        },
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

def get_attendance_analytics_schema():
    schema = deepcopy(ATTENDANCE_ANALYTICS_TABLE_SCHEMA)

    if "variant" in schema:
        schema["variant"]["interaction"] = {
            "editable": False,
            "selectable": False,
            "density": "comfortable",
        }

    return schema

