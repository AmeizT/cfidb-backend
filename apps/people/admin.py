from django.contrib import admin
from apps.people.models import (
    Attendance, 
    Homecell,  
    Kindred, 
    Member,   
    Tally
)

admin.site.register(Attendance)
admin.site.register(Homecell)
admin.site.register(Kindred)
admin.site.register(Member)
admin.site.register(Tally)
