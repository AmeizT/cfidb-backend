# Generated by Django 4.2.9 on 2025-05-16 11:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0045_alter_member_avatar_fallback'),
    ]

    operations = [
        migrations.AlterField(
            model_name='member',
            name='ministries',
            field=models.ManyToManyField(blank=True, null=True, to='people.ministry'),
        ),
        migrations.AlterField(
            model_name='member',
            name='positions',
            field=models.ManyToManyField(blank=True, null=True, to='people.position'),
        ),
    ]
