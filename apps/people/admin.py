from django.contrib import admin
from apps.people.models import Attendance, ChurchAttendance, Homecell, HCAttendance, Kindred, Member, AttendanceRegister, Testimony

admin.site.register(Attendance)
admin.site.register(ChurchAttendance)
admin.site.register(Homecell)
admin.site.register(HCAttendance)
admin.site.register(Kindred)
admin.site.register(Member)
admin.site.register(AttendanceRegister)
admin.site.register(Testimony)

