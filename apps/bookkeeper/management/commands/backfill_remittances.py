from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Retired unsafe command. Use backfill_finance_models after verification."

    def handle(self, *args, **options):
        raise CommandError(
            "backfill_remittances is retired because it treated calculated remittance as paid. "
            "Use backfill_finance_models (dry-run by default) to create obligations and evidence-backed payments."
        )
