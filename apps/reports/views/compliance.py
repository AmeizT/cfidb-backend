from datetime import datetime
from django.http import FileResponse
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.reports.models.compliance import AssemblyCompliance, ZoneCompliance
from rest_framework import viewsets
from apps.reports.models.compliance import AssemblyCompliance, ZoneCompliance
from apps.reports.permissions import IsDbStaff
from apps.reports.serializers import (
    AssemblyComplianceSerializer,
    ZoneComplianceSerializer
)
from apps.reports.services import generate_zone_report_pdf

class ComplianceDashboardView(APIView):
    permission_classes = [IsDbStaff]  

    def get(self, request):
        now = datetime.now()
        try:
            year = int(request.query_params.get("year", now.year))
            month = int(request.query_params.get("month", now.month))
        except ValueError:
            return Response({"error": "Invalid year or month"}, status=400)

        # Start with all assemblies for the month/year
        assembly_qs = AssemblyCompliance.objects.filter(year=year, month=month)

        user = request.user
        if not (user.is_superuser or getattr(user, "is_db_staff", False)):
            if getattr(user, "is_db_zone_staff", False):
                zones = user.assigned_zones.all()
                assembly_qs = assembly_qs.filter(assembly__zone__in=zones)
            elif hasattr(user, "assembly") and user.assembly:
                assembly_qs = assembly_qs.filter(assembly=user.assembly)

        total = assembly_qs.count()
        compliant = assembly_qs.filter(status="COMPLIANT").count()
        non_compliant = total - compliant

        # Zones
        zone_qs = ZoneCompliance.objects.filter(year=year, month=month)
        if not (user.is_superuser or getattr(user, "is_db_staff", False)):
            if getattr(user, "is_db_zone_staff", False):
                zone_qs = zone_qs.filter(zone__in=user.assigned_zones.all())
            elif hasattr(user, "assembly") and user.assembly:
                zone_qs = zone_qs.filter(zone=user.assembly.zone)

        return Response({
            "summary": {
                "total_assemblies": total,
                "compliant": compliant,
                "non_compliant": non_compliant,
                "compliance_rate": (compliant / total * 100) if total else 0
            },
            "zones": zone_qs.values("zone_id", "zone__name", "compliance_rate"),
            "non_compliant_assemblies": assembly_qs.exclude(status="COMPLIANT").values(
                "assembly__name", "zone__name", "status"
            )
        })
    

class AssemblyComplianceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AssemblyComplianceSerializer

    def get_queryset(self): # type: ignore
        user = self.request.user
        queryset = AssemblyCompliance.objects.select_related("assembly", "zone")

        # Superusers / DB staff
        if user.is_superuser or getattr(user, "is_db_staff", False):
            return queryset

        # Zone staff
        if getattr(user, "is_db_zone_staff", False):
            return queryset.filter(
                assembly__zone__in=user.assigned_zones.all() # type: ignore
            )

        # Multi-assembly managers
        if user.assemblies.exists(): # type: ignore
            return queryset.filter(
                assembly__in=user.assemblies.all() # type: ignore
            )

        # Single primary assembly
        if user.assembly: # type: ignore
            return queryset.filter(
                assembly=user.assembly # type: ignore
            )

        return queryset.none()


class ZoneComplianceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ZoneComplianceSerializer

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        zone_compliance = self.get_object()
        zone = zone_compliance.zone

        year = request.query_params.get("year", zone_compliance.year)
        month = request.query_params.get("month", zone_compliance.month)

        pdf_buffer = generate_zone_report_pdf(zone, int(year), int(month))

        filename = (
            f"zone_compliance_{zone.name.replace(' ', '_')}_"
            f"{year}_{str(month).zfill(2)}.pdf"
        )

        return FileResponse(
            pdf_buffer,
            as_attachment=True,
            filename=filename,
        )

    def get_queryset(self): # type: ignore
        user = self.request.user

        if user.is_superuser or getattr(user, "is_db_staff", False):
            # DB staff and superusers see all zones
            return ZoneCompliance.objects.select_related("zone")

        if getattr(user, "is_db_zone_staff", False):
            zones = user.assigned_zones # type: ignore
            return ZoneCompliance.objects.select_related("zone").filter(zone__in=zones)

        # No access
        return ZoneCompliance.objects.none()
    



