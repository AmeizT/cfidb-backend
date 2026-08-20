from django.db.models import Max
from django.db import models, transaction

class ReportRejection(models.Model):
    report = models.ForeignKey(
        "reports.AssemblyReport",
        on_delete=models.CASCADE,
        related_name="rejections"
    )
    rejected_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True
    )
    comment = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    revision_number = models.PositiveIntegerField(editable=False)

    class Meta:
        ordering = ["-timestamp"]
        unique_together = ("report", "revision_number")

    def save(self, *args, **kwargs):
        if not self.pk:  # Only set on creation
            with transaction.atomic():
                last_revision = (
                    ReportRejection.objects
                    .select_for_update()
                    .filter(report=self.report)
                    .aggregate(max_rev=Max("revision_number"))["max_rev"]
                )
                self.revision_number = (last_revision or 0) + 1

                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"Revision {self.revision_number} - {self.rejected_by}"