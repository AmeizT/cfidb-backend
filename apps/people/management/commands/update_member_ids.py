from nanoid import generate # type: ignore
from apps.people.models import Member
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Overwrite all existing member_key values with NanoID'

    def handle(self, *args, **kwargs):
        updated_count = 0
        for member in Member.objects.all():
            old_id = member.member_key
            new_id = generate(size=12)

            if old_id != new_id:
                member.member_key = new_id
                member.save(update_fields=['member_key'])
                updated_count += 1
                self.stdout.write(f"Updated member {member.id} from {old_id} to {new_id}")

        self.stdout.write(self.style.SUCCESS(f"✅ Successfully updated {updated_count} member_key(s)."))