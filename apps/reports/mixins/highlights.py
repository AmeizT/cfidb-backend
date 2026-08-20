from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import timedelta
from django.utils.dateparse import parse_date
from apps.reports.services.highlight_engine import HighlightEngine
from datetime import date
from django.utils.timezone import now


class HighlightsMixin:
    @action(detail=True, methods=["get"])
    def highlights(self, request, pk=None):
        report = self.get_object() # type: ignore

        today = now().date()

        range_param = request.query_params.get("range")
        start = request.query_params.get("start")
        end = request.query_params.get("end")

        # 1. Custom explicit range (highest priority)
        if start and end:
            start_date = parse_date(start)
            end_date = parse_date(end)


        elif range_param:
            if range_param == "7d":
                start_date = today - timedelta(days=7)
                end_date = today

            elif range_param == "1m":
                start_date = today.replace(day=1)
                end_date = today

            elif range_param == "2m":
                month = max(today.month - 2, 1)
                start_date = today.replace(month=month, day=1)
                end_date = today

            elif range_param == "3m":
                month = max(today.month - 3, 1)
                start_date = today.replace(month=month, day=1)
                end_date = today

            elif range_param == "1y":
                start_date = today.replace(month=1, day=1)
                end_date = today

            else:
                start_date = today.replace(day=1)
                end_date = today

        # 3. Default fallback
        else:
            start_date = today.replace(day=1)
            end_date = today

        engine = HighlightEngine(
            assembly=report.assembly,
            start_date=start_date,
            end_date=end_date,
        )

        return Response({
            "highlights": engine.generate()
        })