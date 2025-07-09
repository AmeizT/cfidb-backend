from django.core.management.base import BaseCommand
from apps.bookkeeper.models import Tithe 

class Command(BaseCommand):
    help = "Backfill Tithe payment methods: 'Mobile' → 'Payment By Phone', 'EFT' → 'Bank'"

    def handle(self, *args, **options):
        updated_mobile = Tithe.objects.filter(payment_method="mobile").update(payment_method="Payment By Phone")
        updated_eft = Tithe.objects.filter(payment_method="EFT").update(payment_method="Bank")

        self.stdout.write(self.style.SUCCESS(f"Updated {updated_mobile} records from 'Mobile' to 'Payment By Phone'"))
        self.stdout.write(self.style.SUCCESS(f"Updated {updated_eft} records from 'EFT' to 'Bank'"))