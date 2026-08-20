# apps/people/services/attendance.py
from django.db.models import Sum
from django.db.models.functions import Coalesce
from apps.people.models import Attendance
from .attendance_totals import SUNDAY_SCHOOL_START_DATE, attendance_headcount
from apps.people.models import SundaySchoolAttendance

NUMERIC_FIELDS = [
    "total_adults",
    "total_visitors",
    "total_new_converts",
    "total_baptisms",
    "total_altar_call",
    "online_viewers",
    "volunteers_on_duty",
    "total_leaders_present",
]

def get_monthly_summary(assembly, year, month):
    queryset = Attendance.objects.filter(
        assembly=assembly,
        timestamp__year=year,
        timestamp__month=month
    )

    aggregates = {field: Coalesce(Sum(field), 0) for field in NUMERIC_FIELDS}

    totals = queryset.aggregate(**aggregates)
    legacy_children = sum(
        row.children or 0
        for row in queryset
        if row.collection_schema == Attendance.CollectionSchema.LEGACY
    )
    sunday_children = SundaySchoolAttendance.objects.filter(
        assembly=assembly,
        service_date__year=year,
        service_date__month=month,
        service_date__gte=SUNDAY_SCHOOL_START_DATE,
        is_deleted=False,
    ).aggregate(total=Sum("boys") + Sum("girls"))["total"] or 0
    totals["total_children"] = legacy_children + sunday_children
    totals["headcount"] = sum(attendance_headcount(row) for row in queryset) + sunday_children

    return totals
