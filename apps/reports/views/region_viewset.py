from django.shortcuts import get_object_or_404
from django.http import FileResponse
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.churches.models import Region, Zone
from apps.reports.schemas.regional_schema import (
    get_regional_audit_log_schema,
    get_regional_dashboard_schema,
    get_regional_module_schema,
)
from apps.reports.serializers.region import RegionMetricsSerializer
from apps.reports.services.metrics.audit_log import build_audit_log_payload
from apps.reports.services.metrics.compliance_engine import build_zone_compliance_timeline
from apps.reports.services.metrics.region_dashboard_service import (
    DASHBOARD_DOMAINS,
    build_region_compliance_scorecard,
    build_region_dashboard,
    build_region_dashboard_module,
    get_country_reports,
    get_region_reports,
)
from apps.reports.services.metrics.region_metrics import get_region_metrics
from apps.reports.services.regional_dashboard.finance import build_region_finance_module
from apps.reports.services.regional_dashboard.compliance import build_region_compliance_module
from apps.reports.services.regional_dashboard.growth import build_region_growth_module
from apps.reports.services.regional_dashboard.leadership import build_region_leadership_module
from apps.reports.services.regional_dashboard.ministry import build_region_ministry_module
from apps.reports.services.regional_dashboard.overview import build_region_overview
from apps.reports.services.regional_dashboard.risk import build_region_risk_module
from apps.reports.services.regional_compliance_pdf import (
    build_regional_monthly_compliance_pdf,
)


def _resolve_year(request) -> int:
    raw_year = request.query_params.get("year")

    if raw_year is None:
        return timezone.localdate().year

    try:
        return int(raw_year)
    except (TypeError, ValueError):
        return timezone.localdate().year


def _int_or_none(value):
    if value in (None, ""):
        return None
    return int(value)


class RegionMetricsViewSet(ViewSet):

    def retrieve(self, request, pk=None):
        year = _resolve_year(request)
        month = request.query_params.get("month")
        month = int(month) if month else None

        region = get_object_or_404(Region, pk=pk)
        data = get_region_metrics(region, year, month)

        serializer = RegionMetricsSerializer(data)
        return Response(serializer.data)


