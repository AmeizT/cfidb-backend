from django.contrib import admin
from apps.office.models import Document, Meeting, Minutes

admin.site.register(Document)
admin.site.register(Meeting)
admin.site.register(Minutes)
