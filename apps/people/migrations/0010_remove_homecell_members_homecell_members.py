# Generated by Django 4.2.3 on 2023-10-18 05:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0009_rename_leader_hcattendance_coordinator_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='homecell',
            name='members',
        ),
        migrations.AddField(
            model_name='homecell',
            name='members',
            field=models.ManyToManyField(blank=True, to='people.member'),
        ),
    ]