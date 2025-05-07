from nanoid import generate # type: ignore
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()

class Command(BaseCommand):
    help = "Replace all existing user_id values with NanoIDs"

    def handle(self, *args, **kwargs):
        updated = 0

        users = User.objects.all()
        for user in users:
            new_id = generate(size=12)

            # Optionally handle collisions
            while User.objects.filter(user_id=new_id).exists():
                new_id = generate(size=12)

            user.user_id = new_id
            user.save(update_fields=["user_id"])
            updated += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Updated {updated} user_id(s) to NanoID format"))