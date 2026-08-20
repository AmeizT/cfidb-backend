from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0021_report_lateness_section_followup"),
    ]

    operations = [
        migrations.AddField(
            model_name="assemblyreport",
            name="total_visitors",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="assemblyreport",
            name="total_altar_call",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
