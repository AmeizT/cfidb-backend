# Generated by Django 4.2.3 on 2023-12-19 14:16

import apps.users.utils
from django.db import migrations, models
import imagekit.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_user_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='avatar',
            field=imagekit.models.fields.ProcessedImageField(blank=True, null=True, upload_to=apps.users.utils.user_avatar_url),
        ),
        migrations.AlterField(
            model_name='user',
            name='avatar_fallback',
            field=models.CharField(blank=True, max_length=12),
        ),
    ]
