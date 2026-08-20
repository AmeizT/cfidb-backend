from apps.reports.services.lifecycle import ensure_report


def create_report(*, assembly, period_start, period_end, created_by=None):
    """
    Central report creation entry point.
    Ensures compliance structure is initialized correctly.
    """

    return ensure_report(
        assembly=assembly,
        period_start=period_start,
        period_end=period_end,
        actor=created_by,
    )
