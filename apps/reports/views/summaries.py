from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.churches.models import Church
from apps.reports.services.summaries.access import executive_regions, summary_assemblies, can_view_executive_summary
from apps.reports.services.summaries.filters import regional_scope
from apps.reports.services.summaries.composition import build_summary, contributors, parse_period


def assembly_context(request):
    raw = request.query_params.get("assembly") or request.user.church_id
    if not raw:
        first = summary_assemblies(request.user).order_by("name").first()
        if first is None:
            raise PermissionDenied("No authorized assemblies are available.")
        return first
    try:
        pk = int(raw)
    except (ValueError, TypeError):
        raise ValidationError({"assembly": "Use an assembly ID."})
    # A missing/out-of-scope ID gets the same response and cannot disclose names.
    return get_object_or_404(summary_assemblies(request.user), pk=pk)


class RegionalSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not can_view_executive_summary(request.user):
            raise PermissionDenied("Executive Summary requires a regional admin, overseer or superuser.")
        start, end = parse_period(request.query_params.get("period"))
        available = executive_regions(request.user)
        regions = list(available.values("id", "name"))
        selected = request.query_params.get("region")
        if selected:
            try:
                selected_id = int(selected)
            except ValueError:
                raise ValidationError({"region": "Use a region ID."})
            if selected_id not in [r["id"] for r in regions]:
                raise PermissionDenied("You do not have access to this region.")
            available = available.filter(pk=selected_id)
        names = list(available.values_list("name", flat=True))
        assemblies, filters = regional_scope(
            Church.objects.filter(zone__region__in=available), request.query_params, request.user)
        data = build_summary(assemblies, start, end,
            regional=True, name=" · ".join(names) or "No assigned regions", regions=regions)
        data["filters"] = filters
        return Response(data)


class AssemblySummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        assembly = assembly_context(request)
        start, end = parse_period(request.query_params.get("period"))
        data = build_summary(Church.objects.filter(pk=assembly.pk), start, end, name=assembly.name)
        data["available_assemblies"] = list(summary_assemblies(request.user).order_by("name").values("id", "name"))
        return Response(data)


class SummaryContributorsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        assembly = assembly_context(request)
        start, end = parse_period(request.query_params.get("period"))
        return Response({"assembly": assembly.name, "period": start.strftime("%Y-%m"),
            "currency": assembly.currency or None, "contributors": contributors([assembly.id], start, end)[assembly.id]})
