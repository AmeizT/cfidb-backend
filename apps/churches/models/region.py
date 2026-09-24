from django.db import models # type: ignore
from apps.users.models import User 

class Region(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}-{self.id}" # type: ignore
    

class RegionLeadership(models.Model):
    class Role(models.TextChoices):
        REGIONAL_ADMIN = "regional_admin", "Regional Admin"
        OVERSEER = "overseer", "Overseer"
        OVERSEER_PA = "overseer_pa", "Overseer PA"
        REGION_MODERATOR = "region_moderator", "Region Moderator"

    region = models.ForeignKey(
        Region,
        related_name="leadership",
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        User,
        related_name="region_roles",
        on_delete=models.CASCADE,
    )
    role = models.CharField(
        max_length=50,
        choices=Role.choices,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Region Leadership"
        verbose_name_plural = "Region Leadership"
        constraints = [
            models.UniqueConstraint(
                fields=["region", "user", "role"],
                condition=models.Q(is_active=True),
                name="unique_active_region_user_role",
            )
        ]

    def __str__(self):
        return f"{self.user.full_name} - {self.region.name} - {self.role}"