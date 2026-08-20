from django.contrib import admin
from apps.people.models import (
    Attendance, 
    Homecell,  
    JuniorMember, 
    Member,
    Ministry,
    Position,   
    AssemblyMembership,
    FormerMember,
    Household,
    HouseholdMember,
    MemberTransferRequest,
    SundaySchoolAttendance,
    Tally,
)

admin.site.register(Attendance)
admin.site.register(SundaySchoolAttendance)
admin.site.register(Homecell)
admin.site.register(JuniorMember)
admin.site.register(Member)
admin.site.register(Tally)
admin.site.register(Ministry)
admin.site.register(Position)
admin.site.register(AssemblyMembership)
admin.site.register(MemberTransferRequest)
admin.site.register(FormerMember)
admin.site.register(Household)
admin.site.register(HouseholdMember)
