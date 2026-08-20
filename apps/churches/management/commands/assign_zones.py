from django.core.management.base import BaseCommand
from apps.churches.models import Church, Zone, ZoneName


class Command(BaseCommand):
    help = "Assign churches to their respective zones based on country"

    def handle(self, *args, **options):
        # Define zone codes and their corresponding names
        zones_info = {
            "ZNA001": "Nambia",
            "ZSA001": "Southern Africa",
            "ZEA001": "East Africa",
            "ZIS001": "Islands",
            "ZHOA001": "Horn of Africa",
        }

        # Create or get ZoneName and Zone instances
        zones = {}
        for code, name in zones_info.items():
            zone_name_obj, _ = ZoneName.objects.get_or_create(name=name)
            zone_obj, _ = Zone.objects.get_or_create(code=code, defaults={'name': zone_name_obj})
            zones[code] = zone_obj

        # Mapping countries to zone codes
        country_zone_map = {
            "Australia": "ZIS001",
            "Botswana": "ZSA001",
            "Comoros": "ZIS001",
            "Ethiopia": "ZHOA001",
            "Lesotho": "ZSA001",
            "Kenya": "ZEA001",
            "Namibia": "ZNA001",
            "Nigeria": "ZIS001",
            "Rwanda": "ZEA001",
            "South Sudan": "ZHOA001",
            "Sudan": "ZHOA001",
            "Tanzania": "ZEA001",
            "Zambia": "ZSA001",
            "Zimbabwe": "ZSA001",
        }

        # Assign zones to churches based on country
        default_zone = zones["ZSA001"]
        for church in Church.objects.all():
            zone_code = country_zone_map.get(church.country)
            church.zone = zones[zone_code] if zone_code else default_zone
            church.save(update_fields=["zone"])
            self.stdout.write(self.style.SUCCESS(f"Assigned {church.name} to {church.zone.name}"))

        self.stdout.write(self.style.SUCCESS("✅ Church zones updated successfully."))