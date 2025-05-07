from apps.users.models import User
from django.core.management.base import BaseCommand
from apps.users.utils.colors import generate_oklch_color

class Command(BaseCommand):
    help = 'Populate avatar_fallback with a randomly generated OKLCH color for all users'

    def handle(self, *args, **kwargs):
        updated = 0

        for user in User.objects.all():
            user.avatar_fallback = generate_oklch_color()
            user.save(update_fields=['avatar_fallback'])
            updated += 1
                

        self.stdout.write(self.style.SUCCESS(
            f"Updated {updated} user(s) with random OKLCH avatar fallback colors."
        ))