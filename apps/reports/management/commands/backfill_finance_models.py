from apps.reports.management.commands._historical_base import HistoricalMigrationCommand
from apps.reports.migration.runner import backfill_finance_models


class Command(HistoricalMigrationCommand):
    help = "Migrate authoritative legacy finance components (dry-run unless --apply)."
    runner = staticmethod(backfill_finance_models)

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--allow-post-cutoff",
            action="store_true",
            help="Exceptional manually approved override for legacy rows dated on/after 2026-08-01.",
        )

    def runner_kwargs(self, options):
        return {"allow_post_cutoff": options["allow_post_cutoff"]}
