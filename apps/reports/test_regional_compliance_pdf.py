from copy import deepcopy
from datetime import date, datetime, timezone
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
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

    def test_legacy_states_and_tracked_remittance(self):
        entries = dict(pdf._badge_entries({key: {"status": state} for key, state in [
            ("attendance", "SUB"), ("tithes", "MIS"), ("income", "SKP"),
            ("expenditure", "DRAFT"), ("remittance", "SUBMITTED"), ("junior_members", "SUBMITTED"),
        ]}))
        self.assertEqual(entries, {"AT": "present", "SAT": "missing", "TI": "missing", "IN": "skipped", "EX": "progress", "RM": "present"})

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
