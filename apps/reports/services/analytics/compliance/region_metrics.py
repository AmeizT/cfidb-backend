from statistics import mean


def get_region_metrics(region, zone_metrics_list):
    """
    Aggregates zones into region intelligence
    """

    if not zone_metrics_list:
        return None

    avg_overall = mean([z["scores"]["overall"] for z in zone_metrics_list])

    risk_summary = {
        "LOW": 0,
        "MEDIUM": 0,
        "HIGH": 0,
        "CRITICAL": 0,
    }

    for zone in zone_metrics_list:
        for k, v in zone["risk_distribution"].items():
            risk_summary[k] += v

    improving_zones = 0
    declining_zones = 0

    for zone in zone_metrics_list:
        trend = zone.get("trend", "STABLE")
        if trend == "IMPROVING":
            improving_zones += 1
        elif trend == "DECLINING":
            declining_zones += 1

    return {
        "region": region.id,
        "region_name": region.name,

        "overall_score": round(avg_overall, 2),

        "risk_summary": risk_summary,

        "trends": {
            "improving_zones": improving_zones,
            "declining_zones": declining_zones,
        },
    }