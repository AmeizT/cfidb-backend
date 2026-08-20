# apps/bookkeeper/models/base.py
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from apps.core.middleware.current_user import get_current_user
from apps.reports.mixins.audit import AuditLogMixin


class FinancialBase(models.Model):
    """
    Abstract base class for all financial models (Revenue, Overhead, Tithe).
    Handles:
    - Assembly assignment
    - Auto-report assignment
    - Period validation
    - Report totals update
    - Audit logging via AuditLogMixin
    """

    assembly = models.ForeignKey(
        "churches.Church",
        on_delete=models.CASCADE
    )

    report = models.ForeignKey(
        "reports.AssemblyReport",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="%(class)s_set"
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00")
    )

    timestamp = models.DateField(db_index=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["assembly", "timestamp"]),
        ]

    # -------------------------------------------------
    # REPORT ASSIGNMENT (Auto-create if missing)
    # -------------------------------------------------
    def assign_report(self):
        if self.report:
            return
        from apps.reports.services.lifecycle import ensure_report

        self.report = ensure_report(
            assembly=self.assembly,
            period_start=self.timestamp,
            actor=get_current_user(),
        )

    # -------------------------------------------------
    # VALIDATIONS
    # -------------------------------------------------
    def validate_period(self):
        if self.report and not (
            self.report.period_start <= self.timestamp <= self.report.period_end
        ):
            raise ValidationError("Transaction date outside report period.")

    def clean(self):
        if self.report and self.report.status != self.report.Status.DRAFT:
            raise ValidationError(
                "Cannot modify transaction under finalized/reviewed/approved report."
            )

    # -------------------------------------------------
    # REPORT TOTAL UPDATE
    # -------------------------------------------------
    def update_report_totals(self):
        if self.report and self.report.status == self.report.Status.DRAFT:
            self.report.calculate_totals()
            self.report.save(update_fields=None)

    # -------------------------------------------------
    # SAVE (AUTO TOTAL + AUTO AUDIT)
    # -------------------------------------------------
    def save(self, *args, **kwargs):
        user = get_current_user()
        is_new = self.pk is None
        old_amount = None
        old_data = None

        if not is_new:
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                old_amount = old_instance.amount
                if hasattr(self, "_capture_old_data"):
                    old_data = old_instance._capture_old_data()
            except self.__class__.DoesNotExist:
                pass

        # Auto-assign report
        self.assign_report()

        if self.report and self.report.status != self.report.Status.DRAFT:
            raise ValidationError(
                "Start an amendment before changing source records in a submitted report."
            )

        # Validate timestamp against report period
        self.validate_period()

        # Save record
        super().save(*args, **kwargs)

        # Update report totals if new or amount changed
        if is_new or old_amount != self.amount:
            self.update_report_totals()

        # Automatic audit logging (skip if user is anonymous or None)
        if hasattr(self, "log_audit") and user and getattr(user, "is_authenticated", False):
            action = "Created" if is_new else "Updated"
            description = f"{self.__class__.__name__} of {self.amount} on {self.timestamp}"
            self.log_audit(user=user, action=action, old_data=old_data, description=description)

    def delete(self, *args, **kwargs):
        if self.report and self.report.status != self.report.Status.DRAFT:
            raise ValidationError(
                "Start an amendment before deleting source records from a submitted report."
            )
        return super().delete(*args, **kwargs)
