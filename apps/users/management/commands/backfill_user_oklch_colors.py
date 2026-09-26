from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.shared.utils import generate_oklch_color
from apps.users.models import User


def is_oklch_color(value):
    """
    Return True when the stored avatar fallback already looks like
    an OKLCH CSS color.

    Examples:
        oklch(65% 0.18 240)
        oklch(0.65 0.18 240)
    """
    if not isinstance(value, str):
        return False

    value = value.strip().lower()

    return value.startswith("oklch(") and value.endswith(")")


class Command(BaseCommand):
    help = (
        "Backfill User.avatar_fallback values with OKLCH colors. "
        "Existing OKLCH colors are preserved unless --force-all is used. "
        "Dry-run by default."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist changes. Without this flag no database changes are made.",
        )

        parser.add_argument(
            "--force-all",
            action="store_true",
            help=(
                "Generate a new OKLCH color for every user, including users "
                "who already have a valid OKLCH avatar fallback."
            ),
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        force_all = options["force_all"]

        users = list(
            User.objects
            .only(
                "id",
                "username",
                "avatar_fallback",
                "updated_at",
            )
            .order_by("id")
        )

        planned = []
        already_oklch = []

        # ------------------------------------------------------------------
        # Inspect users
        # ------------------------------------------------------------------

        for user in users:
            current = (user.avatar_fallback or "").strip()

            if is_oklch_color(current) and not force_all:
                already_oklch.append(user)
                continue

            new_color = generate_oklch_color()

            planned.append(
                {
                    "user": user,
                    "old_color": current or "(blank)",
                    "new_color": new_color,
                }
            )

        # ------------------------------------------------------------------
        # Preview
        # ------------------------------------------------------------------

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "USER AVATAR FALLBACK → OKLCH BACKFILL"
            )
        )
        self.stdout.write("")

        if planned:
            self.stdout.write(
                self.style.SUCCESS("Planned updates:")
            )

            for item in planned:
                user = item["user"]

                self.stdout.write(
                    f"  {user.username or f'User #{user.pk}'}: "
                    f"{item['old_color']} → {item['new_color']}"
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING("Summary")
        )

        self.stdout.write(
            f"  Planned:       {len(planned)}"
        )

        self.stdout.write(
            f"  Already OKLCH: {len(already_oklch)}"
        )

        self.stdout.write(
            f"  Total users:   {len(users)}"
        )

        # ------------------------------------------------------------------
        # Dry run
        # ------------------------------------------------------------------

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

        # ------------------------------------------------------------------
        # Nothing to do
        # ------------------------------------------------------------------

        if not planned:
            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    "All users already have OKLCH avatar fallback colors."
                )
            )
            return

        # ------------------------------------------------------------------
        # Apply
        # ------------------------------------------------------------------

        now = timezone.now()
        users_to_update = []

        for item in planned:
            user = item["user"]

            user.avatar_fallback = item["new_color"]
            user.updated_at = now

            users_to_update.append(user)

        with transaction.atomic():
            User.objects.bulk_update(
                users_to_update,
                fields=[
                    "avatar_fallback",
                    "updated_at",
                ],
                batch_size=500,
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully updated "
                f"{len(users_to_update)} user avatar fallback colors."
            )
        )