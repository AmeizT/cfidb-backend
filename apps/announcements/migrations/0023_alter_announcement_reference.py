# Generated by Django 4.2.9 on 2025-05-07 14:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('announcements', '0022_alter_announcement_reference'),
    ]

    operations = [
        migrations.AlterField(
            model_name='announcement',
            name='reference',
            field=models.CharField(default='o4mVgXb_9Py8', max_length=50, unique=True),
        ),
    ]
