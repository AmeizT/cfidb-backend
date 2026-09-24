from datetime import date
from django.urls import reverse
from rest_framework.test import APITestCase
from apps.churches.models import Church, Region, RegionLeadership, Zone, ZoneLeadership
from apps.users.models import User, Role
from apps.users.serializers import CurrentUserSerializer


class AssemblyCreateTests(APITestCase):
    def setUp(self):
        self.assembly = Church.objects.create(name='Existing assembly', country='Legacy', locale='legacy')
        self.user = User.objects.create_user(first_name='Assembly', last_name='Creator', username='creator', email='creator@example.com', password='test', church=self.assembly)
        self.region = Region.objects.create(name='Test region', code='CREATE')
        self.zone = Zone.objects.create(name='Test zone', region=self.region)
        self.client.force_authenticate(self.user)
        self.url = reverse('assemblies-list')

    def create(self, **extra):
        return self.client.post(self.url, {'name': 'New assembly', 'country': 'BW', **extra}, format='json')

    def test_ordinary_and_generic_admin_cannot_create(self):
        for admin in (False, True):
            self.user.is_admin = admin
            self.user.save()
            self.assertEqual(self.create().status_code, 403)
            self.assertFalse(CurrentUserSerializer(self.user).data['can_create_assembly'])

    def test_superuser_defaults_override_client_values_without_touching_existing_data(self):
        self.user.is_superuser = True
        self.user.save()
        response = self.create(country_code='US', currency='USD', locale='xx', zone=self.zone.pk)
        self.assertEqual(response.status_code, 201, response.data)
        assembly = Church.objects.get(name='New assembly')
        self.assertEqual((assembly.country, assembly.country_code, assembly.locale, assembly.currency), ('Botswana', 'BW', 'en-BW', 'BWP'))
        self.assertIsNone(assembly.zone_id)
        self.assembly.refresh_from_db()
        self.assertEqual(self.assembly.locale, 'legacy')

    def test_zone_admin_assignment_allowed_but_overseer_and_inactive_denied(self):
        assignment = ZoneLeadership.objects.create(user=self.user, zone=self.zone, role='overseer', appointed_at=date.today())
        self.assertEqual(self.create().status_code, 403)
        assignment.role = 'admin'
        assignment.save()
        self.assertEqual(self.create().status_code, 201)
        assignment.is_active = False
        assignment.save()
        self.assertEqual(self.create(name='Inactive').status_code, 403)

    def test_named_zone_admin_role_allowed(self):
        self.user.roles.add(Role.objects.create(name='Zone Admin'))
        self.assertEqual(self.create().status_code, 201)

    def test_only_new_regional_admin_assignment_allowed(self):
        assignment = RegionLeadership.objects.create(user=self.user, region=self.region, role='overseer')
        self.assertEqual(self.create().status_code, 403)
        assignment.role = 'regional_admin'
        assignment.save()
        self.assertTrue(CurrentUserSerializer(self.user).data['can_create_assembly'])
        self.assertEqual(self.create().status_code, 201)
        assignment.is_active = False
        assignment.save()
        self.assertEqual(self.create(name='Inactive').status_code, 403)

    def test_invalid_country_and_options_permissions(self):
        options_url = reverse('assemblies-create-options')
        self.assertEqual(self.client.get(options_url).status_code, 403)
        self.user.is_superuser = True
        self.user.save()
        self.assertEqual(self.create(country='invalid').status_code, 400)
        self.assertEqual(self.create(country='').status_code, 400)
        options = self.client.get(options_url)
        self.assertEqual(options.status_code, 200)
        bw = next(country for country in options.data['countries'] if country['country_code'] == 'BW')
        self.assertEqual(bw['currency'], 'BWP')
        self.assertEqual(self.create(country='ZA').data['currency'], 'ZAR')

    def test_bulk_create_also_enforces_country_defaults(self):
        self.user.is_superuser = True
        self.user.save()
        response = self.client.post(self.url, [{'name': 'A', 'country': 'BW'}, {'name': 'B', 'country': 'ZA'}], format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual([row['currency'] for row in response.data], ['BWP', 'ZAR'])
