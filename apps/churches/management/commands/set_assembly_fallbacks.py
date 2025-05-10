from apps.churches.models import Church
from django.core.management.base import BaseCommand
from apps.shared.utils import generate_oklch_color

class Command(BaseCommand):
    help = 'Populate avatar_fallback with a randomly generated OKLCH color for all assemblies'

    def handle(self, *args, **kwargs):
        updated = 0

        for assembly in Church.objects.all():
            assembly.avatar_fallback = generate_oklch_color()
            assembly.save(update_fields=['avatar_fallback'])
            updated += 1
                

        self.stdout.write(self.style.SUCCESS(
            f"Updated {updated} assemblies with random OKLCH avatar fallback colors."
        ))