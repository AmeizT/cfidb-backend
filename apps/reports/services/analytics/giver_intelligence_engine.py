from django.db.models import Sum
from collections import defaultdict
from datetime import date


def build_giver_intelligence(queryset, reports):
    """
    Builds giver intelligence from raw tithe queryset + reports
    """

    member_map = _build_member_profiles(queryset)
    cohorts = _build_cohorts(member_map)
    ltv = _compute_lifetime_value(member_map)

    retention = _compute_retention(member_map)
    churn = _compute_churn(member_map)

    return {
        "members": member_map,
        "cohorts": cohorts,
        "lifetime_value": ltv,
        "retention": retention,
        "churn": churn,
    }


# -------------------------------------------------
# 1. MEMBER PROFILES (core foundation)
# -------------------------------------------------
def _build_member_profiles(queryset):
    """
    Builds per-member giving history
    """

    members = defaultdict(lambda: {
        "total_given": 0,
        "months_active": set(),
        "first_date": None,
        "last_date": None,
    })

    for obj in queryset.select_related("member"):
        m_id = obj.member_id
        m = members[m_id]

        m["total_given"] += float(obj.amount)

        m["months_active"].add(obj.timestamp.month)

        if not m["first_date"] or obj.timestamp < m["first_date"]:
            m["first_date"] = obj.timestamp

        if not m["last_date"] or obj.timestamp > m["last_date"]:
            m["last_date"] = obj.timestamp

    return members


# -------------------------------------------------
# 2. COHORT ANALYSIS
# -------------------------------------------------
def _build_cohorts(member_map):
    """
    Cohort = first month a member gave
    """

    cohorts = defaultdict(list)

    for member_id, data in member_map.items():
        if not data["first_date"]:
            continue

        cohort_key = data["first_date"].strftime("%Y-%m")

        cohorts[cohort_key].append({
            "member_id": member_id,
            "total_given": data["total_given"],
            "active_months": len(data["months_active"]),
        })

    return cohorts


# -------------------------------------------------
# 3. LIFETIME VALUE (LTV)
# -------------------------------------------------
def _compute_lifetime_value(member_map):
    """
    Total + average per member
    """

    total = sum(m["total_given"] for m in member_map.values())
    count = len(member_map)

    return {
        "total_ltv": total,
        "avg_ltv": total / count if count else 0,
    }


# -------------------------------------------------
# 4. RETENTION (simplified v1)
# -------------------------------------------------
def _compute_retention(member_map):
    """
    Active consistency proxy
    """

    if not member_map:
        return {"rate": 0}

    active_members = sum(
        1 for m in member_map.values()
        if len(m["months_active"]) >= 2
    )

    return {
        "rate": active_members / len(member_map)
    }


# -------------------------------------------------
# 5. CHURN
# -------------------------------------------------
def _compute_churn(member_map):
    """
    Opposite of retention (simplified v1)
    """

    if not member_map:
        return {"rate": 0}

    inactive = sum(
        1 for m in member_map.values()
        if len(m["months_active"]) == 1
    )

    return {
        "rate": inactive / len(member_map)
    }