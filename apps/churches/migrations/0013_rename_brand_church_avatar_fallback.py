# Generated by Django 4.2.9 on 2024-05-18 08:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('churches', '0012_alter_church_status'),
    ]

    operations = [
        migrations.RenameField(
            model_name='church',
            old_name='brand',
            new_name='avatar_fallback',
        ),
    ]