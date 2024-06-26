# Generated by Django 4.2.9 on 2024-04-27 16:14

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('chat', '0004_message_created_by'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='created_by',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='message_author', to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
    ]
