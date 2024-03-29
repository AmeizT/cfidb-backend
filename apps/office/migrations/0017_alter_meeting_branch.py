# Generated by Django 5.0.1 on 2024-01-16 16:48

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('churches', '0012_alter_church_status'),
        ('office', '0016_meeting_description_alter_meeting_platform'),
    ]

    operations = [
        migrations.AlterField(
            model_name='meeting',
            name='branch',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='meeting_branch', to='churches.church'),
        ),
    ]
