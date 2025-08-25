from django.core.management.base import BaseCommand
from apps.bookkeeper.models import Tithe 

class Command(BaseCommand):
    help = "Backfill Tithe payment methods: 'Mobile' → 'Payment By Phone', 'EFT' → 'Bank'"

    def handle(self, *args, **options):
        updated_mobile = Tithe.objects.filter(payment_method="mobile").update(payment_method="Payment By Phone")
        updated_eft = Tithe.objects.filter(payment_method="EFT").update(payment_method="Bank")
        updated_eft2 = Tithe.objects.filter(payment_method="eft").update(payment_method="Bank")
        updated_cash = Tithe.objects.filter(payment_method="cash").update(payment_method="Cash")

        self.stdout.write(self.style.SUCCESS(f"Updated {updated_mobile} records from 'Mobile' to 'Payment By Phone'"))
        self.stdout.write(self.style.SUCCESS(f"Updated {updated_eft2} records from 'eft' to 'Bank'"))
        self.stdout.write(self.style.SUCCESS(f"Updated {updated_cash} records from 'cash' to 'Cash'"))
        self.stdout.write(self.style.SUCCESS(f"Updated {updated_eft} records from 'EFT' to 'Bank'"))