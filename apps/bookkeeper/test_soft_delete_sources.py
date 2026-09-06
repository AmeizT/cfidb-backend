from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookkeeper.models import Expenditure, Overhead, OverheadType, Revenue, RevenueCategory, Tithe
from apps.churches.models import Church
from apps.people.models import Attendance, Member, SundaySchoolAttendance
from apps.reports.models import AssemblyReport, ReportVersion
from apps.users.models import User


class SourceSoftDeleteTests(TestCase):
    def setUp(self):
        self.assembly = Church.objects.create(name="Soft Delete Assembly")
        self.user = User.objects.create_user(
            first_name="Data", last_name="Admin", username="data-admin",
            email="data-admin@example.com", password="password", church=self.assembly,
        )
        self.user.is_admin = True
        self.user.save(update_fields=["is_admin"])
        self.member = Member.objects.create(
            assembly=self.assembly, first_name="History", last_name="Keeper",
            date_of_birth=date(1990, 1, 1), gender="Male", country="Botswana",
        )
        self.report = AssemblyReport.objects.create(
            assembly=self.assembly,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 31),
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_financial_delete_is_soft_and_recalculates_report_totals(self):
        category = RevenueCategory.objects.create(
            assembly=self.assembly, name="General Income", needs_review=True,
        )
        overhead_type = OverheadType.objects.create(
            assembly=self.assembly, name="Utilities", needs_review=True,
        )
        tithe = Tithe.objects.create(
            assembly=self.assembly, report=self.report, member=self.member,
            amount=Decimal("100.00"), timestamp=date(2026, 7, 5),
        )
        revenue = Revenue.objects.create(
            assembly=self.assembly, report=self.report, category=category,
            amount=Decimal("200.00"), timestamp=date(2026, 7, 6),
        )
        overhead = Overhead.objects.create(
            assembly=self.assembly, report=self.report, overhead_type=overhead_type,
            amount=Decimal("40.00"), timestamp=date(2026, 7, 7),
        )
        expenditure = Expenditure.objects.create(
            assembly=self.assembly, report=self.report, created_by=self.user,
            invoice_date=date(2026, 7, 8), timestamp=date(2026, 7, 8),
            name="Supplies", category="office", quantity=2, price=Decimal("15.00"),
        )

        for route, record, model in (
            ("tithes", tithe, Tithe),
            ("revenue", revenue, Revenue),
            ("overhead", overhead, Overhead),
            ("expenditure", expenditure, Expenditure),
        ):
            response = self.client.delete(f"/api/v1/bookkeeper/{route}/{record.pk}/")
            self.assertEqual(response.status_code, 204, response.data if hasattr(response, "data") else None)
            self.assertFalse(model.objects.filter(pk=record.pk).exists())
            deleted = model.all_objects.get(pk=record.pk)
            self.assertTrue(deleted.is_trash)
            self.assertIsNotNone(deleted.trash_date)

        self.report.refresh_from_db()
        self.assertEqual(self.report.tithe_total, Decimal("0"))
        self.assertEqual(self.report.income_total, Decimal("0"))
        self.assertEqual(self.report.expense_total, Decimal("0"))
        self.assertEqual(self.report.balance, Decimal("0"))

    def test_attendance_sources_are_soft_deleted_and_totals_recalculate(self):
        attendance = Attendance.objects.create(
            assembly=self.assembly, report=self.report, timestamp=date(2026, 7, 5),
            service_type="Sunday", men=10, women=12,
        )
        sunday_school_report = AssemblyReport.objects.create(
            assembly=self.assembly,
            period_start=date(2026, 9, 1),
            period_end=date(2026, 9, 30),
        )
        sunday_school = SundaySchoolAttendance.objects.create(
            assembly=self.assembly, report=sunday_school_report, teacher=self.member,
            service_date=date(2026, 9, 6), class_name="beginners", boys=4, girls=5,
            reported_by=self.user,
        )

        first = self.client.delete(f"/api/v1/people/attendance/{attendance.pk}/")
        second = self.client.delete(f"/api/v1/people/sunday-school-attendance/{sunday_school.pk}/")
        self.assertEqual(first.status_code, 204, first.data if hasattr(first, "data") else None)
        self.assertEqual(second.status_code, 204, second.data if hasattr(second, "data") else None)
        self.assertFalse(Attendance.objects.filter(pk=attendance.pk).exists())
        self.assertFalse(SundaySchoolAttendance.objects.filter(pk=sunday_school.pk).exists())
        self.assertTrue(Attendance.all_objects.get(pk=attendance.pk).is_deleted)
        self.assertTrue(SundaySchoolAttendance.all_objects.get(pk=sunday_school.pk).is_deleted)
        self.report.refresh_from_db()
        self.assertEqual(self.report.attendance_total, 0)
        sunday_school_report.refresh_from_db()
        self.assertEqual(sunday_school_report.attendance_total, 0)

    def test_submitted_report_source_cannot_be_deleted(self):
        tithe = Tithe.objects.create(
            assembly=self.assembly, report=self.report, member=self.member,
            amount=Decimal("100.00"), timestamp=date(2026, 7, 5),
        )
        version = ReportVersion.objects.create(
            report=self.report, version_number=1, submitted_by=self.user,
            submitted_at=timezone.now(), editable_until=timezone.now() + timedelta(days=7),
            declaration_confirmed=True,
        )
        self.report.current_version = version
        self.report.status = AssemblyReport.Status.SUBMITTED
        self.report.save(update_fields=["current_version", "status"])

        response = self.client.delete(f"/api/v1/bookkeeper/tithes/{tithe.pk}/")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Tithe.objects.filter(pk=tithe.pk).exists())
        self.assertFalse(Tithe.all_objects.get(pk=tithe.pk).is_trash)
