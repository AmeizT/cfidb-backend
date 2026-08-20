import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0023_assemblyreport_amendment_reason_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="assemblyreport",
            name="is_historical_backfill",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AlterField(
            model_name="assemblycompliance",
            name="status",
            field=models.CharField(
                choices=[
                    ("COMPLIANT", "Compliant"),
                    ("LATE", "Late"),
                    ("NOT_SUBMITTED", "Not Submitted"),
                    ("NOT_FINALIZED", "Not Finalized"),
                    ("MISSING_FROM_ZONE", "Missing From Zone"),
                    ("HISTORICAL_NOT_REQUIRED", "Historical - Not Required"),
                ],
                max_length=30,
            ),
        ),
        migrations.CreateModel(
            name="HistoricalMigrationLineage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("run_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False)),
                ("source_app", models.CharField(max_length=100)),
                ("source_model", models.CharField(max_length=100)),
                ("source_pk", models.CharField(max_length=100)),
                ("source_component", models.CharField(default="record", max_length=100)),
                ("target_app", models.CharField(blank=True, max_length=100)),
                ("target_model", models.CharField(blank=True, max_length=100)),
                ("target_pk", models.CharField(blank=True, max_length=100)),
                ("status", models.CharField(choices=[("migrated", "Migrated"), ("superseded", "Superseded"), ("skipped", "Skipped"), ("conflict", "Conflict"), ("verified", "Verified")], max_length=20)),
                ("source_checksum", models.CharField(max_length=64)),
                ("mapping_version", models.CharField(max_length=100)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["created_at", "id"],
                "indexes": [
                    models.Index(fields=["source_app", "source_model", "source_pk"], name="reports_hi_source_2bd8d0_idx"),
                    models.Index(fields=["target_app", "target_model", "target_pk"], name="reports_hi_target_44db2b_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("source_app", "source_model", "source_pk", "source_component", "mapping_version"),
                        name="unique_historical_migration_lineage",
                    )
                ],
            },
        ),
    ]
