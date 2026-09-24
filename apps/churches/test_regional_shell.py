from datetime import date
from importlib import import_module
from io import BytesIO
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from django.apps import apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from PIL import Image

from apps.churches.models import Church, Region, RegionLeadership, Zone
from apps.churches.services.regional_scope import active_zone, permitted_zones, uses_regional_shell
from apps.churches.zone_views import ZoneIdentityView
from apps.churches.regional_views import RegionalChurchesView
from apps.users.choices import UserRoles
from apps.users.models import Role, User
from apps.users.serializers import CurrentUserSerializer
from apps.reports.views.region_viewset import RegionViewSet
from apps.reports.views.summaries import RegionalSummaryView


class RegionalShellTests(TestCase):
    def setUp(self):
        self.region = Region.objects.create(name="Regional", code="RG")
        self.foreign = Region.objects.create(name="Foreign", code="FG")
        self.a = Zone.objects.create(name="A zone", region=self.region)
        self.b = Zone.objects.create(name="B zone", region=self.region)
        self.other = Zone.objects.create(name="Foreign zone", region=self.foreign)
        self.user = User.objects.create(username="regional-shell", email="shell@example.test")
        self.role = RegionLeadership.objects.create(user=self.user, region=self.region, role=RegionLeadership.Role.REGIONAL_ADMIN)
        self.first = Church.objects.create(name="First", zone=self.a, country="Botswana", country_code="BW", currency="BWP")
        self.second = Church.objects.create(name="Second", zone=self.b, country="Namibia", country_code="NA", currency="NAD")

    def test_current_user_endpoint_shell_contract_for_each_role(self):
        """Exercise the actual Djoser endpoint consumed by useUser, not just a helper."""
        client = APIClient()
        for role in (RegionLeadership.Role.REGIONAL_ADMIN, RegionLeadership.Role.OVERSEER):
            with self.subTest(role=role):
                self.role.role = role
                self.role.save()
                client.force_authenticate(self.user)
                response = client.get("/api/v1/auth/users/me/")
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.data["uses_regional_shell"])
                self.assertTrue(response.data["is_region_staff"])
                self.assertFalse(response.data["is_superuser"])
                self.assertEqual(response.data["region_roles"][0]["role"], role)
                self.assertEqual({z["id"] for z in response.data["regional_zones"]}, {self.a.pk, self.b.pk})
                selected = client.patch("/api/v1/auth/users/me/", {"regional_zone": self.b.pk}, format="json")
                self.assertEqual(selected.status_code, 200)
                self.assertEqual(selected.data["active_regional_zone"]["id"], self.b.pk)
                self.user.refresh_from_db()
                self.assertEqual(client.get("/api/v1/auth/users/me/").data["active_regional_zone"]["id"], self.b.pk)
                self.assertEqual(client.patch("/api/v1/auth/users/me/", {"regional_zone": self.other.pk}, format="json").status_code, 400)

        # A regional assignment does not override the explicit superuser exemption.
        self.user.is_superuser = True
        self.user.save()
        data = client.get("/api/v1/auth/users/me/").data
        self.assertTrue(data["is_region_staff"])
        self.assertTrue(data["is_superuser"])
        self.assertFalse(data["uses_regional_shell"])
        self.assertEqual(data["regional_zones"], [])
        self.assertIsNone(data["active_regional_zone"])

        pastor = User.objects.create(email="shell-pastor@example.test", church=self.first)
        pastor.roles.add(Role.objects.get_or_create(name=UserRoles.PASTOR)[0])
        pastor.assemblies.add(self.first)
        client.force_authenticate(pastor)
        data = client.get("/api/v1/auth/users/me/").data
        self.assertFalse(data["uses_regional_shell"])
        self.assertFalse(data["is_region_staff"])
        self.assertEqual(data["assembly"]["id"], self.first.pk)
        self.assertEqual([r["name"] for r in data["roles"]], [UserRoles.PASTOR])

    def test_roles_defaults_persistence_and_revoked_zone(self):
        for role in (RegionLeadership.Role.REGIONAL_ADMIN, RegionLeadership.Role.OVERSEER):
            self.role.role = role; self.role.save()
            self.assertTrue(uses_regional_shell(self.user))
        self.assertEqual(active_zone(self.user), self.a)
        self.assertEqual(set(permitted_zones(self.user)), {self.a, self.b})
        serializer = CurrentUserSerializer(self.user, data={"regional_zone": self.b.pk}, partial=True,
            context={"request": SimpleNamespace(user=self.user)})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.user.refresh_from_db()
        self.assertEqual(active_zone(self.user), self.b)
        self.assertEqual(serializer.data["active_regional_zone"]["id"], self.b.pk)
        self.assertEqual({z["id"] for z in serializer.data["regional_zones"]}, {self.a.pk, self.b.pk})
        bad = CurrentUserSerializer(self.user, data={"regional_zone": self.other.pk}, partial=True, context={"request": SimpleNamespace(user=self.user)})
        self.assertFalse(bad.is_valid())
        self.b.is_active = False; self.b.save()
        self.assertEqual(active_zone(self.user), self.a)
        self.user.is_superuser = True
        self.assertFalse(uses_regional_shell(self.user))
        self.user.is_superuser = False
        self.role.role = RegionLeadership.Role.OVERSEER_PA; self.role.save()
        self.assertFalse(uses_regional_shell(self.user))
        self.assertFalse(permitted_zones(self.user).exists())

    def test_active_zone_scopes_summary_modules_and_directory(self):
        self.user.regional_zone = self.b; self.user.save()
        request = APIRequestFactory().get("/summary/", {"period": "2026-09"})
        force_authenticate(request, self.user)
        data = RegionalSummaryView.as_view()(request).data
        self.assertEqual(data["filters"]["zone"], self.b.pk)
        self.assertEqual(data["filters"]["country"], "NA")
        self.assertEqual([a["id"] for a in data["assemblies"]], [self.second.pk])
        for action in ("finance_aggregate", "growth_aggregate", "ministry_aggregate", "leadership_aggregate", "compliance_aggregate", "risk_aggregate"):
            request = APIRequestFactory().get("/regional/")
            force_authenticate(request, self.user)
            response = RegionViewSet.as_view({"get": action})(request, pk=self.region.pk)
            self.assertEqual(response.status_code, 200)
            self.assertEqual([z["id"] for z in response.data["zones"]], [self.b.pk])
        directory = RegionalChurchesView()
        directory.request = SimpleNamespace(user=self.user)
        self.assertEqual(list(directory.get_queryset().values_list("pk", flat=True)), [self.second.pk])

    def test_fallback_backfill_is_repeatable_and_preserves_valid_values(self):
        backfill = import_module("apps.churches.migrations.0053_zone_avatar").backfill
        Zone.objects.filter(pk=self.a.pk).update(zone_avatar_fallback="")
        original = self.b.zone_avatar_fallback
        editor = SimpleNamespace(connection=SimpleNamespace(alias="default"))
        backfill(apps, editor)
        self.a.refresh_from_db(); self.b.refresh_from_db()
        self.assertRegex(self.a.zone_avatar_fallback, r"^oklch\(0.65 0.2 [\d.]+\)$")
        generated = self.a.zone_avatar_fallback
        self.assertEqual(self.b.zone_avatar_fallback, original)
        self.assertFalse(self.a.zone_avatar)
        backfill(apps, editor); self.a.refresh_from_db()
        self.assertEqual(self.a.zone_avatar_fallback, generated)
        self.assertTrue(self.first.avatar_fallback)

    def test_zone_image_upload_and_scope_validation(self):
        with TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media, STORAGES={"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"}}):
            buffer = BytesIO(); Image.new("RGB", (2,2), "blue").save(buffer, format="PNG")
            upload = SimpleUploadedFile("zone.png", buffer.getvalue(), content_type="image/png")
            request = APIRequestFactory().patch("/identity/", {"zone_avatar": upload}, format="multipart")
            force_authenticate(request, self.user)
            response = ZoneIdentityView.as_view()(request, pk=self.a.pk)
            self.assertEqual(response.status_code, 200)
            self.a.refresh_from_db()
            self.assertIn("zones/profile/", self.a.zone_avatar.name)
            self.assertTrue(response.data["zone_avatar"])
            request = APIRequestFactory().patch("/identity/", {"zone_avatar_fallback": "oklch(0.65 0.2 120)"})
            force_authenticate(request, self.user)
            self.assertEqual(ZoneIdentityView.as_view()(request, pk=self.other.pk).status_code, 404)
            self.role.is_active = False; self.role.save()
            denied = CurrentUserSerializer(self.user, data={"regional_zone": self.a.pk}, partial=True, context={"request": SimpleNamespace(user=self.user)})
            self.assertFalse(denied.is_valid())
