def calculate_trend(current_score, previous_scores):
    """
    Determines improvement direction over time.
    previous_scores = list of last 3–6 months
    """

    if not previous_scores:
        return "STABLE"

    avg_previous = sum(previous_scores) / len(previous_scores)

    diff = current_score - avg_previous

    if diff >= 5:
        return "IMPROVING"
    elif diff <= -5:
        return "DECLINING"
    else:
        return "STABLE"