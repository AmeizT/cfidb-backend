import calendar

from apps.churches.models import Church
from apps.reports.models import AssemblyReport


def build_zone_compliance_timeline(zone, year):

    assemblies = Church.objects.filter(
        zone=zone
    )

    result = []

    for assembly in assemblies:

        monthly = {}

        for month in range(1, 13):

            report = AssemblyReport.objects.filter(
                assembly=assembly,
                period_start__year=year,
                period_start__month=month,
            ).first()

            if report:
                monthly[
                    calendar.month_abbr[month]
                ] = "COMPLIANT"
            else:
                monthly[
                    calendar.month_abbr[month]
                ] = "NOT_SUBMITTED"

        result.append({
            "assembly_id": assembly.id,
            "assembly_name": assembly.name,
            "monthly": monthly,
        })

    return {
        "zone": {
            "id": zone.id,
            "name": zone.name,
        },
        "year": year,
        "assemblies": result,
    }