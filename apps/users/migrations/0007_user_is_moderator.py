# Generated by Django 4.2.3 on 2023-12-17 18:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_user_is_president_user_is_senior_pastor'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_moderator',
            field=models.BooleanField(default=False),
        ),
    ]