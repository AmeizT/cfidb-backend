from decimal import Decimal
from django.db.models import Sum
from django.core.management.base import BaseCommand
from apps.bookkeeper.models import FixedExpenditure, Tithe

class Command(BaseCommand):
    help = 'Backfill remittance values for FixedExpenditure records'

    def handle(self, *args, **kwargs):
        expenditures = FixedExpenditure.objects.all()
        
        for expenditure in expenditures:
            # Find the corresponding tithes for the same month and assembly
            tithes = Tithe.objects.filter(
                branch=expenditure.assembly,
                timestamp__year=expenditure.timestamp.year,
                timestamp__month=expenditure.timestamp.month
            )
            
            # Calculate total tithes for the month
            total_tithes = tithes.aggregate(Sum('amount'))['amount__sum'] or Decimal(0.00)
            
            # Calculate 25% remittance
            remittance_amount = total_tithes * Decimal(0.25)
            
            # Update the FixedExpenditure's remittance value
            expenditure.remittance = remittance_amount
            expenditure.save()
            
            self.stdout.write(f"Updated remittance for {expenditure.assembly.name} for {expenditure.timestamp}: {remittance_amount}")
