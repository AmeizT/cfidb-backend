from django.contrib import admin
from apps.core.models import Blog, Documentation, TOS

admin.site.register(TOS)
admin.site.register(Blog)
admin.site.register(Documentation)
