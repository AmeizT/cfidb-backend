# Generated by Django 4.2.9 on 2024-06-09 14:13

import apps.forum.helpers
from django.db import migrations
import imagekit.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('forum', '0008_alter_changelog_description_alter_changelog_title'),
    ]

    operations = [
        migrations.AlterField(
            model_name='changelog',
            name='image',
            field=imagekit.models.fields.ProcessedImageField(blank=True, null=True, upload_to=apps.forum.helpers.changelog_image_url),
        ),
    ]