from django.contrib import admin
from apps.church.models import (
    Attendance,
    Church,
    Demographics,
    Member
)

admin.site.register(Attendance)
admin.site.register(Church)
admin.site.register(Demographics)
admin.site.register(Member)
