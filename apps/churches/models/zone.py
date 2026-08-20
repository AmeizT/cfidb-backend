from django.db import models # type: ignore
from apps.users.models import User
from apps.churches.utils import generate_zone_code
from django.utils.translation import gettext_lazy as _ # type: ignore

class Zone(models.Model):
    region = models.ForeignKey(
        "churches.Region",
        related_name="zones",
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100)
    code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        blank=True,
        editable=False,
    )
    description = models.TextField(blank=True)

    office_location = models.CharField(max_length=255, blank=True)
    office_address = models.TextField(blank=True)
    office_phone = models.CharField(max_length=30, blank=True)
    office_email = models.EmailField(blank=True)

    deleted_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    established_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["is_active"]),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["region", "name"],
                name="unique_zone_name_per_region"
            )
        ]

    def __str__(self):
        if self.code and self.name:
            return f"{self.name} ({self.code}) - {self.id}"
        return self.name or self.code or "Zone"
    

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_zone_code(self.region)
        super().save(*args, **kwargs)
    

class ZoneLeadership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        OVERSEER = "overseer", "Overseer"
        ASSISTANT = "assistant", "Assistant"
        COORDINATOR = "coordinator", "Coordinator"

    zone = models.ForeignKey(
        Zone,
        on_delete=models.CASCADE,
        related_name="leadership"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="zone_roles"
    )

    role = models.CharField(
        max_length=30,
        choices=Role.choices
    )

    appointed_at = models.DateField()
    ended_at = models.DateField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["zone", "user", "role", "appointed_at"],
                name="unique_zone_role_assignment"
            )
        ]
        indexes = [
            models.Index(fields=["zone", "role"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.zone} ({self.role})"
    

class RegionZoneCounter(models.Model):
    region = models.OneToOneField("Region", on_delete=models.CASCADE)
    last_number = models.PositiveIntegerField(default=0)


