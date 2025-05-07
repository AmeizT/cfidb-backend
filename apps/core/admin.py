from django.contrib import admin
from apps.core.models import Blog, Documentation, TermsAndConditions

admin.site.register(TermsAndConditions)
admin.site.register(Blog)
admin.site.register(Documentation)
