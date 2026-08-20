from rest_framework.viewsets import ViewSet
from rest_framework.response import Response

from apps.churches.models import Zone
from apps.reports.services.metrics.zone_metrics import get_zone_metrics
from apps.reports.serializers.zone import ZoneMetricsSerializer


class ZoneMetricsViewSet(ViewSet):

    def retrieve(self, request, pk=None):
        year = int(request.query_params.get("year"))
        month = request.query_params.get("month")
        month = int(month) if month else None
        zone = Zone.objects.get(pk=pk)

        data = get_zone_metrics(zone, year, month)

        serializer = ZoneMetricsSerializer(data)
        return Response(serializer.data)