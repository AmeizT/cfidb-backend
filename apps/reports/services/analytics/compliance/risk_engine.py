def calculate_risk_level(compliance_score, timeliness_score, consistency_score):
    """
    Core risk classification engine
    """

    overall = (
        compliance_score * 0.5 +
        timeliness_score * 0.3 +
        consistency_score * 0.2
    )

    if overall >= 85:
        return "LOW"
    elif overall >= 70:
        return "MEDIUM"
    elif overall >= 50:
        return "HIGH"
    else:
        return "CRITICAL"