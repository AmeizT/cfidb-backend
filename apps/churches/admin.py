from django.contrib import admin
from apps.churches.models import Church, Zone, ZoneName

admin.site.register(Church)
admin.site.register(Zone)
admin.site.register(ZoneName)

