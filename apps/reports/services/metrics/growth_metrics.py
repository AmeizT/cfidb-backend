def get_growth_status(growth_rate):
    if growth_rate > 3:
        return "GROWING"
    elif growth_rate >= 0:
        return "STABLE"
    return "DECLINING"


def get_growth_metrics(report):
    total_members = report.members_total
    new_members = report.total_new_converts

    # prevent division errors
    growth_rate = (
        (new_members / total_members) * 100
        if total_members > 0 else 0
    )

    return {
        "total_members": total_members,
        "new_members": new_members,
        "growth_rate": round(growth_rate, 2),
        "status": get_growth_status(growth_rate),
    }