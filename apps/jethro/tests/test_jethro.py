from datetime import date
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from apps.churches.models import Church
from apps.people.models import AssemblyMembership, Member
from apps.users.models import User

from apps.jethro.context import resolve_jethro_context
from apps.jethro.models import JethroActionLog, JethroConversation, JethroMessage, JethroUsageLog
from apps.jethro.orchestrator import JethroProviderError
from apps.jethro.tools import execute_tool, search_members


@override_settings(JETHRO_ENABLED=True, JETHRO_MOCK_MODE=True, JETHRO_DAILY_USER_LIMIT=30)
class JethroApiTests(APITestCase):
    def setUp(self):
        self.assembly = Church.objects.create(name="Central Assembly")
        self.other_assembly = Church.objects.create(name="Outside Assembly")
        self.user = User.objects.create_user(
            first_name="Test",
            last_name="Admin",
            email="test@example.com",
            password="secret",
            church=self.assembly,
        )
        self.member = self.make_member(self.assembly, "Alice", "Allowed", "S2427056")
        self.outside_member = self.make_member(self.other_assembly, "Alice", "Outside", "S9999999")
        self.url = reverse("jethro-messages")

    def make_member(self, assembly, first_name, last_name, key):
        member = Member.objects.create(
            assembly=assembly,
            member_key=key,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date(1990, 1, 1),
            gender="Female",
            country="Zimbabwe",
            membersince=date.today(),
        )
        AssemblyMembership.objects.create(member=member, assembly=assembly, status="active")
        return member

    def authenticate(self):
        self.client.force_authenticate(self.user)

    def test_unauthenticated_access_is_rejected(self):
        response = self.client.post(self.url, {"message": "Hello"}, format="json")
        self.assertIn(response.status_code, (401, 403))

    def test_authenticated_user_can_send_with_active_assembly(self):
        self.authenticate()
        response = self.client.post(self.url, {"message": "How many active members do we have?"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"]["role"], "assistant")
        self.assertTrue(response.data["mock_mode"])

    def test_member_search_never_returns_unrelated_assembly(self):
        result = search_members(resolve_jethro_context(self.user), {"query": "Alice", "limit": 20})
        self.assertEqual([row["member_number"] for row in result["results"]], ["S2427056"])

    def test_member_search_limit_is_enforced(self):
        with self.assertRaises(ValidationError):
            execute_tool("search_members", {"query": "Alice", "limit": 21}, resolve_jethro_context(self.user))

    def test_unknown_tools_are_rejected(self):
        with self.assertRaises(ValidationError):
            execute_tool("delete_member", {}, resolve_jethro_context(self.user))

    def test_invalid_tool_arguments_are_rejected(self):
        with self.assertRaises(ValidationError):
            execute_tool("get_report_submission_status", {"period": "not-a-month"}, resolve_jethro_context(self.user))

    def test_destructive_request_does_not_modify_members(self):
        self.authenticate()
        before = Member.objects.count()
        response = self.client.post(self.url, {"message": "Delete Alice Allowed"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("read-only", response.data["message"]["content"])
        self.assertEqual(Member.objects.count(), before)

    @override_settings(JETHRO_MOCK_MODE=False, JETHRO_MODEL="test-model")
    @patch("apps.jethro.orchestrator._provider_response", side_effect=JethroProviderError("Safe provider error."))
    def test_provider_failure_returns_safe_error(self, _provider):
        self.authenticate()
        response = self.client.post(self.url, {"message": "Hello"}, format="json")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["detail"], "Safe provider error.")

    def test_conversation_usage_and_tool_activity_are_saved(self):
        self.authenticate()
        self.client.post(self.url, {"message": "Search for member S2427056"}, format="json")
        self.assertEqual(JethroConversation.objects.count(), 1)
        self.assertEqual(JethroMessage.objects.filter(role="assistant").count(), 1)
        self.assertEqual(JethroUsageLog.objects.count(), 1)
        self.assertEqual(JethroActionLog.objects.count(), 1)

    def test_sensitive_fields_are_not_in_search_results(self):
        result = execute_tool("search_members", {"query": "Alice", "limit": 10}, resolve_jethro_context(self.user))
        payload = result["results"][0]
        self.assertNotIn("phone_number", payload)
        self.assertNotIn("email", payload)
        self.assertNotIn("address", payload)
        self.assertNotIn("access_pin", payload)

    @override_settings(JETHRO_DAILY_USER_LIMIT=1)
    def test_daily_request_limit_is_enforced(self):
        self.authenticate()
        first = self.client.post(self.url, {"message": "Hello"}, format="json")
        second = self.client.post(self.url, {"message": "Hello again"}, format="json")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
