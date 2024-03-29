# Generated by Django 4.2.3 on 2023-10-18 19:47

import apps.strategy.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('churches', '0007_church_currency'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('strategy', '0004_alter_strategy_timestamp'),
    ]

    operations = [
        migrations.RenameField(
            model_name='strategy',
            old_name='description',
            new_name='accountability',
        ),
        migrations.RenameField(
            model_name='strategy',
            old_name='church',
            new_name='branch',
        ),
        migrations.RemoveField(
            model_name='strategy',
            name='attachment',
        ),
        migrations.RemoveField(
            model_name='strategy',
            name='coordinator',
        ),
        migrations.RemoveField(
            model_name='strategy',
            name='file_id',
        ),
        migrations.RemoveField(
            model_name='strategy',
            name='filename',
        ),
        migrations.RemoveField(
            model_name='strategy',
            name='slug',
        ),
        migrations.RemoveField(
            model_name='strategy',
            name='timestamp',
        ),
        migrations.AddField(
            model_name='strategy',
            name='capacity_development',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='strategy',
            name='church_growth',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='strategy',
            name='financial_mandate',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='strategy',
            name='humanitarian_projects',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='strategy',
            name='infrastructure_development',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='strategy',
            name='introduction',
            field=models.TextField(blank=True),
        ),
        migrations.CreateModel(
            name='StrategyLegacy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('attachment', models.FileField(blank=True, null=True, upload_to=apps.strategy.models.strategy_file_path)),
                ('slug', models.SlugField(blank=True, max_length=255, unique=True)),
                ('timestamp', models.DateField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='strategy_legacy', to='churches.church')),
                ('coordinator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='strategy_coordinator', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Strategy Legacy',
                'verbose_name_plural': 'Strategy Legacy',
                'ordering': ['-created_at'],
            },
        ),
    ]
