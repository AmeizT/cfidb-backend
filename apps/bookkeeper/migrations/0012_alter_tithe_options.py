# Generated by Django 4.2.3 on 2023-12-04 10:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookkeeper', '0011_alter_income_timestamp'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='tithe',
            options={'ordering': ['-timestamp'], 'verbose_name': 'tithe', 'verbose_name_plural': 'tithes'},
        ),
    ]
