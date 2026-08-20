from django.db import models
from apps.churches.models import Church
from apps.bookkeeper.models import FinancialBase
from apps.bookkeeper.utils import bank_statement_path
from apps.reports.mixins.audit import AuditLogMixin
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from apps.bookkeeper.category_matching import normalize_financial_category_name

class RevenueCategory(models.Model):
    assembly = models.ForeignKey(Church, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255)
    normalized_name = models.CharField(max_length=255, default="", editable=False)
    is_standard = models.BooleanField(default=False)
    reporting_group = models.CharField(max_length=255, blank=True)
    standard_category = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True,
        related_name="revenue_aliases",
    )
    needs_review = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_revenue_categories",
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["assembly", "normalized_name"],
                name="unique_normalized_revenue_category_per_assembly",
            ),
            models.UniqueConstraint(
                fields=["normalized_name"],
                condition=models.Q(is_standard=True, assembly__isnull=True),
                name="unique_standard_revenue_category_name",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(is_standard=True, assembly__isnull=True)
                    | models.Q(is_standard=False, assembly__isnull=False)
                ),
                name="valid_revenue_category_scope",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(is_standard=True)
                    | models.Q(standard_category__isnull=False)
                    | models.Q(needs_review=True)
                ),
                name="revenue_category_mapping_or_review",
            ),
        ]

    def clean(self):
        if self.is_standard and self.assembly_id:
            raise ValidationError("Standard revenue categories cannot belong to an assembly.")
        if not self.is_standard and not self.assembly_id:
            raise ValidationError("Custom revenue categories must belong to an assembly.")
        if self.standard_category_id and not self.standard_category.is_standard:
            raise ValidationError({"standard_category": "Mapping must use a standard revenue category."})
        if not self.is_standard and not self.standard_category_id and not self.needs_review:
            raise ValidationError({"standard_category": "Choose a standard category or mark this category for review."})

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        self.normalized_name = normalize_financial_category_name(self.name)
        if self.is_standard:
            self.standard_category = None
            self.needs_review = False
        elif not self.standard_category_id:
            self.needs_review = True
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({'Standard' if self.is_standard else 'Custom'})"


class Revenue(AuditLogMixin, FinancialBase):
    """
    Revenue linked to a category. Categories can be standard or user-created.
    """

    AUDIT_TRANSACTION_TYPE = "Revenue"

    category = models.ForeignKey(
        RevenueCategory,
        on_delete=models.PROTECT,
        related_name="revenues"
    )

    statement = models.FileField(
        upload_to=bank_statement_path,
        blank=True,
        null=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["report", "category"],
                name="unique_report_category"
            )
        ]
        indexes = [
            models.Index(fields=["assembly"]),
            models.Index(fields=["report"]),
        ]

    # ----------------------------
    # Validation
    # ----------------------------
    def clean(self):
        super().clean()
        if self.report and self.assembly:
            if self.report.assembly != self.assembly:
                raise ValidationError("Assembly must match the report's assembly.")

    # ----------------------------
    # Save Logic
    # ----------------------------
    def save(self, *args, **kwargs):
        self.assign_report()
        self.validate_period()
        self.full_clean()  # <-- critical
        super().save(*args, **kwargs)
        self.update_report_totals()

    # ----------------------------
    # Audit Snapshot
    # ----------------------------
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.pk:
            self._old_data = {
                "amount": str(self.amount),
                "notes": self.notes,
                "category": (
                    self.category.name
                    if self.category_id else None
                ),
            }
        else:
            self._old_data = None

    # ----------------------------
    # String Representation
    # ----------------------------
    def __str__(self):
        return f"{self.assembly.name} - {self.category.name} - {self.amount}"
