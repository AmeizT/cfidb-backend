from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.churches.models import Church, Region, Zone


# ---------------------------------------------------------------------------
# Region
# ---------------------------------------------------------------------------

REGION_NAME = "Eastern & Southern Africa"


# ---------------------------------------------------------------------------
# Country → Zone mapping
# ---------------------------------------------------------------------------

COUNTRY_ZONE_MAP = {
    # Zone 1 — Namibia
    "namibia": "Zone 1",
    "na": "Zone 1",
    "nam": "Zone 1",

    # Zone 2 — Tanzania, Uganda, Rwanda, Kenya, Zanzibar
    "burundi": "Zone 2",
    "bi": "Zone 2",
    "bdi": "Zone 2",

    "tanzania": "Zone 2",
    "united republic of tanzania": "Zone 2",
    "tz": "Zone 2",
    "tza": "Zone 2",

    "uganda": "Zone 2",
    "ug": "Zone 2",
    "uga": "Zone 2",

    "rwanda": "Zone 2",
    "rw": "Zone 2",
    "rwa": "Zone 2",

    "kenya": "Zone 2",
    "ke": "Zone 2",
    "ken": "Zone 2",

    "zanzibar": "Zone 2",

    # Zone 3 — Lesotho, Zambia
    "angola": "Zone 3",
    "ao": "Zone 3",
    "ago": "Zone 3",

    "lesotho": "Zone 3",
    "ls": "Zone 3",
    "lso": "Zone 3",

    "zambia": "Zone 3",
    "zm": "Zone 3",
    "zmb": "Zone 3",

    # Zone 4 — Ethiopia, Sudan, South Sudan, Eritrea, Djibouti, Somalia
    "ethiopia": "Zone 4",
    "et": "Zone 4",
    "eth": "Zone 4",

    "sudan": "Zone 4",
    "sd": "Zone 4",
    "sdn": "Zone 4",

    "south sudan": "Zone 4",
    "ss": "Zone 4",
    "ssd": "Zone 4",

    "eritrea": "Zone 4",
    "er": "Zone 4",
    "eri": "Zone 4",

    "djibouti": "Zone 4",
    "dj": "Zone 4",
    "dji": "Zone 4",

    "somalia": "Zone 4",
    "so": "Zone 4",
    "som": "Zone 4",

    # Zone 5 — Madagascar, Comoros, Nigeria
    "madagascar": "Zone 5",
    "mg": "Zone 5",
    "mdg": "Zone 5",

    "comoros": "Zone 5",
    "km": "Zone 5",
    "com": "Zone 5",

    "nigeria": "Zone 5",
    "ng": "Zone 5",
    "nga": "Zone 5",
}


# ---------------------------------------------------------------------------
# Expected zones inside Eastern & Southern Africa
# ---------------------------------------------------------------------------

EXPECTED_ZONE_NAMES = {
    "Zone 1",
    "Zone 2",
    "Zone 3",
    "Zone 4",
    "Zone 5",
}


# ---------------------------------------------------------------------------
# Countries intentionally excluded from this backfill
# ---------------------------------------------------------------------------

IGNORED_COUNTRIES = {
    "zimbabwe",
    "zw",
    "zwe",
}


def normalize(value):
    return (value or "").strip().lower()


def resolve_zone_name(assembly):
    """
    Resolve an assembly's intended zone from its country information.

    country_code is preferred because it is generally more consistent.
    country is used as a fallback.

    Zimbabwe is intentionally excluded from this backfill.
    """

    country_code = normalize(assembly.country_code)
    country = normalize(assembly.country)

    # Intentionally excluded
    if (
        country_code in IGNORED_COUNTRIES
        or country in IGNORED_COUNTRIES
    ):
        return "IGNORE"

    # Prefer country code
    if country_code in COUNTRY_ZONE_MAP:
        return COUNTRY_ZONE_MAP[country_code]

    # Fall back to country name
    if country in COUNTRY_ZONE_MAP:
        return COUNTRY_ZONE_MAP[country]

    return None


