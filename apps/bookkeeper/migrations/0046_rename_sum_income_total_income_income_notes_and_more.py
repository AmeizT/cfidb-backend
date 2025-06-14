# Generated by Django 4.2.9 on 2025-05-24 14:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookkeeper', '0045_asset_status'),
    ]

    operations = [
        migrations.RenameField(
            model_name='income',
            old_name='sum',
            new_name='total_income',
        ),
        migrations.AddField(
            model_name='income',
            name='notes',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='income',
            name='timestamp',
            field=models.DateField(blank=True, null=True),
        ),
    ]
