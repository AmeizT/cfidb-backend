from datetime import date
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.bookkeeper.models import Tithe
from apps.churches.models import Church
from apps.people.models import Member
from apps.reports.models import AssemblyReport, ReportSectionSnapshot, ReportSectionStatus, ReportVersion
from apps.reports.services.lifecycle import (
    REQUIRED_SECTIONS,
    ensure_report,
    get_report_sections,
    get_report_state,
    get_section_source,
    set_section_status,
    start_amendment,
    submit_report,
    validate_report,
)
from apps.users.models import User


class ReportTithesAPITests(APITestCase):
    def setUp(self):
        self.assembly = Church.objects.create(
            name="Orwetoveni",
            country="Namibia",
            country_code="NA",
            currency="NAD",
            locale="en-NA",
        )
        self.user = User.objects.create_user(
            first_name="Admin",
            last_name="User",
            username="admin.user",
            email="admin@example.com",
            password="password123",
            church=self.assembly,
        )
        self.user.is_admin = True
        self.user.save(update_fields=["is_admin"])
        self.member = Member.objects.create(
            assembly=self.assembly,
            member_key="member-john-doe",
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1990, 1, 1),
            gender="Male",
            country="Namibia",
            phone_number="+264811111111",
        )
        self.january_report = AssemblyReport.objects.create(
            assembly=self.assembly,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        self.march_report = AssemblyReport.objects.create(
            assembly=self.assembly,
            period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 31),
        )
        Tithe.objects.create(
            assembly=self.assembly,
            report=self.january_report,
            member=self.member,
            amount=Decimal("100.00"),
            timestamp=date(2026, 1, 2),
            payment_method="Bank",
            reference_code="JAN-001",
            notes="January tithe",
        )
        Tithe.objects.create(
            assembly=self.assembly,
            report=self.march_report,
            member=self.member,
            amount=Decimal("200.00"),
            timestamp=date(2026, 3, 4),
            payment_method="Cash",
            reference_code="MAR-001",
            notes="March tithe",
        )
        Tithe.objects.create(
            assembly=self.assembly,
            report=self.january_report,
            member=None,
            amount=Decimal("999.00"),
            timestamp=date(2026, 1, 5),
            payment_method="Cash",
        )
        self.client.force_authenticate(user=self.user)

    def test_paginated_tithes_response_includes_meta_config(self):
        response = self.client.get(
            f"/api/v1/reports/{self.january_report.id}/tithes/",
            {"page_size": 1},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["meta"]["config"]["columns"][0]["id"], "timestamp")
        self.assertEqual(response.data["table_schema"]["columns"][0]["id"], "timestamp")

    def test_tithes_pagination_returns_requested_page(self):
        page_one = self.client.get(
            f"/api/v1/reports/{self.january_report.id}/tithes/",
            {"page": 1, "page_size": 1},
        )
        page_two = self.client.get(
            f"/api/v1/reports/{self.january_report.id}/tithes/",
            {"page": 2, "page_size": 1},
        )

        self.assertEqual(page_one.status_code, status.HTTP_200_OK)
        self.assertEqual(page_two.status_code, status.HTTP_200_OK)
        self.assertEqual(page_one.data["count"], 2)
        self.assertEqual(page_two.data["count"], 2)
        self.assertEqual(len(page_one.data["results"]), 1)
        self.assertEqual(len(page_two.data["results"]), 1)
        self.assertNotEqual(page_one.data["results"][0]["id"], page_two.data["results"][0]["id"])
        self.assertIsNotNone(page_one.data["next"])
        self.assertIsNotNone(page_two.data["previous"])

    def test_tithes_filters_and_pagination_work_together(self):
        Tithe.objects.create(
            assembly=self.assembly,
            report=self.january_report,
            member=None,
            amount=Decimal("50.00"),
            timestamp=date(2026, 1, 20),
            payment_method="Cash",
            reference_code="JAN-002",
            notes="Second January tithe",
        )

        response = self.client.get(
            f"/api/v1/reports/{self.january_report.id}/tithes/",
            {"search": "JAN", "page": 2, "page_size": 1},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIn(
            response.data["results"][0]["reference_code"],
            {"JAN-001", "JAN-002"},
        )

    def test_tithe_contributors_pagination_returns_requested_page(self):
        second_member = Member.objects.create(
            assembly=self.assembly,
            member_key="member-jane-doe",
            first_name="Jane",
            last_name="Doe",
            date_of_birth=date(1991, 1, 1),
            gender="Female",
            country="Namibia",
            phone_number="+264822222222",
        )
        Tithe.objects.create(
            assembly=self.assembly,
            report=self.january_report,
            member=second_member,
            amount=Decimal("80.00"),
            timestamp=date(2026, 1, 10),
            payment_method="Cash",
            reference_code="JAN-003",
        )

        page_one = self.client.get(
            f"/api/v1/reports/{self.january_report.id}/tithes/contributors/",
            {"year": 2026, "page": 1, "page_size": 1},
        )
        page_two = self.client.get(
            f"/api/v1/reports/{self.january_report.id}/tithes/contributors/",
            {"year": 2026, "page": 2, "page_size": 1},
        )

        self.assertEqual(page_one.status_code, status.HTTP_200_OK)
        self.assertEqual(page_two.status_code, status.HTTP_200_OK)
        self.assertEqual(page_one.data["count"], 2)
        self.assertEqual(page_two.data["count"], 2)
        self.assertNotEqual(
            page_one.data["results"][0]["member_id"],
            page_two.data["results"][0]["member_id"],
        )

    def test_paginated_contributors_include_schema_and_full_year_history(self):
        response = self.client.get(
            f"/api/v1/reports/{self.january_report.id}/tithes/contributors/",
            {"year": 2026, "page_size": 1},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["meta"]["config"]["columns"][0]["id"], "contributor")
        self.assertEqual(response.data["table_schema"]["columns"][0]["id"], "contributor")

        row = response.data["results"][0]
        self.assertEqual(row["contributor"], "John Doe")
        self.assertNotEqual(row["contributor"], "Anonymous")
        self.assertEqual(Decimal(str(row["cumulative"])), Decimal("300.00"))
        self.assertEqual(len(row["history"]), 12)
        self.assertEqual([item["month_number"] for item in row["history"]], list(range(1, 13)))
        self.assertEqual(Decimal(str(row["history"][1]["amount"])), Decimal("0.00"))
        self.assertEqual(Decimal(str(row["history"][2]["amount"])), Decimal("200.00"))

    def test_contributors_export_pdf_returns_full_history_report(self):
        response = self.client.get(
            f"/api/v1/reports/{self.january_report.id}/tithes/contributors/export.pdf/",
            {"year": 2026, "page_size": 1},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn(
            "tithe-contributors-2026",
            response["Content-Disposition"],
        )

    def test_contributor_history_export_pdf_returns_member_scoped_report(self):
        response = self.client.get(
            f"/api/v1/reports/{self.january_report.id}/tithes/contributors/{self.member.id}/history/pdf/",
            {"year": 2026},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn(
            "tithes-history-john-doe-2026",
            response["Content-Disposition"],
        )

        content = b"".join(response.streaming_content)
        self.assertTrue(content.startswith(b"%PDF"))

    def test_tithes_submodule_responses_include_view_specific_meta_config(self):
        endpoints = [
            (
                f"/api/v1/reports/{self.january_report.id}/tithes/contributors/{self.member.id}/history/",
                "month",
            ),
            (
                f"/api/v1/reports/{self.january_report.id}/tithes/analytics/",
                "label",
            ),
            (
                f"/api/v1/reports/{self.january_report.id}/tithes/performance/",
                "target",
            ),
            (
                f"/api/v1/reports/{self.january_report.id}/tithes/receipts/",
                "reference_code",
            ),
            (
                f"/api/v1/reports/{self.january_report.id}/tithes/audit-log/",
                "timestamp",
            ),
        ]

        for url, first_column in endpoints:
            with self.subTest(url=url):
                response = self.client.get(url, {"year": 2026, "page_size": 100})

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data["meta"]["config"]["columns"][0]["id"], first_column)
                self.assertEqual(response.data["table_schema"]["columns"][0]["id"], first_column)


class ReportLifecycleTests(APITestCase):
    def setUp(self):
        self.assembly = Church.objects.create(
            name="Lifecycle Assembly",
            country="Botswana",
            currency="BWP",
        )
        self.user = User.objects.create_user(
            first_name="Report",
            last_name="Author",
            username="report.author",
            email="report.author@example.com",
            password="password123",
            church=self.assembly,
        )
        self.report = ensure_report(
            assembly=self.assembly,
            period_start=date(2026, 9, 1),
            actor=self.user,
        )

    def resolve_all_sections(self):
        for section_key in REQUIRED_SECTIONS:
            set_section_status(
                report=self.report,
                section_key=section_key,
                status=ReportSectionStatus.Status.NO_ACTIVITY,
                actor=self.user,
                no_activity_note="Confirmed no activity for this period.",
            )

    def test_canonical_section_states_make_report_ready(self):
        self.assertEqual(get_report_state(self.report, self.user).status, "not_started")
        first = REQUIRED_SECTIONS[0]
        set_section_status(
            report=self.report,
            section_key=first,
            status=ReportSectionStatus.Status.IN_PROGRESS,
            actor=self.user,
        )
        self.assertEqual(get_report_state(self.report, self.user).status, "draft")
        set_section_status(
            report=self.report,
            section_key=first,
            status=ReportSectionStatus.Status.NO_ACTIVITY,
            actor=self.user,
            no_activity_note="No services took place.",
        )
        for section_key in REQUIRED_SECTIONS[1:]:
            set_section_status(
                report=self.report,
                section_key=section_key,
                status=ReportSectionStatus.Status.SKIPPED,
                actor=self.user,
                skip_reason_code=ReportSectionStatus.SkipReason.RECORDS_UNAVAILABLE,
                skip_reason_detail="The source register could not be recovered in time.",
            )
        state = get_report_state(self.report, self.user)
        self.assertEqual(state.status, "ready_to_submit")
        self.assertEqual(state.completion_percentage, 100)
        self.assertTrue(state.can_submit)

    def test_no_activity_is_explicit_and_reversible_without_source_records(self):
        section_key = ReportSectionStatus.Section.REVENUE
        section = set_section_status(
            report=self.report,
            section_key=section_key,
            status=ReportSectionStatus.Status.NO_ACTIVITY,
            actor=self.user,
            no_activity_note="There was no revenue activity this month.",
        )
        self.assertEqual(section.status, ReportSectionStatus.Status.NO_ACTIVITY)
        self.assertIsNotNone(section.no_activity_confirmed_at)
        self.assertEqual(get_section_source(self.report, section_key)["record_count"], 0)

        section = set_section_status(
            report=self.report,
            section_key=section_key,
            status=ReportSectionStatus.Status.NOT_STARTED,
            actor=self.user,
        )
        self.assertEqual(section.status, ReportSectionStatus.Status.NOT_STARTED)
        self.assertIsNone(section.no_activity_confirmed_at)
        self.assertIsNone(section.no_activity_confirmed_by)

    def test_skip_without_notes_persists_and_undo_updates_readiness(self):
        self.resolve_all_sections()
        self.client.force_authenticate(self.user)
        key = ReportSectionStatus.Section.REVENUE
        url = f"/api/v1/reports/{self.report.pk}/sections/{key}/"
        response = self.client.post(url, {
            "status": "skipped", "skip_reason_code": "records_unavailable",
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        section = self.report.sections.get(section=key)
        self.assertEqual(section.status, "skipped")
        self.assertEqual(section.skip_notes, "")
        self.assertTrue(get_report_state(self.report, self.user).can_submit)
        self.assertEqual(validate_report(self.report), [])
        persisted = self.client.get(url)
        self.assertEqual(persisted.data["status"], "skipped")
        response = self.client.post(url, {"status": "not_started"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        section.refresh_from_db()
        self.assertEqual(section.status, "not_started")
        self.assertIsNone(section.skipped_at)
        self.assertIsNone(section.skip_reason)
        self.assertFalse(get_report_state(self.report, self.user).can_submit)

    def test_skip_optional_notes_are_saved_and_submission_accepts_empty_notes(self):
        self.resolve_all_sections()
        for notes in (None, "  Source register pending.  "):
            section = set_section_status(
                report=self.report, section_key=ReportSectionStatus.Section.REVENUE,
                status="skipped", actor=self.user,
                skip_reason_code="records_unavailable", skip_reason_detail=notes,
            )
            section.refresh_from_db()
            self.assertEqual(section.skip_notes, (notes or "").strip())
        set_section_status(
            report=self.report, section_key=ReportSectionStatus.Section.REVENUE,
            status="skipped", actor=self.user, skip_reason_code="records_unavailable",
        )
        version = submit_report(report=self.report, actor=self.user, declaration_confirmed=True)
        self.assertEqual(version.section_snapshots.get(section="revenue").skip_reason_detail, "")

    def test_undo_skip_preserves_source_records_and_skip_requires_reason(self):
        member = Member.objects.create(
            assembly=self.assembly, first_name="Report", last_name="Member",
            member_key="skip-history-member", date_of_birth=date(1990, 1, 1),
            gender="Male", country="Namibia", phone_number="",
        )
        tithe = Tithe.objects.create(
            assembly=self.assembly, report=self.report, member=member,
            amount=Decimal("25.00"), timestamp=self.report.period_start,
        )
        key = ReportSectionStatus.Section.TITHES
        with self.assertRaises(ValidationError):
            set_section_status(report=self.report, section_key=key, status="skipped", actor=self.user)
        set_section_status(
            report=self.report, section_key=key, status="skipped", actor=self.user,
            skip_reason_code="records_unavailable",
        )
        section = set_section_status(report=self.report, section_key=key, status="not_started", actor=self.user)
        section.refresh_from_db()
        self.assertEqual(section.status, "not_started")
        self.assertIsNone(section.skip_reason)
        self.assertIsNone(section.skipped_by)
        tithe.refresh_from_db()
        self.assertEqual(tithe.report_id, self.report.pk)
        self.assertEqual(tithe.amount, Decimal("25.00"))
        self.assertEqual(get_section_source(self.report, key)["record_count"], 1)
        with self.assertRaises(ValidationError):
            set_section_status(report=self.report, section_key=key, status="no_activity", actor=self.user)

    def test_non_required_no_activity_persists_and_allows_submission(self):
        self.report = ensure_report(assembly=self.assembly, period_start=date(2026, 8, 1), actor=self.user)
        self.resolve_all_sections()
        section = self.report.sections.get(section="sunday_school_attendance")
        self.assertEqual(section.status, "no_activity")
        self.assertEqual(section.no_activity_confirmed_by, self.user)
        self.assertIsNotNone(section.no_activity_confirmed_at)
        resolved = next(item for item in get_report_sections(self.report) if item["key"] == section.section)
        self.assertTrue(resolved["resolved"])
        self.assertEqual(resolved["status"], "no_activity")
        self.assertEqual(validate_report(self.report), [])
        self.assertTrue(get_report_state(self.report, self.user).can_submit)
        version = submit_report(report=self.report, actor=self.user, declaration_confirmed=True)
        self.assertEqual(version.section_snapshots.get(section=section.section).status, "no_activity")

    def test_submission_is_versioned_and_boundary_lock_is_derived(self):
        self.resolve_all_sections()
        version = submit_report(
            report=self.report,
            actor=self.user,
            declaration_confirmed=True,
        )
        self.report.refresh_from_db()
        self.assertEqual(version.version_number, 1)
        self.assertEqual(version.section_snapshots.count(), 6)
        self.assertEqual(version.editable_until, version.submitted_at + timedelta(days=7))
        self.assertEqual(get_report_state(self.report, self.user, now=version.editable_until).status, "submitted")
        self.assertEqual(
            get_report_state(self.report, self.user, now=version.editable_until + timedelta(microseconds=1)).status,
            "locked",
        )

    def test_amendment_creates_version_two_without_changing_version_one(self):
        self.resolve_all_sections()
        version_one = submit_report(
            report=self.report,
            actor=self.user,
            declaration_confirmed=True,
        )
        original_snapshot = list(version_one.section_snapshots.values("section", "status", "total"))
        self.report.refresh_from_db()
        start_amendment(report=self.report, actor=self.user, reason="Correct monthly declaration")
        version_two = submit_report(
            report=self.report,
            actor=self.user,
            declaration_confirmed=True,
        )
        self.assertEqual(version_two.version_number, 2)
        self.assertEqual(
            list(version_one.section_snapshots.values("section", "status", "total")),
            original_snapshot,
        )
        snapshot = version_one.section_snapshots.first()
        snapshot.total = Decimal("1.00")
        with self.assertRaises(ValidationError):
            snapshot.save()

    def test_snapshot_failure_rolls_back_submission(self):
        self.resolve_all_sections()
        with patch.object(ReportSectionSnapshot.objects, "bulk_create", side_effect=RuntimeError("snapshot failed")):
            with self.assertRaises(RuntimeError):
                submit_report(
                    report=self.report,
                    actor=self.user,
                    declaration_confirmed=True,
                )
        self.report.refresh_from_db()
        self.assertIsNone(self.report.current_version_id)
        self.assertFalse(ReportVersion.objects.filter(report=self.report).exists())

    def test_list_and_detail_return_the_same_canonical_status(self):
        self.resolve_all_sections()
        self.client.force_authenticate(user=self.user)
        listing = self.client.get("/api/v1/reports/", {"year": self.report.period_start.year})
        detail = self.client.get(f"/api/v1/reports/{self.report.id}/")
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        row = next(item for item in listing.data["results"] if item["id"] == self.report.id)
        self.assertEqual(row["status"], detail.data["status"])
        self.assertEqual(row["status"], "ready_to_submit")

    def test_month_detail_get_supports_placeholder_and_existing_periods(self):
        self.client.force_authenticate(user=self.user)
        report_count = AssemblyReport.objects.count()

        placeholder = self.client.get("/api/v1/reports/current/", {"year": 2000, "month": 1})
        self.assertEqual(placeholder.status_code, status.HTTP_200_OK)
        self.assertIsNone(placeholder.data["id"])
        self.assertEqual(placeholder.data["status"], "overdue")
        self.assertEqual(len(placeholder.data["sections"]), 6)
        self.assertEqual(AssemblyReport.objects.count(), report_count)

        existing = self.client.get(
            "/api/v1/reports/current/",
            {"year": self.report.period_start.year, "month": self.report.period_start.month},
        )
        self.assertEqual(existing.status_code, status.HTTP_200_OK)
        self.assertEqual(existing.data["id"], self.report.id)
        self.assertEqual(len(existing.data["sections"]), 6)

    def test_past_period_can_start_but_future_period_cannot(self):
        self.client.force_authenticate(user=self.user)

        past = self.client.post("/api/v1/reports/current/?year=2000&month=1", {})
        self.assertEqual(past.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(past.data["id"])

        today = timezone.localdate().replace(day=1)
        future_year = today.year + (1 if today.month == 12 else 0)
        future_month = 1 if today.month == 12 else today.month + 1
        AssemblyReport.objects.filter(
            assembly=self.assembly,
            period_start__year=future_year,
            period_start__month=future_month,
        ).delete()
        future_placeholder = self.client.get(
            "/api/v1/reports/current/",
            {"year": future_year, "month": future_month},
        )
        self.assertEqual(future_placeholder.status_code, status.HTTP_200_OK)
        self.assertEqual(future_placeholder.data["status"], "not_started")
        self.assertFalse(future_placeholder.data["capabilities"]["can_start"])
        future = self.client.post(
            f"/api/v1/reports/current/?year={future_year}&month={future_month}",
            {},
        )
        self.assertEqual(future.status_code, status.HTTP_400_BAD_REQUEST)

    def test_assembly_with_no_report_history_can_start_first_current_report(self):
        self.client.force_authenticate(user=self.user)
        AssemblyReport.objects.filter(assembly=self.assembly).delete()

        placeholder = self.client.get("/api/v1/reports/current/")
        self.assertEqual(placeholder.status_code, status.HTTP_200_OK)
        self.assertIsNone(placeholder.data["id"])
        self.assertTrue(placeholder.data["capabilities"]["can_start"])

        created = self.client.post("/api/v1/reports/current/", {})
        self.assertEqual(created.status_code, status.HTTP_200_OK)
        self.assertGreater(created.data["id"], 0)
        self.assertEqual(created.data["assembly"]["id"], self.assembly.id)
        self.assertEqual(len(created.data["sections"]), 6)

        repeated = self.client.post("/api/v1/reports/current/", {})
        self.assertEqual(repeated.status_code, status.HTTP_200_OK)
        self.assertEqual(repeated.data["id"], created.data["id"])
        self.assertEqual(
            AssemblyReport.objects.filter(assembly=self.assembly).count(),
            1,
        )

    def test_assembly_lifecycle_metadata_does_not_make_month_optional(self):
        current_start = timezone.localdate().replace(day=1)
        AssemblyReport.objects.filter(
            assembly=self.assembly,
            period_start=current_start,
        ).delete()
        self.assembly.status = "closed"
        self.assembly.established_date = date(
            current_start.year + 1,
            current_start.month,
            1,
        )
        self.assembly.save(update_fields=["status", "established_date"])
        self.client.force_authenticate(user=self.user)

        placeholder = self.client.get(
            "/api/v1/reports/current/",
            {"year": current_start.year, "month": current_start.month},
        )
        self.assertEqual(placeholder.status_code, status.HTTP_200_OK)
        self.assertIsNone(placeholder.data["id"])
        self.assertEqual(placeholder.data["status"], "not_started")
        self.assertEqual(placeholder.data["completion_percentage"], 0)
        self.assertTrue(placeholder.data["capabilities"]["can_start"])

        overview = self.client.get(
            "/api/v1/reports/overview/",
            {"year": current_start.year},
        )
        self.assertEqual(overview.status_code, status.HTTP_200_OK)
        overview_month = overview.data["months"][current_start.month - 1]
        self.assertEqual(overview_month["status"], "not_started")
        self.assertEqual(overview_month["completion_percentage"], 0)
        self.assertTrue(overview_month["capabilities"]["can_start"])

        created = self.client.post(
            "/api/v1/reports/current/"
            f"?year={current_start.year}&month={current_start.month}",
            {},
        )
        self.assertEqual(created.status_code, status.HTTP_200_OK, created.data)
        repeated = self.client.post(
            "/api/v1/reports/current/"
            f"?year={current_start.year}&month={current_start.month}",
            {},
        )
        self.assertEqual(repeated.status_code, status.HTTP_200_OK, repeated.data)
        self.assertEqual(repeated.data["id"], created.data["id"])
        self.assertEqual(
            AssemblyReport.objects.filter(
                assembly=self.assembly,
                period_start=current_start,
            ).count(),
            1,
        )

    def test_sunday_school_is_not_required_before_september_2026(self):
        august_report = ensure_report(
            assembly=self.assembly,
            period_start=date(2026, 8, 1),
            actor=self.user,
        )
        sections = get_report_sections(august_report)
        sunday_school = next(
            item for item in sections
            if item["key"] == ReportSectionStatus.Section.SUNDAY_SCHOOL_ATTENDANCE
        )

        self.assertEqual(sunday_school["status"], "not_required")
        self.assertTrue(sunday_school["resolved"])
        self.assertFalse(any(
            finding.get("section") == ReportSectionStatus.Section.SUNDAY_SCHOOL_ATTENDANCE
            for finding in validate_report(august_report, sections)
        ))
        confirmed = set_section_status(
            report=august_report,
            section_key=ReportSectionStatus.Section.SUNDAY_SCHOOL_ATTENDANCE,
            status=ReportSectionStatus.Status.NO_ACTIVITY,
            actor=self.user,
        )
        confirmed.refresh_from_db()
        self.assertEqual(confirmed.status, "no_activity")
        set_section_status(
            report=august_report, section_key=confirmed.section,
            status=ReportSectionStatus.Status.NOT_STARTED, actor=self.user,
        )
        restored = next(item for item in get_report_sections(august_report) if item["key"] == confirmed.section)
        self.assertEqual(restored["status"], "not_required")
        self.assertTrue(restored["resolved"])

        september_sections = get_report_sections(self.report)
        september_sunday_school = next(
            item for item in september_sections
            if item["key"] == ReportSectionStatus.Section.SUNDAY_SCHOOL_ATTENDANCE
        )
        self.assertEqual(september_sunday_school["status"], "not_started")
        self.assertFalse(september_sunday_school["resolved"])

    def test_overview_returns_all_months_with_canonical_month_state(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            "/api/v1/reports/overview/",
            {"year": self.report.period_start.year},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["months"]), 12)
        month = response.data["months"][self.report.period_start.month - 1]
        self.assertEqual(month["id"], self.report.id)
        self.assertEqual(month["status"], get_report_state(self.report, self.user).status)

    def test_submitted_month_detail_has_immutable_sections_and_audit_history(self):
        self.resolve_all_sections()
        submitted = submit_report(
            report=self.report,
            actor=self.user,
            declaration_confirmed=True,
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.get(f"/api/v1/reports/{self.report.id}/submitted/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["version_number"], submitted.version_number)
        self.assertTrue(response.data["declaration_confirmed"])
        self.assertEqual(len(response.data["sections"]), 6)
        self.assertGreaterEqual(len(response.data["audit_history"]), 1)

        section_key = response.data["sections"][0]["key"]
        section_url = f"/api/v1/reports/{self.report.id}/submitted/sections/{section_key}/"
        section = self.client.get(section_url)
        self.assertEqual(section.status_code, status.HTTP_200_OK)
        self.assertEqual(section.data["key"], section_key)
        self.assertEqual(self.client.post(section_url, {"total": "999"}).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
