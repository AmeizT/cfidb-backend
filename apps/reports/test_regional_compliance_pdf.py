from copy import deepcopy
from datetime import date, datetime, timezone
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from pypdf import PdfReader
from rest_framework.exceptions import PermissionDenied
from apps.reports.services import regional_compliance_pdf as pdf


class RegionalCompliancePdfTests(SimpleTestCase):
    def test_badges_use_actual_states_without_mutation(self):
        sections = {key: {"status": state} for key, state in [
            ("general_attendance", "COMPLETED"), ("sunday_school_attendance", "IN_PROGRESS"),
            ("tithes", "NO_ACTIVITY"), ("revenue", "NOT_STARTED"),
            ("operating_expenses", "COMPLETED"), ("activity_other_expenses", "NOT_STARTED"),
        ]}
        original = deepcopy(sections)
        self.assertEqual(pdf._badge_entries(sections), [
            ("AT", "present"), ("SAT", "progress"), ("TI", "present"),
            ("IN", "missing"), ("EX", "progress"), ("RM", "unavailable"),
        ])
        self.assertEqual(sections, original)

    def test_display_aliases_are_not_canonical_backend_keys(self):
        entries = dict(pdf._badge_entries({key: {"status": "COMPLETED"} for key in [
            "AT", "attendance", "income", "tithe", "expenditure", "remittance", "sunday_school",
        ]}))
        self.assertEqual(entries, {"AT": "missing", "SAT": "missing", "TI": "missing", "IN": "missing", "EX": "missing", "RM": "unavailable"})

    def test_combined_expenses_preserve_incomplete_and_skipped_states(self):
        for left, right, expected in [
            ("COMPLETED", "NO_ACTIVITY", "present"), ("NOT_STARTED", "NOT_STARTED", "missing"),
            ("COMPLETED", "IN_PROGRESS", "progress"), ("SKIPPED", "COMPLETED", "skipped"),
        ]:
            with self.subTest(left=left, right=right):
                self.assertEqual(dict(pdf._badge_entries({
                    "operating_expenses": {"status": left}, "activity_other_expenses": {"status": right},
                }))["EX"], expected)

    def test_badges_wrap_without_overflow(self):
        badges = pdf.SectionBadges(pdf._badge_entries({}))
        width, height = badges.wrap(80, 500)
        self.assertLessEqual(width, 80)
        self.assertGreater(height, badges.badge_height)

    def test_unauthorized_pdf_does_not_read_report_data(self):
        with patch.object(pdf, "_scope_rows") as rows:
            with self.assertRaises(PermissionDenied):
                pdf.build_regional_monthly_compliance_pdf(region=SimpleNamespace(pk=1), user=SimpleNamespace(is_authenticated=False), query_params={})
            rows.assert_not_called()

    def test_large_multimonth_pdf_pagination_and_data_preservation(self):
        rows = [{
            "name": f"Assembly {index:02d} with a longer name", "zone": "A long zone name", "country": "Namibia",
            "monthly_compliance": [{
                "period": f"2026-{month:02d}", "completion": 50, "report_status": "DRAFT",
                "due_date": date(2026, 9, 5), "submitted_at": None, "is_late": False,
                "sections": {"sunday_school_attendance": {"status": "SKIPPED", "skip_reason": "records_unavailable"}},
            } for month in [7, 8]],
        } for index in range(45)]
        original = deepcopy(rows)
        with patch.object(pdf, "_scope_rows", return_value=(rows, None)), patch.object(pdf, "_record_audit_event") as audit, patch.object(pdf.timezone, "now", return_value=datetime(2026, 9, 24, tzinfo=timezone.utc)):
            result = pdf.build_regional_monthly_compliance_pdf(
                region=SimpleNamespace(pk=1, name="Sample Region"),
                user=SimpleNamespace(is_authenticated=True, is_admin=True, full_name="Test Overseer"),
                query_params={"year": "2026", "from_month": "7", "to_month": "8"},
            )
        self.assertEqual(rows, original)
        audit.assert_called_once()
        reader = PdfReader(BytesIO(result.buffer.getvalue()))
        texts = [page.extract_text() for page in reader.pages]
        self.assertGreater(len(reader.pages), 5)
        text = "\n".join(texts)
        for expected in ["July-August 2026", "Sunday School Attendance", "Records Unavailable", "Due 5 September 2026"]:
            self.assertIn(expected, text)
        self.assertNotIn("Report fields", text)
        self.assertNotIn("AT: MIS", text)
        for index, (page, content) in enumerate(zip(reader.pages, texts), 1):
            self.assertGreater(float(page.mediabox.width), float(page.mediabox.height))
            self.assertIn(f"Page {index} of {len(reader.pages)}", content)
            if "50%" in content and index > 1:
                self.assertIn("Assembly", content)
                self.assertIn("Submitted on", content)
                self.assertIn("Sections", content)
        self.assertEqual(" ".join(text.split()).count("Assembly 44 with a longer name"), 4)


