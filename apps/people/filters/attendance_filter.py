from apps.people.models.attendance import Attendance
from apps.shared.filters.soft_delete_filter import SoftDeleteFilterSet
import django_filters

class AttendanceFilter(SoftDeleteFilterSet):
    year = django_filters.NumberFilter(field_name="timestamp", lookup_expr="year")
    month = django_filters.NumberFilter(field_name="timestamp", lookup_expr="month")
    class Meta:
        model = Attendance
        fields = ["is_deleted", "year", "month", "report", "service_type"]
