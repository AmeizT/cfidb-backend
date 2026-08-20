from apps.reports.models import ReportSectionStatus


STRICT_SECTIONS = [value for value, _label in ReportSectionStatus.Section.choices]


def create_default_sections(report, created_by=None):
    """
    Create ONLY strict monthly compliance sections.
    Optional sections are not created.
    """

    sections = []

    for section in STRICT_SECTIONS:
        sections.append(
            ReportSectionStatus(
                report=report,
                section=section,
                status=ReportSectionStatus.Status.NOT_STARTED,
            )
        )

    return ReportSectionStatus.objects.bulk_create(sections, ignore_conflicts=True)
