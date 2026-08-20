import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("examinations", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="examinationimportrow",
            name="matched_student",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="matched_examination_import_rows",
                to="examinations.cbastudentreference",
            ),
        ),
        migrations.AlterField(
            model_name="examinationresult",
            name="student",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="examination_results",
                to="examinations.cbastudentreference",
            ),
        ),
    ]
