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


class RegionalWorkflowStatusTests(SimpleTestCase):
    def report(self, status="draft", submitted_at=None, section_status="not_started"):
        from apps.reports.models import AssemblyReport, ReportSectionStatus
        report = AssemblyReport(
            pk=1, assembly_id=1, period_start=date(2026, 9, 1), period_end=date(2026, 9, 30),
            status=status, submitted_at=submitted_at,
        )
        report._prefetched_objects_cache = {"sections": [
            ReportSectionStatus(report=report, section=key, status=section_status)
            for key in ReportSectionStatus.Section.values
        ]}
        return report

    def monthly_row(self, report):
        from apps.reports.services.regional_dashboard.compliance import build_assembly_compliance_row
        assembly = SimpleNamespace(id=1, name="Example", zone=None)
        return build_assembly_compliance_row(assembly, [report] if report else [], country="Namibia", year=2026)["monthly_compliance"][8]

    def test_incomplete_draft_is_not_submitted_and_shows_explicit_due_date(self):
        row = self.monthly_row(self.report(section_status="in_progress"))
        self.assertEqual(row["report_status"], "DRAFT")
        self.assertFalse(row["is_submitted"])
        self.assertEqual(pdf._monthly_status_label(row), "Draft")
        self.assertEqual(pdf._submitted_on_text(row), "Due 5 October 2026")

    def test_complete_sections_do_not_submit_a_draft(self):
        row = self.monthly_row(self.report(section_status="completed"))
        self.assertEqual(row["completion"], 100)
        self.assertEqual(row["report_status"], "DRAFT")
        self.assertFalse(row["is_submitted"])
        self.assertIsNone(row["submitted_at"])
        self.assertEqual(pdf._monthly_status_label(row), "Draft")
        self.assertEqual(pdf._submitted_on_text(row), "Due 5 October 2026")

    def test_walvis_bay_submission_survives_stale_stored_section_flags(self):
        timestamp = datetime(2026, 10, 4, 22, 9, 37, tzinfo=timezone.utc)
        report = self.report(status="submitted", submitted_at=timestamp)
        from apps.reports.models import ReportSectionStatus
        assembly = SimpleNamespace(id=1, name="Walvis Bay", zone=None, country="Namibia", zone_id=None)
        effective = {key: {"status": "completed"} for key in ReportSectionStatus.Section.values}
        with patch.object(pdf, "get_region_reports", return_value=[(assembly, [report])]), patch.object(pdf, "resolved_report_sections", return_value=effective):
            rows, _ = pdf._scope_rows(region=SimpleNamespace(pk=1), user=SimpleNamespace(is_admin=True), year=2026, zone_id=None, country=None, from_month=9, to_month=9)
        self.assertEqual(rows[0]["monthly_compliance"][8]["completion"], 100)
        self.assertEqual(rows[0]["monthly_compliance"][8]["report_status"], "SUBMITTED")
        row = self.monthly_row(report)
        self.assertEqual(row["report_status"], "SUBMITTED")
        self.assertTrue(row["is_submitted"])
        self.assertEqual(pdf._monthly_status_label(row), "Submitted")
        self.assertEqual(pdf._submitted_on_text(row), "5 October 2026")

    def test_submission_timestamp_is_not_hidden_by_stale_workflow_field(self):
        row = self.monthly_row(self.report(submitted_at=datetime(2026, 10, 5, tzinfo=timezone.utc)))
        self.assertEqual(row["report_status"], "SUBMITTED")
        self.assertEqual(pdf._monthly_status_label(row), "Submitted")

    def test_submitted_approved_and_under_review_states_do_not_require_complete_flags(self):
        for status in ["submitted", "approved", "under_review"]:
            with self.subTest(status=status):
                row = self.monthly_row(self.report(status=status))
                self.assertEqual(row["report_status"], "SUBMITTED")
                self.assertEqual(pdf._monthly_status_label(row), "Submitted")

    def test_missing_report_remains_not_submitted(self):
        row = self.monthly_row(None)
        self.assertEqual(row["report_status"], "NOT_SUBMITTED")
        self.assertEqual(pdf._monthly_status_label(row), "Not submitted")
        self.assertEqual(pdf._submitted_on_text(row), "-")

    def test_locked_report_keeps_submitted_workflow_status(self):
        from apps.reports.models import ReportVersion
        from apps.reports.services.lifecycle import get_report_state
        report = self.report(status="submitted", submitted_at=datetime(2026, 9, 30, tzinfo=timezone.utc))
        report.current_version = ReportVersion(pk=1, report=report, submitted_at=report.submitted_at, editable_until=datetime(2026, 10, 1, tzinfo=timezone.utc))
        with patch("apps.reports.services.lifecycle.get_section_source", return_value={"record_count": 1, "total": 0, "breakdown": []}):
            state = get_report_state(report, now=datetime(2026, 10, 8, tzinfo=timezone.utc))
        self.assertTrue(state.is_locked)
        self.assertEqual(state.status, "locked")
        self.assertEqual(self.monthly_row(report)["report_status"], "SUBMITTED")


