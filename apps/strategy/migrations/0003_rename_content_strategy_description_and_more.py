# Generated by Django 4.2.3 on 2023-10-13 13:11

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('strategy', '0002_alter_strategy_options_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='strategy',
            old_name='content',
            new_name='description',
        ),
        migrations.RenameField(
            model_name='strategy',
            old_name='title',
            new_name='filename',
        ),
        migrations.RemoveField(
            model_name='strategy',
            name='file',
        ),
        migrations.AddField(
            model_name='strategy',
            name='attachment',
            field=models.FileField(blank=True, null=True, upload_to='documents/strategy'),
        ),
        migrations.AddField(
            model_name='strategy',
            name='coordinator',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='strategy_coordinator', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='strategy',
            name='file_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AddField(
            model_name='strategy',
            name='timestamp',
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]