class EffectivePdfSectionTests(SimpleTestCase):
    def report(self, month=9):
        from apps.reports.models import AssemblyReport, ReportSectionStatus
        report = AssemblyReport(pk=1, assembly_id=1, period_start=date(2026, month, 1), period_end=date(2026, month, 28))
        sections = [ReportSectionStatus(report=report, section=key) for key in ReportSectionStatus.Section.values]
        report._prefetched_objects_cache = {"sections": sections}
        return report, sections

    def test_three_source_sections_are_green_and_fifty_percent_with_stale_stored_status(self):
        from apps.reports.services.pdf_section_states import resolved_report_sections, resolve_section_display
        report, sections = self.report()
        present = {"general_attendance", "sunday_school_attendance", "tithes"}
        def source(_report, key):
            return {"record_count": int(key in present), "breakdown": [{"status": "submitted"}] if key in present else []}
        with patch("apps.reports.services.lifecycle.get_section_source", side_effect=source):
            badges, completion = resolve_section_display(resolved_report_sections(report))
        self.assertEqual(completion, 50)
        self.assertEqual([label for label, state in badges if state == "present"], ["AT", "SAT", "TI"])
        self.assertTrue(all(section.status == "not_started" for section in sections))

    def test_sunday_school_drafts_skips_and_no_activity_use_lifecycle_rules(self):
        from apps.reports.services.pdf_section_states import resolved_report_sections, resolve_section_display
        report, sections = self.report()
        sections[2].status = "skipped"
        sections[2].skip_reason = "records_unavailable"
        sections[3].status = "no_activity"
        def source(_report, key):
            return {"record_count": 1, "breakdown": [{"status": "draft"}]}
        with patch("apps.reports.services.lifecycle.get_section_source", side_effect=source):
            values = resolved_report_sections(report)
        badges, completion = resolve_section_display(values)
        self.assertEqual(dict(badges), {"AT": "present", "SAT": "progress", "TI": "skipped", "IN": "present", "EX": "present", "RM": "unavailable"})
        self.assertEqual(completion, 66.67)
        self.assertEqual(values["tithes"]["skip_reason"], "records_unavailable")

    def test_nonrequired_sections_do_not_inflate_denominator(self):
        from apps.reports.services.pdf_section_states import resolved_report_sections, resolve_section_display, missing_report_sections
        report, _sections = self.report(month=8)
        with patch("apps.reports.services.lifecycle.get_section_source", return_value={"record_count": 1, "breakdown": []}):
            badges, completion = resolve_section_display(resolved_report_sections(report))
        self.assertEqual(dict(badges)["SAT"], "unavailable")
        self.assertEqual(dict(badges)["RM"], "unavailable")
        self.assertEqual(completion, 100)
        self.assertEqual(missing_report_sections(date(2026, 8, 1))["sunday_school_attendance"]["status"], "not_required")


class PdfSourceIntegrationTests(TestCase):
    def test_pdf_scope_reads_actual_tithes_despite_not_started_status(self):
        from decimal import Decimal
        from apps.bookkeeper.models import Tithe
        from apps.churches.models import Church
        from apps.reports.models import AssemblyReport, ReportSectionStatus
        assembly = Church.objects.create(name="Source regression", country="Botswana", currency="BWP")
        report = AssemblyReport.objects.create(assembly=assembly, period_start=date(2026, 9, 1), period_end=date(2026, 9, 30))
        for key in ReportSectionStatus.Section.values:
            ReportSectionStatus.objects.get_or_create(report=report, section=key)
        Tithe.objects.create(assembly=assembly, report=report, member=None, amount=Decimal("100"), timestamp=date(2026, 9, 5))
        august = AssemblyReport.objects.create(assembly=assembly, period_start=date(2026, 8, 1), period_end=date(2026, 8, 31))
        Tithe.objects.create(assembly=assembly, report=august, member=None, amount=Decimal("999"), timestamp=date(2026, 8, 5))
        with patch.object(pdf, "get_region_reports", return_value=[(assembly, [report])]):
            rows, _zone = pdf._scope_rows(
                region=SimpleNamespace(pk=1), user=SimpleNamespace(is_admin=True), year=2026,
                zone_id=None, country=None, from_month=9, to_month=9,
            )
        month = rows[0]["monthly_compliance"][8]
        self.assertEqual(month["completion"], 16.67)
        self.assertEqual(dict(pdf._badge_entries(month["sections"]))["TI"], "present")
        self.assertEqual(month["report_status"], "DRAFT")
        self.assertEqual(report.sections.get(section="tithes").status, "not_started")
