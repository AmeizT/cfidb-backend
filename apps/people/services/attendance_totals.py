from django.db.models import Sum

from apps.people.constants import SUNDAY_SCHOOL_START_DATE


def _number(value):
    return int(value or 0)


def attendance_headcount(record) -> int:
    """Apply the collection schema that was active when the row was recorded."""
    if record.collection_schema == record.CollectionSchema.LEGACY:
        return (
            _number(record.total_adults)
            + _number(record.children)
            + _number(record.online_viewers)
        )
    return (
        _number(record.total_adults)
        + _number(record.total_visitors)
        + _number(record.online_viewers)
    )


def calculate_report_attendance(report) -> dict[str, int]:
    from apps.people.models import Attendance, SundaySchoolAttendance

    attendances = list(Attendance.objects.filter(report=report, is_deleted=False))
    legacy_children = sum(
        _number(row.children)
        for row in attendances
        if row.collection_schema == Attendance.CollectionSchema.LEGACY
    )
    sunday_children = (
        SundaySchoolAttendance.objects.filter(
            report=report,
            service_date__gte=SUNDAY_SCHOOL_START_DATE,
            is_deleted=False,
        ).aggregate(total=Sum("boys") + Sum("girls"))["total"]
        or 0
    )
    return {
        "total_adults": sum(_number(row.total_adults) for row in attendances),
        "total_children": legacy_children + sunday_children,
        "total_visitors": sum(_number(row.total_visitors) for row in attendances),
        "total_new_converts": sum(_number(row.total_new_converts) for row in attendances),
        "total_altar_call": sum(_number(row.total_altar_call) for row in attendances),
        "total_baptisms": sum(_number(row.total_baptisms) for row in attendances),
        "total_online_viewers": sum(_number(row.online_viewers) for row in attendances),
        "headcount": sum(attendance_headcount(row) for row in attendances) + sunday_children,
    }
