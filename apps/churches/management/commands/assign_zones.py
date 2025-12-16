from django.core.management.base import BaseCommand
from apps.churches.models import Church, Zone, ZoneName


class Command(BaseCommand):
    help = "Assign churches to their respective zones based on country"

    def handle(self, *args, **options):
        # Ensure zones exist
        zone1_name, _ = ZoneName.objects.get_or_create(name="Zone 1")
        zone2_name, _ = ZoneName.objects.get_or_create(name="Zone 2")
        zone3_name, _ = ZoneName.objects.get_or_create(name="Zone 3")
        zone4_name, _ = ZoneName.objects.get_or_create(name="Zone 4")

        zone1, _ = Zone.objects.get_or_create(name=zone1_name)
        zone2, _ = Zone.objects.get_or_create(name=zone2_name)
        zone3, _ = Zone.objects.get_or_create(name=zone3_name)
        zone4, _ = Zone.objects.get_or_create(name=zone4_name)

        # Define mappings
        zone1_countries = ["Zimbabwe", "South Africa", "Botswana"]
        zone2_countries = ["England", "Germany", "France", "Spain", "Italy", "Europe"]  # expand as needed
        zone3_countries = ["Namibia"]

        # Assign zone per country
        for church in Church.objects.all():
            if church.country in zone1_countries:
                church.zone = zone1
            elif church.country in zone2_countries:
                church.zone = zone2
            elif church.country in zone3_countries:
                church.zone = zone3
            else:
                church.zone = zone4

            church.save(update_fields=["zone"])
            self.stdout.write(self.style.SUCCESS(f"Assigned {church.name} to {church.zone.name}"))

        self.stdout.write(self.style.SUCCESS("✅ Church zones updated successfully."))