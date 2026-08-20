import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0020_compliancealert"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="assemblyreport",
            name="is_late",
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AddField(
            model_name="assemblyreport",
            name="days_late",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="reportsectionstatus",
            name="follow_up_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("contacted", "Contacted"),
                    ("resolved", "Resolved"),
                    ("escalated", "Escalated"),
                ],
                db_index=True,
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="reportsectionstatus",
            name="follow_up_notes",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="reportsectionstatus",
            name="follow_up_assigned_to",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assigned_follow_ups",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
