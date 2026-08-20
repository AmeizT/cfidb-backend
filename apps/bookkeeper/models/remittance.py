from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from apps.bookkeeper.historical import REMITTANCE_RATE
from apps.bookkeeper.utils import remittance_receipt_path


class RemittanceObligation(models.Model):
    """The amount due for an assembly/month; it is not itself an expense."""

    assembly = models.ForeignKey(
        "churches.Church", on_delete=models.PROTECT, related_name="remittance_obligations"
    )
    report = models.OneToOneField(
        "reports.AssemblyReport",
        on_delete=models.PROTECT,
        related_name="remittance_obligation",
    )
    period_start = models.DateField(db_index=True)
    tithe_total_snapshot = models.DecimalField(max_digits=14, decimal_places=2)
    rate = models.DecimalField(
        max_digits=6, decimal_places=5, default=Decimal(REMITTANCE_RATE)
    )
    amount_due = models.DecimalField(max_digits=14, decimal_places=2)
    source_fixed_expenditure = models.OneToOneField(
        "bookkeeper.FixedExpenditure",
        on_delete=models.PROTECT,
        related_name="migrated_remittance_obligation",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["period_start", "assembly_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["assembly", "period_start"],
                name="unique_remittance_obligation_month",
            )
        ]

    @property
    def verified_paid(self):
        return self.payments.filter(
            status=RemittancePayment.Status.VERIFIED
        ).aggregate(total=Sum("amount_paid"))["total"] or Decimal("0.00")

    @property
    def outstanding_amount(self):
        return max(self.amount_due - self.verified_paid, Decimal("0.00"))

    def clean(self):
        errors = {}
        if self.report_id:
            if self.report.assembly_id != self.assembly_id:
                errors["report"] = "Obligation report belongs to another assembly."
            if self.period_start != self.report.period_start:
                errors["period_start"] = "Obligation month must match its report."
        if self.period_start and self.period_start.day != 1:
            errors["period_start"] = "Obligation period must be the first day of a month."
        expected = (self.tithe_total_snapshot * self.rate).quantize(Decimal("0.01"))
        if self.amount_due != expected:
            errors["amount_due"] = f"Expected {expected} from the tithe snapshot and rate."
        if errors:
            raise ValidationError(errors)


class RemittancePayment(models.Model):
    """A payment claim; only verified rows are actual cash expenses."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    obligation = models.ForeignKey(
        RemittanceObligation, on_delete=models.PROTECT, related_name="payments"
    )
    report = models.ForeignKey(
        "reports.AssemblyReport",
        on_delete=models.PROTECT,
        related_name="remittance_payments",
        help_text="Cash-reporting month for the actual payment.",
    )
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2)
    payment_date = models.DateField()
    receipt = models.FileField(upload_to=remittance_receipt_path)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="submitted_remittance_payments",
        null=True,
        blank=True,
    )
    submitted_at = models.DateTimeField(default=timezone.now)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="verified_remittance_payments",
        null=True,
        blank=True,
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    source_fixed_expenditure = models.ForeignKey(
        "bookkeeper.FixedExpenditure",
        on_delete=models.PROTECT,
        related_name="migrated_remittance_payments",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["payment_date", "id"]

    def clean(self):
        errors = {}
        if self.amount_paid is not None and self.amount_paid <= 0:
            errors["amount_paid"] = "Payment amount must be greater than zero."
        if self.report_id and self.obligation_id:
            if self.report.assembly_id != self.obligation.assembly_id:
                errors["report"] = "Payment report belongs to another assembly."
            if not self.report.period_start <= self.payment_date <= self.report.period_end:
                errors["payment_date"] = "Payment date is outside its cash-reporting month."
        if self.status == self.Status.VERIFIED:
            if not self.verified_by_id or not self.verified_at:
                errors["status"] = "Verified payments require reviewer and verification time."
            if not self.receipt:
                errors["receipt"] = "Verified payments require a receipt."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        result = super().save(*args, **kwargs)
        if self.report.status == self.report.Status.DRAFT:
            self.report.calculate_totals()
            self.report.save(update_fields=["expense_total", "balance", "income_total", "tithe_total"])
        return result
