from django.conf import settings
from django.db import models
from django.db.models import F, Q


class MemberTransferRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending_acceptance", "Pending acceptance"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    member = models.ForeignKey(
        "people.Member",
        on_delete=models.CASCADE,
        related_name="transfer_requests",
    )
    from_assembly = models.ForeignKey(
        "churches.Church",
        on_delete=models.PROTECT,
        related_name="outgoing_transfer_requests",
    )
    to_assembly = models.ForeignKey(
        "churches.Church",
        on_delete=models.PROTECT,
        related_name="incoming_transfer_requests",
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
    )
    effective_date = models.DateField()
    reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="requested_member_transfers",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_member_transfers",
    )
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_member_transfers",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["member"]),
            models.Index(fields=["from_assembly"]),
            models.Index(fields=["to_assembly"]),
            models.Index(fields=["status"]),
            models.Index(fields=["effective_date"]),
            models.Index(fields=["requested_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~Q(from_assembly=F("to_assembly")),
                name="transfer_from_and_to_assembly_must_differ",
            ),
            models.UniqueConstraint(
                fields=["member"],
                condition=Q(status__in=["pending_acceptance", "accepted"]),
                name="unique_open_transfer_per_member",
            ),
        ]

    def __str__(self):
        return (
            f"{self.member.full_name}: "
            f"{self.from_assembly.name} -> {self.to_assembly.name} ({self.status})"
        )
