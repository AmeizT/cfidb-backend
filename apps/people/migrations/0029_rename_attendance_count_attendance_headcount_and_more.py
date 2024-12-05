# Generated by Django 4.2.9 on 2024-05-09 17:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0028_alter_homecell_church'),
    ]

    operations = [
        migrations.RenameField(
            model_name='attendance',
            old_name='attendance_count',
            new_name='headcount',
        ),
        migrations.AlterField(
            model_name='attendance',
            name='homecell',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='homecell', to='people.homecell'),
        ),
    ]