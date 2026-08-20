from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ImmutableSnapshotModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Submitted report snapshots are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Submitted report snapshots cannot be deleted.")


class ReportVersion(ImmutableSnapshotModel):
    report = models.ForeignKey(
        "reports.AssemblyReport",
        on_delete=models.PROTECT,
        related_name="versions",
    )
    version_number = models.PositiveIntegerField()
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="submitted_report_versions",
    )
    submitted_at = models.DateTimeField()
    editable_until = models.DateTimeField()
    declaration_confirmed = models.BooleanField(default=False)
    validation_findings = models.JSONField(default=list, blank=True)
    attendance_total = models.PositiveIntegerField(default=0)
    sunday_school_attendance_total = models.PositiveIntegerField(default=0)
    tithe_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    revenue_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    operating_expense_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    activity_other_expense_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    net_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["report", "version_number"],
                name="unique_report_version_number",
            )
        ]

    def __str__(self):
        return f"{self.report} v{self.version_number}"


class ReportSectionSnapshot(ImmutableSnapshotModel):
    version = models.ForeignKey(
        ReportVersion,
        on_delete=models.PROTECT,
        related_name="section_snapshots",
    )
    section = models.CharField(max_length=50)
    label = models.CharField(max_length=100)
    status = models.CharField(max_length=20)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    record_count = models.PositiveIntegerField(default=0)
    breakdown = models.JSONField(default=list, blank=True)
    source_references = models.JSONField(default=dict, blank=True)
    skip_reason_code = models.CharField(max_length=40, blank=True, null=True)
    skip_reason_detail = models.TextField(blank=True, null=True)
    skipped_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_skipped_section_snapshots",
    )
    skipped_at = models.DateTimeField(null=True, blank=True)
    no_activity_confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_no_activity_section_snapshots",
    )
    no_activity_confirmed_at = models.DateTimeField(null=True, blank=True)
    no_activity_note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["version", "section"],
                name="unique_report_version_section_snapshot",
            )
        ]


class ReportReopeningRequest(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    report = models.ForeignKey(
        "reports.AssemblyReport",
        on_delete=models.CASCADE,
        related_name="reopening_requests",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="report_reopening_requests",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    request_reason = models.TextField()
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_report_reopening_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-requested_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["report"],
                condition=models.Q(status="requested"),
                name="unique_active_report_reopening_request",
            )
        ]
