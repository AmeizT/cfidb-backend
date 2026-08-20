import django_filters

from apps.people.models import SundaySchoolAttendance
from apps.shared.filters.soft_delete_filter import SoftDeleteFilterSet


class SundaySchoolAttendanceFilter(SoftDeleteFilterSet):
    service_date = django_filters.DateFromToRangeFilter()

    class Meta:
        model = SundaySchoolAttendance
        fields = [
            "is_deleted",
            "status",
            "class_name",
            "teacher",
            "assembly",
            "service_date",
        ]
