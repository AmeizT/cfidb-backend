import uuid

from django.conf import settings
from django.db import models


def generate_public_id():
    return uuid.uuid4().hex[:21]


class JethroConversation(models.Model):
    public_id = models.CharField(max_length=21, unique=True, db_index=True, default=generate_public_id, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="jethro_conversations")
    assembly = models.ForeignKey("churches.Church", on_delete=models.CASCADE, related_name="jethro_conversations")
    title = models.CharField(max_length=120, default="New conversation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["user", "assembly", "is_archived"])]

    def __str__(self):
        return f"{self.title} ({self.user})"


class JethroMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        TOOL = "tool", "Tool"
        SYSTEM = "system", "System"

    conversation = models.ForeignKey(JethroConversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=12, choices=Role.choices)
    content = models.TextField()
    structured_content = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]


class JethroActionLog(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        ERROR = "error", "Error"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="jethro_actions")
    assembly = models.ForeignKey("churches.Church", on_delete=models.CASCADE, related_name="jethro_actions")
    conversation = models.ForeignKey(JethroConversation, on_delete=models.CASCADE, related_name="actions")
    tool_name = models.CharField(max_length=80)
    arguments = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=Status.choices)
    error_message = models.CharField(max_length=255, blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class JethroUsageLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="jethro_usage")
    conversation = models.ForeignKey(JethroConversation, on_delete=models.CASCADE, related_name="usage")
    model = models.CharField(max_length=100)
    input_tokens = models.PositiveIntegerField(default=0)
    cached_input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class JethroTitheDraft(models.Model):
    class Status(models.TextChoices):
        PENDING_MEMBER_SELECTION = "pending_member_selection", "Pending member selection"
        PENDING_CONFIRMATION = "pending_confirmation", "Pending confirmation"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"
        FAILED = "failed", "Failed"

    public_id = models.CharField(
        max_length=21,
        unique=True,
        db_index=True,
        default=generate_public_id,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="jethro_tithe_drafts",
    )
    assembly = models.ForeignKey(
        "churches.Church",
        on_delete=models.CASCADE,
        related_name="jethro_tithe_drafts",
    )
    conversation = models.ForeignKey(
        JethroConversation,
        on_delete=models.CASCADE,
        related_name="tithe_drafts",
    )
    member = models.ForeignKey(
        "people.Member",
        on_delete=models.PROTECT,
        related_name="jethro_tithe_drafts",
        null=True,
        blank=True,
    )
    created_tithe = models.ForeignKey(
        "bookkeeper.Tithe",
        on_delete=models.SET_NULL,
        related_name="jethro_drafts",
        null=True,
        blank=True,
    )
    member_query = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=26)
    payment_date = models.DateField()
    reference_code = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    original_request = models.TextField(max_length=2000)
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING_MEMBER_SELECTION,
        db_index=True,
    )
    expires_at = models.DateTimeField(db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "assembly", "status"]),
        ]

    def __str__(self):
        return f"Tithe draft {self.public_id} ({self.status})"
