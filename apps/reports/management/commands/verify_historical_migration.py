import json
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.reports.migration.core import assert_local_or_explicitly_authorized, parse_date
from apps.reports.migration.verification import verify_historical_migration


class Command(BaseCommand):
    help = "Read-only verification of historical migration invariants. Never writes to the database."

    def add_arguments(self, parser):
        parser.add_argument("--assembly", help="Assembly primary key or code.")
        parser.add_argument("--from", dest="from_date", help="Inclusive start date (YYYY-MM-DD).")
        parser.add_argument("--to", dest="to_date", help="Inclusive end date (YYYY-MM-DD).")
        parser.add_argument("--format", choices=["human", "json"], default="human")
        parser.add_argument("--output", help="Optional JSON output path (does not write to the database).")

    def handle(self, *args, **options):
        try:
            assert_local_or_explicitly_authorized(apply=False)
            from_date = parse_date(options.get("from_date"), "from")
            to_date = parse_date(options.get("to_date"), "to")
            result = verify_historical_migration(
                assembly=options.get("assembly"), from_date=from_date, to_date=to_date
            )
        except (ValidationError, ImproperlyConfigured) as exc:
            raise CommandError(str(exc)) from exc
        payload = result.payload()
        rendered = json.dumps(payload, indent=2, default=str)
        if options["output"]:
            Path(options["output"]).write_text(rendered + "\n", encoding="utf-8")
        if options["format"] == "json":
            self.stdout.write(rendered)
        else:
            self.stdout.write(
                f"Historical migration verification: {payload['status'].upper()} | "
                + ", ".join(f"{key}={value}" for key, value in sorted(payload["counts"].items()))
            )
            for finding in result.findings:
                self.stdout.write(f"[{finding.severity.upper()}] {finding.code}: {finding.message}")
        if result.blocked:
            raise CommandError("Historical migration verification found blocker/high-risk failures.")
