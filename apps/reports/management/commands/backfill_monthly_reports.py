from apps.reports.management.commands._historical_base import HistoricalMigrationCommand
from apps.reports.migration.runner import backfill_monthly_reports


class Command(HistoricalMigrationCommand):
    help = "Create canonical historical monthly reports (dry-run unless --apply)."
    runner = staticmethod(backfill_monthly_reports)