class Command(BaseCommand):
    help = (
        "Backfill assembly zone assignments for the "
        "Eastern & Southern Africa region based on country. "
        "Runs as a dry-run unless --apply is supplied."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help=(
                "Persist changes. Without this flag "
                "no database changes are made."
            ),
        )

        parser.add_argument(
            "--overwrite",
            action="store_true",
            help=(
                "Replace an assembly's existing zone when it differs "
                "from the country-derived zone."
            ),
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        overwrite = options["overwrite"]

        # ------------------------------------------------------------------
        # Resolve the parent region
        # ------------------------------------------------------------------

        try:
            region = Region.objects.get(name=REGION_NAME)

        except Region.DoesNotExist:
            raise CommandError(
                f"Could not find region '{REGION_NAME}'. "
                "Check the exact region name in the database."
            )

        except Region.MultipleObjectsReturned:
            raise CommandError(
                f"Multiple regions named '{REGION_NAME}' were found. "
                "The backfill cannot safely continue."
            )

        # ------------------------------------------------------------------
        # Resolve Zones 1–5 inside the ESA region
        # ------------------------------------------------------------------

        zone_queryset = (
            Zone.objects
            .select_related("region")
            .filter(
                region=region,
                name__in=EXPECTED_ZONE_NAMES,
                is_active=True,
                deleted_at__isnull=True,
            )
        )

        zones = {
            zone.name: zone
            for zone in zone_queryset
        }

        missing_zones = EXPECTED_ZONE_NAMES - set(zones.keys())

        if missing_zones:
            raise CommandError(
                f"Could not find the following active zones inside "
                f"'{REGION_NAME}': "
                f"{', '.join(sorted(missing_zones))}"
            )

        # ------------------------------------------------------------------
        # Inspect assemblies
        # ------------------------------------------------------------------

        assemblies = (
            Church.objects
            .select_related("zone", "zone__region")
            .order_by("country", "name")
        )

        planned_updates = []
        already_correct = []
        conflicts = []
        unmapped = []
        ignored = []

        for assembly in assemblies:
            zone_name = resolve_zone_name(assembly)

            # Zimbabwe / intentionally excluded countries
            if zone_name == "IGNORE":
                ignored.append(assembly)
                continue

            # Country does not appear in our mapping
            if not zone_name:
                unmapped.append(assembly)
                continue

            target_zone = zones[zone_name]

            # Already assigned correctly
            if assembly.zone_id == target_zone.id: # type: ignore
                already_correct.append(assembly)
                continue

            # Existing assignment differs from expected assignment
            if assembly.zone_id and not overwrite:
                conflicts.append(
                    (assembly, target_zone)
                )
                continue

            planned_updates.append(
                (assembly, target_zone)
            )

        # ------------------------------------------------------------------
        # Header
        # ------------------------------------------------------------------

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "ASSEMBLY → ZONE BACKFILL"
            )
        )

        self.stdout.write(
            f"Region: {region.name}"
        )

        self.stdout.write("")

        # ------------------------------------------------------------------
        # Zone structure
        # ------------------------------------------------------------------

        self.stdout.write(
            self.style.MIGRATE_LABEL(
                "Zone structure:"
            )
        )

        for zone_name in sorted(EXPECTED_ZONE_NAMES):
            zone = zones[zone_name]

            self.stdout.write(
                f"  {zone.name} "
                f"[{zone.code}] "
                f"→ {region.name}"
            )

        # ------------------------------------------------------------------
        # Planned assignments
        # ------------------------------------------------------------------

        if planned_updates:
            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    "Planned assignments:"
                )
            )

            for assembly, target_zone in planned_updates:
                if assembly.zone:
                    current_region = (
                        assembly.zone.region.name
                        if assembly.zone.region
                        else "No Region"
                    )

                    current = (
                        f"{assembly.zone.name} "
                        f"({current_region})"
                    )
                else:
                    current = "Unassigned"

                country_label = (
                    assembly.country
                    or assembly.country_code
                    or "Unknown country"
                )

                self.stdout.write(
                    f"  {assembly.name} "
                    f"[{country_label}] "
                    f"{current} → "
                    f"{target_zone.name} ({region.name})"
                )

        # ------------------------------------------------------------------
        # Already correct
        # ------------------------------------------------------------------

        if already_correct:
            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    "Already correct:"
                )
            )

            for assembly in already_correct:
                self.stdout.write(
                    f"  {assembly.name} "
                    f"→ {assembly.zone.name}"
                )

        # ------------------------------------------------------------------
        # Existing conflicting assignments
        # ------------------------------------------------------------------

        if conflicts:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "Existing conflicting assignments:"
                )
            )

            for assembly, target_zone in conflicts:
                current_region = (
                    assembly.zone.region.name
                    if assembly.zone
                    and assembly.zone.region
                    else "No Region"
                )

                self.stdout.write(
                    f"  {assembly.name}: "
                    f"{assembly.zone.name} "
                    f"({current_region}) "
                    f"→ {target_zone.name} "
                    f"({region.name})"
                )

        # ------------------------------------------------------------------
        # Intentionally ignored
        # ------------------------------------------------------------------

        if ignored:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "Intentionally ignored:"
                )
            )

            for assembly in ignored:
                self.stdout.write(
                    f"  {assembly.name} "
                    f"[{assembly.country or assembly.country_code}]"
                )

        # ------------------------------------------------------------------
        # Unmapped assemblies
        # ------------------------------------------------------------------

        if unmapped:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "Unmapped assemblies:"
                )
            )

            for assembly in unmapped:
                self.stdout.write(
                    f"  {assembly.name}: "
                    f"country='{assembly.country}' "
                    f"country_code='{assembly.country_code}'"
                )

        # ------------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------------

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Summary"
            )
        )

        self.stdout.write(
            f"  Planned:         {len(planned_updates)}"
        )

        self.stdout.write(
            f"  Already correct: {len(already_correct)}"
        )

        self.stdout.write(
            f"  Conflicts:       {len(conflicts)}"
        )

        self.stdout.write(
            f"  Unmapped:        {len(unmapped)}"
        )

        self.stdout.write(
            f"  Ignored:         {len(ignored)}"
        )

        self.stdout.write(
            f"  Total:           {assemblies.count()}"
        )

        # ------------------------------------------------------------------
        # Dry-run
        # ------------------------------------------------------------------

        if not apply_changes:
            self.stdout.write("")

            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN — no database changes were made."
                )
            )

            if conflicts:
                self.stdout.write(
                    self.style.WARNING(
                        "Existing conflicting assignments were skipped. "
                        "Review them before using --overwrite."
                    )
                )

            if unmapped:
                self.stdout.write(
                    self.style.WARNING(
                        "Some assemblies could not be mapped. "
                        "Review their country/country_code values."
                    )
                )

            self.stdout.write("")
            self.stdout.write(
                "Run with --apply after reviewing the results."
            )

            return

        # ------------------------------------------------------------------
        # Production safety checks
        # ------------------------------------------------------------------

        if conflicts and not overwrite:
            raise CommandError(
                f"{len(conflicts)} conflicting zone assignment(s) "
                "were found. No database changes were made. "
                "Review them first or intentionally use --overwrite."
            )

        if unmapped:
            raise CommandError(
                f"{len(unmapped)} assembly/assemblies could not "
                "be mapped. No database changes were made. "
                "Correct their country information before applying."
            )

        # ------------------------------------------------------------------
        # Nothing to update
        # ------------------------------------------------------------------

        if not planned_updates:
            self.stdout.write("")

            self.stdout.write(
                self.style.SUCCESS(
                    "All applicable assemblies are already "
                    "assigned correctly. Nothing to update."
                )
            )

            return

        # ------------------------------------------------------------------
        # Apply changes atomically
        # ------------------------------------------------------------------

        now = timezone.now()

        with transaction.atomic():
            for assembly, target_zone in planned_updates:
                assembly.zone = target_zone
                assembly.updated_at = now

                assembly.save(
                    update_fields=[
                        "zone",
                        "updated_at",
                    ]
                )

        # ------------------------------------------------------------------
        # Success
        # ------------------------------------------------------------------

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully assigned "
                f"{len(planned_updates)} assemblies "
                f"to zones in {region.name}."
            )
        )