from django.urls import path, include
from rest_framework.routers import SimpleRouter
from apps.reports.views import ReportViewSet, ZoneReportView
from apps.reports.views.audit import AuditLogViewSet
from apps.reports.views.compliance import (
    AssemblyComplianceViewSet,
    ZoneComplianceViewSet,
    ComplianceDashboardView
)
from apps.reports.views.alert_viewset import AlertViewSet
from apps.reports.views.section_viewset import ReportSectionViewSet
from apps.reports.views.region_viewset import RegionMetricsViewSet, RegionViewSet
from apps.reports.views.zone_viewset import ZoneMetricsViewSet

from apps.reports.views.summaries import RegionalSummaryView, AssemblySummaryView, SummaryContributorsView

app_name = "reports"

router = SimpleRouter()

router.register("audit-logs", AuditLogViewSet, basename="audit-logs")
router.register("", ReportViewSet, basename="assembly_report")
router.register("compliance/assemblies", AssemblyComplianceViewSet, basename="assembly-compliance")
router.register("compliance/zones", ZoneComplianceViewSet, basename="zone-compliance")
router.register(r"sections", ReportSectionViewSet, basename="sections")
router.register(r"alerts", AlertViewSet, basename="alerts")

router.register(r"metrics/zones", ZoneMetricsViewSet, basename="zone-metrics")

router.register(r"metrics/regions", RegionViewSet, basename="region-metrics")

urlpatterns = [
    path("summaries/regional/", RegionalSummaryView.as_view(), name="summary-regional"),
    path("summaries/assembly/", AssemblySummaryView.as_view(), name="summary-assembly"),
    path("summaries/contributors/", SummaryContributorsView.as_view(), name="summary-contributors"),
    path("", include(router.urls)),
    path(
        "region/<int:pk>/overview/",
        RegionViewSet.as_view({"get": "overview"}),
        name="regional-overview",
    ),
    path(
        "region/<int:pk>/finance/",
        RegionViewSet.as_view({"get": "finance_aggregate"}),
        name="regional-finance",
    ),
    path(
        "region/<int:pk>/compliance/",
        RegionViewSet.as_view({"get": "compliance_aggregate"}),
        name="regional-compliance",
    ),
    path(
        "region/<int:pk>/compliance/monthly-report.pdf",
        RegionViewSet.as_view({"get": "monthly_compliance_report_pdf"}),
        name="regional-compliance-monthly-report-pdf",
    ),
    path(
        "region/<int:pk>/risk/",
        RegionViewSet.as_view({"get": "risk_aggregate"}),
        name="regional-risk",
    ),
    path(
        "region/<int:pk>/growth/",
        RegionViewSet.as_view({"get": "growth_aggregate"}),
        name="regional-growth",
    ),
    path(
        "region/<int:pk>/ministry/",
        RegionViewSet.as_view({"get": "ministry_aggregate"}),
        name="regional-ministry",
    ),
    path(
        "region/<int:pk>/leadership/",
        RegionViewSet.as_view({"get": "leadership_aggregate"}),
        name="regional-leadership",
    ),
    path(
        "region/metrics/<int:pk>/overview/",
        RegionViewSet.as_view({"get": "overview"}),
        name="region-metrics-overview",
    ),
    path(
        "region/metrics/<int:pk>/finance/aggregate/",
        RegionViewSet.as_view({"get": "finance_aggregate"}),
        name="region-finance-aggregate",
    ),
    path(
        "region/metrics/<int:pk>/compliance/aggregate/",
        RegionViewSet.as_view({"get": "compliance_aggregate"}),
        name="region-compliance-aggregate",
    ),
    path(
        "region/metrics/<int:pk>/risk/aggregate/",
        RegionViewSet.as_view({"get": "risk_aggregate"}),
        name="region-risk-aggregate",
    ),
    path(
        "region/metrics/<int:pk>/growth/aggregate/",
        RegionViewSet.as_view({"get": "growth_aggregate"}),
        name="region-growth-aggregate",
    ),
    path(
        "region/metrics/<int:pk>/ministry/aggregate/",
        RegionViewSet.as_view({"get": "ministry_aggregate"}),
        name="region-ministry-aggregate",
    ),
    path(
        "region/metrics/<int:pk>/leadership/aggregate/",
        RegionViewSet.as_view({"get": "leadership_aggregate"}),
        name="region-leadership-aggregate",
    ),
    path(
        "region/metrics/<int:pk>/compliance/scorecard/",
        RegionViewSet.as_view({"get": "compliance_scorecard"}),
        name="region-compliance-scorecard",
    ),
    path(
        "region/metrics/<int:pk>/compliance/audit-log/",
        RegionViewSet.as_view({"get": "compliance_audit_log"}),
        name="region-compliance-audit-log",
    ),
    path(
        "region/metrics/<int:pk>/<str:domain>/",
        RegionViewSet.as_view({"get": "module"}),
        name="region-metrics-module",
    ),
    path("zone-reports/<int:zone_id>/", ZoneReportView.as_view(), name="zone-reports"),
    path("compliance/dashboard/", ComplianceDashboardView.as_view(), name="compliance-dashboard"),
]
