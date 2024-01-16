# Generated by Django 4.2.3 on 2023-12-06 10:51

import apps.bookkeeper.utils
from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0020_alter_kindred_guardian'),
        ('churches', '0007_church_currency'),
        ('bookkeeper', '0012_alter_tithe_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='Remittance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount_due', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('amount_paid', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('shortfall', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('payment_method', models.CharField(choices=[('Bank', 'Bank'), ('Cash', 'Cash'), ('Cheque', 'Cheque'), ('EFT', 'EFT'), ('Other', 'Other')], default='Bank', max_length=10)),
                ('attachment', models.FileField(blank=True, null=True, upload_to=apps.bookkeeper.utils.pledge_receipt_path)),
                ('has_shortfall', models.BooleanField(default=False)),
                ('timestamp', models.DateField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='remitter', to='churches.church')),
                ('editor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='remittance_editor', to='people.member')),
            ],
            options={
                'verbose_name': 'remittance',
                'verbose_name_plural': 'remittances',
                'ordering': ['timestamp'],
            },
        ),
    ]