class SubmitterPdfTests(SimpleTestCase):
    def test_submission_date_name_and_lateness_order_and_escaping(self):
        item = {"submitted_at": datetime(2026, 10, 5, tzinfo=timezone.utc), "submitted_by_name": "John <Doe> & Co", "is_late": True, "days_late": 1}
        text = pdf._submitted_on_text(item)
        self.assertTrue(text.startswith("5 October 2026<br/>"))
        self.assertIn('<font size="7.5" color="#64748B">John &lt;Doe&gt; &amp; Co</font>', text)
        self.assertTrue(text.endswith("<br/>Late by 1 day"))
        item["days_late"] = 2
        self.assertTrue(pdf._submitted_on_text(item).endswith("Late by 2 days"))
        item["is_late"] = False
        self.assertNotIn("Late by", pdf._submitted_on_text(item))

    def test_legacy_missing_submitter_and_unsubmitted_due_date(self):
        self.assertEqual(pdf._submitted_on_text({"submitted_at": datetime(2026, 10, 4, tzinfo=timezone.utc)}), "4 October 2026")
        self.assertEqual(pdf._submitted_on_text({"submitted_at": None, "submitted_by_name": "Stale name", "due_date": date(2026, 10, 5)}), "Due 5 October 2026")

    def test_authoritative_submitter_full_name_and_username_fallback(self):
        from apps.reports.models import AssemblyReport
        from apps.users.models import User
        from apps.reports.services.regional_dashboard.compliance import build_assembly_compliance_row
        for status in ["submitted", "approved", "under_review"]:
            for first_name, last_name, expected in [("John", "Doe", "John Doe"), ("", "", "john.doe")]:
                with self.subTest(status=status, expected=expected):
                    report = AssemblyReport(pk=1, status=status, period_start=date(2026,9,1), period_end=date(2026,9,30), submitted_at=datetime(2026,10,4,tzinfo=timezone.utc))
                    report.submitted_by = User(pk=9, first_name=first_name, last_name=last_name, username="john.doe")
                    report._prefetched_objects_cache = {"sections": []}
                    row = build_assembly_compliance_row(SimpleNamespace(id=1,name="Assembly",zone=None),[report],country="Namibia",year=2026)
                    self.assertEqual(row["monthly_compliance"][8]["submitted_by_name"], expected)


