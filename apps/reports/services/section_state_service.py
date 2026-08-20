from apps.reports.services.lifecycle import set_section_status


def update_section_status(
    *, section_obj, status, skip_reason=None, skip_notes=None, updated_by=None,
    no_activity_note=None,
):
    """Compatibility wrapper around the canonical lifecycle transition service."""
    return set_section_status(
        report=section_obj.report,
        section_key=section_obj.section,
        status=status,
        actor=updated_by,
        skip_reason_code=skip_reason,
        skip_reason_detail=skip_notes,
        no_activity_note=no_activity_note,
    )
