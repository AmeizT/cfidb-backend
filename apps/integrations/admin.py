from django.contrib import admin
from apps.integrations.models import Integration, IntegrationProvider

admin.site.register(Integration)
admin.site.register(IntegrationProvider)
