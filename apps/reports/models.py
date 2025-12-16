from django.db import models
from django.utils import timezone
from apps.people.models import Attendance
from django.utils import timezone
from apps.bookkeeper.models import Tithe, Income, Expenditure

class UnifiedReport(models.Model):
    church = models.ForeignKey("churches.Church", on_delete=models.CASCADE)
    finalized_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finalized_reports"
    )
    period_start = models.DateField()
    period_end = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=[("draft", "Draft"), ("finalized", "Finalized")],
        default="draft",
    )
    finalized_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def finalize(self):
        """
        Validates required data and finalizes report.
        """
        errors = []

        if not Attendance.objects.filter(report=self, category="SUNDAY").exists():
            errors.append("Sunday attendance is required before finalizing.")

        if not self.tithe_set.exists():
            errors.append("At least one tithe record is required before finalizing.")

        if not self.income_set.exists():
            errors.append("At least one income record is required before finalizing.")

        if not self.expenditure_set.exists():
            errors.append("At least one expenditure record is required before finalizing.")

        if errors:
            raise ValueError(errors)

        self.status = "finalized"
        self.finalized_at = timezone.now()
        self.save()

    def reopen(self):
        self.status = "draft"
        self.finalized_at = None
        self.save()

    def __str__(self):
        return f"{self.church} - {self.period_start} to {self.period_end} ({self.status})"