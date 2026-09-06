from copy import deepcopy

ATTENDANCE_TABLE_SCHEMA = {
    "intent": "attendance",
    "columns": [
        {"id": "timestamp", "label": "Date", "formatter": "date", "editable": True},
        {"id": "service_type", "label": "Service", "editable": True},
        {"id": "preacher", "label": "Preacher", "editable": True},
        {
            "id": "total_adults", 
            "label": "Adults", 
            "editable": False,
            "isNumeric": True, 
            "meta": {
                "align": "right",
            }
        },
        {
            "id": "total_children", 
            "label": "Children",
            "editable": False, 
            "isNumeric": True, 
            "meta": {
                "align": "right",
            }
        },
        {
            "id": "total_visitors", 
            "label": "Visitors",
            "editable": False,  
            "isNumeric": True,
            "meta": {
                "align": "right",
            }
        },
        {
            "id": "online_viewers", 
            "label": "Attended Online",
            "editable": True,  
            "isNumeric": True,
            "meta": {
                "align": "right",
            }
        },
        {
            "id": "headcount", 
            "label": "Total",
            "editable": False,  
            "isNumeric": True,
            "meta": {
                "align": "right",
            }
        },
        {
            "id": "total_new_converts", 
            "label": "New Converts", 
            "editable": False, 
            "isNumeric": True,
            "meta": {
                "align": "right",
            }
        },
        {
            "id": "total_altar_call", 
            "label": "Altar Call", 
            "editable": False, 
            "isNumeric": True,
            "meta": {
                "align": "right",
            }
        },
        {
            "id": "total_baptisms", 
            "label": "Baptisms", 
            "editable": False, 
            "isNumeric": True,
            "meta": {
                "align": "right",
            }
        },
        {
            "id": "total_leaders_present", 
            "label": "Leaders", 
            "editable": True, 
            "isNumeric": True,
            "meta": {
                "align": "right",
            }
        },
        {"id": "weather", "label": "Weather"},
    ],
    "variant": {
        "mode": "list",
        "border": "y",
        "theme": "neutral",
        "interaction": {
            "editable": True,
            "selectable": True,
            "density": "comfortable"
        }
    },
}

def get_attendance_schema(user, *, editable=True):
    schema = deepcopy(ATTENDANCE_TABLE_SCHEMA)

    if "variant" in schema:
        schema["variant"]["interaction"] = {
            "editable": editable,
            "selectable": True,
            "density": "comfortable",
        }

    return schema
