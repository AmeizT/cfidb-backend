from datetime import date
from decimal import Decimal
from io import StringIO
import os
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.management.base import CommandError
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.utils import timezone

from apps.bookkeeper.models import (
    FixedExpenditure,
    Income,
    Overhead,
    RemittanceObligation,
    RemittancePayment,
    Revenue,
    RevenueCategory,
    Tithe,
)
from apps.churches.models import Church
from apps.people.models import Attendance, Member, SundaySchoolAttendance
from apps.reports.migration.runner import (
    backfill_attendance_headcounts,
    backfill_finance_models,
    backfill_report_relationships,
    latest_wins,
)
from apps.reports.migration.core import (
    assert_local_or_explicitly_authorized,
    load_mapping_manifest,
)
from apps.reports.migration.verification import verify_historical_migration
from apps.reports.models import (
    AssemblyReport,
    HistoricalMigrationLineage,
    ReportSectionStatus,
)
from apps.reports.services.lifecycle import REQUIRED_SECTIONS, ensure_report, get_report_state
from apps.users.models import User


class HistoricalMigrationBase(TestCase):
    def setUp(self):
        self.assembly = Church.objects.create(name="Historical Migration Assembly")
        self.member = Member.objects.create(
            assembly=self.assembly,
            member_key="historical-member",
            first_name="History",
            last_name="Member",
            date_of_birth=date(1990, 1, 1),
            gender="Male",
            country="Botswana",
        )

    def report(self, value=date(2026, 7, 1), **kwargs):
        return ensure_report(assembly=self.assembly, period_start=value, **kwargs)


class CanonicalReportSafetyTests(HistoricalMigrationBase):
    def test_ensure_report_creates_canonical_month_and_six_sections(self):
        report = ensure_report(assembly=self.assembly, period_start=date(2026, 7, 17))
        self.assertEqual(report.period_start, date(2026, 7, 1))
        self.assertEqual(report.period_end, date(2026, 7, 31))
        self.assertEqual(set(report.sections.values_list("section", flat=True)), set(REQUIRED_SECTIONS))

    def test_noncanonical_overlap_blocks_canonical_creation(self):
        AssemblyReport.objects.create(
            assembly=self.assembly,
            period_start=date(2026, 7, 31),
            period_end=date(2026, 7, 31),
        )
        with self.assertRaises(ValidationError):
            ensure_report(assembly=self.assembly, period_start=date(2026, 7, 1))
        verification = verify_historical_migration(assembly=self.assembly.pk)
        self.assertTrue(verification.blocked)
        self.assertIn("noncanonical_period", {item.code for item in verification.findings})

    def test_historical_report_is_not_marked_overdue(self):
        report = ensure_report(
            assembly=self.assembly,
            period_start=date(2020, 1, 1),
            historical_backfill=True,
        )
        state = get_report_state(report, now=timezone.now())
        self.assertFalse(state.is_overdue)
        self.assertEqual(state.status, "historical_backfill")


class HistoricalAttendanceTests(HistoricalMigrationBase):
    def test_historical_formula_excludes_visitors_and_survives_save(self):
        report = self.report()
        attendance = Attendance.objects.create(
            assembly=self.assembly,
            report=report,
            timestamp=date(2026, 7, 5),
            adults=100,
            children=25,
            guest_attendance=12,
            online_viewers=8,
            collection_schema=Attendance.CollectionSchema.LEGACY,
            men=None,
            women=None,
            visitor_men=None,
            visitor_women=None,
            new_convert_men=None,
            new_convert_women=None,
            altar_call_men=None,
            altar_call_women=None,
            baptism_men=None,
            baptism_women=None,
        )
        self.assertEqual(attendance.headcount, 133)
        attendance.notes = "later edit"
        attendance.save(update_fields=["notes"])
        attendance.refresh_from_db()
        self.assertEqual(attendance.total_adults, 100)
        self.assertEqual(attendance.total_visitors, 12)
        self.assertIsNone(attendance.men)
        report.refresh_from_db()
        self.assertEqual(report.attendance_total, 133)

    def test_attendance_backfill_dry_run_and_apply_are_durable(self):
        self.report()
        row = Attendance.objects.create(
            assembly=self.assembly,
            timestamp=date(2026, 7, 5),
            adults=40,
            children=9,
            guest_attendance=5,
            online_viewers=2,
            men=20,
            women=20,
        )
        before = HistoricalMigrationLineage.objects.count()
        result = backfill_attendance_headcounts(apply=False, assembly=self.assembly.pk)
        row.refresh_from_db()
        self.assertTrue(result.dry_run)
        self.assertEqual(row.collection_schema, Attendance.CollectionSchema.GENDER_SPLIT)
        self.assertEqual(HistoricalMigrationLineage.objects.count(), before)
        backfill_attendance_headcounts(apply=True, assembly=self.assembly.pk)
        row.refresh_from_db()
        self.assertEqual(row.collection_schema, Attendance.CollectionSchema.LEGACY)
        self.assertIsNone(row.men)
        self.assertEqual(row.headcount, 51)

    def test_sunday_school_rejects_prelaunch_and_links_report(self):
        invalid = SundaySchoolAttendance(
            assembly=self.assembly,
            teacher=self.member,
            service_date=date(2026, 8, 30),
            class_name="primary",
        )
        with self.assertRaises(ValidationError):
            invalid.save()
        valid = SundaySchoolAttendance.objects.create(
            assembly=self.assembly,
            teacher=self.member,
            service_date=date(2026, 9, 6),
            class_name="primary",
            boys=4,
            girls=5,
        )
        self.assertEqual(valid.report.period_start, date(2026, 9, 1))


