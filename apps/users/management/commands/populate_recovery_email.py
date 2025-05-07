from django.core.management.base import BaseCommand
from apps.users.models import User

class Command(BaseCommand):
    help = 'Populate recovery_email field with existing email value for all users where recovery_email is empty.'

    def handle(self, *args, **options):
        users_to_update = User.objects.filter(recovery_email__isnull=True).exclude(email__isnull=True)

        count = 0
        for user in users_to_update:
            user.recovery_email = user.email
            user.save(update_fields=['recovery_email'])
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Updated {count} user(s) with recovery_email.'))