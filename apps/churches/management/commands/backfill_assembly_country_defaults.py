from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.churches.country_defaults import get_country_defaults
from apps.churches.models import Church, AssemblyCurrency


class Command(BaseCommand):
    help = (
        "Backfill missing assembly currencies and locales from country defaults. "
        "Existing currency values are preserved. "
        "Dry-run by default; use --apply to persist changes."
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

    def handle(self, *args, **options):
        apply_changes = options["apply"]

        assemblies = (
            Church.objects
            .prefetch_related("currencies")
            .order_by("country", "name")
        )

        planned = []
        already_complete = []
        unmapped = []
        warnings = []

        # ------------------------------------------------------------------
        # Inspect assemblies
        # ------------------------------------------------------------------

        for assembly in assemblies:
            currencies = list(assembly.currencies.all())  # type: ignore

            # Preserve an existing primary currency, even if it differs
            # from the country's normal/default currency.
            primary_currency = next(
                (
                    item
                    for item in currencies
                    if item.is_primary
                ),
                None,
            )

            legacy_currency = (
                (assembly.currency or "")
                .strip()
                .upper()
            )

            locale = (
                (assembly.locale or "")
                .strip()
            )

            defaults = get_country_defaults(
                country_code=assembly.country_code,
                country=assembly.country,
            )

            # --------------------------------------------------------------
            # Determine whether country defaults are required
            # --------------------------------------------------------------

            needs_locale_default = not locale

            needs_currency_default = (
                primary_currency is None
                and not legacy_currency
            )

            if (
                (needs_locale_default or needs_currency_default)
                and not defaults
            ):
                unmapped.append(
                    (
                        assembly,
                        needs_locale_default,
                        needs_currency_default,
                    )
                )
                continue

            default_currency = (
                defaults["currency"].upper()
                if defaults
                else None
            )

            default_locale = (
                defaults["locale"]
                if defaults
                else None
            )

            # --------------------------------------------------------------
            # Determine authoritative currency
            # --------------------------------------------------------------

            if primary_currency:
                target_currency = (
                    primary_currency.currency
                    .strip()
                    .upper()
                )

            elif legacy_currency:
                target_currency = legacy_currency

            else:
                target_currency = default_currency

            if not target_currency:
                unmapped.append(
                    (
                        assembly,
                        needs_locale_default,
                        True,
                    )
                )
                continue

            changes = []

            # --------------------------------------------------------------
            # Locale
            # --------------------------------------------------------------

            if not locale and default_locale:
                changes.append(
                    f"locale: blank → {default_locale}"
                )

            # --------------------------------------------------------------
            # Legacy Church.currency
            #
            # If a primary currency already exists, use that value instead
            # of blindly applying the country default.
            # --------------------------------------------------------------

            if not legacy_currency:
                changes.append(
                    f"currency: blank → {target_currency}"
                )

            # --------------------------------------------------------------
            # Primary AssemblyCurrency
            # --------------------------------------------------------------

            matching_currency = next(
                (
                    item
                    for item in currencies
                    if (
                        (item.currency or "")
                        .strip()
                        .upper()
                        == target_currency
                    )
                ),
                None,
            )

            if primary_currency is None:
                if matching_currency:
                    changes.append(
                        f"primary currency: "
                        f"{matching_currency.currency} "
                        f"→ primary"
                    )

                    if not matching_currency.is_active:
                        changes.append(
                            f"currency {matching_currency.currency}: "
                            f"inactive → active"
                        )
                else:
                    changes.append(
                        f"primary currency: none → {target_currency}"
                    )

            # --------------------------------------------------------------
            # Non-blocking consistency warnings
            # --------------------------------------------------------------

            if (
                primary_currency
                and legacy_currency
                and primary_currency.currency.strip().upper()
                != legacy_currency
            ):
                warnings.append(
                    (
                        assembly,
                        "Church.currency "
                        f"({legacy_currency}) differs from primary "
                        "AssemblyCurrency "
                        f"({primary_currency.currency.upper()}). "
                        "Existing values will be preserved.",
                    )
                )

            if primary_currency and not primary_currency.is_active:
                warnings.append(
                    (
                        assembly,
                        f"Primary currency "
                        f"{primary_currency.currency.upper()} "
                        "is inactive. It will not be changed "
                        "by this backfill.",
                    )
                )

            # --------------------------------------------------------------
            # Store plan
            # --------------------------------------------------------------

            if changes:
                planned.append(
                    {
                        "assembly": assembly,
                        "target_currency": target_currency,
                        "target_locale": default_locale,
                        "changes": changes,
                    }
                )
            else:
                already_complete.append(assembly)

        # ------------------------------------------------------------------
        # Preview
        # ------------------------------------------------------------------

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "ASSEMBLY COUNTRY DEFAULTS BACKFILL"
            )
        )
        self.stdout.write("")

        if planned:
            self.stdout.write(
                self.style.SUCCESS("Planned updates:")
            )

            for item in planned:
                assembly = item["assembly"]

                self.stdout.write("")
                self.stdout.write(
                    f"  {assembly.name} "
                    f"[{assembly.country or assembly.country_code}]"
                )

                for change in item["changes"]:
                    self.stdout.write(
                        f"    - {change}"
                    )

        # ------------------------------------------------------------------
        # Warnings
        # ------------------------------------------------------------------

        if warnings:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "Existing values preserved:"
                )
            )

            for assembly, message in warnings:
                self.stdout.write(
                    f"  {assembly.name}: {message}"
                )

        # ------------------------------------------------------------------
        # Unmapped
        # ------------------------------------------------------------------

        if unmapped:
            self.stdout.write("")
            self.stdout.write(
                self.style.ERROR(
                    "Unmapped countries:"
                )
            )

            for (
                assembly,
                needs_locale,
                needs_currency,
            ) in unmapped:
                missing = []

                if needs_currency:
                    missing.append("currency")

                if needs_locale:
                    missing.append("locale")

                self.stdout.write(
                    f"  {assembly.name}: "
                    f"country='{assembly.country}' "
                    f"country_code='{assembly.country_code}' "
                    f"missing={', '.join(missing)}"
                )

        # ------------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------------

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING("Summary")
        )

        self.stdout.write(
            f"  Planned:          {len(planned)}"
        )

        self.stdout.write(
            f"  Already complete: {len(already_complete)}"
        )

        self.stdout.write(
            f"  Warnings:         {len(warnings)}"
        )

        self.stdout.write(
            f"  Unmapped:         {len(unmapped)}"
        )

        self.stdout.write(
            f"  Total:            {assemblies.count()}"
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

            if unmapped:
                self.stdout.write(
                    self.style.WARNING(
                        "Resolve unmapped countries before applying."
                    )
                )

            return

        # ------------------------------------------------------------------
        # Safety
        # ------------------------------------------------------------------

        if unmapped:
            raise CommandError(
                f"{len(unmapped)} assembly/assemblies require country "
                "defaults that could not be resolved. "
                "No database changes were made."
            )

        if not planned:
            self.stdout.write("")

            self.stdout.write(
                self.style.SUCCESS(
                    "All assemblies already have the required "
                    "currency and locale data. Nothing to update."
                )
            )

            return

        # ------------------------------------------------------------------
        # Apply
        # ------------------------------------------------------------------

        with transaction.atomic():
            for item in planned:
                assembly = item["assembly"]
                target_currency = item["target_currency"]
                target_locale = item["target_locale"]

                update_fields = []

                # ----------------------------------------------------------
                # Locale
                # ----------------------------------------------------------

                if (
                    not (assembly.locale or "").strip()
                    and target_locale
                ):
                    assembly.locale = target_locale
                    update_fields.append("locale")

                # ----------------------------------------------------------
                # Legacy Church.currency
                # ----------------------------------------------------------

                if not (assembly.currency or "").strip():
                    assembly.currency = target_currency
                    update_fields.append("currency")

                if update_fields:
                    assembly.save(
                        update_fields=[
                            *update_fields,
                            "updated_at",
                        ]
                    )

                # ----------------------------------------------------------
                # Primary AssemblyCurrency
                # ----------------------------------------------------------

                existing_primary = (
                    AssemblyCurrency.objects
                    .filter(
                        assembly=assembly,
                        is_primary=True,
                    )
                    .first()
                )

                # Existing primary currency is authoritative.
                if existing_primary:
                    continue

                matching_currency = (
                    AssemblyCurrency.objects
                    .filter(
                        assembly=assembly,
                        currency__iexact=target_currency,
                    )
                    .first()
                )

                if matching_currency:
                    matching_currency.currency = target_currency
                    matching_currency.is_primary = True
                    matching_currency.is_active = True

                    matching_currency.save(
                        update_fields=[
                            "currency",
                            "is_primary",
                            "is_active",
                        ]
                    )

                else:
                    AssemblyCurrency.objects.create(
                        assembly=assembly,
                        currency=target_currency,
                        is_primary=True,
                        is_active=True,
                    )

        # ------------------------------------------------------------------
        # Success
        # ------------------------------------------------------------------

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully backfilled "
                f"{len(planned)} assemblies."
            )
        )