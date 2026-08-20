from django.core.management.base import BaseCommand, CommandError

from apps.examinations.services.cba_students import sync_cba_students


class Command(BaseCommand):
    help = "Fetch and synchronize students from the legacy CBA API."

    def handle(self, *args, **options):
        try:
            result = sync_cba_students()
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "CBA student sync complete: "
                f"received={result['received']}, "
                f"created={result['created']}, "
                f"updated={result['updated']}, "
                f"skipped={result['skipped']}, "
                f"active={result['active_students']}"
            )
        )