class RegionViewSet(ViewSet):
    def _dashboard_context(self, pk, year):
        region = get_object_or_404(Region, pk=pk)
        assemblies_with_reports = get_region_reports(
            region=region,
            year=year,
        )
        return region, assemblies_with_reports

    def retrieve(self, request, pk=None):
        year = _resolve_year(request)
        region, assemblies_with_reports = self._dashboard_context(pk, year)

        data = build_region_dashboard(
            region,
            assemblies_with_reports,
            year=year,
        )

        return Response({
            "data": data,
            "table_schema": get_regional_dashboard_schema(request.user),
        })

    @action(detail=True, methods=["get"], url_path="overview")
    def overview(self, request, pk=None):
        year = _resolve_year(request)
        region, assemblies_with_reports = self._dashboard_context(pk, year)

        return Response(build_region_overview(
            region,
            assemblies_with_reports,
            year=year,
        ))

    @action(detail=True, methods=["get"], url_path="finance/aggregate")
    def finance_aggregate(self, request, pk=None):
        year = _resolve_year(request)
        region, assemblies_with_reports = self._dashboard_context(pk, year)

        return Response(build_region_finance_module(
            region,
            assemblies_with_reports,
            year=year,
            period=request.query_params.get("period"),
        ))

    @action(detail=True, methods=["get"], url_path="compliance/aggregate")
    def compliance_aggregate(self, request, pk=None):
        year = _resolve_year(request)
        region, assemblies_with_reports = self._dashboard_context(pk, year)

        return Response(build_region_compliance_module(
            region,
            assemblies_with_reports,
            year=year,
            period=request.query_params.get("period"),
        ))

    @action(detail=True, methods=["get"], url_path="risk/aggregate")
    def risk_aggregate(self, request, pk=None):
        year = _resolve_year(request)
        region, assemblies_with_reports = self._dashboard_context(pk, year)

        return Response(build_region_risk_module(
            region,
            assemblies_with_reports,
            year=year,
            period=request.query_params.get("period"),
        ))

    @action(detail=True, methods=["get"], url_path="growth/aggregate")
    def growth_aggregate(self, request, pk=None):
        year = _resolve_year(request)
        region, assemblies_with_reports = self._dashboard_context(pk, year)

        return Response(build_region_growth_module(
            region,
            assemblies_with_reports,
            year=year,
            period=request.query_params.get("period"),
        ))

    @action(detail=True, methods=["get"], url_path="ministry/aggregate")
    def ministry_aggregate(self, request, pk=None):
        year = _resolve_year(request)
        region, assemblies_with_reports = self._dashboard_context(pk, year)

        return Response(build_region_ministry_module(
            region,
            assemblies_with_reports,
            year=year,
            period=request.query_params.get("period"),
        ))

    @action(detail=True, methods=["get"], url_path="leadership/aggregate")
    def leadership_aggregate(self, request, pk=None):
        year = _resolve_year(request)
        region, assemblies_with_reports = self._dashboard_context(pk, year)

        return Response(build_region_leadership_module(
            region,
            assemblies_with_reports,
            year=year,
            period=request.query_params.get("period"),
        ))

    def _module_response(self, request, pk, domain):
        domain = (domain or "").lower()

        if domain not in DASHBOARD_DOMAINS:
            raise ValidationError({
                "domain": f"Unsupported dashboard domain '{domain}'."
            })

        year = _resolve_year(request)
        region, assemblies_with_reports = self._dashboard_context(pk, year)
        data = build_region_dashboard_module(
            region,
            assemblies_with_reports,
            domain,
            year=year,
        )

        return Response({
            "data": data,
            "table_schema": get_regional_module_schema(request.user, domain),
        })

    @action(
        detail=True,
        methods=["get"],
        url_path=r"(?P<domain>finance|growth|ministry|leadership|compliance|risk)",
    )
    def module(self, request, pk=None, domain=None):
        return self._module_response(request, pk, domain)

    @action(
        detail=True,
        methods=["get"],
        url_path=r"metrics/(?P<domain>finance|growth|ministry|leadership|compliance|risk)",
    )
    def metric_module(self, request, pk=None, domain=None):
        return self._module_response(request, pk, domain)

    @action(detail=True, methods=["get"], url_path="countries/(?P<country>[^/.]+)")
    def country(self, request, pk=None, country=None):
        year = _resolve_year(request)
        region = get_object_or_404(Region, pk=pk)
        assemblies = get_country_reports(
            region=region,
            country=country,
            year=year,
        )

        from apps.reports.services.metrics.country_dashboard_service import (
            build_country_dashboard,
        )

        return Response(build_country_dashboard(country, assemblies))

    @action(detail=True, methods=["get"], url_path="zones/(?P<zone_id>[^/.]+)/compliance")
    def zone_compliance(self, request, pk=None, zone_id=None):
        year = _resolve_year(request)
        zone = get_object_or_404(Zone, pk=zone_id)
        data = build_zone_compliance_timeline(zone, year)
        return Response(data)

    @action(detail=True, methods=["get"], url_path="compliance/scorecard")
    def compliance_scorecard(self, request, pk=None):
        year = _resolve_year(request)
        region, assemblies_with_reports = self._dashboard_context(pk, year)
        data = build_region_compliance_scorecard(
            region,
            assemblies_with_reports,
            year=year,
        )

        return Response({
            "data": data,
            "table_schema": get_regional_module_schema(request.user, "compliance"),
        })

    @action(detail=True, methods=["get"], url_path="compliance/audit-log")
    def compliance_audit_log(self, request, pk=None):
        year = _resolve_year(request)
        payload = build_audit_log_payload(
            region_id=int(pk),
            zone_id=_int_or_none(request.query_params.get("zone_id")),
            country=request.query_params.get("country"),
            assembly_id=_int_or_none(request.query_params.get("assembly_id")),
            reason=request.query_params.get("reason"),
            follow_up_status=request.query_params.get("follow_up_status"),
            year=year,
        )

        return Response({
            "data": payload,
            "table_schema": get_regional_audit_log_schema(request.user),
        })

    @action(detail=True, methods=["get"], url_path="compliance/monthly-report.pdf")
    def monthly_compliance_report_pdf(self, request, pk=None):
        region = get_object_or_404(Region, pk=pk)
        result = build_regional_monthly_compliance_pdf(
            region=region,
            user=request.user,
            query_params=request.query_params,
        )
        response = FileResponse(
            result.buffer,
            as_attachment=True,
            filename=result.filename,
            content_type="application/pdf",
        )
        response["Cache-Control"] = "no-store"
        return response
