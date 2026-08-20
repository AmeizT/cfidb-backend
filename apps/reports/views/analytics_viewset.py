from rest_framework.views import APIView
from rest_framework.response import Response

from apps.reports.services.analytics.compliance.assembly_metrics import get_assembly_metrics
from apps.reports.services.analytics.compliance.zone_metrics import get_zone_metrics
from apps.reports.services.analytics.compliance.region_metrics import get_region_metrics


class AssemblyAnalyticsView(APIView):
    def get(self, request, assembly_id):
        # placeholder: plug real aggregation later
        metrics = request.data.get("metrics", {})
        history = request.data.get("history", [])

        return Response(get_assembly_metrics(
            assembly=request.user,
            section_stats=metrics,
            historical_scores=history
        ))