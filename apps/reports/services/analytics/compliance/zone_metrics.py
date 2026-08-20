from statistics import mean
from apps.reports.services.analytics.compliance.assembly_metrics import get_assembly_metrics


def get_zone_metrics(zone, assemblies_metrics):
    """
    Aggregates all assemblies in a zone
    """

    if not assemblies_metrics:
        return None

    avg_compliance = mean([a["scores"]["compliance"] for a in assemblies_metrics])
    avg_timeliness = mean([a["scores"]["timeliness"] for a in assemblies_metrics])
    avg_consistency = mean([a["scores"]["consistency"] for a in assemblies_metrics])
    avg_overall = mean([a["scores"]["overall"] for a in assemblies_metrics])

    risk_distribution = {
        "LOW": 0,
        "MEDIUM": 0,
        "HIGH": 0,
        "CRITICAL": 0,
    }

    for a in assemblies_metrics:
        risk_distribution[a["risk_level"]] += 1

    return {
        "zone": zone.id,
        "zone_name": zone.name,

        "scores": {
            "compliance": round(avg_compliance, 2),
            "timeliness": round(avg_timeliness, 2),
            "consistency": round(avg_consistency, 2),
            "overall": round(avg_overall, 2),
        },

        "risk_distribution": risk_distribution,
    }