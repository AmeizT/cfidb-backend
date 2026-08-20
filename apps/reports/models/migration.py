import uuid

from django.db import models


class HistoricalMigrationLineage(models.Model):
    """Durable, idempotent evidence for every historical migration decision."""

    class Status(models.TextChoices):
        MIGRATED = "migrated", "Migrated"
        SUPERSEDED = "superseded", "Superseded"
        SKIPPED = "skipped", "Skipped"
        CONFLICT = "conflict", "Conflict"
        VERIFIED = "verified", "Verified"

    run_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    source_app = models.CharField(max_length=100)
    source_model = models.CharField(max_length=100)
    source_pk = models.CharField(max_length=100)
    source_component = models.CharField(max_length=100, default="record")
    target_app = models.CharField(max_length=100, blank=True)
    target_model = models.CharField(max_length=100, blank=True)
    target_pk = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices)
    source_checksum = models.CharField(max_length=64)
    mapping_version = models.CharField(max_length=100)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "source_app",
                    "source_model",
                    "source_pk",
                    "source_component",
                    "mapping_version",
                ],
                name="unique_historical_migration_lineage",
            )
        ]
        indexes = [
            models.Index(
                fields=["source_app", "source_model", "source_pk"],
                name="reports_hi_source_2bd8d0_idx",
            ),
            models.Index(
                fields=["target_app", "target_model", "target_pk"],
                name="reports_hi_target_44db2b_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.source_app}.{self.source_model}:{self.source_pk}/"
            f"{self.source_component} ({self.status})"
        )
