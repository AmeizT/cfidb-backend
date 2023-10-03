from django.contrib import admin
from apps.people.models import Attendance, Homecell, HCAttendance, Kin, Member, Testimony

admin.site.register(Attendance)
admin.site.register(Homecell)
admin.site.register(HCAttendance)
admin.site.register(Kin)
admin.site.register(Member)
admin.site.register(Testimony)

