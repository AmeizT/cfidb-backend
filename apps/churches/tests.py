from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.churches.models import Church, Region, RegionLeadership, Zone
from apps.users.models import User


class ChurchAppearanceAPITests(APITestCase):
    def setUp(self):
        self.assembly = Church.objects.create(name="Appearance Assembly")
        self.admin = User.objects.create_user(
            username="appearance-admin",
            email="appearance-admin@example.com",
            password="password123",
            church=self.assembly,
            is_admin=True,
        )
        self.member = User.objects.create_user(
            username="appearance-member",
            email="appearance-member@example.com",
            password="password123",
            church=self.assembly,
        )
        self.url = reverse("assemblies-appearance")

    def test_admin_can_update_active_assembly_appearance(self):
        self.client.force_authenticate(user=self.admin)
        color = "oklch(0.58 0.23 275)"

        response = self.client.patch(self.url, {"avatar_fallback": color}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assembly.refresh_from_db()
        self.assertEqual(self.assembly.avatar_fallback, color)

    def test_admin_can_patch_appearance_by_public_id(self):
        self.client.force_authenticate(user=self.admin)
        color = "oklch(0.59 0.24 305)"
        url = reverse(
            "assemblies-detail",
            kwargs={"public_id": self.assembly.public_id},
        )

        response = self.client.patch(
            url,
            {"avatar_fallback": color},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["public_id"], self.assembly.public_id)
        self.assembly.refresh_from_db()
        self.assertEqual(self.assembly.avatar_fallback, color)

    def test_numeric_database_id_is_not_a_valid_detail_lookup(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f"/api/v1/churches/assemblies/{self.assembly.id}/",
            {"avatar_fallback": "oklch(0.59 0.24 305)"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_regular_member_cannot_update_appearance(self):
        self.client.force_authenticate(user=self.member)

        response = self.client.patch(
            self.url,
            {"avatar_fallback": "oklch(0.58 0.23 275)"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_appearance_rejects_color_outside_palette(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"avatar_fallback": "oklch(0.10 0.10 10)"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RegionalDirectoryAPITests(APITestCase):
    def setUp(self):
        self.region = Region.objects.create(name="Eastern Africa", code="EAF")
        self.other_region = Region.objects.create(name="Southern Africa", code="SAF")

        self.zone = Zone.objects.create(region=self.region, name="East Zone")
        self.other_zone = Zone.objects.create(region=self.other_region, name="South Zone")

        self.regional_staff = self.create_user(
            "regional.staff@example.com",
            first_name="Regional",
            last_name="Staff",
        )
        RegionLeadership.objects.create(
            region=self.region,
            user=self.regional_staff,
            role=RegionLeadership.Role.OVERSEER,
            is_active=True,
        )

        self.regular_user = self.create_user(
            "regular.user@example.com",
            first_name="Regular",
            last_name="User",
        )

        self.region_churches = [
            Church.objects.create(
                name=f"Assembly {index:02d}",
                code=f"EAF-{index:03d}",
                zone=self.zone,
                city="Nairobi",
                country="Kenya",
                country_code="KE",
                currency="KES",
            )
            for index in range(11)
        ]
        self.alpha_church = Church.objects.create(
            name="Alpha Assembly",
            code="EAF-999",
            zone=self.zone,
            city="Kampala",
            country="Uganda",
            country_code="UG",
            currency="UGX",
        )
        self.outside_church = Church.objects.create(
            name="Outside Assembly",
            code="SAF-001",
            zone=self.other_zone,
            city="Gaborone",
            country="Botswana",
            country_code="BW",
            currency="BWP",
        )

        self.region_users = [
            self.create_user(
                f"regional.user{index}@example.com",
                first_name=f"Regional{index}",
                last_name="Member",
                church=self.region_churches[index % len(self.region_churches)],
            )
            for index in range(6)
        ]
        self.alpha_user = self.create_user(
            "alpha.user@example.com",
            first_name="Alpha",
            last_name="Member",
            church=self.alpha_church,
        )
        self.outside_user = self.create_user(
            "outside.user@example.com",
            first_name="Outside",
            last_name="Member",
            church=self.outside_church,
        )

        self.churches_url = reverse("regional-churches")
        self.users_url = reverse("regional-users")

    def create_user(self, email, first_name="Test", last_name="User", church=None):
        return User.objects.create_user(
            first_name=first_name,
            last_name=last_name,
            username=email.split("@")[0],
            email=email,
            password="password123",
            church=church,
        )

    def authenticate_regional_staff(self):
        self.client.force_authenticate(user=self.regional_staff)

    def test_regional_staff_can_list_region_churches(self):
        self.authenticate_regional_staff()

        response = self.client.get(self.churches_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 12)
        self.assertEqual(len(response.data["results"]), 10)
        self.assertIn("table_schema", response.data)
        self.assertIn("churches", response.data["table_schemas"])

    def test_regular_user_cannot_list_region_churches(self):
        self.client.force_authenticate(user=self.regular_user)

        response = self.client.get(self.churches_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_region_churches_are_server_scoped_and_ignore_region_query_params(self):
        self.authenticate_regional_staff()

        response = self.client.get(
            self.churches_url,
            {"region": self.other_region.id, "page_size": 100},
        )

        names = {church["name"] for church in response.data["results"]}
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 12)
        self.assertIn("Alpha Assembly", names)
        self.assertNotIn("Outside Assembly", names)

    def test_region_churches_support_pagination_search_and_ordering(self):
        self.authenticate_regional_staff()

        paginated = self.client.get(self.churches_url, {"page_size": 5})
        self.assertEqual(paginated.status_code, status.HTTP_200_OK)
        self.assertEqual(paginated.data["count"], 12)
        self.assertEqual(len(paginated.data["results"]), 5)
        self.assertIsNotNone(paginated.data["next"])

        searched = self.client.get(self.churches_url, {"search": "Alpha"})
        self.assertEqual(searched.status_code, status.HTTP_200_OK)
        self.assertEqual(searched.data["count"], 1)
        self.assertEqual(searched.data["results"][0]["name"], "Alpha Assembly")

        ordered = self.client.get(
            self.churches_url,
            {"ordering": "-name", "page_size": 100},
        )
        ordered_names = [church["name"] for church in ordered.data["results"]]
        self.assertEqual(ordered_names, sorted(ordered_names, reverse=True))

    def test_regional_staff_can_list_only_region_users(self):
        self.authenticate_regional_staff()

        response = self.client.get(self.users_url, {"page_size": 100})

        emails = {user["email"] for user in response.data["results"]}
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 7)
        self.assertIn("alpha.user@example.com", emails)
        self.assertNotIn("outside.user@example.com", emails)
        self.assertIn("table_schema", response.data)
        self.assertIn("users", response.data["table_schemas"])

    def test_regular_user_cannot_list_region_users(self):
        self.client.force_authenticate(user=self.regular_user)

        response = self.client.get(self.users_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_region_users_support_pagination_search_and_ordering(self):
        self.authenticate_regional_staff()

        paginated = self.client.get(self.users_url, {"page_size": 3})
        self.assertEqual(paginated.status_code, status.HTTP_200_OK)
        self.assertEqual(paginated.data["count"], 7)
        self.assertEqual(len(paginated.data["results"]), 3)
        self.assertIsNotNone(paginated.data["next"])

        searched_by_email = self.client.get(self.users_url, {"search": "alpha.user"})
        self.assertEqual(searched_by_email.status_code, status.HTTP_200_OK)
        self.assertEqual(searched_by_email.data["count"], 1)
        self.assertEqual(searched_by_email.data["results"][0]["email"], "alpha.user@example.com")

        searched_by_church = self.client.get(self.users_url, {"search": "Alpha Assembly"})
        self.assertEqual(searched_by_church.status_code, status.HTTP_200_OK)
        self.assertEqual(searched_by_church.data["count"], 1)
        self.assertEqual(searched_by_church.data["results"][0]["church_name"], "Alpha Assembly")

        ordered = self.client.get(
            self.users_url,
            {"ordering": "email", "page_size": 100},
        )
        emails = [user["email"] for user in ordered.data["results"]]
        self.assertEqual(emails, sorted(emails))

    def test_region_users_ignore_region_query_params(self):
        self.authenticate_regional_staff()

        response = self.client.get(
            self.users_url,
            {"region": self.other_region.id, "page_size": 100},
        )

        emails = {user["email"] for user in response.data["results"]}
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 7)
        self.assertNotIn("outside.user@example.com", emails)
