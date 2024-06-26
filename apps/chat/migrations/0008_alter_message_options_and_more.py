# Generated by Django 4.2.9 on 2024-04-27 16:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0007_rename_umid_message_message_id'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='message',
            options={'ordering': ['-created_at'], 'verbose_name': 'Message', 'verbose_name_plural': 'Messages'},
        ),
        migrations.RenameField(
            model_name='message',
            old_name='createdAt',
            new_name='created_at',
        ),
        migrations.RenameField(
            model_name='message',
            old_name='updatedAt',
            new_name='updated_at',
        ),
    ]
