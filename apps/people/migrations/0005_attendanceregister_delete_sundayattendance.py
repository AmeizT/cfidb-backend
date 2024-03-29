# Generated by Django 4.2.3 on 2023-10-09 13:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0004_kindred_alter_churchattendance_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='AttendanceRegister',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendance_register', to='people.member')),
            ],
            options={
                'verbose_name': 'kindred',
                'verbose_name_plural': 'kindred',
                'ordering': ['-date'],
                'unique_together': {('member', 'date')},
            },
        ),
        migrations.DeleteModel(
            name='SundayAttendance',
        ),
    ]
