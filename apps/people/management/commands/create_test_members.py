from django.core.management.base import BaseCommand
from datetime import date
from apps.people.models import Member

class Command(BaseCommand):
    help = "Create 20 test members for development and testing"

    def handle(self, *args, **kwargs):
        names = [
            ("John", "Michael", "Doe"),
            ("Jane", "Elizabeth", "Smith"),
            ("David", "Alexander", "Brown"),
            ("Emily", "Sophia", "Johnson"),
            ("Daniel", "William", "Martins"),
            ("Sophia", "Grace", "Anderson"),
            ("James", "Matthew", "Lee"),
            ("Olivia", "Marie", "Harris"),
            ("Benjamin", "Samuel", "Davis"),
            ("Charlotte", "Rose", "Wilson"),
            ("Ethan", "Joseph", "Taylor"),
            ("Amelia", "Faith", "Thomas"),
            ("Mason", "Andrew", "Moore"),
            ("Ava", "Louise", "Jackson"),
            ("Liam", "Christopher", "White"),
            ("Isabella", "Ann", "Harris"),
            ("Lucas", "Daniel", "Clark"),
            ("Mia", "Isabelle", "Lewis"),
            ("Noah", "Jonathan", "Walker"),
            ("Emma", "Nicole", "Hall"),
        ]

        test_members = []
        for i, (first_name, middle_name, last_name) in enumerate(names, start=1):
            test_members.append(
                Member(
                    church_id=2,
                    prefix="Mr." if i % 2 == 0 else "Ms.",
                    first_name=first_name,
                    middle_name=middle_name,
                    last_name=last_name,
                    date_of_birth=date(1990 + (i % 10), (i % 12) + 1, (i % 28) + 1),
                    gender="Male" if i % 2 == 0 else "Female",
                    relationship="Single",
                    occupation="Engineer" if i % 3 == 0 else "Teacher",
                    address=f"Street {i}, Windhoek",
                    city="Windhoek",
                    country="Namibia",
                    phone_number=f"+264 81 000 000{i}",
                    email=f"user{i}@example.com",
                    membersince=date(2020, 1, 1),
                    membership_status="Established",
                    ministry="Youth Ministry" if i % 2 == 0 else "Music Ministry",
                    position="Member",
                    baptized_at=date(2005, 6, 15),
                    avatar_fallback="default.png",
                )
            )

        Member.objects.bulk_create(test_members)
        self.stdout.write(self.style.SUCCESS("Successfully added 20 test members"))