class FinanceMigrationTests(HistoricalMigrationBase):
    def _income(self, offering, **values):
        return Income.objects.create(
            church=self.assembly,
            timestamp=date(2026, 7, 31),
            offering=Decimal(offering),
            fundraising=Decimal(values.get("fundraising", "0")),
            thanksgiving=Decimal(values.get("thanksgiving", "0")),
            donations=Decimal(values.get("donations", "0")),
        )

    def test_latest_income_wins_superseded_lineage_and_idempotency(self):
        report = self.report()
        older = self._income("100.00")
        winner = self._income("250.00", fundraising="30.00")
        selected, superseded = latest_wins([older, winner])
        self.assertEqual(selected, winner)
        self.assertEqual(superseded, [older])
        dry = backfill_finance_models(apply=False, assembly=self.assembly.pk)
        self.assertEqual(Revenue.objects.filter(report=report).count(), 0)
        self.assertEqual(HistoricalMigrationLineage.objects.count(), 0)
        self.assertTrue(any("DUPLICATE MONTHLY INCOME" in line for line in dry.messages))
        first = backfill_finance_models(apply=True, assembly=self.assembly.pk)
        self.assertEqual(
            Revenue.objects.filter(report=report).aggregate(total=Sum("amount"))["total"],
            Decimal("280.00"),
        )
        self.assertTrue(HistoricalMigrationLineage.objects.filter(
            source_model="income", source_pk=str(older.pk), status="superseded"
        ).exists())
        target_count = Revenue.objects.filter(report=report).count()
        second = backfill_finance_models(apply=True, assembly=self.assembly.pk)
        self.assertEqual(Revenue.objects.filter(report=report).count(), target_count)
        self.assertEqual(second.created, 0)
        self.assertGreater(first.created, 0)

    def test_fixed_expenditure_investment_and_verified_remittance(self):
        report = self.report()
        reviewer = User.objects.create_user(
            first_name="Remittance",
            last_name="Reviewer",
            username="remittance-reviewer",
            email="reviewer@example.com",
            password="password",
            church=self.assembly,
        )
        Tithe.objects.create(
            assembly=self.assembly,
            report=report,
            member=self.member,
            timestamp=date(2026, 7, 10),
            amount=Decimal("1000.00"),
        )
        fixed = FixedExpenditure.objects.create(
            assembly=self.assembly,
            timestamp=date(2026, 7, 31),
            investment=Decimal("75.00"),
            remittance=Decimal("100.00"),
            remittance_receipt="remittance/legacy.pdf",
            is_remittance_verified=True,
            remittance_moderator=reviewer,
        )
        backfill_finance_models(apply=True, assembly=self.assembly.pk)
        investment = Overhead.objects.get(report=report, overhead_type__name="Investment")
        self.assertEqual(investment.amount, Decimal("75.00"))
        self.assertEqual(investment.overhead_type.reporting_group, "Operating Expenses")
        obligation = RemittanceObligation.objects.get(source_fixed_expenditure=fixed)
        self.assertEqual(obligation.amount_due, Decimal("100.00"))
        self.assertEqual(obligation.outstanding_amount, Decimal("0.00"))
        payment = RemittancePayment.objects.get(obligation=obligation)
        self.assertEqual(payment.status, RemittancePayment.Status.VERIFIED)
        report.refresh_from_db()
        self.assertEqual(report.expense_total, Decimal("175.00"))

    def test_latest_fixed_expenditure_wins_without_aggregation(self):
        report = self.report()
        older = FixedExpenditure.objects.create(
            assembly=self.assembly,
            timestamp=date(2026, 7, 31),
            rent=Decimal("10.00"),
        )
        winner = FixedExpenditure.objects.create(
            assembly=self.assembly,
            timestamp=date(2026, 7, 31),
            rent=Decimal("45.00"),
        )
        result = backfill_finance_models(apply=True, assembly=self.assembly.pk)
        self.assertTrue(any("DUPLICATE MONTHLY FIXEDEXPENDITURE" in line for line in result.messages))
        self.assertEqual(
            Overhead.objects.get(report=report, overhead_type__name="Rent").amount,
            Decimal("45.00"),
        )
        self.assertTrue(HistoricalMigrationLineage.objects.filter(
            source_model="fixedexpenditure",
            source_pk=str(older.pk),
            status=HistoricalMigrationLineage.Status.SUPERSEDED,
        ).exists())
        self.assertFalse(HistoricalMigrationLineage.objects.filter(
            source_model="fixedexpenditure",
            source_pk=str(winner.pk),
            status=HistoricalMigrationLineage.Status.SUPERSEDED,
        ).exists())

    def test_pending_remittance_claim_does_not_reduce_cash_balance(self):
        report = self.report()
        Tithe.objects.create(
            assembly=self.assembly,
            report=report,
            member=self.member,
            timestamp=date(2026, 7, 10),
            amount=Decimal("1000.00"),
        )
        FixedExpenditure.objects.create(
            assembly=self.assembly,
            timestamp=date(2026, 7, 31),
            remittance=Decimal("100.00"),
            remittance_receipt="remittance/unverified.pdf",
            is_remittance_verified=False,
        )
        backfill_finance_models(apply=True, assembly=self.assembly.pk)
        payment = RemittancePayment.objects.get()
        obligation = payment.obligation
        self.assertEqual(payment.status, RemittancePayment.Status.PENDING)
        self.assertEqual(obligation.amount_due, Decimal("100.00"))
        self.assertEqual(obligation.outstanding_amount, Decimal("100.00"))
        report.refresh_from_db()
        self.assertEqual(report.expense_total, Decimal("0.00"))

    def test_cutoff_rejects_new_legacy_rows(self):
        with self.assertRaises(ValidationError):
            Income.objects.create(
                church=self.assembly,
                timestamp=date(2026, 8, 1),
                offering=Decimal("10.00"),
            )
        with self.assertRaises(ValidationError):
            FixedExpenditure.objects.create(
                assembly=self.assembly,
                timestamp=date(2026, 8, 1),
            )

    def test_submitted_report_is_protected(self):
        report = self.report()
        AssemblyReport.objects.filter(pk=report.pk).update(status=AssemblyReport.Status.SUBMITTED)
        self._income("100.00")
        result = backfill_finance_models(apply=True, assembly=self.assembly.pk)
        self.assertGreater(result.conflicts, 0)
        self.assertEqual(Revenue.objects.filter(report=report).count(), 0)


