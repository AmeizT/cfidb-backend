from django.core.management.base import BaseCommand
from apps.people.models import Member
from apps.shared.utils import generate_oklch_color

class Command(BaseCommand):
    help = 'Populate avatar_fallback with a randomly generated OKLCH color for all users'

    def handle(self, *args, **kwargs):
        updated = 0

        for member in Member.objects.all():
            member.avatar_fallback = generate_oklch_color()
            member.save(update_fields=['avatar_fallback'])
            updated += 1
                

        self.stdout.write(self.style.SUCCESS(
            f"Updated {updated} user(s) with random OKLCH avatar fallback colors."
        ))