from django.db import models
from apps.churches.models import Church    

class Homecell(models.Model):
    church = models.ForeignKey(
        Church, on_delete=models.PROTECT, related_name="homecell"
    )
    group_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    members = models.ManyToManyField("people.Member", blank=True)
    non_church_members = models.TextField(blank=True)
    leader = models.ForeignKey(
        "people.Member", 
        on_delete=models.SET_NULL, 
        related_name="homecell_leader", 
        blank=True, 
        null=True
    )
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "homecell"
        verbose_name_plural = "homecells"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.group_name}"