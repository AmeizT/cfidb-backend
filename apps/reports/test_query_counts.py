from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookkeeper.models import Expenditure, Overhead, OverheadType, Revenue, RevenueCategory, Tithe
from apps.churches.models import Church
from apps.people.models import Attendance, Member, SundaySchoolAttendance
from apps.reports.serializers.report import AssemblyReportSerializer
from apps.reports.services.lifecycle import (
    REQUIRED_SECTIONS, ensure_report, get_report_sections, get_section_source,
    set_section_status, start_amendment, submit_report,
)
from apps.users.models import User


class ReportSourceQueryTests(TestCase):
    def setUp(self):
        self.assembly = Church.objects.create(name="Report query assembly", currency="BWP")
        self.user = User.objects.create_user(
            username="report-query", email="report-query@example.com",
            first_name="Report", last_name="Query", church=self.assembly,
        )
        self.report = ensure_report(assembly=self.assembly, period_start=date(2026, 9, 1))
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.context = {"request": SimpleNamespace(user=self.user)}

    def add_source_records(self):
        member = Member.objects.create(
            assembly=self.assembly, first_name="Source", last_name="Member",
            date_of_birth=date(1990, 1, 1), gender="Male", country="Botswana",
        )
        Attendance.objects.create(
            assembly=self.assembly, report=self.report, timestamp=date(2026, 9, 6),
            collection_schema="legacy", adults=10, children=5, guest_attendance=9, online_viewers=2,
        )
        Attendance.objects.create(
            assembly=self.assembly, report=self.report, timestamp=date(2026, 9, 13),
            men=4, women=6, children=999, visitor_men=2, visitor_women=3, online_viewers=3,
        )
        Attendance.objects.create(
            assembly=self.assembly, report=self.report, timestamp=date(2026, 9, 27),
            men=999, is_deleted=True,
        )
        SundaySchoolAttendance.objects.bulk_create([
            SundaySchoolAttendance(
                assembly=self.assembly, report=self.report, service_date=date(2026, 9, 6),
                teacher=member, class_name="PRIMARY", boys=3, girls=4, male_visitors=2, female_visitors=1,
                male_first_timers=2, female_first_timers=1, status="draft",
            ),
            SundaySchoolAttendance(
                assembly=self.assembly, report=self.report, service_date=date(2026, 9, 13),
                teacher=member, class_name="PRIMARY", boys=2, girls=3, status="submitted",
            ),
        ])
        Tithe.objects.create(
            assembly=self.assembly, report=self.report, member=member,
            timestamp=date(2026, 9, 1), amount=Decimal("12.30"),
        )
        revenue_category = RevenueCategory.objects.create(name="Query revenue", is_standard=True)
        overhead_type = OverheadType.objects.create(name="Query overhead", is_global=True)
        Revenue.objects.create(
            assembly=self.assembly, report=self.report, category=revenue_category,
            timestamp=date(2026, 9, 1), amount=Decimal("23.40"), notes="Detailed revenue note",
        )
        Overhead.objects.create(
            assembly=self.assembly, report=self.report, overhead_type=overhead_type,
            timestamp=date(2026, 9, 1), amount=Decimal("5.60"), notes="Detailed overhead note",
        )
        Expenditure.objects.create(
            assembly=self.assembly, report=self.report, timestamp=date(2026, 9, 1),
            invoice_date=date(2026, 9, 1), name="Query expense", quantity=2, price=Decimal("7.50"),
        )
        self.report.refresh_from_db()

    def test_minimal_sources_preserve_totals_ids_statuses_and_response(self):
        self.add_source_records()
        full = get_report_sections(self.report)
        minimal = get_report_sections(self.report, include_breakdown=False)
        for expected, actual in zip(full, minimal):
            with self.subTest(section=expected["key"]):
                self.assertEqual(actual["status"], expected["status"])
                self.assertEqual(actual["resolved"], expected["resolved"])
                for field in ("record_count", "total", "source"):
                    self.assertEqual(actual["source"][field], expected["source"][field])
        self.assertEqual(minimal[0]["source"]["total"], 35)
        self.assertEqual(minimal[1]["status"], "in_progress")
        with patch("django.utils.timezone.now", return_value=timezone.now()):
            actual = AssemblyReportSerializer(self.report, context=self.context).data
            with patch("apps.reports.serializers.report.get_report_sections", return_value=full):
                expected = AssemblyReportSerializer(self.report, context=self.context).data
        self.assertEqual(actual, expected)
        with CaptureQueriesContext(connection) as queries:
            get_section_source(self.report, "general_attendance", include_breakdown=False)
        self.assertEqual(len(queries), 1)

    def test_overview_builds_sources_once_and_keeps_query_count_bounded(self):
        for month in range(1, 13):
            ensure_report(assembly=self.assembly, period_start=date(2026, month, 1))
        self.client.get("/api/v1/reports/overview/", {"year": 2026})
        with patch("apps.reports.services.lifecycle.get_section_source", wraps=get_section_source) as source:
            with CaptureQueriesContext(connection) as queries:
                response = self.client.get("/api/v1/reports/overview/", {"year": 2026})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["months"]), 12)
        self.assertEqual(source.call_count, 12 * len(REQUIRED_SECTIONS))
        self.assertLessEqual(len(queries), 145)

    def test_skip_no_activity_and_submitted_snapshots_keep_full_source_data(self):
        self.add_source_records()
        for key in ("general_attendance", "sunday_school_attendance"):
            set_section_status(
                report=self.report, section_key=key, status="skipped", actor=self.user,
                skip_reason_code="records_unavailable",
            )
        version = submit_report(report=self.report, actor=self.user, declaration_confirmed=True)
        revenue_snapshot = version.section_snapshots.get(section="revenue")
        self.assertEqual(revenue_snapshot.breakdown[0]["notes"], "Detailed revenue note")
        self.assertIn("reporting_category", revenue_snapshot.breakdown[0])
        self.assertEqual(version.section_snapshots.get(section="general_attendance").status, "skipped")
        snapshot_data = self.client.get(f"/api/v1/reports/{self.report.pk}/submitted/").json()
        self.report = start_amendment(report=self.report, actor=self.user, reason="Query regression")
        Revenue.objects.filter(report=self.report).update(notes="Changed live note")
        after = self.client.get(f"/api/v1/reports/{self.report.pk}/submitted/").json()
        self.assertEqual(after["sections"], snapshot_data["sections"])
        self.assertEqual(after["version_number"], snapshot_data["version_number"])
        empty = ensure_report(assembly=self.assembly, period_start=date(2026, 8, 1))
        set_section_status(report=empty, section_key="revenue", status="no_activity", actor=self.user)
        sections = get_report_sections(empty, include_breakdown=False)
        revenue = next(item for item in sections if item["key"] == "revenue")
        self.assertEqual(revenue["status"], "no_activity")
        self.assertTrue(revenue["resolved"])
