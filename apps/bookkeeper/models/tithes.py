import uuid
from decimal import Decimal
from django.db import models
from apps.people.models import Member
from apps.bookkeeper.models import FinancialBase
from apps.bookkeeper.utils import tithe_receipt_path
from apps.reports.mixins.audit import AuditLogMixin


class PaymentMethod(models.TextChoices):
    BANK = 'Bank', 'Bank'
    CASH = 'Cash', 'Cash'
    CHEQUE = 'Cheque', 'Cheque'
    PBP = 'Mobile Money', 'Mobile Money'
    OTHER = 'Other', 'Other'


class Tithe(AuditLogMixin, FinancialBase):
    member = models.ForeignKey(
        "people.Member",
        on_delete=models.PROTECT,
        related_name='tithes',
        blank=True,
        null=True
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    payment_method = models.CharField(
        max_length=26,
        choices=PaymentMethod.choices,
        default=PaymentMethod.BANK,
    )

    receipt = models.FileField(
        upload_to=tithe_receipt_path,
        null=True,
        blank=True,
    )
    reference_code = models.CharField(max_length=100, blank=True)
    class Meta: # type: ignore
        verbose_name = "Tithe"
        verbose_name_plural = "Tithes"
        ordering = ["-timestamp"]
        constraints = [
            models.UniqueConstraint(
                fields=["report", "member"],
                condition=models.Q(is_trash=False),
                name="unique_report_member_tithe"
            )
        ]

    def __str__(self):
        member_name = self.member.full_name if self.member else "Anonymous"
        return f"{member_name}, {self.timestamp} - {self.assembly.name}"

    def save(self, *args, **kwargs):
        is_create = not self.pk

        # Auto-assign report (month-based grouping)
        self.assign_report()

        super().save(*args, **kwargs)

        # Audit logging
        if hasattr(self, "log_audit"):
            self.log_audit(
                user=getattr(self, "_current_user", None),
                action=(
                    "CREATE" if is_create else "UPDATE"
                )
            )


class GeneratedTitheReceipt(models.Model):
    tithe = models.OneToOneField(Tithe, on_delete=models.PROTECT, related_name="generated_receipt")
    receipt_number = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    receipt_data = models.JSONField(default=dict)
    issued_at = models.DateTimeField(auto_now_add=True)
    issued_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='issued_tithe_receipts')
    printed_at = models.DateTimeField(null=True, blank=True)
    printed_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='printed_tithe_receipts')
    last_printed_at = models.DateTimeField(null=True, blank=True)
