# Generated by Django 4.2.9 on 2024-04-27 16:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0006_alter_message_created_by'),
    ]

    operations = [
        migrations.RenameField(
            model_name='message',
            old_name='umid',
            new_name='message_id',
        ),
    ]