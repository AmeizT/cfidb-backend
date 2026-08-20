from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("people", "0066_rename_people_sund_assembl_3123e1_idx_people_sund_assembl_64cd9b_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="attendance",
            name="men",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="attendance",
            name="women",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="attendance",
            name="visitor_men",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="attendance",
            name="visitor_women",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="attendance",
            name="new_convert_men",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="attendance",
            name="new_convert_women",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="attendance",
            name="altar_call_men",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="attendance",
            name="altar_call_women",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="attendance",
            name="baptism_men",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="attendance",
            name="baptism_women",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="attendance",
            name="total_adults",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.AddField(
            model_name="attendance",
            name="total_visitors",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.AddField(
            model_name="attendance",
            name="total_new_converts",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.AddField(
            model_name="attendance",
            name="total_altar_call",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.AddField(
            model_name="attendance",
            name="total_baptisms",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
    ]
