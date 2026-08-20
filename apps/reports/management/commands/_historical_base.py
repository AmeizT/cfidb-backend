import json

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.reports.migration.core import (
    assert_local_or_explicitly_authorized,
    mapping_metadata,
    parse_date,
)


class HistoricalMigrationCommand(BaseCommand):
    runner = None

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Apply writes. Omit for dry-run.")
        parser.add_argument("--dry-run", action="store_true", help="Explicitly request the default no-write mode.")
        parser.add_argument("--verify-only", action="store_true", help="Run the read-only verifier instead.")
        parser.add_argument("--assembly", help="Assembly primary key or code.")
        parser.add_argument("--from", dest="from_date", help="Inclusive start date (YYYY-MM-DD).")
        parser.add_argument("--to", dest="to_date", help="Inclusive end date (YYYY-MM-DD).")

    def runner_kwargs(self, options):
        return {}

    def handle(self, *args, **options):
        if options["apply"] and options["dry_run"]:
            raise CommandError("Choose either --apply or --dry-run, not both.")
        if options["verify_only"] and options["apply"]:
            raise CommandError("--verify-only cannot be combined with --apply.")
        try:
            from_date = parse_date(options.get("from_date"), "from")
            to_date = parse_date(options.get("to_date"), "to")
            if from_date and to_date and from_date > to_date:
                raise ValidationError({"date_range": "--from must not be after --to."})
            assert_local_or_explicitly_authorized(apply=options["apply"])
        except (ValidationError, ImproperlyConfigured) as exc:
            raise CommandError(str(exc)) from exc
        if options["verify_only"]:
            from apps.reports.migration.verification import verify_historical_migration
            verification = verify_historical_migration(
                assembly=options.get("assembly"), from_date=from_date, to_date=to_date
            )
            self.stdout.write(json.dumps(verification.payload(), indent=2, default=str))
            if verification.blocked:
                raise CommandError("Historical migration verification found blockers.")
            return
        try:
            result = self.runner(
                apply=options["apply"],
                assembly=options.get("assembly"),
                from_date=from_date,
                to_date=to_date,
                **self.runner_kwargs(options),
            )
        except ValidationError as exc:
            raise CommandError(str(exc)) from exc
        mode = "APPLY" if options["apply"] else "DRY-RUN (NO WRITES)"
        self.stdout.write(f"{mode} | run_id={result.run_id}")
        for message in result.messages:
            self.stdout.write(message)
        self.stdout.write(json.dumps({
            "run_id": str(result.run_id),
            "dry_run": result.dry_run,
            "created": result.created,
            "updated": result.updated,
            "skipped": result.skipped,
            "conflicts": result.conflicts,
            "mapping": mapping_metadata(),
        }, sort_keys=True))
        if result.conflicts:
            raise CommandError(f"{result.conflicts} conflict(s) require manual review.")
