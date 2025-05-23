from django.contrib import admin
from apps.people.models import (
    Attendance, 
    Homecell,  
    JuniorMember, 
    Member,
    Ministry,
    Position,   
    Tally
)

admin.site.register(Attendance)
admin.site.register(Homecell)
admin.site.register(JuniorMember)
admin.site.register(Member)
admin.site.register(Tally)
admin.site.register(Ministry)
admin.site.register(Position)
