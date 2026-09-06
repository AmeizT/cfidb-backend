from datetime import date
from io import BytesIO
from tempfile import TemporaryDirectory

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.bookkeeper.models import Asset
from apps.churches.models import Church
from apps.people.models import Homecell, Household, Member
from apps.users.models import User


class CreateSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.assembly = Church.objects.create(name="Create A")
        cls.other = Church.objects.create(name="Create B")
        cls.user = User.objects.create_user(
            username="create-test", email="create-test@example.com", password="test-only-password",
            first_name="Create", last_name="Test", church=cls.assembly,
        )
        # All create and isolation checks run as a regular user with no staff roles.
        cls.member = Member.objects.create(assembly=cls.assembly, first_name="Local", last_name="Member",
            date_of_birth=date(1990, 1, 1), gender="Female", country="Botswana")
        cls.foreign = Member.objects.create(assembly=cls.other, first_name="Foreign", last_name="Member",
            date_of_birth=date(1990, 1, 1), gender="Male", country="Botswana")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.scope = {"HTTP_X_ASSEMBLY_ID": str(self.assembly.pk)}

    def contracts(self):
        return [
            ("/api/v1/people/members/", Member, {
                "first_name": "Created", "last_name": "Member", "date_of_birth": "2000-01-01",
                "gender": "Male", "country": "Botswana", "phone_number": "", "ministries": [], "positions": [],
            }, "first_name"),
            ("/api/v1/people/households/", Household, {"name": "Created Household"}, "name"),
            ("/api/v1/people/homecells/", Homecell, {"group_name": "Created Homecell"}, "group_name"),
            ("/api/v1/bookkeeper/assets/", Asset, {"item_name": "Created Asset", "acquisition_date": "2026-01-01",
                "asset_type": "Furniture", "condition": "Good", "units": 1}, "item_name"),
        ]

    def test_each_create_is_persisted_and_readable_in_active_assembly(self):
        for endpoint, model, payload, _ in self.contracts():
            with self.subTest(endpoint=endpoint):
                before = model.objects.count()
                response = self.client.post(endpoint, payload, format="json", **self.scope)
                self.assertEqual(response.status_code, 201, response.data)
                self.assertEqual(model.objects.count(), before + 1)
                key = response.data.get("member_key") if model is Member else response.data["id"]
                read = self.client.get(f"{endpoint}{key}/", **self.scope)
                self.assertEqual(read.status_code, 200, read.data)
                assembly = read.data["assembly"]
                self.assertEqual(assembly["id"] if isinstance(assembly, dict) else assembly, self.assembly.pk)
                if model is Member:
                    self.assertNotIn("access_pin", read.data)

    def test_anonymous_cannot_create_or_load_selectors(self):
        self.client.force_authenticate(None)
        for endpoint, model, payload, _ in self.contracts():
            before = model.objects.count()
            self.assertIn(self.client.post(endpoint, payload, format="json").status_code, [401, 403])
            self.assertEqual(model.objects.count(), before)
        self.assertIn(self.client.post("/api/v1/people/create-options/", {}, format="json").status_code, [401, 403])

    def test_foreign_assembly_and_stale_workspace_are_rejected(self):
        for endpoint, model, payload, _ in self.contracts():
            with self.subTest(endpoint=endpoint):
                before = model.objects.count()
                for headers, extra in [({}, {"assembly": self.other.pk}),
                                       ({"HTTP_X_ASSEMBLY_ID": str(self.other.pk)}, {})]:
                    response = self.client.post(endpoint, {**payload, **extra}, format="json", **headers)
                    self.assertIn(response.status_code, [400, 403], response.data)
                    self.assertEqual(model.objects.count(), before)

    def test_required_fields_reject_missing_values_without_writes(self):
        for endpoint, model, payload, required in self.contracts():
            before = model.objects.count()
            del payload[required]
            response = self.client.post(endpoint, payload, format="json", **self.scope)
            self.assertEqual(response.status_code, 400)
            self.assertIn(required, response.data)
            self.assertEqual(model.objects.count(), before)

    def test_member_relationships_reject_foreign_and_missing_ids(self):
        endpoint, _, payload, _ = self.contracts()[0]
        for member_id in [self.foreign.pk, 9999999]:
            self.assertEqual(self.client.post(endpoint, {**payload, "spouse": member_id}, format="json").status_code, 400)
        response = self.client.post(endpoint, {**payload, "spouse": self.member.pk}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Member.objects.get(pk=response.data["id"]).spouse_id, self.member.pk)

    def test_homecell_relationships_reject_foreign_and_missing_ids(self):
        endpoint = "/api/v1/people/homecells/"
        for key in ["leader_id", "member_ids"]:
            for member_id in [self.foreign.pk, 9999999]:
                value = [member_id] if key == "member_ids" else member_id
                response = self.client.post(endpoint, {"group_name": "Invalid", key: value}, format="json")
                self.assertEqual(response.status_code, 400, response.data)
                self.assertFalse(Homecell.objects.exists())
        response = self.client.post(endpoint, {"group_name": "Valid", "leader_id": self.member.pk, "member_ids": [self.member.pk]}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(list(Homecell.objects.get(pk=response.data["id"]).members.values_list("pk", flat=True)), [self.member.pk])

    def test_household_member_must_belong_to_household_assembly(self):
        household = Household.objects.create(assembly=self.assembly, name="Local")
        for endpoint, extra in [(f"/api/v1/people/households/{household.pk}/add-member/", {}),
                                ("/api/v1/people/household-members/", {"household": household.pk})]:
            response = self.client.post(endpoint, {**extra, "member": self.foreign.pk, "role": "adult", "joined_on": "2026-01-01"}, format="json")
            self.assertEqual(response.status_code, 400, response.data)
        foreign_household = Household.objects.create(assembly=self.other, name="Foreign")
        response = self.client.post("/api/v1/people/household-members/", {"household": foreign_household.pk, "member": self.foreign.pk, "role": "adult", "joined_on": "2026-01-01"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_household_updates_cannot_reassign_ownership_to_an_unauthorized_assembly(self):
        from apps.people.models import HouseholdMember
        local = Household.objects.create(assembly=self.assembly, name="Owned")
        foreign = Household.objects.create(assembly=self.other, name="Other owned")
        endpoint = f"/api/v1/people/households/{local.pk}/"
        response = self.client.patch(endpoint, {"assembly": self.other.pk}, format="json")
        self.assertEqual(response.status_code, 403)
        membership = HouseholdMember.objects.create(household=local, member=self.member, role="adult", joined_on=date(2026, 1, 1))
        response = self.client.patch(f"/api/v1/people/household-members/{membership.pk}/",
            {"household": foreign.pk, "member": self.foreign.pk}, format="json")
        self.assertEqual(response.status_code, 403)
        membership.refresh_from_db()
        self.assertEqual(membership.household_id, local.pk)

    def test_malformed_member_fields_are_rejected(self):
        endpoint, _, payload, _ = self.contracts()[0]
        for field, invalid in [("date_of_birth", "2026-02-30"), ("gender", "invalid"), ("email", "invalid"),
                               ("phone_number", "abc"), ("membership_status", "invalid"), ("ministries", ["unknown"]),
                               ("positions", ["unknown"])]:
            with self.subTest(field=field):
                response = self.client.post(endpoint, {**payload, field: invalid}, format="json")
                self.assertEqual(response.status_code, 400, response.data)
                self.assertIn(field, response.data)

    def test_asset_validation_and_server_owned_author(self):
        endpoint, _, payload, _ = self.contracts()[3]
        for field, value in [("units", -1), ("units", "abc"), ("acquisition_date", "2026-02-30"),
                             ("asset_type", "invalid"), ("condition", "invalid"), ("acquisition_cost", "NaN"),
                             ("residual", "1.234")]:
            response = self.client.post(endpoint, {**payload, field: value}, format="json")
            self.assertEqual(response.status_code, 400, response.data)
        response = self.client.post(endpoint, {**payload, "created_by": 999999, "acquisition_cost": "123.45"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        asset = Asset.objects.get(pk=response.data["id"])
        self.assertEqual(asset.created_by_id, self.user.pk)
        self.assertEqual(str(asset.acquisition_cost), "123.45")

    def test_selector_data_is_minimal_and_changes_with_workspace(self):
        endpoint = "/api/v1/people/create-options/"
        response = self.client.post(endpoint, {}, format="json", **self.scope)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["members"], [{"id": self.member.pk, "label": self.member.full_name}])
        self.user.church = self.other
        self.user.save(update_fields=["church"])
        self.assertEqual(self.client.post(endpoint, {}, format="json", **self.scope).status_code, 400)
        response = self.client.post(endpoint, {}, format="json", HTTP_X_ASSEMBLY_ID=str(self.other.pk))
        self.assertEqual(response.data["members"], [{"id": self.foreign.pk, "label": self.foreign.full_name}])

    def test_asset_images_validate_content_size_and_persist(self):
        endpoint, _, payload, _ = self.contracts()[3]
        invalid = SimpleUploadedFile("file.png", b"<script>invalid</script>", content_type="image/png")
        response = self.client.post(endpoint, {**payload, "asset_images": [invalid]}, format="multipart")
        self.assertEqual(response.status_code, 400, response.data)
        output = BytesIO()
        Image.new("RGB", (2, 2)).save(output, "PNG")
        oversized = SimpleUploadedFile("large.png", output.getvalue() + b"0" * (501 * 1024), content_type="image/png")
        self.assertEqual(self.client.post(endpoint, {**payload, "asset_images": [oversized]}, format="multipart").status_code, 400)
        self.assertFalse(Asset.objects.exists())
        with TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            valid = SimpleUploadedFile("image.png", output.getvalue(), content_type="image/png")
            response = self.client.post(endpoint, {**payload, "asset_images": [valid]}, format="multipart")
            self.assertEqual(response.status_code, 201, response.data)
            self.assertEqual(Asset.objects.get(pk=response.data["id"]).asset_images.count(), 1)

    def test_member_image_multipart_preserves_empty_relationship_lists(self):
        endpoint, _, payload, _ = self.contracts()[0]
        output = BytesIO()
        Image.new("RGB", (2, 2)).save(output, "PNG")
        with TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            photo = SimpleUploadedFile("avatar.png", output.getvalue(), content_type="image/png")
            response = self.client.post(endpoint, {**payload, "avatar": photo}, format="multipart", **self.scope)
            self.assertEqual(response.status_code, 201, response.data)
            read = self.client.get(f"{endpoint}{response.data['member_key']}/")
            self.assertEqual(read.status_code, 200)
            self.assertTrue(read.data["avatar"])

    def test_regular_user_can_create_but_cannot_assign_audit_fields_or_manage_members(self):
        endpoint, _, payload, _ = self.contracts()[0]
        ordinary = User.objects.create_user(username="ordinary-create", email="ordinary@example.com",
            first_name="Ordinary", last_name="Test", password="test-only", church=self.assembly)
        self.client.force_authenticate(ordinary)
        options = self.client.post("/api/v1/people/create-options/", {}, format="json")
        self.assertEqual(options.status_code, 200)
        self.assertTrue(options.data["can_create_member"])
        response = self.client.post(endpoint, {**payload, "created_by": self.user.pk, "updated_by": self.user.pk,
            "access_pin": "not-allowed", "is_trash": True}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        saved = Member.objects.get(pk=response.data["id"])
        self.assertEqual(saved.created_by_id, ordinary.pk)
        self.assertEqual(saved.updated_by_id, ordinary.pk)
        self.assertFalse(saved.is_trash)
        self.assertEqual(saved.access_pin, "")
        detail = f"{endpoint}{saved.member_key}/"
        read = self.client.get(detail)
        self.assertEqual(read.status_code, 200)
        self.assertEqual(read.data["assembly"], self.assembly.pk)
        self.assertEqual(self.client.patch(detail, {"first_name": "Changed"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(detail).status_code, 403)
        self.assertEqual(self.client.post(f"{detail}restore/", {}, format="json").status_code, 403)
