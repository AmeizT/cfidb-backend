from django.contrib import admin
from apps.uploads.models import UploadError, UploadSession

admin.site.register(UploadError)
admin.site.register(UploadSession)


