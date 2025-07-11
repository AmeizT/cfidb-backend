# Generated by Django 4.2.9 on 2025-06-23 06:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookkeeper', '0050_rename_branch_tithe_assembly'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pledge',
            name='payment_method',
            field=models.CharField(choices=[('Bank', 'Bank'), ('Cash', 'Cash'), ('Cheque', 'Cheque'), ('Payment By Phone', 'Payment By Phone'), ('Other', 'Other')], default='Bank', max_length=26),
        ),
        migrations.AlterField(
            model_name='remittance',
            name='payment_method',
            field=models.CharField(choices=[('Bank', 'Bank'), ('Cash', 'Cash'), ('Cheque', 'Cheque'), ('Payment By Phone', 'Payment By Phone'), ('Other', 'Other')], default='Bank', max_length=26),
        ),
        migrations.AlterField(
            model_name='shortfallpayment',
            name='payment_method',
            field=models.CharField(choices=[('Bank', 'Bank'), ('Cash', 'Cash'), ('Cheque', 'Cheque'), ('Payment By Phone', 'Payment By Phone'), ('Other', 'Other')], default='Bank', max_length=26),
        ),
        migrations.AlterField(
            model_name='tithe',
            name='payment_method',
            field=models.CharField(choices=[('Bank', 'Bank'), ('Cash', 'Cash'), ('Cheque', 'Cheque'), ('Payment By Phone', 'Payment By Phone'), ('Other', 'Other')], default='Bank', max_length=26),
        ),
    ]
