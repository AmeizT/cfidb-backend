# Generated by Django 4.2.9 on 2024-04-28 20:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookkeeper', '0025_alter_fixedexpenditure_receipt'),
    ]

    operations = [
        migrations.RenameField(
            model_name='fixedexpenditure',
            old_name='branch',
            new_name='assembly',
        ),
    ]
