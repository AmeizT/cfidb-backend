from django.core.management.base import BaseCommand
from apps.churches.models import Church

class Command(BaseCommand):
    help = "Capitalize each word in all church names (Title Case)"

    def handle(self, *args, **options):
        churches = Church.objects.all()
        updated = 0
        for church in churches:
            new_name = church.name.title()
            if church.name != new_name:
                church.name = new_name
                church.save(update_fields=["name"])
                updated += 1
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} church names to Title Case."))