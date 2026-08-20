def get_report_compliance(report):
    sections = report.sections.all()

    total = sections.count()
    submitted = sections.filter(status__in=["completed", "no_activity"]).count()
    skipped = sections.filter(status="skipped").count()
    pending = sections.filter(status__in=["not_started", "in_progress"]).count()

    progress = round((submitted / total) * 100) if total else 0

    # IMPORTANT FIX:
    # coverage = submitted + skipped (everything that has a decision)
    coverage = round(((submitted + skipped) / total) * 100) if total else 0

    # FIXED STATUS LOGIC (IMPORTANT)
    if total == 0:
        status = "NO_DATA"
    elif pending == 0 and skipped > 0:
        status = "COMPLIANT_WITH_EXCEPTIONS"
    elif pending == 0:
        status = "COMPLIANT"
    else:
        status = "INCOMPLETE"

    return {
        "total_sections": total,
        "submitted": submitted,
        "skipped": skipped,
        "pending": pending,
        "progress": progress,
        "coverage": coverage,
        "status": status,

        "sections": [
            {
                "name": s.section,
                "status": s.status,
                "reason": s.skip_reason if s.status == "skipped" else None,
                "notes": s.skip_notes,
            }
            for s in sections
        ]
    }


def aggregate_compliance(reports):
    compliant = 0
    incomplete = 0
    non_compliant = 0

    for r in reports:
        status = get_report_compliance(r)["status"]

        if status == "COMPLIANT":
            compliant += 1
        elif status == "INCOMPLETE":
            incomplete += 1
        else:
            non_compliant += 1

    total = len(reports)

    return {
        "compliant": compliant,
        "incomplete": incomplete,
        "non_compliant": non_compliant,
        "compliance_rate": round((compliant / total) * 100, 2) if total else 0,
    }
