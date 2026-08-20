from __future__ import annotations

from copy import deepcopy


def _text_column(column_id: str, label: str) -> dict:
    return {"id": column_id, "label": label}


def _number_column(
    column_id: str,
    label: str,
    *,
    formatter: str = "number",
) -> dict:
    return {
        "id": column_id,
        "label": label,
        "formatter": formatter,
        "isNumeric": True,
        "meta": {"align": "right"},
    }


def _table_schema(intent: str, columns: list[dict]) -> dict:
    return {
        "intent": intent,
        "columns": columns,
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


FINANCE_TABLE_SCHEMA = {
    "intent": "finance",
    "columns": [
        {"id": "name", "label": "Assembly"},
        {"id": "zone", "label": "Zone"},
        {"id": "country", "label": "Country"},
        {"id": "currency", "label": "Currency"},
        {
            "id": "tithes",
            "label": "Tithes",
            "formatter": "currency",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {
            "id": "other_revenue",
            "label": "Other Revenue",
            "formatter": "currency",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {
            "id": "total_revenue",
            "label": "Total Revenue",
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
            "id": "remittance_owed",
            "label": "Remittance Owed",
            "formatter": "currency",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {
            "id": "remittance_paid",
            "label": "Remittance Paid",
            "formatter": "currency",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {
            "id": "remittance_balance",
            "label": "Remittance Balance",
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
        {"id": "financial_health", "label": "Financial Health"},
        {
            "id": "avg_tithes_per_member",
            "label": "Avg Tithes / Member",
            "formatter": "currency",
            "isNumeric": True,
            "meta": {"align": "right"},
        },
        {
            "id": "income_concentration",
            "label": "Tithe %",
            "formatter": "percentage",
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

COMPLIANCE_TABLE_SCHEMA = _table_schema(
    "compliance",
    [
        _text_column("name", "Assembly"),
        _text_column("zone", "Zone"),
        _text_column("country", "Country"),
        _number_column("expected_reports", "Expected"),
        _number_column("submitted_reports", "Submitted"),
        _number_column("missing_reports", "Missing"),
        _number_column("incomplete_reports", "Incomplete"),
        _number_column("skipped_reports", "Skipped"),
        _number_column("late_reports", "Late"),
        _number_column("compliance_rate", "Compliance", formatter="percentage"),
        _number_column("on_time_rate", "On Time", formatter="percentage"),
        _number_column("completion_rate", "Completion", formatter="percentage"),
        _number_column("average_days_late", "Avg Days Late"),
        _text_column("current_status", "Status"),
        _text_column("risk_level", "Risk"),
        _text_column("last_submitted_at", "Last Submitted"),
        _text_column("last_missing_period", "Last Missing"),
    ],
)

RISK_TABLE_SCHEMA = _table_schema(
    "risk",
    [
        _text_column("name", "Assembly"),
        _text_column("zone", "Zone"),
        _text_column("country", "Country"),
        _number_column("risk_score", "Score"),
        _text_column("risk_level", "Level"),
        _text_column("risk_status", "Status"),
        _number_column("reporting_risk", "Reporting"),
        _number_column("finance_risk", "Finance"),
        _number_column("growth_risk", "Growth"),
        _number_column("ministry_risk", "Ministry"),
        _number_column("leadership_risk", "Leadership"),
        _number_column("compliance_risk", "Compliance"),
        _text_column("recommended_action", "Action"),
    ],
)

GROWTH_TABLE_SCHEMA = _table_schema(
    "growth",
    [
        _text_column("name", "Assembly"),
        _text_column("zone", "Zone"),
        _text_column("country", "Country"),
        _number_column("total_members", "Members"),
        _number_column("previous_members", "Previous"),
        _number_column("new_members", "New Members"),
        _number_column("lost_members", "Lost"),
        _number_column("net_growth", "Net Growth"),
        _number_column("growth_rate", "Growth", formatter="percentage"),
        _number_column("total_baptisms", "Baptisms"),
        _number_column("total_visitors", "Visitors"),
        _number_column("total_new_converts", "New Converts"),
        _text_column("established_date", "Established"),
        _number_column("church_age_years", "Age"),
        _text_column("growth_status", "Status"),
    ],
)

MINISTRY_TABLE_SCHEMA = _table_schema(
    "ministry",
    [
        _text_column("name", "Assembly"),
        _text_column("zone", "Zone"),
        _text_column("country", "Country"),
        _number_column("planned_outreaches", "Planned"),
        _number_column("actual_outreaches", "Actual"),
        _number_column("outreach_completion_rate", "Outreach", formatter="percentage"),
        _number_column("homecells_planted", "Homecells Planted"),
        _number_column("active_homecells", "Active Homecells"),
        _number_column("homecell_attendance", "Homecell Attendance"),
        _number_column("ministry_events", "Events"),
        _number_column("volunteers", "Volunteers"),
        _number_column("ministry_score", "Score"),
        _text_column("ministry_status", "Status"),
    ],
)

LEADERSHIP_TABLE_SCHEMA = _table_schema(
    "leadership",
    [
        _text_column("name", "Assembly"),
        _text_column("zone", "Zone"),
        _text_column("country", "Country"),
        _number_column("assigned_pastors_count", "Pastors"),
        _number_column("leaders_count", "Leaders"),
        _number_column("meetings_conducted", "Meetings"),
        _number_column("reports_verified", "Verified"),
        _number_column("unverified_reports", "Unverified"),
        _number_column("verification_rate", "Verification", formatter="percentage"),
        _number_column("assets_valuation", "Assets", formatter="currency"),
        _text_column("leadership_status", "Status"),
    ],
)


def get_finance_table_schema() -> dict:
    return deepcopy(FINANCE_TABLE_SCHEMA)


def get_compliance_table_schema() -> dict:
    return deepcopy(COMPLIANCE_TABLE_SCHEMA)


def get_risk_table_schema() -> dict:
    return deepcopy(RISK_TABLE_SCHEMA)


def get_growth_table_schema() -> dict:
    return deepcopy(GROWTH_TABLE_SCHEMA)


def get_ministry_table_schema() -> dict:
    return deepcopy(MINISTRY_TABLE_SCHEMA)


def get_leadership_table_schema() -> dict:
    return deepcopy(LEADERSHIP_TABLE_SCHEMA)
