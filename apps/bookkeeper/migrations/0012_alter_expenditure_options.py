# Generated by Django 4.2.3 on 2023-10-13 13:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookkeeper', '0011_alter_expenditure_receipt'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='expenditure',
            options={'ordering': ['-invoice_date'], 'verbose_name': 'Expenditure', 'verbose_name_plural': 'Expenditure'},
        ),
    ]