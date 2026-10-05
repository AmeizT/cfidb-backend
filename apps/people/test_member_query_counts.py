from datetime import date
from types import SimpleNamespace

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.churches.models import Church
from apps.people.models import Member, MemberTransferRequest, Ministry, Position
from apps.people.serializers.members import MemberSerializer
from apps.users.models import User


class MemberDirectoryQueryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.assembly = Church.objects.create(name="Directory query assembly")
        cls.other = Church.objects.create(name="Other query assembly")
        cls.user = User.objects.create_user(
            username="directory-query", email="directory-query@example.com",
            first_name="Query", last_name="Author", church=cls.assembly,
        )
        ministry = Ministry.objects.create(name="Query ministry")
        position = Position.objects.create(name="Query position")
        cls.members = []
        for index in range(100):
            member = Member.objects.create(
                assembly=cls.assembly, first_name=f"Query{index}", last_name="Member",
                date_of_birth=date(1990, 1, 1), gender="Male", country="Botswana",
                spouse=cls.members[0] if cls.members else None,
            )
            member.ministries.add(ministry)
            member.positions.add(position)
            cls.members.append(member)
        cls.pending = MemberTransferRequest.objects.create(
            member=cls.members[-1], from_assembly=cls.assembly, to_assembly=cls.other,
            effective_date=date(2026, 10, 1), requested_by=cls.user,
        )
        MemberTransferRequest.objects.create(
            member=cls.members[-1], from_assembly=cls.assembly, to_assembly=cls.other,
            effective_date=date(2026, 10, 1), requested_by=cls.user, status="rejected",
        )
        Member.objects.create(
            assembly=cls.other, first_name="Outside", last_name="Scope",
            date_of_birth=date(1990, 1, 1), gender="Male", country="Botswana",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.client.get("/api/v1/people/members/", {"page_size": 20})

    def test_relationship_queries_are_bounded_and_responses_match(self):
        counts = []
        for size in (20, 50, 100):
            with self.subTest(page_size=size):
                expected = MemberSerializer(
                    Member.objects.filter(assembly=self.assembly)[:size], many=True,
                    context={"request": SimpleNamespace(user=self.user)},
                ).data
                with CaptureQueriesContext(connection) as queries:
                    response = self.client.get("/api/v1/people/members/", {"page_size": size})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["results"], expected)
                counts.append(len(queries))
                self.assertLessEqual(len(queries), 10)
                first = response.data["results"][0]
                self.assertTrue(first["has_pending_transfer"])
                self.assertEqual(first["pending_transfer_id"], self.pending.pk)
                self.assertEqual(first["spouse_full_name"], self.members[0].full_name)
        self.assertEqual(counts, [counts[0]] * 3)

    def test_prefetched_detail_keeps_non_pending_transfer_out_of_response(self):
        response = self.client.get(f"/api/v1/people/members/{self.members[1].member_key}/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["has_pending_transfer"])
        self.assertIsNone(response.data["pending_transfer_id"])
