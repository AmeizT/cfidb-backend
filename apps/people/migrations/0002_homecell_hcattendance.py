# Generated by Django 4.2.3 on 2023-07-12 12:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('churches', '0002_rename_desc_church_description_alter_church_address'),
        ('people', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Homecell',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('leader', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('church', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='homecell', to='churches.church')),
            ],
            options={
                'verbose_name': 'Home Cell',
                'verbose_name_plural': 'Home Cells',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='HCAttendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField()),
                ('venue', models.CharField(max_length=255)),
                ('attendance', models.BigIntegerField(default=0)),
                ('visitors', models.BigIntegerField(default=0)),
                ('new', models.BigIntegerField(default=0)),
                ('repented', models.BigIntegerField(default=0)),
                ('activities', models.TextField(blank=True)),
                ('achievements', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('church', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='hc_church', to='churches.church')),
                ('homecell', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='hc_attendance', to='people.homecell')),
            ],
            options={
                'verbose_name': 'Home Cell Attendance',
                'verbose_name_plural': 'Home Cell Attendance',
                'ordering': ['-created_at'],
            },
        ),
    ]