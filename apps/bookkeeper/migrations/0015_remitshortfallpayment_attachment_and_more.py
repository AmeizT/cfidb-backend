# Generated by Django 4.2.3 on 2023-12-06 12:05

import apps.bookkeeper.utils
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookkeeper', '0014_remove_remittance_has_shortfall_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='remitshortfallpayment',
            name='attachment',
            field=models.FileField(blank=True, null=True, upload_to=apps.bookkeeper.utils.shortfall_receipt_path),
        ),
        migrations.AlterField(
            model_name='remittance',
            name='attachment',
            field=models.FileField(blank=True, null=True, upload_to=apps.bookkeeper.utils.remittance_receipt_path),
        ),
    ]