# Generated by Django 4.2.3 on 2023-12-23 12:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_alter_user_avatar_alter_user_avatar_fallback'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(blank=True, choices=[('President', 'President'), ('Senior Pastor', 'Senior Pastor'), ('Overseer', 'Overseer'), ('Moderator', 'Moderator'), ('Pastor', 'Pastor'), ('Secretary', 'Secretary'), ('Secretary General', 'Secretary General'), ('Admin', 'Admin')], max_length=24),
        ),
    ]
