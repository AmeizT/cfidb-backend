from datetime import date
from rest_framework.test import APITestCase
from apps.churches.models import Church
from apps.people.models import Household, HouseholdMember, Member
from apps.users.models import User


class HouseholdRowActionsTests(APITestCase):
    def setUp(self):
        self.assembly = Church.objects.create(name='Source')
        self.other = Church.objects.create(name='Destination')
        self.user = User.objects.create_user(first_name='Test', last_name='User', username='household-user', email='households@example.com', password='test', church=self.assembly)
        self.household = Household.objects.create(name='Home', assembly=self.assembly)
        self.url = f'/api/v1/people/households/{self.household.pk}/'
        self.client.force_authenticate(self.user)

    def test_delete_keeps_existing_visible_household_permission(self):
        self.assertEqual(self.client.delete(self.url).status_code, 204)

    def test_other_assembly_delete_and_transfer_are_denied(self):
        response = self.client.patch(self.url, {'assembly': self.other.pk}, format='json')
        self.assertEqual(response.status_code, 403)
        self.user.church = self.other
        self.user.save()
        self.assertEqual(self.client.delete(self.url).status_code, 404)
        self.assertTrue(Household.objects.filter(pk=self.household.pk).exists())

    def test_options_only_include_authorized_destinations(self):
        url = '/api/v1/people/households/transfer-options/'
        self.assertEqual([row['id'] for row in self.client.get(url).data], [self.assembly.pk])
        self.user.is_superuser = True
        self.user.save()
        self.assertEqual({row['id'] for row in self.client.get(url).data}, {self.assembly.pk, self.other.pk})

    def test_existing_update_api_can_transfer_empty_household(self):
        self.user.is_superuser = True
        self.user.save()
        response = self.client.patch(self.url, {'assembly': self.other.pk}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.household.refresh_from_db()
        self.assertEqual(self.household.assembly_id, self.other.pk)

    def test_existing_member_consistency_rule_is_preserved(self):
        member = Member.objects.create(assembly=self.assembly, first_name='Test', last_name='Member', date_of_birth=date(1990, 1, 1), gender='Male')
        HouseholdMember.objects.create(household=self.household, member=member, joined_on=date.today())
        self.user.is_superuser = True
        self.user.save()
        response = self.client.patch(self.url, {'assembly': self.other.pk}, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.household.refresh_from_db()
        self.assertEqual(self.household.assembly_id, self.assembly.pk)
