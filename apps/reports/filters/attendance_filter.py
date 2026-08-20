from apps.people.models.attendance import Attendance
from apps.shared.filters.soft_delete_filter import SoftDeleteFilterSet

class AttendanceFilter(SoftDeleteFilterSet):
    class Meta:
        model = Attendance
        fields = ["is_deleted"]