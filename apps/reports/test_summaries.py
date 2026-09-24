from datetime import date
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate
from apps.churches.models import Church, Region, Zone, RegionLeadership, Forecast
from apps.users.models import User, Role
from apps.users.choices import UserRoles
from apps.reports.models import AssemblyReport
from apps.bookkeeper.models import Tithe, RemittanceObligation, RemittancePayment
from apps.people.models import Member
from apps.reports.services.summaries.composition import build_summary, parse_period
from apps.reports.views.summaries import RegionalSummaryView, AssemblySummaryView, SummaryContributorsView


class SummaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region = Region.objects.create(name="South", code="ST")
        cls.other_region = Region.objects.create(name="North", code="NT")
        cls.zone = Zone.objects.create(name="Central", region=cls.region)
        cls.other_zone = Zone.objects.create(name="Other", region=cls.other_region)
        cls.assembly = Church.objects.create(name="First", zone=cls.zone, currency="BWP", established_date=date(2026, 3, 1))
        cls.other = Church.objects.create(name="Other church", zone=cls.other_zone, currency="BWP")
        cls.overseer = User.objects.create(username="regional", email="regional@example.test")
        RegionLeadership.objects.create(user=cls.overseer, region=cls.region, role=RegionLeadership.Role.OVERSEER)
        cls.pastor = User.objects.create(username="pastor", email="pastor@example.test", church=cls.assembly)
        cls.pastor.roles.add(Role.objects.get_or_create(name=UserRoles.PASTOR)[0])
        cls.plain = User.objects.create(username="ordinary", email="ordinary@example.test", church=cls.assembly)
        cls.superuser = User.objects.create(username="super", email="super@example.test", is_superuser=True)
        cls.reports = {}
        for month, members, tithes in [(1, 70, 100), (8, 90, 200), (9, 100, 300), (10, 999, 9000)]:
            from apps.reports.services.periods import report_period
            start, end = report_period(date(2026, month, 1))
            cls.reports[month] = AssemblyReport.objects.create(assembly=cls.assembly, period_start=start, period_end=end,
                members_total=members, tithe_total=tithes, income_total=tithes+50, expense_total=20, attendance_total=100)
        AssemblyReport.objects.create(assembly=cls.other, period_start=date(2026, 9, 1), period_end=date(2026, 9, 30), tithe_total=99999)

    def request(self, view, user, **params):
        request = APIRequestFactory().get("/summary/", params)
        if user:
            force_authenticate(request, user=user)
        return view.as_view()(request)

    def build(self, regional=True):
        return build_summary(Church.objects.filter(pk=self.assembly.pk), *parse_period("2026-09"), regional=regional)

    def test_roles_and_region_isolation(self):
        for user in (None, self.pastor, self.plain):
            self.assertIn(self.request(RegionalSummaryView, user).status_code, (401, 403))
        response = self.request(RegionalSummaryView, self.overseer, period="2026-09")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([a["id"] for a in response.data["assemblies"]], [self.assembly.id])
        self.assertEqual(self.request(RegionalSummaryView, self.overseer, region=self.other_region.id).status_code, 403)
        self.assertEqual(len(self.request(RegionalSummaryView, self.superuser).data["regions"]), 2)
        RegionLeadership.objects.filter(user=self.overseer).update(role=RegionLeadership.Role.OVERSEER_PA)
        self.assertEqual(self.request(RegionalSummaryView, self.overseer).status_code, 403)
        RegionLeadership.objects.filter(user=self.overseer).update(role=RegionLeadership.Role.REGIONAL_ADMIN)
        self.assertEqual(self.request(RegionalSummaryView, self.overseer).status_code, 200)

    def test_pastor_and_contributor_isolation_and_regional_drilldown(self):
        for view in (AssemblySummaryView, SummaryContributorsView):
            self.assertEqual(self.request(view, self.pastor, assembly=self.other.pk).status_code, 404)
            self.assertEqual(self.request(view, self.plain, assembly=self.assembly.pk).status_code, 404)
            self.assertEqual(self.request(view, self.pastor, assembly=self.assembly.pk).status_code, 200)
            self.assertEqual(self.request(view, self.overseer, assembly=self.assembly.pk).status_code, 200)
            self.assertEqual(self.request(view, self.overseer, assembly=self.other.pk).status_code, 404)
        self.assembly.assigned_pastors.add(self.plain)
        self.assertEqual(self.request(AssemblySummaryView, self.plain, assembly=self.assembly.pk).status_code, 200)

    def test_period_ytd_monthly_and_membership(self):
        result = self.build()
        self.assertEqual(result["summary"]["finance"]["tithes"], 600)
        self.assertEqual(result["summary"]["finance"]["other_revenue"], 150)
        self.assertEqual(result["summary"]["membership"]["previous"], 90)
        self.assertEqual(result["summary"]["membership"]["current"], 100)
        self.assertEqual(result["summary"]["membership"]["net"], 10)
        self.assertAlmostEqual(result["summary"]["membership"]["percent"], 11.11)
        self.assertEqual(self.build(False)["summary"]["finance"]["tithes"], 300)
        self.assertEqual(len(result["summary"]["outreach"]["plants"]), 1)
        self.assertEqual(result["zones"][0]["id"], self.zone.id)
        for period in ("2026-13", "2026-9", "invalid"):
            self.assertEqual(self.request(RegionalSummaryView, self.overseer, period=period).status_code, 400)

    def test_january_previous_year_and_missing_zero(self):
        AssemblyReport.objects.create(assembly=self.assembly, period_start=date(2025,12,1), period_end=date(2025,12,31), members_total=0)
        january = build_summary(Church.objects.filter(pk=self.assembly.pk), *parse_period("2026-01"))
        self.assertEqual(january["summary"]["membership"]["previous"], 0)
        self.assertIsNone(january["summary"]["membership"]["percent"])
        missing = build_summary(Church.objects.filter(pk=self.assembly.pk), *parse_period("2026-07"))
        self.assertIsNone(missing["summary"]["finance"]["tithes"])
        self.assertIsNone(missing["summary"]["membership"]["current"])

    def test_targets_and_currency_safety(self):
        result = self.build()
        self.assertTrue(all(t["target"] is None for t in result["summary"]["targets"]))
        Forecast.objects.create(assembly=self.assembly, year=2026, month=9, tithes_collected=400, attendance=200, new_members=20)
        targets = self.build()["summary"]["targets"]
        self.assertEqual(targets[0]["percent"], 75)
        self.assertEqual(targets[1]["percent"], 50)
        self.assertIsNone(targets[2]["target"])
        Church.objects.filter(pk=self.other.pk).update(currency="USD")
        mixed = build_summary(Church.objects.all(), *parse_period("2026-09"), regional=True)
        self.assertTrue(mixed["summary"]["mixed_currencies"])
        self.assertIsNone(mixed["summary"]["finance"]["tithes"])

    def test_contributors_count_order_and_soft_delete(self):
        first = Member.objects.create(assembly=self.assembly, first_name="Anne", last_name="One", date_of_birth=date(1990,1,1))
        second = Member.objects.create(assembly=self.assembly, first_name="Ben", last_name="Two", date_of_birth=date(1990,1,1))
        Tithe.objects.bulk_create([
            Tithe(assembly=self.assembly, report=self.reports[9], timestamp=date(2026,9,3), member=first, amount=50),
            Tithe(assembly=self.assembly, report=self.reports[9], timestamp=date(2026,9,4), member=second, amount=150),
            Tithe(assembly=self.assembly, report=self.reports[9], timestamp=date(2026,9,4), amount=500),
            Tithe(assembly=self.assembly, report=self.reports[10], timestamp=date(2026,10,4), member=first, amount=900),
            Tithe(assembly=self.assembly, report=self.reports[9], timestamp=date(2026,9,4), member=first, amount=9000, is_trash=True),
        ])
        giving = self.build()["assemblies"][0]["giving"]
        self.assertEqual(giving["count"], 2)
        self.assertEqual(giving["top"][0]["name"], "Ben Two")
        self.assertEqual(giving["top"][0]["amount"], 150)

    def test_verified_remittance_cutoff_and_no_join_duplication(self):
        obligation = RemittanceObligation.objects.create(assembly=self.assembly, report=self.reports[9], period_start=date(2026,9,1), tithe_total_snapshot=300, amount_due=30)
        RemittancePayment.objects.bulk_create([
            RemittancePayment(obligation=obligation, report=self.reports[9], amount_paid=5, payment_date=date(2026,9,10), status=RemittancePayment.Status.VERIFIED),
            RemittancePayment(obligation=obligation, report=self.reports[9], amount_paid=10, payment_date=date(2026,9,11), status=RemittancePayment.Status.VERIFIED),
            RemittancePayment(obligation=obligation, report=self.reports[9], amount_paid=8, payment_date=date(2026,9,12), status=RemittancePayment.Status.PENDING),
            RemittancePayment(obligation=obligation, report=self.reports[10], amount_paid=15, payment_date=date(2026,10,1), status=RemittancePayment.Status.VERIFIED),
        ])
        finance = self.build()["summary"]["finance"]
        self.assertEqual((finance["due"], finance["paid"], finance["outstanding"]), (30, 15, 15))

    def test_query_count_does_not_grow_per_assembly(self):
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        with CaptureQueriesContext(connection) as one:
            self.build()
        for n in range(5):
            Church.objects.create(name=f"Extra {n}", zone=self.zone, currency="BWP")
        with CaptureQueriesContext(connection) as many:
            build_summary(Church.objects.all(), *parse_period("2026-09"), regional=True)
        self.assertEqual(len(one), len(many))
        self.assertLessEqual(len(many), 22)

    def test_single_assembly_api_uses_identical_canonical_monthly_values(self):
        monthly = self.request(AssemblySummaryView, self.pastor, period="2026-09").data
        regional = self.request(RegionalSummaryView, self.overseer, period="2026-09").data
        self.assertEqual(regional["monthly_summary"], monthly["summary"])
        row = regional["assemblies"][0]
        for key in ("attendance", "finance", "report_count", "expected_reports"):
            self.assertEqual(row[key], monthly["assemblies"][0]["ytd"][key])
        for key in ("membership", "giving", "targets", "assets", "monthly_attendance"):
            self.assertEqual(row[key], monthly["assemblies"][0][key])

    def test_partial_coverage_preserves_observations_and_missing_rows(self):
        missing = Church.objects.create(name="Missing reports", zone=self.zone, currency="BWP")
        data = self.request(RegionalSummaryView, self.overseer, period="2026-09").data
        total = data["summary"]
        self.assertEqual((total["report_count"], total["expected_reports"]), (3, 18))
        self.assertEqual(total["finance"]["tithes"], 600)
        self.assertEqual(total["attendance"]["total"], 300)
        self.assertEqual(total["membership"]["current"], 100)
        self.assertEqual(total["membership"]["net"], 10)
        self.assertEqual(total["coverage"]["attendance.total"], {"available": 1, "total": 2})
        empty = next(r for r in data["assemblies"] if r["id"] == missing.pk)
        self.assertIsNone(empty["finance"]["tithes"])
        self.assertIsNone(empty["membership"]["current"])
        self.assertIsNone(total["attendance"]["school"])
        self.assertIsNone(total["outreach"]["ordained"])
        self.assertEqual(data["zones"][0]["summary"]["finance"]["tithes"], 600)

    def test_multiple_assemblies_currencies_and_comparable_membership(self):
        from apps.people.models import Homecell
        second = Church.objects.create(name="Second", zone=self.zone, currency="BWP")
        report = AssemblyReport.objects.create(assembly=second, period_start=date(2026,9,1), period_end=date(2026,9,30),
            tithe_total=50, income_total=75, expense_total=10, attendance_total=25, members_total=20)
        Homecell.objects.create(church=second, group_name="Active")
        Homecell.objects.create(church=second, group_name="Archived", is_archived=True)
        data = self.request(RegionalSummaryView, self.overseer, period="2026-09").data
        self.assertEqual(data["summary"]["finance"]["tithes"], 650)
        self.assertEqual(data["monthly_summary"]["finance"]["tithes"], 350)
        self.assertEqual(data["summary"]["attendance"]["total"], 325)
        self.assertEqual(data["monthly_summary"]["attendance"]["total"], 125)
        self.assertEqual(data["summary"]["membership"]["current"], 120)
        self.assertEqual(data["summary"]["membership"]["previous"], 90)
        self.assertEqual(data["summary"]["membership"]["net"], 10)  # only matched assembly
        self.assertEqual(data["summary"]["membership"]["comparable_assemblies"], 1)
        self.assertEqual(data["summary"]["outreach"]["homecells"], 1)
        Church.objects.filter(pk=second.pk).update(currency="USD")
        mixed = self.request(RegionalSummaryView, self.overseer, period="2026-09").data
        groups = {g["currency"]: g["finance"] for g in mixed["summary"]["finance_by_currency"]}
        self.assertEqual(groups["BWP"]["tithes"], 600)
        self.assertEqual(groups["USD"]["tithes"], 50)
        self.assertIsNone(mixed["summary"]["finance"]["tithes"])
        for key in ("attendance", "membership", "outreach", "giving"):
            self.assertEqual(mixed["summary"][key], data["summary"][key])
        self.assertEqual(mixed["zones"][0]["summary"]["finance_by_currency"], mixed["summary"]["finance_by_currency"])

    def test_regional_contributors_sum_identified_assembly_month_counts(self):
        second = Church.objects.create(name="Second", zone=self.zone, currency="USD")
        report = AssemblyReport.objects.create(assembly=second, period_start=date(2026,9,1), period_end=date(2026,9,30))
        member = Member.objects.create(assembly=self.assembly, first_name="Giver", last_name="One", date_of_birth=date(1990,1,1))
        Tithe.objects.bulk_create([
            Tithe(assembly=self.assembly, report=self.reports[9], timestamp=date(2026,9,3), member=member, amount=50),
            Tithe(assembly=second, report=report, timestamp=date(2026,9,4), member=member, amount=20),
            Tithe(assembly=second, report=report, timestamp=date(2026,9,4), amount=500),
            Tithe(assembly=second, report=report, timestamp=date(2026,9,4), member=member, amount=9000, is_trash=True),
            Tithe(assembly=self.assembly, report=self.reports[8], timestamp=date(2026,8,4), member=member, amount=10),
        ])
        result = self.request(RegionalSummaryView, self.overseer, period="2026-09").data
        self.assertEqual(result["summary"]["giving"], {"count": 2, "previous_count": 1})
        self.assertEqual(result["monthly_summary"]["giving"], result["summary"]["giving"])
        self.assertEqual(result["zones"][0]["summary"]["giving"], result["summary"]["giving"])

    def test_rollup_all_missing_zero_and_unknown_currency_are_distinct(self):
        from copy import deepcopy
        from apps.reports.services.summaries.composition import combine
        row = self.build(False)["assemblies"][0]
        a, b = deepcopy(row), deepcopy(row)
        a["id"], b["id"] = 1001, 1002
        a["currency"] = b["currency"] = None
        a["finance"]["tithes"], b["finance"]["tithes"] = 0, None
        a["outreach"]["ordained"] = 3
        result = combine([a, b])
        self.assertIsNone(result["finance"]["tithes"])
        self.assertEqual(len(result["finance_by_currency"]), 2)
        self.assertEqual(result["finance_by_currency"][0]["finance"]["tithes"], 0)
        self.assertIsNone(result["finance_by_currency"][1]["finance"]["tithes"])
        self.assertEqual(result["outreach"]["ordained"], 3)
        a["membership"]["previous"] = None
        b["membership"]["current"] = None
        self.assertIsNone(combine([a, b])["membership"]["net"])
        self.assertIsNone(combine([])["attendance"]["total"])
        self.assertIsNone(combine([])["giving"]["count"])

    def test_regional_default_zone_country_and_scoped_options(self):
        from apps.churches.models.zone import ZoneLeadership
        Church.objects.filter(pk=self.assembly.pk).update(country="Botswana", country_code="BW")
        extra_zone = Zone.objects.create(name="Western", region=self.region)
        namibia = Church.objects.create(name="Namibian assembly", zone=extra_zone, country="Namibia", country_code="NA", currency="NAD")
        south_africa = Church.objects.create(name="SA assembly", zone=self.zone, country="South Africa", country_code="ZA", currency="ZAR")
        default = self.request(RegionalSummaryView, self.overseer, period="2026-09").data
        self.assertEqual((default["filters"]["zone"], default["filters"]["country"]), (self.zone.id, "BW"))
        self.assertEqual([a["id"] for a in default["assemblies"]], [self.assembly.id])
        self.assertEqual({c["id"] for c in default["filters"]["countries"]}, {"BW", "ZA"})
        self.assertEqual({z["id"] for z in default["filters"]["zones"]}, {self.zone.id, extra_zone.id})
        western = self.request(RegionalSummaryView, self.overseer, period="2026-09", zone=extra_zone.id).data
        self.assertEqual(western["filters"]["country"], "NA")
        self.assertEqual([c["id"] for c in western["filters"]["countries"]], ["NA"])
        self.assertEqual([a["id"] for a in western["assemblies"]], [namibia.id])
        ZoneLeadership.objects.create(user=self.overseer, zone=extra_zone, role=ZoneLeadership.Role.OVERSEER, appointed_at=date(2026,1,1))
        assigned = self.request(RegionalSummaryView, self.overseer, period="2026-09").data
        self.assertEqual(assigned["filters"]["zone"], extra_zone.id)
        super_default = self.request(RegionalSummaryView, self.superuser, period="2026-09").data
        self.assertEqual(super_default["filters"]["zone"], self.zone.id)
        super_explicit = self.request(RegionalSummaryView, self.superuser, period="2026-09", zone=extra_zone.id, country="NA").data
        self.assertEqual(super_explicit["filters"]["country"], "NA")
        for params in ({"zone": self.other_zone.id}, {"zone": self.zone.id, "country": "NA"}, {"country": "not-permitted"}):
            self.assertEqual(self.request(RegionalSummaryView, self.overseer, **params).status_code, 403)
        self.assertEqual(self.request(RegionalSummaryView, self.overseer, zone="bad").status_code, 400)
        self.assertEqual(self.request(RegionalSummaryView, self.pastor, zone=self.zone.id).status_code, 403)

    def test_country_scope_and_all_countries_keep_monthly_ytd_currency_safety(self):
        Church.objects.filter(pk=self.assembly.pk).update(country="Botswana", country_code="BW")
        namibia = Church.objects.create(name="Namibia", zone=self.zone, country="Namibia", country_code="NA", currency="NAD")
        AssemblyReport.objects.create(assembly=namibia, period_start=date(2026,9,1), period_end=date(2026,9,30),
            tithe_total=40000, income_total=90000, expense_total=4000, attendance_total=40, members_total=10)
        AssemblyReport.objects.create(assembly=namibia, period_start=date(2026,1,1), period_end=date(2026,1,31),
            tithe_total=16050, income_total=16550, expense_total=23410, attendance_total=20)
        Forecast.objects.create(assembly=namibia, year=2026, month=9, tithes_collected=50000, attendance=50)
        data = self.request(RegionalSummaryView, self.overseer, period="2026-09", zone=self.zone.id, country="NA").data
        monthly, ytd = data["monthly_summary"], data["summary"]
        self.assertEqual((monthly["finance"]["tithes"], ytd["finance"]["tithes"]), (40000, 56050))
        self.assertEqual((monthly["finance"]["other_revenue"], ytd["finance"]["other_revenue"]), (50000, 50500))
        self.assertEqual((monthly["finance"]["expenses"], ytd["finance"]["expenses"]), (4000, 27410))
        self.assertEqual((monthly["attendance"]["total"], ytd["attendance"]["total"]), (40, 60))
        self.assertEqual(monthly["currency"], "NAD")
        self.assertEqual(monthly["targets"][0]["percent"], 80)
        self.assertEqual(monthly["targets"][1]["percent"], 80)
        self.assertIsNone(monthly["targets"][2]["target"])
        self.assertEqual(data["assemblies"][0]["monthly"]["finance"], monthly["finance"])
        self.assertEqual(data["assemblies"][0]["finance"], ytd["finance"])
        combined = self.request(RegionalSummaryView, self.overseer, period="2026-09", zone=self.zone.id, country="all").data
        self.assertEqual(combined["summary"]["attendance"]["total"], 360)
        self.assertEqual(combined["monthly_summary"]["attendance"]["total"], 140)
        self.assertIsNone(combined["summary"]["finance"]["tithes"])
        currencies = {c["currency"]: c["finance"]["tithes"] for c in combined["summary"]["finance_by_currency"]}
        self.assertEqual(currencies, {"BWP": 600, "NAD": 56050})
        # Country metadata never overwrites actual stored currency denominations.
        Church.objects.create(name="USD in Namibia", zone=self.zone, country="Namibia", country_code="NA", currency="USD")
        same_country = self.request(RegionalSummaryView, self.overseer, period="2026-09", country="NA").data
        self.assertIsNone(same_country["summary"]["finance"]["tithes"])
        self.assertEqual({c["currency"] for c in same_country["summary"]["finance_by_currency"]}, {"NAD", "USD"})

    def test_general_attendance_month_and_ytd_use_assembly_canonical_values(self):
        from apps.people.models import Attendance
        from apps.people.choices.services import AttendanceCategories
        Attendance.objects.bulk_create([
            Attendance(assembly=self.assembly, report=self.reports[8], timestamp=date(2026,8,2), total_adults=10, total_visitors=2, service_type=AttendanceCategories.SUNDAY),
            Attendance(assembly=self.assembly, report=self.reports[9], timestamp=date(2026,9,6), total_adults=20, total_visitors=3, service_type=AttendanceCategories.SUNDAY),
            Attendance(assembly=self.assembly, report=self.reports[9], timestamp=date(2026,9,7), total_adults=5, service_type=AttendanceCategories.HOMECELL),
            Attendance(assembly=self.assembly, report=self.reports[10], timestamp=date(2026,10,4), total_adults=999, service_type=AttendanceCategories.SUNDAY),
        ])
        data = self.request(RegionalSummaryView, self.overseer, period="2026-09").data
        assembly = self.request(AssemblySummaryView, self.pastor, period="2026-09").data
        self.assertEqual(data["monthly_summary"]["attendance"], assembly["summary"]["attendance"])
        self.assertEqual(data["monthly_summary"]["attendance"]["general"], 23)
        self.assertEqual(data["summary"]["attendance"]["general"], 35)
        self.assertEqual(data["assemblies"][0]["monthly"]["attendance"]["cells"], 5)
        self.assertEqual(data["summary"]["membership"]["current"], 100)
        self.assertEqual(data["monthly_summary"]["membership"]["net"], 10)
        self.assertEqual(data["monthly_summary"]["outreach"]["plants"], [])
        self.assertEqual(len(data["summary"]["outreach"]["plants"]), 1)

    def test_scope_handles_empty_and_legacy_country_metadata(self):
        Church.objects.filter(pk=self.assembly.pk).update(country="Botswana", country_code="BW")
        legacy = Church.objects.create(name="Legacy country", zone=self.zone, country="Botswana", currency="BWP")
        result = self.request(RegionalSummaryView, self.overseer, country="BW").data
        self.assertEqual([c["id"] for c in result["filters"]["countries"]], ["BW"])
        self.assertEqual({r["id"] for r in result["assemblies"]}, {self.assembly.id, legacy.id})
        Church.objects.filter(zone=self.zone).update(zone=None)
        empty = self.request(RegionalSummaryView, self.overseer).data
        self.assertEqual(empty["filters"]["zones"], [])
        self.assertEqual(empty["assemblies"], [])
