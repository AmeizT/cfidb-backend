# apps/reports/models/compliance.py

from django.db import models
from django.utils import timezone
from apps.churches.models import Church
from apps.reports.models import AssemblyReport

class AssemblyCompliance(models.Model):
    class Status(models.TextChoices):
        COMPLIANT = "COMPLIANT", "Compliant"
        LATE = "LATE", "Late"
        NOT_SUBMITTED = "NOT_SUBMITTED", "Not Submitted"
        NOT_FINALIZED = "NOT_FINALIZED", "Not Finalized"
        MISSING_FROM_ZONE = "MISSING_FROM_ZONE", "Missing From Zone"
        HISTORICAL_NOT_REQUIRED = "HISTORICAL_NOT_REQUIRED", "Historical - Not Required"

    assembly = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        related_name="compliance_records"
    )

    zone = models.ForeignKey(
        "churches.Zone",
        on_delete=models.CASCADE,
        related_name="assembly_compliance"
    )

    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()

    report = models.ForeignKey(
        AssemblyReport,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices
    )

    evaluated_at = models.DateTimeField(auto_now=True)
    compliance_score = models.FloatField(default=0)
    timeliness_score = models.FloatField(default=0)
    consistency_score = models.FloatField(default=0)

    overall_score = models.FloatField(default=0)

    trend = models.CharField(max_length=20, default="stable")
    risk_level = models.CharField(max_length=20, default="low")

    class Meta:
        unique_together = ("assembly", "year", "month")
        ordering = ["-year", "-month"]


class ZoneCompliance(models.Model):
    zone = models.ForeignKey(
        "churches.Zone",
        on_delete=models.CASCADE,
        related_name="compliance_records"
    )

    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()

    total_assemblies = models.PositiveIntegerField(default=0)
    compliant_assemblies = models.PositiveIntegerField(default=0)
    compliance_rate = models.FloatField(default=0)

    evaluated_at = models.DateTimeField(auto_now=True)

    compliance_score = models.FloatField(default=0)
    timeliness_score = models.FloatField(default=0)
    consistency_score = models.FloatField(default=0)

    overall_score = models.FloatField(default=0)

    trend = models.CharField(max_length=20, default="stable")
    risk_level = models.CharField(max_length=20, default="low")

    class Meta:
        unique_together = ("zone", "year", "month")
        ordering = ["-year", "-month"]
