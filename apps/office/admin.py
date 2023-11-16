from django.contrib import admin
from apps.office.models import Circular, Meeting, Minutes

admin.site.register(Circular)
admin.site.register(Meeting)
admin.site.register(Minutes)
