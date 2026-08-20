from copy import deepcopy


COMMON_COLUMNS = [
    {
        "id": "country",
        "label": "Country",
    },
    {
        "id": "assembly",
        "label": "Assembly",
    },
]


RISK_SCHEMA = {
    "intent": "risk",
    "columns": [
        *COMMON_COLUMNS,
        {
            "id": "score",
            "label": "Risk Score",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {"id": "level", "label": "Risk Level"},
        {
            "id": "reports",
            "label": "Reports",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
    ],
    "variant": {
        "mode": "list",
        "border": "y",
        "theme": "neutral",
        "interaction": {
            "editable": False,
            "selectable": True,
            "density": "comfortable",
        },
    },
}


FINANCE_SCHEMA = {
    "intent": "finance",
    "columns": [
        *COMMON_COLUMNS,
        {
            "id": "tithes",
            "label": "Tithes",
            "formatter": "currency",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {
            "id": "income",
            "label": "Income",
            "formatter": "currency",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {
            "id": "expenditure",
            "label": "Expenditure",
            "formatter": "currency",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {
            "id": "balance",
            "label": "Balance",
            "formatter": "currency",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {"id": "status", "label": "Status"},
    ],
    "variant": {
        "mode": "list",
        "border": "y",
        "theme": "neutral",
        "interaction": {
            "editable": False,
            "selectable": True,
            "density": "comfortable",
        },
    },
}


GROWTH_SCHEMA = {
    "intent": "growth",
    "columns": [
        *COMMON_COLUMNS,
        {
            "id": "total_members",
            "label": "Members",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {
            "id": "new_members",
            "label": "New Members",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {
            "id": "growth_rate",
            "label": "Growth %",
            "formatter": "percentage",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {"id": "status", "label": "Status"},
    ],
    "variant": {
        "mode": "list",
        "border": "y",
        "theme": "neutral",
        "interaction": {
            "editable": False,
            "selectable": True,
            "density": "comfortable",
        },
    },
}


MINISTRY_SCHEMA = {
    "intent": "ministry",
    "columns": [
        *COMMON_COLUMNS,
        {
            "id": "outreaches",
            "label": "Planned",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {
            "id": "actual_outreaches",
            "label": "Actual",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {
            "id": "homecells_planted",
            "label": "Homecells",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {
            "id": "homecell_attendance",
            "label": "Attendance",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {"id": "status", "label": "Status"},
    ],
    "variant": {
        "mode": "list",
        "border": "y",
        "theme": "neutral",
        "interaction": {
            "editable": False,
            "selectable": True,
            "density": "comfortable",
        },
    },
}


LEADERSHIP_SCHEMA = {
    "intent": "leadership",
    "columns": [
        *COMMON_COLUMNS,
        {
            "id": "leaders_count",
            "label": "Leaders",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {
            "id": "meetings_conducted",
            "label": "Meetings",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {
            "id": "assets_valuation",
            "label": "Assets",
            "formatter": "currency",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
    ],
    "variant": {
        "mode": "list",
        "border": "y",
        "theme": "neutral",
        "interaction": {
            "editable": False,
            "selectable": True,
            "density": "comfortable",
        },
    },
}


COMPLIANCE_SCHEMA = {
    "intent": "compliance",
    "columns": [
        *COMMON_COLUMNS,
        {
            "id": "total_sections",
            "label": "Sections",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {
            "id": "submitted",
            "label": "Submitted",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {
            "id": "skipped",
            "label": "Skipped",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {
            "id": "pending",
            "label": "Pending",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {
            "id": "progress",
            "label": "Progress",
            "formatter": "percentage",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {
            "id": "coverage",
            "label": "Coverage",
            "formatter": "percentage",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {"id": "status", "label": "Status"},
    ],
    "variant": {
        "mode": "list",
        "border": "y",
        "theme": "neutral",
        "interaction": {
            "editable": False,
            "selectable": True,
            "density": "comfortable",
        },
    },
}


AUDIT_LOG_SCHEMA = {
    "intent": "compliance_audit_log",
    "columns": [
        {"id": "assembly_name", "label": "Assembly"},
        {"id": "zone", "label": "Zone"},
        {"id": "country", "label": "Country"},
        {"id": "period", "label": "Period"},
        {"id": "section_skipped", "label": "Section"},
        {"id": "reason_for_skipping", "label": "Reason"},
        {"id": "follow_up_status", "label": "Follow-up"},
        {"id": "follow_up_assigned_to", "label": "Assigned To"},
        {"id": "is_late_submission", "label": "Late"},
        {
            "id": "days_late",
            "label": "Days Late",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
    ],
    "variant": {
        "mode": "list",
        "border": "y",
        "theme": "neutral",
        "interaction": {
            "editable": True,
            "selectable": True,
            "density": "comfortable",
        },
    },
}


def get_regional_dashboard_schema(user):
    return {
        "risk": deepcopy(RISK_SCHEMA),
        "finance": deepcopy(FINANCE_SCHEMA),
        "growth": deepcopy(GROWTH_SCHEMA),
        "ministry": deepcopy(MINISTRY_SCHEMA),
        "leadership": deepcopy(LEADERSHIP_SCHEMA),
        "compliance": deepcopy(COMPLIANCE_SCHEMA),
    }


def get_regional_module_schema(user, domain):
    return deepcopy(get_regional_dashboard_schema(user)[domain])


def get_regional_audit_log_schema(user):
    return deepcopy(AUDIT_LOG_SCHEMA)
