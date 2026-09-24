from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.bookkeeper.models import Tithe
from apps.churches.models import Church
from apps.people.models import Member
from apps.reports.models import AssemblyReport
from apps.users.models import Role, User


class MemberDataIntegrityTests(TestCase):
    def setUp(self):
        self.assembly = Church.objects.create(name="Member Assembly")
        self.other_assembly = Church.objects.create(name="Other Member Assembly")
        self.admin = User.objects.create_user(
            first_name="Member", last_name="Admin", username="member-admin",
            email="member-admin@example.com", password="password", church=self.assembly,
        )
        self.admin.is_admin = True
        self.admin.save(update_fields=["is_admin"])
        self.other_admin = User.objects.create_user(
            first_name="Other", last_name="Admin", username="other-member-admin",
            email="other-member-admin@example.com", password="password", church=self.other_assembly,
        )
        self.other_admin.roles.add(Role.objects.create(name="Senior Pastor"))
        self.regular_user = User.objects.create_user(
            first_name="Regular", last_name="User", username="regular-member-user",
            email="regular-member-user@example.com", password="password", church=self.assembly,
        )
        self.member = Member.objects.create(
            assembly=self.assembly, member_key="soft-delete-member",
            first_name="Safe", last_name="History", date_of_birth=date(1991, 2, 3),
            phone_number="+26771111111", gender="Female", country="Botswana",
        )
        self.report = AssemblyReport.objects.create(
            assembly=self.assembly, period_start=date(2026, 7, 1), period_end=date(2026, 7, 31),
        )
        self.tithe = Tithe.objects.create(
            assembly=self.assembly, report=self.report, member=self.member,
            amount=Decimal("75.00"), timestamp=date(2026, 7, 4),
        )
        self.client = APIClient()

    def test_delete_hides_member_but_preserves_historical_tithe(self):
        self.client.force_authenticate(self.admin)
        response = self.client.delete(f"/api/v1/people/members/{self.member.member_key}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Member.objects.filter(pk=self.member.pk).exists())
        deleted = Member.all_objects.get(pk=self.member.pk)
        self.assertTrue(deleted.is_trash)
        self.assertIsNotNone(deleted.trash_date)
        self.assertEqual(deleted.updated_by, self.admin)
        self.assertTrue(Tithe.objects.filter(pk=self.tithe.pk, member_id=deleted.pk).exists())

        listing = self.client.get("/api/v1/people/members/")
        self.assertEqual(listing.status_code, 200)
        self.assertNotIn(self.member.member_key, str(listing.data))
        detail = self.client.get(f"/api/v1/people/members/{self.member.member_key}/")
        self.assertEqual(detail.status_code, 404)

    def test_admin_can_edit_and_duplicate_update_is_rejected(self):
        duplicate = Member.objects.create(
            assembly=self.assembly, member_key="duplicate-member",
            first_name="Already", last_name="Exists", date_of_birth=date(1990, 1, 1),
            phone_number="+26772222222", gender="Male", country="Botswana",
        )
        self.client.force_authenticate(self.admin)
        updated = self.client.patch(
            f"/api/v1/people/members/{self.member.member_key}/",
            {"first_name": "Updated", "email": "updated@example.com"},
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        self.member.refresh_from_db()
        self.assertEqual(self.member.first_name, "Updated")
        self.assertEqual(self.member.updated_by, self.admin)

        invalid = self.client.patch(
            f"/api/v1/people/members/{self.member.member_key}/",
            {
                "first_name": duplicate.first_name,
                "last_name": duplicate.last_name,
                "date_of_birth": duplicate.date_of_birth.isoformat(),
                "phone_number": duplicate.phone_number,
            },
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)

    def test_member_writes_require_role_and_assembly_scope(self):
        self.client.force_authenticate(self.regular_user)
        forbidden = self.client.patch(
            f"/api/v1/people/members/{self.member.member_key}/",
            {"first_name": "Forbidden"}, format="json",
        )
        self.assertEqual(forbidden.status_code, 403)

        self.client.force_authenticate(self.other_admin)
        outside_scope = self.client.patch(
            f"/api/v1/people/members/{self.member.member_key}/",
            {"first_name": "Outside"}, format="json",
        )
        self.assertEqual(outside_scope.status_code, 404)

    def test_regular_user_can_delete_visible_member_but_not_edit_or_restore(self):
        self.client.force_authenticate(self.regular_user)
        url = f"/api/v1/people/members/{self.member.member_key}/"
        self.assertEqual(self.client.patch(url, {"first_name": "Denied"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertTrue(Member.all_objects.get(pk=self.member.pk).is_trash)
        self.assertTrue(Tithe.objects.filter(member_id=self.member.pk).exists())
        self.assertEqual(self.client.post(f"{url}restore/").status_code, 403)

    def test_regular_user_cannot_delete_member_outside_visible_assembly(self):
        self.regular_user.church = self.other_assembly
        self.regular_user.save()
        self.client.force_authenticate(self.regular_user)
        self.assertEqual(self.client.delete(f"/api/v1/people/members/{self.member.member_key}/").status_code, 404)
        self.assertTrue(Member.objects.filter(pk=self.member.pk).exists())
