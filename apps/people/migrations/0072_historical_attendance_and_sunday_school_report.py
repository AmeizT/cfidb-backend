import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("people", "0071_remove_membertransferrequest_unique_pending_transfer_per_member_and_more"),
        ("reports", "0024_historical_migration_foundation"),
    ]

    operations = [
        migrations.AddField(
            model_name="attendance",
            name="collection_schema",
            field=models.CharField(
                choices=[
                    ("legacy", "Historical totals (gender not collected)"),
                    ("gender_split", "Gender-split collection"),
                ],
                db_index=True,
                default="gender_split",
                max_length=20,
            ),
        ),
        *[
            migrations.AlterField(
                model_name="attendance",
                name=field_name,
                field=models.PositiveIntegerField(blank=True, default=0, null=True),
            )
            for field_name in (
                "men", "women", "visitor_men", "visitor_women",
                "new_convert_men", "new_convert_women", "altar_call_men",
                "altar_call_women", "baptism_men", "baptism_women",
            )
        ],
        migrations.AddField(
            model_name="sundayschoolattendance",
            name="report",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="sunday_school_attendance_set",
                to="reports.assemblyreport",
            ),
        ),
    ]
