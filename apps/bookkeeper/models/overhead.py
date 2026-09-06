from django.db import models
from apps.churches.models import Church
from apps.bookkeeper.models.base import FinancialBase
from apps.reports.mixins.audit import AuditLogMixin
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from apps.bookkeeper.category_matching import normalize_financial_category_name

class OverheadType(models.Model):
    name = models.CharField(max_length=100)
    normalized_name = models.CharField(max_length=100, default="", editable=False)
    is_global = models.BooleanField(default=False)
    is_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    reporting_group = models.CharField(max_length=255, blank=True)
    standard_category = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True,
        related_name="overhead_aliases",
    )
    needs_review = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_overhead_types",
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    assembly = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="overhead_types"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["assembly", "normalized_name"],
                name="unique_normalized_overhead_type_per_assembly",
            ),
            models.UniqueConstraint(
                fields=["normalized_name"],
                condition=models.Q(is_global=True, assembly__isnull=True),
                name="unique_standard_overhead_type_name",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(is_global=True, assembly__isnull=True)
                    | models.Q(is_global=False, assembly__isnull=False)
                ),
                name="valid_overhead_type_scope",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(is_global=True)
                    | models.Q(standard_category__isnull=False)
                    | models.Q(needs_review=True)
                ),
                name="overhead_type_mapping_or_review",
            ),
        ]

    def clean(self):
        if self.is_global and self.assembly:
            raise ValidationError("Global types cannot belong to an assembly.")

        if not self.is_global and not self.assembly:
            raise ValidationError("Assembly-specific types must belong to an assembly.")
        if self.standard_category_id and not self.standard_category.is_global:
            raise ValidationError({"standard_category": "Mapping must use a standard overhead category."})
        if not self.is_global and not self.standard_category_id and not self.needs_review:
            raise ValidationError({"standard_category": "Choose a standard category or mark this type for review."})

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        self.normalized_name = normalize_financial_category_name(self.name)
        if self.is_global:
            self.standard_category = None
            self.needs_review = False
        elif not self.standard_category_id:
            self.needs_review = True
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Overhead(AuditLogMixin, FinancialBase):
    AUDIT_TRANSACTION_TYPE = "Overhead"

    overhead_type = models.ForeignKey(
        OverheadType,
        on_delete=models.PROTECT,
        related_name="overheads"
    )

    class Meta: # type: ignore
        constraints = [
            models.UniqueConstraint(
                fields=["report", "overhead_type"],
                condition=models.Q(is_trash=False),
                name="unique_report_overhead_type"
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
        is_create = not self.pk

        # Auto-assign report if missing
        self.assign_report()

        # Ensure transaction falls within valid reporting period
        self.validate_period()

        # Run model validation
        self.full_clean()

        super().save(*args, **kwargs)

        # Update report totals after save
        self.update_report_totals()

        # Audit logging (align with Attendance pattern)
        if hasattr(self, "log_audit"):
            self.log_audit(
                user=getattr(self, "_current_user", None),
                action="CREATE" if is_create else "UPDATE"
            )

    # ----------------------------
    # Audit Snapshot
    # ----------------------------
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.pk:
            self._old_data = {
                "amount": str(self.amount),
                "notes": self.notes,
                "overhead_type": (
                    self.overhead_type.name
                    if self.overhead_type_id else None # type: ignore
                ),
            }
        else:
            self._old_data = None

    # ----------------------------
    # String Representation
    # ----------------------------
    def __str__(self):
        return f"{self.assembly.name} - {self.overhead_type.name} - {self.amount}"
    