class TitheDuplicateTests(HistoricalMigrationBase):
    def test_latest_active_tithe_is_linked_and_older_is_superseded(self):
        report = self.report()
        rows = [
            Tithe(
                assembly=self.assembly,
                member=self.member,
                timestamp=date(2026, 7, 5),
                amount=Decimal("100.00"),
                report=None,
            ),
            Tithe(
                assembly=self.assembly,
                member=self.member,
                timestamp=date(2026, 7, 20),
                amount=Decimal("150.00"),
                report=None,
            ),
        ]
        Tithe.all_objects.bulk_create(rows)
        winner = max(rows, key=lambda row: row.pk)
        older = min(rows, key=lambda row: row.pk)
        result = backfill_report_relationships(apply=True, assembly=self.assembly.pk)
        winner.refresh_from_db()
        older.refresh_from_db()
        self.assertEqual(winner.report_id, report.pk)
        self.assertIsNone(older.report_id)
        self.assertTrue(any("DUPLICATE TITHE" in line for line in result.messages))
        self.assertTrue(HistoricalMigrationLineage.objects.filter(
            source_model="tithe", source_pk=str(older.pk), status="superseded"
        ).exists())


class CommandSafetyTests(HistoricalMigrationBase):
    def test_dry_run_command_writes_nothing(self):
        self._make_source()
        before = (
            AssemblyReport.objects.count(),
            HistoricalMigrationLineage.objects.count(),
        )
        output = StringIO()
        call_command(
            "backfill_monthly_reports",
            "--assembly", str(self.assembly.pk),
            stdout=output,
        )
        self.assertIn("DRY-RUN (NO WRITES)", output.getvalue())
        self.assertEqual(before, (
            AssemblyReport.objects.count(),
            HistoricalMigrationLineage.objects.count(),
        ))

    def test_rehearsal_neon_requires_rehearsal_authorization(self):
        with patch.dict(
            connection.settings_dict,
            {
                "HOST": "ep-example.neon.tech",
                "NAME": "rehearsal",
                "ENGINE": "django.db.backends.postgresql",
            },
        ), patch.dict(os.environ, {"DJANGO_ENV": "REHEARSAL"}, clear=False):
            os.environ.pop("CFI_MIGRATION_REHEARSAL", None)
            with self.assertRaises(CommandError):
                assert_local_or_explicitly_authorized(apply=False)

    def test_production_neon_dry_run_is_allowed(self):
        with patch.dict(
            connection.settings_dict,
            {
                "HOST": "ep-example.neon.tech",
                "NAME": "production",
                "ENGINE": "django.db.backends.postgresql",
            },
        ), patch.dict(os.environ, {"DJANGO_ENV": "PRODUCTION"}, clear=False):
            os.environ.pop("CFI_MIGRATION_REHEARSAL", None)
            os.environ.pop("CFI_ALLOW_HISTORICAL_MIGRATION", None)
            assert_local_or_explicitly_authorized(apply=False)

    def test_production_neon_write_requires_write_authorization(self):
        with patch.dict(
            connection.settings_dict,
            {
                "HOST": "ep-example.neon.tech",
                "NAME": "production",
                "ENGINE": "django.db.backends.postgresql",
            },
        ), patch.dict(os.environ, {"DJANGO_ENV": "PRODUCTION"}, clear=False):
            os.environ.pop("CFI_MIGRATION_REHEARSAL", None)
            os.environ.pop("CFI_ALLOW_HISTORICAL_MIGRATION", None)
            with self.assertRaises(CommandError):
                assert_local_or_explicitly_authorized(apply=True)

    def test_production_neon_rehearsal_flag_is_blocked(self):
        with patch.dict(
            connection.settings_dict,
            {
                "HOST": "ep-example.neon.tech",
                "NAME": "production",
                "ENGINE": "django.db.backends.postgresql",
            },
        ), patch.dict(
            os.environ,
            {
                "DJANGO_ENV": "PRODUCTION",
                "CFI_MIGRATION_REHEARSAL": "1",
            },
            clear=False,
        ):
            with self.assertRaises(CommandError):
                assert_local_or_explicitly_authorized(apply=False)

    def _make_source(self):
        Attendance.objects.bulk_create([Attendance(
            assembly=self.assembly,
            timestamp=date(2026, 6, 1),
            adults=10,
        )])

    def test_completed_sequence_reconciles_without_blockers(self):
        self.report()
        for mapping in load_mapping_manifest()["income_to_revenue"]:
            RevenueCategory.objects.get_or_create(
                assembly=None,
                is_standard=True,
                name=mapping["target_category"],
            )
        Income.objects.create(
            church=self.assembly,
            timestamp=date(2026, 7, 31),
            offering=Decimal("125.00"),
        )
        Attendance.objects.create(
            assembly=self.assembly,
            timestamp=date(2026, 7, 6),
            adults=20,
            children=4,
            guest_attendance=3,
            online_viewers=1,
        )
        relationship_result = backfill_report_relationships(
            apply=True,
            assembly=self.assembly.pk,
        )
        self.assertEqual(
            relationship_result.conflicts,
            0,
            relationship_result.payload(),
        )
        attendance_result = backfill_attendance_headcounts(
            apply=True,
            assembly=self.assembly.pk,
        )
        self.assertEqual(
            attendance_result.conflicts,
            0,
            attendance_result.payload(),
        )
        finance_result = backfill_finance_models(
            apply=True,
            assembly=self.assembly.pk,
        )
        self.assertEqual(
            finance_result.conflicts,
            0,
            finance_result.payload(),
        )
        verification = verify_historical_migration(assembly=self.assembly.pk)
        self.assertFalse(verification.blocked, verification.payload())


# Imported at the end to keep the financial assertion above visually close to its use.
from django.db.models import Sum
