from django.db import models

from apps.people.models import SundaySchoolAttendance


def get_children_count(assembly, date):
    return (
        SundaySchoolAttendance.objects
        .filter(
            assembly=assembly,
            service_date=date,
            is_deleted=False,
        )
        .aggregate(
            total=models.Sum(models.F("boys") + models.F("girls"))
        )["total"]
        or 0
    )


def get_children_counts_by_date(assembly, start_date, end_date):
    rows = (
        SundaySchoolAttendance.objects
        .filter(
            assembly=assembly,
            service_date__gte=start_date,
            service_date__lte=end_date,
            is_deleted=False,
        )
        .values("service_date")
        .annotate(total=models.Sum(models.F("boys") + models.F("girls")))
    )

    return {
        row["service_date"]: row["total"] or 0
        for row in rows
    }
