from rest_framework.decorators import action
from rest_framework.response import Response
from apps.reports.services.overview_analytics import OverviewAnalyticsService
from apps.reports.services.highlight_engine import HighlightEngine
from apps.reports.utils.date_ranges import resolve_date_range


class OverviewAnalyticsMixin:
    @action(detail=True, methods=["get"])
    def overview(self, request, pk=None):
        report = self.get_object()  # type: ignore
        start_date, end_date = resolve_date_range(request)

        service = OverviewAnalyticsService(
            assembly=report.assembly,
            start_date=start_date,
            end_date=end_date,
        )

        engine = HighlightEngine(
            assembly=report.assembly,
            start_date=start_date,
            end_date=end_date,
        )

        data = service.generate()
        data["highlights"] = engine.generate()

        return Response(data)