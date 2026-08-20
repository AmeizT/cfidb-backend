from copy import deepcopy

BASE_TITHES_VARIANT = {
    "mode": "list",
    "border": "y",
    "theme": "neutral",
    "interaction": {
        "editable": False,
        "selectable": False,
        "density": "comfortable",
    }
}

TITHES_TABLE_SCHEMA = {
    "intent": "finance",    
    "columns": [
        {"id": "timestamp", "label": "Date", "formatter": "date", "editable": True},
        {
            "id": "member_name",
            "label": "Member",
            "formatter": "avatar",
            "meta": {
                "avatarField": "member_avatar",
                "avatarFallback": "member_avatar_fallback",
            }
        },
        {
            "id": "amount", 
            "label": "Amount", 
            "formatter": "currency", 
            "isFooterSum": True, 
            "editable": True, 
            "isNumeric": True,
            "meta": {
                "align": "right",
            }
        },
        {
            "id": "payment_method", 
            "label": "Payment Method", 
            "editable": True,
            "meta": {
                "badge": True,
            }
        },
        {"id": "reference_code", "label": "Reference"},
    ],
    "footer": {
        "enabled": True,
        "sumFields": ["amount"],
    },
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

TITHES_CONTRIBUTOR_HISTORY_TABLE_SCHEMA = {
    "intent": "finance",
    "columns": [
        {"id": "month", "label": "Month"},
        {
            "id": "amount",
            "label": "Amount",
            "formatter": "currency",
            "isFooterSum": True,
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {"id": "payment_method", "label": "Payment Method"},
        {"id": "recorded_by", "label": "Recorded By"},
        {"id": "recorded_date", "label": "Recorded Date", "formatter": "date"},
        {"id": "receipt", "label": "Receipt"},
    ],
    "footer": {
        "enabled": True,
        "sumFields": ["amount"],
    },
    "variant": BASE_TITHES_VARIANT,
}

TITHES_CONTRIBUTORS_TABLE_SCHEMA = {
    "intent": "finance",
    "columns": [
        {
            "id": "contributor",
            "label": "Name",
            "formatter": "avatar",
            "meta": {
                "avatarField": "contributor_avatar",
                "avatarFallback": "contributor_avatar_fallback",
            },
        },
        {
            "id": "cumulative",
            "label": "Cumulative",
            "formatter": "currency",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {
            "id": "median",
            "label": "Median",
            "formatter": "currency",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {"id": "interval", "label": "Pattern"},
        {"id": "average_payment_date", "label": "Average Date"},
        {
            "id": "commitment",
            "label": "Commitment",
            "formatter": "percentage",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
    ],
    "children": {
        "rowKey": "history",
        "columns": TITHES_CONTRIBUTOR_HISTORY_TABLE_SCHEMA["columns"],
    },
    "footer": {
        "enabled": True,
        "sumFields": ["cumulative"],
    },
    "variant": BASE_TITHES_VARIANT,
}

TITHES_CUMULATIVE_TABLE_SCHEMA = {
    "intent": "finance",
    "columns": [
        {"id": "label", "label": "Month"},
        {"id": "total", "label": "Monthly Total", "formatter": "currency", "isNumeric": True},
        {"id": "previous_total", "label": "Previous Month", "formatter": "currency", "isNumeric": True},
        {"id": "change", "label": "Change", "formatter": "percentage", "isNumeric": True},
        {"id": "givers", "label": "Contributors", "formatter": "numeric", "isNumeric": True},
        {"id": "median", "label": "Median", "formatter": "currency", "isNumeric": True},
        {"id": "highest_amount", "label": "Highest", "formatter": "currency", "isNumeric": True},
    ],
    "footer": {
        "enabled": True,
        "sumFields": ["total"],
    },
    "variant": BASE_TITHES_VARIANT,
}

TITHES_PERFORMANCE_TABLE_SCHEMA = {
    "intent": "finance",
    "columns": [
        {"id": "target", "label": "Target", "formatter": "currency", "isNumeric": True},
        {"id": "actual", "label": "Actual", "formatter": "currency", "isNumeric": True},
        {"id": "remaining", "label": "Remaining", "formatter": "currency", "isNumeric": True},
        {"id": "achievement", "label": "Achievement", "formatter": "percentage", "isNumeric": True},
    ],
    "variant": BASE_TITHES_VARIANT,
}

TITHES_RECEIPTS_TABLE_SCHEMA = {
    "intent": "finance",
    "columns": [
        {"id": "reference_code", "label": "Receipt Number"},
        {
            "id": "member_name",
            "label": "Contributor",
            "formatter": "avatar",
            "meta": {
                "avatarField": "member_avatar",
                "avatarFallback": "member_avatar_fallback",
            },
        },
        {"id": "amount", "label": "Amount", "formatter": "currency", "isNumeric": True},
        {"id": "timestamp", "label": "Tithe Date", "formatter": "date"},
        {"id": "payment_method", "label": "Payment Method"},
        {"id": "receipt", "label": "Receipt"},
    ],
    "footer": {
        "enabled": True,
        "sumFields": ["amount"],
    },
    "variant": BASE_TITHES_VARIANT,
}

TITHES_AUDIT_TABLE_SCHEMA = {
    "intent": "finance",
    "columns": [
        {"id": "timestamp", "label": "Date and Time", "formatter": "date"},
        {"id": "action", "label": "Action"},
        {"id": "object_id", "label": "Tithe / Receipt Reference"},
        {"id": "user_name", "label": "Performed By"},
        {"id": "description", "label": "Details"},
    ],
    "variant": BASE_TITHES_VARIANT,
}


def _schema_with_interaction(schema, *, editable=False, selectable=False, density="comfortable"):
    schema = deepcopy(schema)

    if "variant" in schema:
        schema["variant"]["interaction"] = {
            "editable": editable,
            "selectable": selectable,
            "density": density,
        }

    return schema


def get_tithes_schema(user):
    return _schema_with_interaction(
        TITHES_TABLE_SCHEMA,
        editable=True,
        selectable=True,
    )


def get_tithes_contributors_schema(user):
    return _schema_with_interaction(TITHES_CONTRIBUTORS_TABLE_SCHEMA)


def get_tithes_contributor_history_schema(user):
    return _schema_with_interaction(TITHES_CONTRIBUTOR_HISTORY_TABLE_SCHEMA)


def get_tithes_cumulative_schema(user):
    return _schema_with_interaction(TITHES_CUMULATIVE_TABLE_SCHEMA)


def get_tithes_performance_schema(user):
    return _schema_with_interaction(TITHES_PERFORMANCE_TABLE_SCHEMA)


def get_tithes_receipts_schema(user):
    return _schema_with_interaction(TITHES_RECEIPTS_TABLE_SCHEMA)


def get_tithes_audit_schema(user):
    return _schema_with_interaction(TITHES_AUDIT_TABLE_SCHEMA)
