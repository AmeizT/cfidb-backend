# Generated by Django 4.2.3 on 2023-10-18 10:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0012_rename_new_hcattendance_new_members'),
    ]

    operations = [
        migrations.RenameField(
            model_name='hcattendance',
            old_name='attendance',
            new_name='total_attendance',
        ),
    ]