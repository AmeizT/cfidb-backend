from apps.reports.services.analytics.compliance.risk_engine import calculate_risk_level
from apps.reports.services.analytics.compliance.trend_engine import calculate_trend


def get_assembly_metrics(assembly, section_stats, historical_scores):
    """
    section_stats example:
    {
        "compliance": 80,
        "timeliness": 70,
        "consistency": 60
    }
    """

    compliance = section_stats["compliance"]
    timeliness = section_stats["timeliness"]
    consistency = section_stats["consistency"]

    overall = (
        compliance * 0.5 +
        timeliness * 0.3 +
        consistency * 0.2
    )

    risk = calculate_risk_level(compliance, timeliness, consistency)

    trend = calculate_trend(overall, historical_scores)

    return {
        "assembly": assembly.id,
        "assembly_name": assembly.name,

        "scores": {
            "compliance": compliance,
            "timeliness": timeliness,
            "consistency": consistency,
            "overall": round(overall, 2),
        },

        "risk_level": risk,
        "trend": trend,
    }