from django.core.management.base import BaseCommand
from apps.users.models import User

class Command(BaseCommand):
    help = "Updates user usernames based on email prefix"

    def handle(self, *args, **kwargs):
        updated_count = 0

        for user in User.objects.all():
            if not user.username or len(user.username) > 30:  # UUID check
                base_username = user.email.split('@')[0]
                username = base_username
                counter = 1

                while User.objects.filter(username=username).exclude(pk=user.pk).exists():
                    username = f"{base_username}{counter}"
                    counter += 1

                user.username = username
                user.save()
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f"Updated: {user.email} → {user.username}"))

        self.stdout.write(self.style.SUCCESS(f"✅ Updated {updated_count} user(s)"))