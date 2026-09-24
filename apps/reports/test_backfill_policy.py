from datetime import date, datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.bookkeeper.models import Tithe
from apps.churches.models import Church
from apps.people.models import Attendance
from apps.reports.models import AssemblyReport, ReportVersion
from apps.reports.services.lifecycle import (
    can_complete_report, can_create_report, ensure_report,
    get_report_state, is_backfill_period,
)
from apps.users.models import User


def local_time(year, month, day, hour=12):
    return timezone.make_aware(datetime(year, month, day, hour))


@override_settings(TIME_ZONE="Africa/Harare")
class ReportBackfillPolicyTests(APITestCase):
    def setUp(self):
        self.now = local_time(2026, 9, 15)
        clock = patch("django.utils.timezone.now", return_value=self.now)
        clock.start()
        self.addCleanup(clock.stop)
        self.assembly = Church.objects.create(name="Backfill Assembly", country="Botswana", currency="BWP")
        self.other_assembly = Church.objects.create(name="Other Assembly", country="Botswana", currency="BWP")
        self.user = User.objects.create_user(first_name="Test", last_name="Secretary", username="backfill.secretary", email="backfill@example.com", church=self.assembly)
        self.outsider = User.objects.create_user(first_name="Test", last_name="Secretary", username="other.secretary", email="other@example.com", church=self.other_assembly)
        self.client.force_authenticate(self.user)

    def report(self, month=1, year=2026):
        return ensure_report(assembly=self.assembly, period_start=date(year, month, 1), actor=self.user)

    def submit_fixture(self, report, *, locked=False):
        submitted_at = self.now - timedelta(days=10 if locked else 1)
        version = ReportVersion.objects.create(
            report=report, version_number=1, submitted_by=self.user,
            submitted_at=submitted_at, editable_until=submitted_at + timedelta(days=7),
            declaration_confirmed=True,
        )
        report.current_version = version
        report.status = AssemblyReport.Status.SUBMITTED
        report.submitted_at = submitted_at
        report.save(update_fields=["current_version", "status", "submitted_at"])

    def test_january_and_august_overdue_capabilities_and_patch(self):
        for month in (1, 8):
            with self.subTest(month=month):
                report = self.report(month)
                record = Attendance.objects.create(assembly=self.assembly, report=report, timestamp=date(2026, month, 10), preacher="Original")
                state = get_report_state(report, self.user, now=self.now)
                self.assertEqual(state.status, "overdue")
                self.assertTrue(state.is_editable)
                self.assertTrue(state.backfill_active)
                detail = self.client.get(f"/api/v1/reports/{report.pk}/")
                self.assertEqual(detail.status_code, 200)
                self.assertTrue(detail.data["capabilities"]["is_editable"])
                self.assertTrue(detail.data["capabilities"]["backfill_active"])
                response = self.client.patch(f"/api/v1/people/attendance/{record.pk}/", {"preacher": "Updated"}, format="json")
                self.assertEqual(response.status_code, 200, response.data)
                record.refresh_from_db()
                self.assertEqual(record.preacher, "Updated")

    def test_missing_january_and_august_can_be_created(self):
        for month in (1, 8):
            url = f"/api/v1/reports/current/?year=2026&month={month}"
            placeholder = self.client.get(url)
            self.assertEqual(placeholder.status_code, 200)
            self.assertIsNone(placeholder.data["id"])
            self.assertTrue(placeholder.data["capabilities"]["can_start"])
            response = self.client.post(url, {}, format="json")
            self.assertEqual(response.status_code, 200, response.data)
            self.assertTrue(response.data["capabilities"]["is_editable"])
            self.assertTrue(response.data["capabilities"]["backfill_active"])
            self.assertEqual(AssemblyReport.objects.filter(assembly=self.assembly, period_start=date(2026, month, 1)).count(), 1)

    def test_submitted_and_locked_cannot_be_patched_or_recreated(self):
        for month, locked in ((1, False), (8, True)):
            report = self.report(month)
            record = Attendance.objects.create(assembly=self.assembly, report=report, timestamp=date(2026, month, 10), preacher="Protected")
            self.submit_fixture(report, locked=locked)
            state = get_report_state(report, self.user, now=self.now)
            self.assertEqual(state.status, "locked" if locked else "submitted")
            self.assertFalse(state.is_editable)
            self.assertFalse(state.backfill_active)
            response = self.client.patch(f"/api/v1/people/attendance/{record.pk}/", {"preacher": "Bypass"}, format="json")
            self.assertIn(response.status_code, (400, 403))
            response = self.client.patch(f"/api/v1/reports/{report.pk}/", {"attendance_total": 999}, format="json")
            self.assertEqual(response.status_code, 403)
            response = self.client.post(f"/api/v1/reports/current/?year=2026&month={month}", {}, format="json")
            self.assertEqual(response.status_code, 403)
            record.refresh_from_db()
            self.assertEqual(record.preacher, "Protected")

    def test_legacy_submitted_without_a_version_is_not_opened(self):
        report = self.report()
        report.status = AssemblyReport.Status.SUBMITTED
        report.save(update_fields=["status"])
        self.assertFalse(can_complete_report(self.user, report, now=self.now))

    def test_unauthorised_user_cannot_edit_or_create_for_another_assembly(self):
        report = self.report()
        record = Attendance.objects.create(assembly=self.assembly, report=report, timestamp=date(2026, 1, 10))
        self.assertFalse(can_complete_report(self.outsider, report, now=self.now))
        self.assertFalse(can_create_report(self.outsider, assembly=self.assembly, period_start=date(2026, 8, 1), now=self.now))
        with self.assertRaises(PermissionDenied):
            ensure_report(assembly=self.assembly, period_start=date(2026, 8, 1), actor=self.outsider)
        self.client.force_authenticate(self.outsider)
        response = self.client.patch(f"/api/v1/people/attendance/{record.pk}/", {"preacher": "Bypass"}, format="json")
        self.assertIn(response.status_code, (403, 404))
        self.client.force_authenticate(user=None)
        response = self.client.post("/api/v1/reports/current/?year=2026&month=8", {}, format="json")
        self.assertIn(response.status_code, (401, 403))

    def test_outside_periods_follow_normal_policy(self):
        for year, month in ((2025, 12), (2026, 9)):
            report = self.report(month, year)
            state = get_report_state(report, self.user, now=self.now)
            self.assertFalse(state.backfill_active)
            with override_settings(REPORT_BACKFILL={**settings.REPORT_BACKFILL, "enabled": False}):
                self.assertEqual(state.is_editable, get_report_state(report, self.user, now=self.now).is_editable)
        self.assertFalse(can_create_report(self.user, assembly=self.assembly, period_start=date(2026, 10, 1), now=self.now))

    def test_window_boundaries_expire_to_normal_policy(self):
        report = self.report()
        for moment, active in (
            (local_time(2026, 8, 31), False),
            (local_time(2026, 9, 1, 0), True),
            (local_time(2026, 9, 30, 23), True),
            (local_time(2026, 10, 1, 0), False),
        ):
            state = get_report_state(report, self.user, now=moment)
            self.assertEqual(state.backfill_active, active)
            if not active:
                with override_settings(REPORT_BACKFILL={**settings.REPORT_BACKFILL, "enabled": False}):
                    self.assertEqual(state.is_editable, get_report_state(report, self.user, now=moment).is_editable)
        # Midnight is in the project's timezone, not the UTC calendar date.
        self.assertFalse(is_backfill_period(report.period_start, now=datetime(2026, 9, 30, 22, tzinfo=ZoneInfo("UTC"))))

    def test_october_api_response_and_patch_follow_normal_policy(self):
        report = self.report()
        record = Attendance.objects.create(assembly=self.assembly, report=report, timestamp=date(2026, 1, 10))
        with patch("django.utils.timezone.now", return_value=local_time(2026, 10, 1)):
            response = self.client.get(f"/api/v1/reports/{report.pk}/")
            self.assertFalse(response.data["capabilities"]["backfill_active"])
            # Existing normal policy still permits open overdue reports.
            self.assertTrue(response.data["capabilities"]["is_editable"])
            response = self.client.patch(f"/api/v1/people/attendance/{record.pk}/", {"preacher": "Normal policy"}, format="json")
            self.assertEqual(response.status_code, 200, response.data)

    def test_report_schemas_preserve_column_and_row_restrictions(self):
        report = self.report()
        Attendance.objects.create(assembly=self.assembly, report=report, timestamp=date(2026, 1, 10))
        response = self.client.get(f"/api/v1/reports/{report.pk}/attendance/")
        self.assertEqual(response.status_code, 200, response.data)
        config = response.data["config"]
        self.assertTrue(config["variant"]["interaction"]["editable"])
        columns = {col["id"]: col for col in config["columns"]}
        self.assertTrue(columns["preacher"]["editable"])
        self.assertFalse(columns["total_adults"]["editable"])
        self.submit_fixture(report)
        response = self.client.get(f"/api/v1/reports/{report.pk}/attendance/")
        self.assertFalse(response.data["config"]["variant"]["interaction"]["editable"])

    def test_incomplete_sources_and_finance_batch_use_central_policy(self):
        report = self.report()
        report.status = AssemblyReport.Status.IN_PROGRESS
        report.save(update_fields=["status"])
        record = Attendance.objects.create(assembly=self.assembly, report=report, timestamp=date(2026, 1, 10))
        response = self.client.patch(f"/api/v1/people/attendance/{record.pk}/", {"preacher": "Incomplete"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        payload = {"period": "2026-01", "report": report.pk, "entries": [{"member": None, "amount": "10.00", "payment_method": "Cash", "timestamp": "2026-01-10"}]}
        response = self.client.post("/api/v1/bookkeeper/tithes/batch/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        tithe = Tithe.objects.get(report=report)
        response = self.client.patch(f"/api/v1/bookkeeper/tithes/{tithe.pk}/", {"amount": "25.00"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.submit_fixture(report)
        response = self.client.patch(f"/api/v1/bookkeeper/tithes/{tithe.pk}/", {"amount": "999.00"}, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        response = self.client.post("/api/v1/bookkeeper/tithes/batch/", payload, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        tithe.refresh_from_db()
        self.assertEqual(str(tithe.amount), "25.00")

    def test_ineligible_period_cannot_receive_the_backfill_grant(self):
        for period in (date(2025, 12, 1), date(2026, 9, 1), date(2027, 1, 1)):
            self.assertFalse(is_backfill_period(period, now=self.now))
        with override_settings(REPORT_BACKFILL={**settings.REPORT_BACKFILL, "enabled": False}):
            self.assertFalse(is_backfill_period(date(2026, 1, 1), now=self.now))
