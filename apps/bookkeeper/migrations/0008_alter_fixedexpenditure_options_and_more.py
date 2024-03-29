# Generated by Django 4.2.3 on 2023-10-30 22:48

import apps.bookkeeper.utils
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookkeeper', '0007_alter_expenditure_options_alter_income_options_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='fixedexpenditure',
            options={'ordering': ['timestamp'], 'verbose_name': 'Fixed Expenditure', 'verbose_name_plural': 'Fixed Expenditures'},
        ),
        migrations.RenameField(
            model_name='income',
            old_name='entry_date',
            new_name='timestamp',
        ),
        migrations.RemoveField(
            model_name='income',
            name='pledges',
        ),
        migrations.RemoveField(
            model_name='income',
            name='tithes',
        ),
        migrations.AddField(
            model_name='expenditure',
            name='receipt',
            field=models.FileField(blank=True, null=True, upload_to=apps.bookkeeper.utils.expenditure_receipt_path),
        ),
        migrations.AddField(
            model_name='fixedexpenditure',
            name='total',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10),
        ),
        migrations.AddField(
            model_name='income',
            name='statement',
            field=models.FileField(blank=True, null=True, upload_to=apps.bookkeeper.utils.bank_statement_path),
        ),
    ]
