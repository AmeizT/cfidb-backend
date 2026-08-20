from django.db import models
from django.utils import timezone


class ComplianceAlert(models.Model):

    class Level(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        RESOLVED = "resolved", "Resolved"

    class Type(models.TextChoices):
        RISK = "risk", "Risk Warning"
        TREND = "trend", "Trend Alert"
        MISSING = "missing", "Missing Data"
        SKIP_PATTERN = "skip_pattern", "Repeated Skipping"

    assembly = models.ForeignKey(
        "churches.Church",
        on_delete=models.CASCADE,
        related_name="alerts"
    )

    zone = models.ForeignKey(
        "churches.Zone",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    type = models.CharField(max_length=30, choices=Type.choices)

    level = models.CharField(max_length=20, choices=Level.choices)

    title = models.CharField(max_length=255)
    message = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN
    )

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def acknowledge(self):
        self.status = self.Status.ACKNOWLEDGED
        self.acknowledged_at = timezone.now()
        self.save()

    def resolve(self):
        self.status = self.Status.RESOLVED
        self.resolved_at = timezone.now()
        self.save()