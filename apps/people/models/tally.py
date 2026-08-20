from django.db import models
from datetime import datetime
from apps.users.models import User
from apps.churches.models import Church
from apps.people.choices.services import AttendanceCategories


class Tally(models.Model):
    branch = models.ForeignKey(
        Church,
        on_delete=models.CASCADE, 
        related_name="tally_branch"
    )
    members = models.ManyToManyField("people.Member", blank=True)
    category = models.CharField(
        max_length=24, 
        blank=True, 
        choices=AttendanceCategories.choices,
        default=AttendanceCategories.SUNDAY
    )
    timestamp = models.DateTimeField(
        null=True, 
        blank=True, 
        default=datetime(1900, 1, 1, 0, 0, 0)
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name="tally_editor", 
        blank=True, 
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "tally"
        verbose_name_plural = "tallies"
        ordering = ["-timestamp"]
        

    def __str__(self):
        return f"{self.branch.name}"