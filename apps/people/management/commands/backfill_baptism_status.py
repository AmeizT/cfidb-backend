from datetime import date
from django.core.management.base import BaseCommand
from apps.people.models import Member

class Command(BaseCommand):
    help = "Backfill the baptized field based on baptized_at"

    def handle(self, *args, **options):
        updated = 0
        for member in Member.objects.all():
            if member.baptized_at and member.baptized_at != date(1900, 1, 1):
                if not member.baptized:
                    member.baptized = True
                    member.save(update_fields=["baptized"])
                    updated += 1
            else:
                if member.baptized:
                    member.baptized = False
                    member.save(update_fields=["baptized"])
                    updated += 1

        self.stdout.write(self.style.SUCCESS(f"Updated {updated} members."))