# Generated by Django 4.2.3 on 2023-08-10 06:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('churches', '0003_church_avatar_church_header'),
    ]

    operations = [
        migrations.RenameField(
            model_name='church',
            old_name='header',
            new_name='banner',
        ),
    ]
