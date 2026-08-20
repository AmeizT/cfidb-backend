def aggregate_ministry(reports):
    outreaches = sum(getattr(r, "total_outreaches", 0) for r in reports)
    homecells = sum(getattr(r, "total_homecells_planted", 0) for r in reports)
    attendance = sum(getattr(r, "total_homecell_attendance", 0) for r in reports)

    score = (
        min(outreaches / 5, 1) * 40 +
        min(homecells / 3, 1) * 40 +
        min(attendance / 100, 1) * 20
    )

    status = (
        "HIGH" if score >= 70 else
        "MODERATE" if score >= 40 else
        "LOW"
    )

    return {
        "outreaches": outreaches,
        "homecells_planted": homecells,
        "homecell_attendance": attendance,
        "status": status,
    }