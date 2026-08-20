def aggregate_growth(reports):
    total_members = sum(r.members_total for r in reports)
    new_members = sum(r.total_new_converts for r in reports)

    growth_rate = (
        (new_members / total_members) * 100
        if total_members > 0 else 0
    )

    status = (
        "GROWING" if growth_rate > 3 else
        "STABLE" if growth_rate >= 0 else
        "DECLINING"
    )

    return {
        "total_members": total_members,
        "new_members": new_members,
        "growth_rate": round(growth_rate, 2),
        "status": status,
    }