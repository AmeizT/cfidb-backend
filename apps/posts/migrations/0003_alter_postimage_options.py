# Generated by Django 4.2.3 on 2023-09-03 12:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0002_rename_text_post_description'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='postimage',
            options={'verbose_name': 'Gallery', 'verbose_name_plural': 'Gallery'},
        ),
    ]