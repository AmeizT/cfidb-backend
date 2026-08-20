import calendar
from datetime import date, datetime

from django.db import models # type: ignore
from django.db.models import Sum, Max, F
from django.utils import timezone
from django.core.exceptions import PermissionDenied, ValidationError
from apps.users.models import User


REPORT_DUE_DAY = 5


class AssemblyReport(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_PROGRESS = "in_progress", "In Progress"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        ARCHIVED = "archived", "Archived"

    assembly = models.ForeignKey("churches.Church", on_delete=models.CASCADE)
    period_start = models.DateField(db_index=True)
    period_end = models.DateField(db_index=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    submitted_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="submitted_reports"
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    editable_until = models.DateTimeField(null=True, blank=True)
    current_version = models.ForeignKey(
        "reports.ReportVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_for_reports",
    )
    amendment_reason = models.TextField(blank=True, null=True)
    amendment_started_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="started_report_amendments",
    )
    amendment_started_at = models.DateTimeField(null=True, blank=True)
    amendment_base_version = models.ForeignKey(
        "reports.ReportVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="based_amendments",
    )
    is_late = models.BooleanField(default=False, db_index=True)
    days_late = models.PositiveIntegerField(null=True, blank=True)
    is_historical_backfill = models.BooleanField(default=False, db_index=True)

    attendance_total = models.IntegerField(default=0)
    income_total = models.DecimalField(max_digits=14, decimal_places=2, default=0) # type: ignore
    expense_total = models.DecimalField(max_digits=14, decimal_places=2, default=0) # type: ignore
    tithe_total = models.DecimalField(max_digits=14, decimal_places=2, default=0) # type: ignore
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0) # type: ignore
    members_total = models.IntegerField(default=0)

    total_adults = models.PositiveIntegerField(default=0)
    total_children = models.PositiveIntegerField(default=0)
    total_guests = models.PositiveIntegerField(default=0)
    total_visitors = models.PositiveIntegerField(default=0)
    total_new_converts = models.PositiveIntegerField(default=0)
    total_altar_call = models.PositiveIntegerField(default=0)
    total_baptisms = models.PositiveIntegerField(default=0)
    total_online_viewers = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def submitted_sections(self):
        return self.sections.filter(status="completed").count()

    @property
    def skipped_sections(self):
        return self.sections.filter(status="skipped").count()

    @property
    def pending_sections(self):
        return self.sections.filter(status__in=["not_started", "in_progress"]).count()

    @property
    def due_date(self) -> date:
        """
        Reports are due on REPORT_DUE_DAY of the month after period_end.
        """
        year = self.period_end.year
        month = self.period_end.month + 1

        if month > 12:
            month = 1
            year += 1

        day = min(REPORT_DUE_DAY, calendar.monthrange(year, month)[1])
        return date(year, month, day)

    class Meta:
        ordering = ["-period_start"]
        constraints = [
            models.UniqueConstraint(fields=["assembly", "period_start", "period_end"], name="unique_assembly_report_period")
        ]

    def __str__(self):
        return f"{self.assembly.name} - {self.period_start.strftime('%b %Y')} ({self.status})"

    def calculate_totals(self):
        from apps.bookkeeper.models import (
            Expenditure,
            Overhead,
            RemittancePayment,
            Revenue,
            Tithe,
        )
        # --- Revenue (Revenue model) ---
        revenue = Revenue.objects.filter(report=self).aggregate(
            total=Sum("amount")
        )["total"] or 0

        # --- Tithes ---
        tithes = Tithe.objects.filter(report=self).aggregate(
            total=Sum("amount")
        )["total"] or 0

        self.tithe_total = tithes

        # revenue_total (stored in income_total for now)
        self.income_total = revenue + tithes

        # --- Expenses ---
        overheads = Overhead.objects.filter(report=self).aggregate(
            total=Sum("amount")
        )["total"] or 0

        variable_expenses = Expenditure.objects.filter(report=self).aggregate(
            total=Sum(F("price") * F("quantity"))
        )["total"] or 0

        verified_remittances = RemittancePayment.objects.filter(
            report=self,
            status=RemittancePayment.Status.VERIFIED,
        ).aggregate(total=Sum("amount_paid"))["total"] or 0

        self.expense_total = overheads + variable_expenses + verified_remittances

        # --- Balance ---
        self.balance = self.income_total - self.expense_total

    def recalculate_attendance_totals(self):
        from apps.people.services.attendance_totals import calculate_report_attendance

        totals = calculate_report_attendance(self)
        self.total_adults = totals["total_adults"]
        self.total_children = totals["total_children"]
        self.total_visitors = totals["total_visitors"]
        self.total_guests = self.total_visitors
        self.total_new_converts = totals["total_new_converts"]
        self.total_altar_call = totals["total_altar_call"]
        self.total_baptisms = totals["total_baptisms"]
        self.total_online_viewers = totals["total_online_viewers"]
        self.attendance_total = totals["headcount"]

        self.save(update_fields=[
            "total_adults",
            "total_children",
            "total_guests",
            "total_visitors",
            "total_new_converts",
            "total_altar_call",
            "total_baptisms",
            "total_online_viewers",
            "attendance_total",  
        ])

    def _compute_lateness(self, at: datetime) -> tuple[bool, int | None]:
        submitted_date = timezone.localtime(at).date()

        if submitted_date <= self.due_date:
            return False, None

        return True, (submitted_date - self.due_date).days

    def finalize(self, user=None):
        from apps.reports.services.lifecycle import submit_report

        return submit_report(report=self, actor=user, declaration_confirmed=True)

    def reopen(self, user=None, reason="Authorised correction"):
        from apps.reports.services.lifecycle import start_amendment

        return start_amendment(report=self, actor=user, reason=reason, authorised=True)

    # --- Rejection Workflow ---
    def reject(self, user, comment):
        if self.status not in [self.Status.SUBMITTED]:
            raise ValidationError("Only submitted reports can be rejected.")

        if not user.has_role("zone_reviewer") and not user.has_role("region_approver"):
            raise PermissionDenied("You do not have permission to reject this report.")

        from reports.models import ReportRejection

        last_revision = self.rejections.aggregate(max_rev=Max("revision_number"))["max_rev"] or 0 # type: ignore

        ReportRejection.objects.create(
            report=self,
            rejected_by=user,
            comment=comment,
            revision_number=last_revision + 1
        )

        # Reset to DRAFT
        self.status = self.Status.DRAFT
        self.submitted_by = None
        self.submitted_at = None
        self.save()


    def get_compliance(self):
        from apps.reports.services.compliance_calculator import calculate_report_compliance
        return calculate_report_compliance(self)

    def get_report_status(self) -> str:
        """
        Section-derived report status for compliance dashboards.
        This is separate from the workflow status stored in self.status.
        """
        from apps.reports.services.lifecycle import get_report_state

        return get_report_state(self).status
