import re
from django.db.models import Max
from django.apps import apps
from django.db import transaction

ZONE_ABBREVIATIONS = {
    "Namibia": "NA",
    "Southern Africa": "SA",
    "East Africa": "EA",
    "Islands": "IS",
    "Horn of Africa": "HOA",
}


def generate_zone_code_1(zone_name):
    abbreviation = ZONE_ABBREVIATIONS.get(zone_name)

    if not abbreviation:
        abbreviation = "".join(word[0] for word in zone_name.split()).upper()

    Zone = apps.get_model("churches", "Zone")

    with transaction.atomic():
        # Lock existing rows to avoid race condition
        existing_codes = (
            Zone.objects.select_for_update()
            .filter(code__startswith=f"Z{abbreviation}")
            .values_list("code", flat=True)
        )

        numbers = []
        for code in existing_codes:
            match = re.search(r"(\d+)$", code)
            if match:
                numbers.append(int(match.group(1)))

        next_number = (max(numbers) + 1) if numbers else 1

    return f"Z{abbreviation}{str(next_number).zfill(3)}"






from django.db import transaction
from django.apps import apps


def generate_zone_code(region):
    """
    Concurrency-safe, non-reusable zone code generator.
    Uses a persistent counter per region.
    """

    if not region:
        raise ValueError("Region is required")

    prefix = getattr(region, "code", None)
    if not prefix:
        raise ValueError("Region must have a code")

    RegionZoneCounter = apps.get_model("churches", "RegionZoneCounter")

    with transaction.atomic():
        counter, _ = RegionZoneCounter.objects.select_for_update().get_or_create(
            region=region
        )

        counter.last_number += 1 # type: ignore
        counter.save()

        return f"{prefix}-{counter.last_number:03d}" # type: ignore