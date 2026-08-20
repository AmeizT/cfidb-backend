from datetime import date

from apps.reports.management.commands._historical_base import HistoricalMigrationCommand
from apps.reports.migration.runner import backfill_attendance_headcounts


class Command(HistoricalMigrationCommand):
    help = "Backfill historical attendance semantics (dry-run unless --apply)."
    runner = staticmethod(backfill_attendance_headcounts)

    def handle(self, *args, **options):
        if not options.get("to_date"):
            options["to_date"] = date(2026, 8, 31).isoformat()
        return super().handle(*args, **options)