class MasterPdfRenderingTests(SimpleTestCase):
    def rows(self):
        return [{
            "id": i, "name": f"Assembly {i:02d}", "zone_id": 1 if i < 40 else 2,
            "zone": "Zone 2" if i < 40 else "Zone 10", "country": "Namibia",
            "monthly_compliance": [{"period": "2026-09", "report_status": "SUBMITTED", "completion": 100,
                "submitted_at": datetime(2026,10,6,tzinfo=timezone.utc), "submitted_by_name": "John Doe",
                "is_late": True, "days_late": 1, "sections": {}}],
        } for i in range(43)]

    def render(self, rows, layout="master"):
        zones = [SimpleNamespace(pk=1,name="Zone 2"), SimpleNamespace(pk=2,name="Zone 10"), SimpleNamespace(pk=3,name="Empty zone")]
        with patch.object(pdf,"_scope_rows",return_value=(rows,None)) as scope, patch.object(pdf,"_master_zones",return_value=zones), patch.object(pdf,"_record_audit_event"):
            result = pdf.build_regional_monthly_compliance_pdf(region=SimpleNamespace(pk=1,name="Sample region"), user=SimpleNamespace(is_authenticated=True,is_admin=True,full_name="Exporter"), query_params={"year":"2026","from_month":"9","to_month":"9","layout":layout})
        scope.assert_called_once()
        return result

    def test_single_document_zone_grouping_pagination_and_existing_export(self):
        rows = self.rows()
        original = deepcopy(rows)
        result = self.render(rows)
        self.assertTrue(result.filename.startswith("master-"))
        reader = PdfReader(result.buffer)
        pages = [page.extract_text() for page in reader.pages]
        starts = [page.splitlines()[0] for page in pages[1:] if page.splitlines()]
        self.assertEqual(starts.count("Zone 2"),1)
        self.assertEqual(starts.count("Zone 10"),1)
        self.assertEqual(starts.count("Empty zone"),1)
        zone_two_end = next(i for i,text in enumerate(pages) if text.startswith("Zone 10"))
        for index, text in enumerate(pages,1):
            self.assertIn(f"Page {index} of {len(pages)}",text)
            if "Assembly 00" in text or "Assembly 39" in text or "Assembly 42" in text:
                for header in ["Submitted on","Report status","Sections"]:
                    self.assertIn(header,text)
                self.assertIn("John Doe",text)
                self.assertIn("Late by 1 day",text)
        self.assertNotIn("Assembly 40", "\n".join(pages[:zone_two_end]))
        self.assertNotIn("Assembly 39", "\n".join(pages[zone_two_end:]))
        self.assertIn("No assemblies match",pages[-1])
        self.assertEqual(rows,original)
        individual = PdfReader(self.render(rows[:40],layout="monthly").buffer)
        self.assertIn("Assembly 39", "\n".join(page.extract_text() for page in individual.pages))

    def test_empty_authorized_zones_render_without_assemblies(self):
        text = "\n".join(page.extract_text() for page in PdfReader(self.render([]).buffer).pages)
        self.assertEqual(text.count("No assemblies match"),3)
        self.assertIn("Total zones",text)


