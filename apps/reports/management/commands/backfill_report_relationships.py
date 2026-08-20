from apps.reports.management.commands._historical_base import HistoricalMigrationCommand
from apps.reports.migration.runner import backfill_report_relationships


class Command(HistoricalMigrationCommand):
    help = "Link historical source rows to canonical reports (dry-run unless --apply)."
    runner = staticmethod(backfill_report_relationships)
