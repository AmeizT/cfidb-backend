def get_ministry_status(score):
    if score >= 20:
        return "HIGH"
    elif score >= 10:
        return "MODERATE"
    return "LOW"


def get_ministry_metrics(report):
    outreaches = 0
    homecells_planted = 0
    homecell_attendance = 0

    score = (
        min(outreaches / 5, 1) * 40 +
        min(homecells_planted / 3, 1) * 40 +
        min(homecell_attendance / 100, 1) * 20
    )

    return {
        "outreaches": outreaches,
        "homecells_planted": homecells_planted,
        "homecell_attendance": homecell_attendance,
        "status": get_ministry_status(score),
    }