from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import override_settings
from django.db import DatabaseError
from django.urls import reverse
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APITestCase

from apps.bookkeeper.models import PaymentMethod, Tithe
from apps.bookkeeper.services import BatchEntryValidationError
from apps.churches.models import Church
from apps.jethro.context import resolve_jethro_context
from apps.jethro.models import JethroActionLog, JethroConversation, JethroTitheDraft
from apps.jethro.tithe_services import confirm_tithe_creation
from apps.jethro.tools import execute_tool
from apps.people.models import AssemblyMembership, Member
from apps.users.models import DelegatePermission, PermissionType, User


@override_settings(
    JETHRO_ENABLED=True,
    JETHRO_MOCK_MODE=True,
    JETHRO_DAILY_USER_LIMIT=100,
    JETHRO_TITHE_DRAFT_TTL_MINUTES=15,
)
class JethroTitheWorkflowTests(APITestCase):
    def setUp(self):
        self.assembly = Church.objects.create(name="Central Assembly")
        self.other_assembly = Church.objects.create(name="Outside Assembly")
        self.user = User.objects.create_user(
            first_name="Finance",
            last_name="User",
            email="finance@example.com",
            password="secret",
            church=self.assembly,
        )
        self.member = self.make_member(self.assembly, "John", "Doe", "CFI-00124")
        self.outside = self.make_member(self.other_assembly, "John", "Doe", "CFI-99999")
        self.client.force_authenticate(self.user)

    def make_member(self, assembly, first_name, last_name, key, *, active=True):
        member = Member.objects.create(
            assembly=assembly,
            member_key=key,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date(1990, 1, 1),
            gender="Male",
            country="Botswana",
            membersince=date.today(),
            phone_number=f"+2677{Member.objects.count():06d}",
        )
        AssemblyMembership.objects.create(
            member=member,
            assembly=assembly,
            status="active" if active else "inactive",
        )
        return member

    def send(self, message="Create tithes for John Doe for 5000 paid via bank."):
        return self.client.post(reverse("jethro-messages"), {"message": message}, format="json")

    def prepare(self, **overrides):
        conversation = JethroConversation.objects.create(
            user=self.user,
            assembly=self.assembly,
            title="Tithe",
        )
        arguments = {
            "member_query": "John Doe",
            "amount": "5000.00",
            "payment_method": "bank",
            "payment_date": None,
            "reference": "REF-1",
            "notes": "",
            **overrides,
        }
        return execute_tool(
            "prepare_tithe_creation",
            arguments,
            resolve_jethro_context(self.user),
            conversation,
        )

    def test_natural_language_prepares_decimal_safe_draft_without_creating_tithe(self):
        response = self.send()
        self.assertEqual(response.status_code, 200)
        structured = response.data["message"]["structured_content"]
        self.assertEqual(structured["type"], "tithe_confirmation")
        self.assertEqual(structured["draft"]["amount"], "5000.00")
        self.assertEqual(structured["draft"]["payment_method"], PaymentMethod.BANK)
        self.assertEqual(structured["draft"]["payment_date"], timezone.localdate().isoformat())
        self.assertEqual(JethroTitheDraft.objects.count(), 1)
        self.assertEqual(Tithe.objects.count(), 0)

    def test_supported_sentence_shapes_extract_member_amount_and_payment(self):
        response = self.send("Record a tithe of 2500 for John Doe by cash on 2026-07-15.")
        draft = response.data["message"]["structured_content"]["draft"]
        self.assertEqual(draft["member"]["public_id"], self.member.member_key)
        self.assertEqual(draft["amount"], "2500.00")
        self.assertEqual(draft["payment_method"], PaymentMethod.CASH)
        self.assertEqual(draft["payment_date"], "2026-07-15")
        self.assertIn("Payment date: 2026-07-15", response.data["message"]["content"])

    def test_multiple_exact_matches_require_selection(self):
        self.make_member(self.assembly, "  JOHN ", " DOE ", "CFI-00125")
        response = self.send()
        structured = response.data["message"]["structured_content"]
        self.assertEqual(structured["type"], "tithe_member_selection")
        self.assertEqual(len(structured["results"]), 2)
        self.assertEqual(Tithe.objects.count(), 0)

    def test_missing_match_keeps_draft_and_can_browse_paginated_members(self):
        response = self.send("Add $100 tithe for Missing Person using mobile money.")
        structured = response.data["message"]["structured_content"]
        self.assertEqual(structured["empty_reason"], "no_match")
        draft_id = structured["draft"]["public_id"]
        members = self.client.get(
            reverse("jethro-tithe-members", kwargs={"public_id": draft_id}),
            {"query": "", "page": 1, "page_size": 1},
        )
        self.assertEqual(members.status_code, 200)
        self.assertEqual(members.data["pagination"]["page_size"], 1)
        self.assertEqual(len(members.data["results"]), 1)
        self.assertNotEqual(members.data["results"][0]["public_id"], self.outside.member_key)

    def test_member_number_search_is_exact_and_assembly_scoped(self):
        result = self.prepare(member_query=" CFI-00124 ")
        self.assertEqual(result["type"], "tithe_confirmation")
        self.assertEqual(result["draft"]["member"]["public_id"], self.member.member_key)

    def test_member_selector_caps_page_size_and_excludes_inactive_members(self):
        inactive = self.make_member(self.assembly, "Inactive", "Person", "CFI-INACTIVE", active=False)
        result = self.prepare(member_query="Nobody")
        response = self.client.get(
            reverse("jethro-tithe-members", kwargs={"public_id": result["draft"]["public_id"]}),
            {"query": "", "page_size": 999},
        )
        self.assertEqual(response.data["pagination"]["page_size"], 20)
        self.assertNotIn(inactive.member_key, [row["public_id"] for row in response.data["results"]])

    def test_select_member_continues_same_draft(self):
        result = self.prepare(member_query="Missing")
        draft_id = result["draft"]["public_id"]
        response = self.client.post(
            reverse("jethro-tithe-select-member", kwargs={"public_id": draft_id}),
            {"member_public_id": self.member.member_key},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["type"], "tithe_confirmation")
        self.assertEqual(response.data["draft"]["public_id"], draft_id)

    def test_confirmation_creates_exactly_once_with_report_and_audit(self):
        result = self.prepare()
        draft_id = result["draft"]["public_id"]
        url = reverse("jethro-tithe-confirm", kwargs={"public_id": draft_id})
        first = self.client.post(url, {}, format="json")
        second = self.client.post(url, {}, format="json")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data["type"], "tithe_success")
        self.assertEqual(second.status_code, 400)
        self.assertEqual(Tithe.objects.count(), 1)
        tithe = Tithe.objects.select_related("report").get()
        self.assertEqual(tithe.member, self.member)
        self.assertEqual(tithe.assembly, self.assembly)
        self.assertEqual(tithe.amount, Decimal("5000.00"))
        self.assertEqual(tithe.payment_method, PaymentMethod.BANK)
        self.assertIsNotNone(tithe.report)
        log = JethroActionLog.objects.filter(
            tool_name="confirm_tithe_creation",
            status=JethroActionLog.Status.SUCCESS,
        ).get()
        self.assertEqual(log.arguments["outcome"], "created")
        self.assertEqual(log.arguments["member_public_id"], self.member.member_key)

    def test_cancelled_and_expired_drafts_cannot_be_confirmed(self):
        cancelled = self.prepare()
        cancel_url = reverse("jethro-tithe-cancel", kwargs={"public_id": cancelled["draft"]["public_id"]})
        self.assertEqual(self.client.post(cancel_url).status_code, 200)
        confirm_url = reverse("jethro-tithe-confirm", kwargs={"public_id": cancelled["draft"]["public_id"]})
        self.assertEqual(self.client.post(confirm_url).status_code, 400)

        expired = self.prepare()
        JethroTitheDraft.objects.filter(public_id=expired["draft"]["public_id"]).update(
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        expired_url = reverse("jethro-tithe-confirm", kwargs={"public_id": expired["draft"]["public_id"]})
        self.assertEqual(self.client.post(expired_url).status_code, 400)
        self.assertEqual(Tithe.objects.count(), 0)

    def test_cross_user_and_cross_assembly_selection_are_rejected(self):
        result = self.prepare(member_query="Missing")
        draft_id = result["draft"]["public_id"]
        select_url = reverse("jethro-tithe-select-member", kwargs={"public_id": draft_id})
        outside = self.client.post(select_url, {"member_public_id": self.outside.member_key}, format="json")
        self.assertEqual(outside.status_code, 400)

        other_user = User.objects.create_user(
            username="other-user", first_name="Other", last_name="User", email="other@example.com", password="secret", church=self.assembly,
        )
        self.client.force_authenticate(other_user)
        cross_user = self.client.get(reverse("jethro-tithe-members", kwargs={"public_id": draft_id}))
        self.assertEqual(cross_user.status_code, 400)

    def test_permission_is_checked_at_prepare_and_confirmation(self):
        permission = DelegatePermission.objects.create(
            user=self.user,
            permission_type=PermissionType.FINANCE,
            can_create=False,
        )
        with self.assertRaises(PermissionDenied):
            self.prepare()
        permission.can_create = True
        permission.save(update_fields=["can_create"])
        result = self.prepare()
        permission.can_create = False
        permission.save(update_fields=["can_create"])
        response = self.client.post(
            reverse("jethro-tithe-confirm", kwargs={"public_id": result["draft"]["public_id"]}),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Tithe.objects.count(), 0)

    def test_invalid_amount_and_payment_method_are_rejected(self):
        with self.assertRaises(ValidationError):
            self.prepare(amount="0")
        with self.assertRaises(ValidationError):
            self.prepare(payment_method="credit card")

    def test_message_requests_clarification_for_ambiguous_date_and_payment(self):
        date_response = self.send("Record a tithe of 2500 for John Doe by cash on yesterday.")
        self.assertIn("YYYY-MM-DD", date_response.data["message"]["content"])
        self.assertEqual(JethroTitheDraft.objects.count(), 0)
        payment_response = self.send("Record a tithe of 2500 for John Doe by credit card.")
        self.assertIn("not supported", payment_response.data["message"]["content"])
        self.assertEqual(JethroTitheDraft.objects.count(), 0)

    @patch("apps.jethro.orchestrator.execute_tool", side_effect=DatabaseError("database unavailable"))
    def test_database_error_is_not_masked_by_broken_transaction(self, _execute):
        response = self.send()
        self.assertEqual(response.status_code, 503)
        self.assertIn("database migrations", response.data["detail"])

    @patch("apps.jethro.tithe_services.create_tithes", side_effect=BatchEntryValidationError({"entries": {"0": {"amount": ["Invalid."]}}}))
    def test_finance_failure_rolls_back_and_marks_draft_failed(self, _create):
        result = self.prepare()
        draft = JethroTitheDraft.objects.get(public_id=result["draft"]["public_id"])
        with self.assertRaises(ValidationError):
            confirm_tithe_creation(resolve_jethro_context(self.user), draft)
        draft.refresh_from_db()
        self.assertEqual(draft.status, JethroTitheDraft.Status.FAILED)
        self.assertEqual(Tithe.objects.count(), 0)
