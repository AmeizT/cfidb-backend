# Generated by Django 4.2.9 on 2025-03-31 10:32

import apps.people.utils
import datetime
from django.db import migrations, models
import imagekit.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0034_remove_member_member_id_remove_member_tithes'),
    ]

    operations = [
        migrations.AddField(
            model_name='member',
            name='address_line2',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='member',
            name='avatar',
            field=imagekit.models.fields.ProcessedImageField(blank=True, null=True, upload_to=apps.people.utils.member_avatar_url),
        ),
        migrations.AlterField(
            model_name='member',
            name='address',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='member',
            name='baptized_at',
            field=models.DateField(default=datetime.date(1900, 1, 1), null=True),
        ),
        migrations.AlterField(
            model_name='member',
            name='membersince',
            field=models.DateField(default=datetime.date(1900, 1, 1), null=True),
        ),
    ]
