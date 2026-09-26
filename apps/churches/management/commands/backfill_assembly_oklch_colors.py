from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.churches.models import Church
from apps.churches.utils import generate_oklch_color


def is_oklch_color(value):
    """
    Return True when avatar_fallback already appears to contain
    a valid OKLCH CSS color.

    Examples:
        oklch(65% 0.18 240)
        oklch(0.65 0.18 240)
    """
    if not isinstance(value, str):
        return False

    value = value.strip().lower()

    return (
        value.startswith("oklch(")
        and value.endswith(")")
    )


class Command(BaseCommand):
    help = (
        "Backfill Church.avatar_fallback values with OKLCH colors. "
        "Existing OKLCH colors are preserved unless --force-all is used. "
        "Dry-run by default."
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
            "--force-all",
            action="store_true",
            help=(
                "Generate a new OKLCH color for every assembly, "
                "including assemblies that already have OKLCH colors."
            ),
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        force_all = options["force_all"]

        assemblies = list(
            Church.objects
            .only(
                "id",
                "name",
                "avatar_fallback",
                "updated_at",
            )
            .order_by("name")
        )

        planned = []
        already_oklch = []

        # --------------------------------------------------------------
        # Inspect current values
        # --------------------------------------------------------------

        for assembly in assemblies:
            current = (
                assembly.avatar_fallback or ""
            ).strip()

            if (
                is_oklch_color(current)
                and not force_all
            ):
                already_oklch.append(assembly)
                continue

            new_color = generate_oklch_color()

            planned.append(
                {
                    "assembly": assembly,
                    "old_color": current or "(blank)",
                    "new_color": new_color,
                }
            )

        # --------------------------------------------------------------
        # Preview
        # --------------------------------------------------------------

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "ASSEMBLY AVATAR FALLBACK → OKLCH BACKFILL"
            )
        )
        self.stdout.write("")

        if planned:
            self.stdout.write(
                self.style.SUCCESS(
                    "Planned updates:"
                )
            )

            for item in planned:
                assembly = item["assembly"]

                self.stdout.write(
                    f"  {assembly.name}: "
                    f"{item['old_color']} "
                    f"→ {item['new_color']}"
                )

        # --------------------------------------------------------------
        # Summary
        # --------------------------------------------------------------

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Summary"
            )
        )

        self.stdout.write(
            f"  Planned:       {len(planned)}"
        )

        self.stdout.write(
            f"  Already OKLCH: {len(already_oklch)}"
        )

        self.stdout.write(
            f"  Total:         {len(assemblies)}"
        )

        # --------------------------------------------------------------
        # Dry run
        # --------------------------------------------------------------

        if not apply_changes:
            self.stdout.write("")

            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN — no database changes were made."
                )
            )

            self.stdout.write("")
            self.stdout.write(
                "Run with --apply after reviewing the results."
            )

            return

        # --------------------------------------------------------------
        # Nothing to update
        # --------------------------------------------------------------

        if not planned:
            self.stdout.write("")

            self.stdout.write(
                self.style.SUCCESS(
                    "All assemblies already have OKLCH "
                    "avatar fallback colors."
                )
            )

            return

        # --------------------------------------------------------------
        # Apply
        # --------------------------------------------------------------

        now = timezone.now()
        assemblies_to_update = []

        for item in planned:
            assembly = item["assembly"]

            assembly.avatar_fallback = item["new_color"]
            assembly.updated_at = now

            assemblies_to_update.append(assembly)

        with transaction.atomic():
            Church.objects.bulk_update(
                assemblies_to_update,
                fields=[
                    "avatar_fallback",
                    "updated_at",
                ],
                batch_size=500,
            )

        # --------------------------------------------------------------
        # Success
        # --------------------------------------------------------------

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully updated "
                f"{len(assemblies_to_update)} "
                f"assembly avatar fallback colors."
            )
        )