class MasterPdfAuthorizationTests(TestCase):
    def setUp(self):
        from apps.churches.models import Region, Zone, Church
        self.region = Region.objects.create(name="Region A",code="TEST-A")
        self.zones = [Zone.objects.create(name=name,region=self.region) for name in ["Zone 10","Zone 2","Empty zone"]]
        self.assemblies = [Church.objects.create(name=name,zone=zone,country=country) for name,zone,country in [
            ("Zebra",self.zones[0],"Namibia"),("Alpha",self.zones[0],"Namibia"),("Bravo",self.zones[1],"Botswana"),
        ]]
        other_region = Region.objects.create(name="Other region",code="TEST-B")
        other_zone = Zone.objects.create(name="Other zone",region=other_region)
        Church.objects.create(name="Secret assembly",zone=other_zone,country="Namibia")
        self.user = SimpleNamespace(is_authenticated=True,is_admin=True,full_name="Exporter")

    def test_authorized_dataset_once_zone_order_country_and_individual_consistency(self):
        original = pdf.get_region_reports
        with patch.object(pdf,"get_region_reports",wraps=original) as get_reports, patch.object(pdf,"_record_audit_event"), patch.object(pdf,"_add_month_section",wraps=pdf._add_month_section) as sections:
            result = pdf.build_regional_monthly_compliance_pdf(region=self.region,user=self.user,query_params={"year":"2026","from_month":"9","to_month":"9","layout":"master","zone_id":str(self.zones[1].pk),"country":"Namibia"})
        get_reports.assert_called_once()
        self.assertEqual([call.kwargs["title"] for call in sections.call_args_list],["Zone 10"])
        master_records = sections.call_args.kwargs["records"]
        self.assertEqual([row["name"] for row,_ in master_records],["Alpha","Zebra"])
        individual_rows,_ = pdf._scope_rows(region=self.region,user=self.user,year=2026,zone_id=self.zones[0].pk,country="Namibia",from_month=9,to_month=9)
        individual_records = pdf._records_by_month(individual_rows,from_month=9,to_month=9)[9]
        self.assertEqual(master_records,individual_records)
        text = "\n".join(page.extract_text() for page in PdfReader(result.buffer).pages)
        self.assertNotIn("Secret assembly",text)
        self.assertNotIn("Bravo",text)
        self.assertEqual([zone.name for zone in pdf._master_zones(self.region,self.user)],["Empty zone","Zone 2","Zone 10"])

    def test_zone_authorization_and_active_scope_are_never_expanded(self):
        with patch.object(pdf,"_visible_zone_ids",return_value={self.zones[0].pk}), patch.object(pdf,"_record_audit_event"):
            result = pdf.build_regional_monthly_compliance_pdf(region=self.region,user=self.user,query_params={"year":"2026","from_month":"9","to_month":"9","layout":"master"})
        text = "\n".join(page.extract_text() for page in PdfReader(result.buffer).pages)
        self.assertIn("Alpha",text)
        self.assertNotIn("Bravo",text)
        self.region._summary_zone_id = self.zones[1].pk
        self.assertEqual([zone.pk for zone in pdf._master_zones(self.region,self.user)],[self.zones[1].pk])

    def test_submitter_is_joined_without_one_query_per_report(self):
        from apps.reports.models import AssemblyReport
        from apps.users.models import User
        from apps.reports.services.metrics.region_dashboard_service import get_region_reports
        submitter = User.objects.create_user(first_name="John", last_name="Doe", username="submitter", email="submitter@example.test", password="test")
        for assembly in self.assemblies:
            AssemblyReport.objects.create(assembly=assembly,period_start=date(2026,9,1),period_end=date(2026,9,30),submitted_by=submitter)
        with self.assertNumQueries(3):
            for assembly,reports in get_region_reports(self.region,2026):
                for report in reports:
                    self.assertEqual(report.submitted_by.username,"submitter")

    def test_regional_executive_master_expands_active_zone_only_to_permitted_zones(self):
        from apps.churches.models import RegionLeadership
        from apps.users.models import User
        from apps.reports.views.region_viewset import RegionViewSet
        from rest_framework.test import APIRequestFactory, force_authenticate
        user = User.objects.create_user(first_name="Regional",last_name="Overseer",username="regional",email="regional@example.test",password="test")
        RegionLeadership.objects.create(user=user,region=self.region,role=RegionLeadership.Role.OVERSEER)
        user.regional_zone_id = self.zones[0].pk
        view = RegionViewSet.as_view({"get":"monthly_compliance_report_pdf"})
        for layout in ["master","monthly"]:
            request = APIRequestFactory().get("/compliance/monthly-report.pdf/",{"year":2026,"from_month":9,"to_month":9,"layout":layout})
            force_authenticate(request,user=user)
            with patch.object(pdf,"_record_audit_event"):
                response = view(request,pk=self.region.pk)
            self.assertEqual(response.status_code,200)
            reader = PdfReader(BytesIO(b"".join(response.streaming_content)))
            text = "\n".join(page.extract_text() for page in reader.pages)
            self.assertIn("Alpha",text)
            if layout == "master":
                self.assertIn("Bravo",text)
            else:
                self.assertNotIn("Bravo",text)
        with patch.object(pdf,"_visible_zone_ids",wraps=pdf._visible_zone_ids):
            self.zones[1].is_active = False
            self.zones[1].save(update_fields=["is_active"])
            self.assertNotIn(self.zones[1].pk,pdf._visible_zone_ids(user,self.region))
        request = APIRequestFactory().get("/compliance/monthly-report.pdf/",{"layout":"master"})
        force_authenticate(request,user=user)
        with patch("apps.reports.views.region_viewset.build_regional_monthly_compliance_pdf") as builder:
            response = view(request,pk=self.region.pk + 1)
        self.assertEqual(response.status_code,403)
        builder.assert_not_called()
