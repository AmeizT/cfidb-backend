from django.db import models

class Integration(models.Model):
    INTEGRATION_TYPE_CHOICES = [
        ("student", "Student"),
        ("staff", "Staff"),
        ("other", "Other"),
    ]

    integration_id = models.CharField(
        max_length=32,
        unique=True,
        verbose_name="Student/Staff/External ID",
    )
    user = models.ForeignKey(
        "users.User",
        related_name="integrations",
        on_delete=models.CASCADE,
    )
    integration_type = models.CharField(
        max_length=10,
        choices=INTEGRATION_TYPE_CHOICES,
        default="other",
    )
    integration_provider = models.ForeignKey(
        "integrations.IntegrationProvider",
        related_name="integrations",
        on_delete=models.PROTECT,
    )
    meta_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Optional data from the integration provider",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "integration_provider")
        verbose_name = "Integration"
        verbose_name_plural = "Integrations"

    def __str__(self):
        return f"{self.integration_provider.name} ({self.integration_id})"


class IntegrationProvider(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name of the external system (e.g. LMS, HR System)"
    )

    description = models.TextField(
        blank=True,
        help_text="Optional description of the system"
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Toggle to disable use of the system"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Integration Provider"
        verbose_name_plural = "Integration Providers"
        ordering = ["name"]

    def __str__(self):
        return self.name