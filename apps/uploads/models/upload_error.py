from django.db import models
from apps.uploads.models.upload_session import UploadSession

class UploadError(models.Model):
    session = models.ForeignKey(UploadSession, related_name="errors", on_delete=models.CASCADE)
    row_number = models.IntegerField()
    error_message = models.TextField()
    raw_data = models.JSONField()