# Generated by Django 4.2.9 on 2024-05-10 10:51

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookkeeper', '0027_remove_fixedexpenditure_receipt_remove_tithe_editor_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='income',
            name='donations',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10),
        ),
        migrations.AlterField(
            model_name='expenditure',
            name='expense_type',
            field=models.CharField(choices=[('amenities', 'Amenities'), ('conference', 'Conference'), ('decor', 'Decor'), ('fellowship', 'Fellowship'), ('hotel bookings', 'Hotel Bookings'), ('humanitarian', 'Humanitarian'), ('office', 'Office'), ('other', 'Other'), ('outreach', 'Outreach'), ('repair', 'Repair'), ('travel', 'Travel'), ('wages', 'Wages')], max_length=255),
        ),
    ]
