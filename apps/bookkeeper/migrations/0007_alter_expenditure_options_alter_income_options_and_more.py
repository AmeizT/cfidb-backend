# Generated by Django 4.2.3 on 2023-10-26 18:11

import apps.bookkeeper.utils
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0002_project_status'),
        ('people', '0015_tally'),
        ('churches', '0007_church_currency'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bookkeeper', '0006_income_entry_date'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='expenditure',
            options={'ordering': ['-invoice_date'], 'verbose_name': 'Expenditure', 'verbose_name_plural': 'Expenditure'},
        ),
        migrations.AlterModelOptions(
            name='income',
            options={'ordering': ['-created_at'], 'verbose_name': 'income', 'verbose_name_plural': 'income'},
        ),
        migrations.AlterField(
            model_name='asset',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to=apps.bookkeeper.utils.asset_image_path),
        ),
        migrations.CreateModel(
            name='Tithe',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('payment_method', models.CharField(choices=[('Bank', 'Bank'), ('Cash', 'Cash'), ('Cheque', 'Cheque'), ('EFT', 'EFT'), ('Other', 'Other')], default='Bank', max_length=10)),
                ('receipt', models.FileField(blank=True, null=True, upload_to=apps.bookkeeper.utils.tithe_receipt_path)),
                ('timestamp', models.DateField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tithe_branch', to='churches.church')),
                ('editor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tithe_editor', to=settings.AUTH_USER_MODEL)),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tither', to='people.member')),
            ],
            options={
                'verbose_name': 'tithe',
                'verbose_name_plural': 'tithes',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Pledge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('payment_method', models.CharField(choices=[('Bank', 'Bank'), ('Cash', 'Cash'), ('Cheque', 'Cheque'), ('EFT', 'EFT'), ('Other', 'Other')], default='Bank', max_length=10)),
                ('receipt', models.FileField(blank=True, null=True, upload_to=apps.bookkeeper.utils.pledge_receipt_path)),
                ('deadline', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_fulfilled', models.BooleanField(default=False)),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pledge_branch', to='churches.church')),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pledger', to='people.member')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_pledge', to='projects.project')),
            ],
            options={
                'verbose_name': 'pledge',
                'verbose_name_plural': 'pledges',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='FixedExpenditure',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('central_account_remittance', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('rent', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('water', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('electricity', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('telephone', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('internet', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('security', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('fuel', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('wages', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('insurance', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('humanitarian', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('investment', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('car_maintenance', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('bank_charges', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('remarks', models.TextField(blank=True)),
                ('receipt', models.FileField(blank=True, upload_to=apps.bookkeeper.utils.fixed_expenditure_receipt_path)),
                ('timestamp', models.DateField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fixed_expenditure', to='churches.church')),
                ('editor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='fixed_expenditure_editor', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Fixed Expenditure',
                'verbose_name_plural': 'Fixed Expenditures',
                'ordering': ['-created_at'],
            },
        ),
    ]
