from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from apps.reports.models import UnifiedReport
from apps.reports.serializers import UnifiedReportSerializer
from apps.churches.models import Church


class UnifiedReportViewSet(viewsets.ModelViewSet):
    serializer_class = UnifiedReportSerializer

    def get_queryset(self):
        user = self.request.user

        # Return all reports regardless of finalized status
        queryset = UnifiedReport.objects.all()

        # Admins or DB staff see all reports (no restriction)
        if not (user.is_admin or user.is_db_staff):
            # DB Zone staff see reports only for churches in their zones
            if user.is_db_zone_staff:
                zone_ids = user.zones_as_admin.values_list("id", flat=True)
                churches_in_zones = Church.objects.filter(zone__in=zone_ids)
                queryset = queryset.filter(church__in=churches_in_zones)

            # Other users (pastors, secretaries, etc.) only see their assigned churches
            elif user.church or user.assemblies.exists():
                allowed_churches = Church.objects.filter(
                    id__in=[user.church_id] if user.church else []
                ) | user.assemblies.all()
                queryset = queryset.filter(church__in=allowed_churches)

        # Optional filtering by year/month
        year = self.request.query_params.get("year")
        month = self.request.query_params.get("month")
        try:
            if year and month:
                year = int(year)
                month = int(month)
                queryset = queryset.filter(
                    period_start__year=year,
                    period_start__month=month
                )
            elif year:
                year = int(year)
                queryset = queryset.filter(period_start__year=year)
            elif month:
                month = int(month)
                queryset = queryset.filter(period_start__month=month)
        except ValueError:
            pass 

        return queryset.order_by("period_start")

    @action(detail=True, methods=["post"])
    def finalize(self, request, pk=None):
        report = self.get_object()
        try:
            report.finalize()
            return Response({"status": "finalized"}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"errors": e.args[0]}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        report = self.get_object()
        report.reopen()
        return Response({"status": "reopened"}, status=status.HTTP_200_OK)