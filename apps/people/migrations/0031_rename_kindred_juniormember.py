# Generated by Django 4.2.9 on 2024-09-30 10:38

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('churches', '0016_alter_imageupload_options'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('people', '0030_alter_attendance_category_alter_tally_category'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Kindred',
            new_name='JuniorMember',
        ),
    ]
